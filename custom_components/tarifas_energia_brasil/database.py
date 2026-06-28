"""Módulo para gerenciar a interação com o banco de dados SQLite via SQLAlchemy."""
import logging
from datetime import date, datetime
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, Concessionaria, HistoricoTarifa

_LOGGER = logging.getLogger(__name__)

_NEW_COLUMNS = [
    ("tarifa_base_te", "REAL"),
    ("tarifa_base_tusd", "REAL"),
    ("dat_inicio_vigencia", "TEXT"),
    ("dat_fim_vigencia", "TEXT"),
    ("dat_competencia_bandeira", "TEXT"),
    ("valor_adicional_bandeira", "REAL"),
]


class DatabaseManager:
    """Gerencia a conexão e operações com o banco de dados."""

    def __init__(self, hass, db_path):
        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url, echo=False)
        self.session_factory = sessionmaker(
            self.engine, expire_on_commit=False, class_=Session
        )
        self.hass = hass

    async def async_setup_database(self):
        """Cria as tabelas e aplica migrações incrementais."""
        Base.metadata.create_all(self.engine)
        self._migrate_database()
        _LOGGER.info("Banco de dados verificado/criado com sucesso.")

    def _migrate_database(self):
        """Aplica migrações incrementais no schema existente."""
        with self.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(historico_tarifas)"))
            colunas = {row[1] for row in result}

            # Migração legada: dat_competencia
            if "dat_competencia" not in colunas:
                conn.execute(text("ALTER TABLE historico_tarifas ADD COLUMN dat_competencia DATE"))
                conn.commit()
                _LOGGER.info("Migração: coluna 'dat_competencia' adicionada.")

            # Novas colunas da v1.2 (API Cloudflare)
            for col_name, col_type in _NEW_COLUMNS:
                if col_name not in colunas:
                    conn.execute(text(f"ALTER TABLE historico_tarifas ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    _LOGGER.info("Migração: coluna '%s' adicionada.", col_name)

    async def async_save_tarifa_snapshot(
        self,
        concessionaria_nome: str,
        bandeira_vigente: str,
        tarifa_vigente: float,
        dat_competencia: date,
        api_status: str = "online",
        tarifa_base_te: float | None = None,
        tarifa_base_tusd: float | None = None,
        dat_inicio_vigencia: str | None = None,
        dat_fim_vigencia: str | None = None,
        dat_competencia_bandeira: str | None = None,
        valor_adicional_bandeira: float | None = None,
    ) -> dict:
        """Insere no histórico apenas se dat_competencia for mais recente que o último registro."""
        with self.session_factory() as session:
            stmt = select(Concessionaria).where(Concessionaria.nome == concessionaria_nome)
            concessionaria = session.execute(stmt).scalar_one_or_none()

            if not concessionaria:
                concessionaria = Concessionaria(nome=concessionaria_nome)
                session.add(concessionaria)
                session.flush()

            latest_stmt = (
                select(HistoricoTarifa.dat_competencia)
                .where(HistoricoTarifa.concessionaria_id == concessionaria.id)
                .order_by(HistoricoTarifa.dat_competencia.desc())
                .limit(1)
            )
            ultima_competencia = session.execute(latest_stmt).scalar_one_or_none()

            if ultima_competencia is not None and dat_competencia <= ultima_competencia:
                _LOGGER.info(
                    "Histórico não atualizado: competência %s já registrada para %s.",
                    dat_competencia,
                    concessionaria_nome,
                )
                existing_stmt = (
                    select(HistoricoTarifa)
                    .where(HistoricoTarifa.concessionaria_id == concessionaria.id)
                    .order_by(HistoricoTarifa.dat_competencia.desc())
                    .limit(1)
                )
                snapshot = session.execute(existing_stmt).scalar_one()
            else:
                snapshot = HistoricoTarifa(
                    concessionaria_id=concessionaria.id,
                    bandeira_vigente=bandeira_vigente,
                    tarifa_vigente=tarifa_vigente,
                    dat_competencia=dat_competencia,
                    api_status=api_status,
                    timestamp=datetime.now(),
                    tarifa_base_te=tarifa_base_te,
                    tarifa_base_tusd=tarifa_base_tusd,
                    dat_inicio_vigencia=dat_inicio_vigencia,
                    dat_fim_vigencia=dat_fim_vigencia,
                    dat_competencia_bandeira=dat_competencia_bandeira,
                    valor_adicional_bandeira=valor_adicional_bandeira,
                )
                session.add(snapshot)
                session.commit()
                _LOGGER.info(
                    "Novo registro inserido no histórico para %s (competência: %s).",
                    concessionaria_nome,
                    dat_competencia,
                )

            return self._snapshot_to_dict(snapshot)

    async def async_get_latest_tarifa_snapshot(self, concessionaria_nome: str) -> dict | None:
        """Retorna a leitura de tarifa mais recente para uma concessionária."""
        with self.session_factory() as session:
            stmt = (
                select(HistoricoTarifa)
                .join(Concessionaria, HistoricoTarifa.concessionaria_id == Concessionaria.id)
                .where(Concessionaria.nome == concessionaria_nome)
                .order_by(HistoricoTarifa.timestamp.desc())
                .limit(1)
            )
            snapshot = session.execute(stmt).scalar_one_or_none()
            return self._snapshot_to_dict(snapshot) if snapshot else None

    def _snapshot_to_dict(self, snapshot: HistoricoTarifa) -> dict:
        return {
            "bandeira_vigente": snapshot.bandeira_vigente,
            "tarifa_vigente": snapshot.tarifa_vigente,
            "dat_competencia": snapshot.dat_competencia.isoformat() if snapshot.dat_competencia else None,
            "api_status": snapshot.api_status,
            "timestamp": snapshot.timestamp.isoformat(),
            "tarifa_base_te": snapshot.tarifa_base_te,
            "tarifa_base_tusd": snapshot.tarifa_base_tusd,
            "dat_inicio_vigencia": snapshot.dat_inicio_vigencia,
            "dat_fim_vigencia": snapshot.dat_fim_vigencia,
            "dat_competencia_bandeira": snapshot.dat_competencia_bandeira,
            "valor_adicional_bandeira": snapshot.valor_adicional_bandeira,
        }
