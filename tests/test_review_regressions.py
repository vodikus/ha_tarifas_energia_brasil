"""Regressões da revisão: cache legado e republicação na virada local, sem rede."""

from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from test_polling_and_status import API_PATH, WORKER_RESPONSE, _coordinator, _entry
from custom_components.tarifas_energia_brasil.const import CONF_POLLING_MODE


@pytest.mark.parametrize(
    "price", [0, -1, float("nan"), float("inf"), None, True, "0.75"]
)
async def test_rejects_invalid_legacy_cache_after_api_failure(hass, price):
    entry = _entry(hass)
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    coord = _coordinator(hass, entry)
    last_success = coord.last_success
    legacy = {
        "tarifa_vigente": price,
        "bandeira_vigente": "Verde",
        "timestamp": "2026-11-26T10:00:00",
    }
    with (
        patch(API_PATH, AsyncMock(side_effect=TimeoutError())),
        patch.object(
            coord.db, "async_get_latest_tarifa_snapshot", AsyncMock(return_value=legacy)
        ),
    ):
        await coord.async_refresh()
        await hass.async_block_till_done()
    assert coord.last_update_success is False
    assert coord.last_success == last_success
    assert (
        hass.states.get("sensor.tarifas_celesc_tarifa_vigente").state == "unavailable"
    )
    assert (
        hass.states.get("sensor.tarifas_celesc_status_da_atualizacao").state
        == "sem_dados"
    )


async def test_accepts_positive_legacy_price_with_missing_metadata(hass):
    entry = _entry(hass)
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    coord = _coordinator(hass, entry)
    legacy = {
        "tarifa_vigente": 0.75,
        "bandeira_vigente": "Verde",
        "timestamp": "2026-11-26T10:00:00",
    }
    with (
        patch(API_PATH, AsyncMock(side_effect=TimeoutError())),
        patch.object(
            coord.db, "async_get_latest_tarifa_snapshot", AsyncMock(return_value=legacy)
        ),
    ):
        await coord.async_refresh()
        await hass.async_block_till_done()
    assert coord.last_update_success is True
    assert hass.states.get("sensor.tarifas_celesc_tarifa_vigente").state == "0.75"
    assert (
        hass.states.get("sensor.tarifas_celesc_status_da_atualizacao").state == "cache"
    )
    assert (
        hass.states.get("sensor.tarifas_celesc_atualidade_dos_dados").state
        == "dados_incompletos"
    )


@pytest.mark.parametrize(
    ("end", "initial_start", "flag", "before", "after", "expired"),
    [
        (
            "2027-08-21",
            "2026-08-22",
            "2026-11-01",
            "atual",
            "bandeira_desatualizada",
            False,
        ),
        ("2026-11-30", "2026-08-22", "2026-11-01", "atual", "tarifa_expirada", True),
        ("2027-08-21", "2026-12-01", "2026-12-01", "tarifa_futura", "atual", False),
    ],
)
async def test_midnight_republishes_content_without_fetch(
    hass, freezer, end, initial_start, flag, before, after, expired
):
    tz = ZoneInfo("America/Sao_Paulo")
    hass.config.time_zone = "America/Sao_Paulo"
    dt_util.set_default_time_zone(tz)
    freezer.move_to(datetime(2026, 11, 30, 23, 59, tzinfo=tz))
    response = deepcopy(WORKER_RESPONSE)
    response["tarifa"]["dat_fim_vigencia"] = end
    response["tarifa"]["dat_inicio_vigencia"] = initial_start
    response["bandeira_tarifaria"]["data_competencia"] = flag
    entry = _entry(hass, {CONF_POLLING_MODE: "weekly"})
    fetch = AsyncMock(return_value=response)
    with patch(API_PATH, fetch):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        coord = _coordinator(hass, entry)
        last_success = coord.last_success
        count = fetch.await_count
        assert (
            hass.states.get("sensor.tarifas_celesc_atualidade_dos_dados").state
            == before
        )
        freezer.tick(timedelta(minutes=2))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
        assert fetch.await_count == count
        assert coord.last_success == last_success
        assert (
            hass.states.get("sensor.tarifas_celesc_atualidade_dos_dados").state == after
        )
        status = hass.states.get("sensor.tarifas_celesc_status_da_atualizacao")
        assert status.state == "online"
        assert status.attributes["vigencia_expirada"] is expired


async def test_midnight_listener_removed_on_entry_unload(hass, freezer):
    entry = _entry(hass, {CONF_POLLING_MODE: "weekly"})
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    component = hass.data["sensor"]
    entities = [
        component.get_entity("sensor.tarifas_celesc_atualidade_dos_dados"),
        component.get_entity("sensor.tarifas_celesc_status_da_atualizacao"),
    ]
    assert all(entities)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    with (
        patch.object(entities[0], "async_write_ha_state") as write_content,
        patch.object(entities[1], "async_write_ha_state") as write_status,
    ):
        freezer.tick(timedelta(days=1, minutes=2))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
        write_content.assert_not_called()
        write_status.assert_not_called()
