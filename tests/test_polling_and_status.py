"""Testes de polling configurável, status de diagnóstico e unique IDs (HA real, API simulada)."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNKNOWN
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tarifas_energia_brasil.const import (
    CONF_CONCESSIONARIA,
    CONF_POLLING_MODE,
    DOMAIN,
)

API_PATH = "custom_components.tarifas_energia_brasil.cloudflare_api.CloudflareAPI.async_fetch_tarifas"

WORKER_RESPONSE = {
    "concessionaria": {"nome": "CELESC"},
    "bandeira_tarifaria": {
        "data_competencia": "2026-11-01",
        "nome_bandeira": "Verde",
        "valor_adicional": 0,
    },
    "tarifa": {
        "bandeira_vigente": "Verde",
        "tarifa_base_te": 0.34571,
        "tarifa_base_tusd": 0.41404,
        "tarifa_vigente": 0.75975,
        "dat_inicio_vigencia": "2026-08-22",
        "dat_fim_vigencia": "2027-08-21",
        "timestamp": "2026-11-26T10:00:12",
    },
}

EXPECTED_UNIQUE_SUFFIXES = {
    "tarifa_vigente",
    "bandeira_vigente",
    "dat_competencia_bandeira",
    "dat_inicio_vigencia",
    "dat_fim_vigencia",
    "ultima_atualizacao",
    "status_atualizacao",
    "ultima_consulta",
    "ultima_consulta_sucesso",
    "atualidade_dados",
    "atualizar_tarifas",
}


def _entry(hass, options=None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="CELESC",
        data={CONF_CONCESSIONARIA: "CELESC"},
        options=options or {},
    )
    entry.add_to_hass(hass)
    return entry


def _coordinator(hass, entry):
    return hass.data[DOMAIN][entry.entry_id]


async def test_default_automatic_mode_keeps_previous_interval(hass):
    """Entradas sem opção mantêm o comportamento anterior (intervalo automático)."""
    entry = _entry(hass)
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coord = _coordinator(hass, entry)
    assert coord.polling_mode == "automatic"
    # dat_fim_vigencia (2027-08-21) é futura: automático usa 1 semana.
    assert coord.update_interval == timedelta(weeks=1)
    assert coord.last_success is not None
    assert coord.last_success.tzinfo is not None
    assert coord.last_attempt is not None


@pytest.mark.parametrize(
    ("mode", "days"), [("daily", 1), ("every_2_days", 2), ("weekly", 7)]
)
async def test_fixed_mode_applied_after_success(hass, mode, days):
    entry = _entry(hass, options={CONF_POLLING_MODE: mode})
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert _coordinator(hass, entry).update_interval == timedelta(days=days)


async def test_fixed_mode_applied_on_first_setup_even_if_fails(hass):
    """Falha inicial no modo semanal: o coordinator já nasce com intervalo de 7 dias."""
    from custom_components.tarifas_energia_brasil.coordinator import (
        TarifasEnergiaCoordinator,
    )
    from custom_components.tarifas_energia_brasil.cloudflare_api import CloudflareAPI
    from custom_components.tarifas_energia_brasil.database import DatabaseManager

    entry = _entry(hass, options={CONF_POLLING_MODE: "weekly"})
    with patch(API_PATH, AsyncMock(side_effect=RuntimeError("offline"))):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY

    coord = TarifasEnergiaCoordinator(
        hass,
        CloudflareAPI(hass, None),
        DatabaseManager(hass, hass.config.path(f"{DOMAIN}_probe.sqlite")),
        "CELESC",
        "weekly",
    )
    assert coord.update_interval == timedelta(days=7)


async def test_fallback_to_cache_marks_cache_and_keeps_last_success_empty(hass):
    entry = _entry(hass, options={CONF_POLLING_MODE: "daily"})
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    coord = _coordinator(hass, entry)
    first_success = coord.last_success
    assert first_success is not None

    with patch(API_PATH, AsyncMock(side_effect=RuntimeError("down"))):
        await coord.async_refresh()
    await hass.async_block_till_done()

    assert coord.data["data_status"] == "cache"
    assert coord.data["last_success"] is None
    assert coord.last_error == "RuntimeError"
    assert coord.last_update_success is True  # cache é fallback bem-sucedido
    assert coord.update_interval == timedelta(days=1)  # modo fixo continua valendo
    assert hass.states.get("sensor.tarifas_celesc_status_da_atualizacao") is not None
    status = hass.states.get("sensor.tarifas_celesc_status_da_atualizacao")
    assert status.state == "cache"
    assert hass.states.get("sensor.tarifas_celesc_tarifa_vigente").state == "0.75975"


async def test_failed_refresh_without_cache_reports_sem_dados(hass):
    """Sem dado válido, o status vira sem_dados e a tarifa nunca mostra um valor antigo como atual."""
    entry = _entry(hass)
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    coord = _coordinator(hass, entry)

    with (
        patch(API_PATH, AsyncMock(side_effect=RuntimeError("down"))),
        patch.object(
            coord.db,
            "async_get_latest_tarifa_snapshot",
            AsyncMock(return_value=None),
        ),
    ):
        await coord.async_refresh()
    await hass.async_block_till_done()

    assert coord.last_update_success is False
    status = hass.states.get("sensor.tarifas_celesc_status_da_atualizacao")
    assert status.state == "sem_dados"
    assert status.attributes["ultima_consulta_erro"] == "RuntimeError"
    # Tarifa segue indisponível (UpdateFailed), não um valor "online" atual.
    assert (
        hass.states.get("sensor.tarifas_celesc_tarifa_vigente").state == "unavailable"
    )


async def test_status_online_and_timestamps(hass):
    entry = _entry(hass)
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    status = hass.states.get("sensor.tarifas_celesc_status_da_atualizacao")
    assert status.state == "online"
    assert status.attributes["vigencia_expirada"] is False
    # Fonte da API é texto cru (sem offset comprovado), não é reinterpretada como fuso.
    assert (
        hass.states.get("sensor.tarifas_celesc_ultima_atualizacao").state
        == "2026-11-26T10:00:12"
    )
    last_success = hass.states.get("sensor.tarifas_celesc_ultima_consulta_com_sucesso")
    assert last_success is not None
    assert last_success.state not in (STATE_UNKNOWN, "unavailable")


async def test_unique_ids_unchanged_and_tariff_has_no_monetary_class(hass):
    entry = _entry(hass)
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    unique_ids = {
        e.unique_id.removeprefix(f"{entry.entry_id}_")
        for e in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    assert unique_ids == EXPECTED_UNIQUE_SUFFIXES

    tarifa = hass.states.get("sensor.tarifas_celesc_tarifa_vigente")
    assert tarifa.attributes.get("device_class") is None
    assert tarifa.attributes["unit_of_measurement"] == "R$/kWh"


async def test_options_change_reloads_once_and_updates_interval(hass, freezer):
    entry = _entry(hass)
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        old = _coordinator(hass, entry)

        flow = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            flow["flow_id"], {CONF_POLLING_MODE: "weekly"}
        )
        await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert entry.options[CONF_POLLING_MODE] == "weekly"
    new = _coordinator(hass, entry)
    assert new is not old
    assert new.update_interval == timedelta(days=7)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.entry_id in hass.data[DOMAIN]
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    fetch = AsyncMock(return_value=WORKER_RESPONSE)
    with patch(API_PATH, fetch):
        freezer.tick(timedelta(days=7, seconds=2))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
    # O timer do coordenador antigo foi removido na recarga.
    assert fetch.await_count == 1
    assert entry.options[CONF_POLLING_MODE] == "weekly"


async def test_options_form_shows_four_modes(hass):
    entry = _entry(hass)
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    assert flow["type"] == "form"
    options = flow["data_schema"].schema
    selector = next(
        v
        for k, v in options.items()
        if k == CONF_POLLING_MODE or getattr(k, "schema", None) == CONF_POLLING_MODE
    )
    assert set(selector.config["options"]) == {
        "automatic",
        "daily",
        "every_2_days",
        "weekly",
    }
    await hass.config_entries.options.async_configure(
        flow["flow_id"], {CONF_POLLING_MODE: "daily"}
    )


async def test_manual_refresh_still_uses_nocache(hass):
    entry = _entry(hass, options={CONF_POLLING_MODE: "daily"})
    mock_fetch = AsyncMock(return_value=WORKER_RESPONSE)
    with patch(API_PATH, mock_fetch):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await _coordinator(hass, entry).async_force_refresh_nocache()
    assert mock_fetch.await_args_list[-1].kwargs == {"nocache": True}


@pytest.mark.parametrize(
    "price", [None, 0, -1, float("nan"), float("inf"), True, "0.75"]
)
async def test_invalid_price_never_overwrites_cache(hass, price):
    from copy import deepcopy

    entry = _entry(hass)
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    coord = _coordinator(hass, entry)
    first = coord.last_success
    bad = deepcopy(WORKER_RESPONSE)
    bad["tarifa"]["tarifa_vigente"] = price
    with patch(API_PATH, AsyncMock(return_value=bad)):
        await coord.async_refresh()
        await hass.async_block_till_done()
    assert coord.data["data_status"] == "cache"
    assert coord.last_success == first
    assert coord.data["tarifa_vigente"] == WORKER_RESPONSE["tarifa"]["tarifa_vigente"]


async def test_equal_price_advances_success_and_recovers(hass, freezer):
    entry = _entry(hass, {CONF_POLLING_MODE: "daily"})
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    coord = _coordinator(hass, entry)
    first = coord.last_success
    freezer.tick(timedelta(seconds=60))
    with patch(API_PATH, AsyncMock(side_effect=TimeoutError())):
        await coord.async_refresh()
    assert coord.last_success == first
    assert coord.data["data_status"] == "cache"
    freezer.tick(timedelta(seconds=60))
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        await coord.async_refresh()
        await hass.async_block_till_done()
    assert coord.last_success > first
    assert coord.last_error is None
    assert coord.data["data_status"] == "online"


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"end": "2026-11-25"}, "tarifa_expirada"),
        ({"start": "2026-11-27"}, "tarifa_futura"),
        ({"flag": "2026-10-01"}, "bandeira_desatualizada"),
        ({"flag": "2026-12-01"}, "bandeira_desatualizada"),
        ({"flag": None}, "dados_incompletos"),
        ({}, "atual"),
    ],
)
async def test_content_status_is_independent_from_online(hass, changes, expected):
    from copy import deepcopy

    response = deepcopy(WORKER_RESPONSE)
    if "end" in changes:
        response["tarifa"]["dat_fim_vigencia"] = changes["end"]
    if "start" in changes:
        response["tarifa"]["dat_inicio_vigencia"] = changes["start"]
    if "flag" in changes:
        response["bandeira_tarifaria"]["data_competencia"] = changes["flag"]
    entry = _entry(hass)
    with patch(API_PATH, AsyncMock(return_value=response)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert (
        hass.states.get("sensor.tarifas_celesc_status_da_atualizacao").state == "online"
    )
    assert (
        hass.states.get("sensor.tarifas_celesc_atualidade_dos_dados").state == expected
    )


async def test_month_boundary_does_not_accept_previous_or_future_flag(hass, freezer):
    from copy import deepcopy
    from zoneinfo import ZoneInfo
    from datetime import datetime

    hass.config.time_zone = "America/Sao_Paulo"
    dt_util.set_default_time_zone(ZoneInfo("America/Sao_Paulo"))
    freezer.move_to(
        datetime(2026, 11, 30, 23, 59, tzinfo=ZoneInfo("America/Sao_Paulo"))
    )
    entry = _entry(hass)
    with patch(API_PATH, AsyncMock(return_value=WORKER_RESPONSE)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert (
            hass.states.get("sensor.tarifas_celesc_atualidade_dos_dados").state
            == "atual"
        )
        freezer.tick(timedelta(minutes=2))
        await _coordinator(hass, entry).async_refresh()
        await hass.async_block_till_done()
        assert (
            hass.states.get("sensor.tarifas_celesc_atualidade_dos_dados").state
            == "bandeira_desatualizada"
        )
    updated = deepcopy(WORKER_RESPONSE)
    updated["bandeira_tarifaria"]["data_competencia"] = "2026-12-01"
    with patch(API_PATH, AsyncMock(return_value=updated)):
        await _coordinator(hass, entry).async_refresh()
        await hass.async_block_till_done()
    assert (
        hass.states.get("sensor.tarifas_celesc_atualidade_dos_dados").state == "atual"
    )
    # Falha depois da virada: o cache precisa ser o de dezembro, não o antigo anual.
    with patch(API_PATH, AsyncMock(side_effect=TimeoutError())):
        await _coordinator(hass, entry).async_refresh()
        await hass.async_block_till_done()
    assert (
        hass.states.get("sensor.tarifas_celesc_status_da_atualizacao").state == "cache"
    )
    assert (
        hass.states.get("sensor.tarifas_celesc_atualidade_dos_dados").state == "atual"
    )
    assert (
        hass.states.get("sensor.tarifas_celesc_data_competencia_bandeira").state
        == "2026-12-01"
    )


async def test_two_scheduled_daily_cycles_without_manual_refresh(hass, freezer):
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    entry = _entry(hass, {CONF_POLLING_MODE: "daily"})
    fetch = AsyncMock(return_value=WORKER_RESPONSE)
    with patch(API_PATH, fetch):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        first = _coordinator(hass, entry).last_success
        initial_count = fetch.await_count
        for index in range(2):
            freezer.tick(timedelta(days=1, seconds=2))
            async_fire_time_changed(hass, dt_util.utcnow())
            await hass.async_block_till_done()
            assert fetch.await_count == initial_count + index + 1
            assert fetch.await_args_list[-1].kwargs == {"nocache": False}
        assert _coordinator(hass, entry).last_success > first
