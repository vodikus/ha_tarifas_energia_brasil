"""Módulo para gerenciar a interação com o banco de dados SQLite via SQLAlchemy."""

from datetime import date, datetime
import logging

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from .models import BandeiraTarifaria, Base, Concessionaria, HistoricoTarifa, StorageDadosLocal

_LOGGER = logging.getLogger(__name__)


class DatabaseManager:
    """Gerencia a conexão e operações com o banco de dados."""

    def __init__(self, hass, db_path):
        """Inicializa o gerenciador do banco de dados."""
        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url, echo=False)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False, class_=Session)
        self.hass = hass

    async def async_setup_database(self):
        """Cria as tabelas no banco de dados se não existirem e aplica migrações necessárias."""
        Base.metadata.create_all(self.engine)
        self._migrate_database()
        _LOGGER.info("Banco de dados e tabelas verificados/criados com sucesso.")

    def _migrate_database(self):
        """Aplica migrações incrementais no banco de dados existente."""
        with self.engine.connect() as conn:
            # Migrações passadas
            result = conn.execute(text("PRAGMA table_info(historico_tarifas)"))
            colunas = {row[1] for row in result}

            if "dat_competencia" not in colunas:
                conn.execute(text("ALTER TABLE historico_tarifas ADD COLUMN dat_competencia DATE"))
                conn.commit()
                _LOGGER.info("Migração aplicada: coluna 'dat_competencia' adicionada.")

            if "tarifa_base_te" not in colunas:
                conn.execute(text("ALTER TABLE historico_tarifas ADD COLUMN tarifa_base_te FLOAT DEFAULT 0.0"))
                conn.execute(text("ALTER TABLE historico_tarifas ADD COLUMN tarifa_base_tusd FLOAT DEFAULT 0.0"))
                conn.execute(text("ALTER TABLE historico_tarifas ADD COLUMN aliquota_pis FLOAT"))
                conn.execute(text("ALTER TABLE historico_tarifas ADD COLUMN aliquota_cofins FLOAT"))
                conn.execute(text("ALTER TABLE historico_tarifas ADD COLUMN aliquota_icms FLOAT"))
                conn.commit()
                _LOGGER.info("Migração aplicada: colunas de TE, TUSD e impostos adicionadas.")

    async def async_update_concessionarias(self, nomes_concessionarias: set[str]):
        """Atualiza a tabela de concessionárias com uma nova lista."""
        with self.session_factory() as session:
            stmt = select(Concessionaria.nome)
            existentes = set(session.scalars(stmt).all())
            novas_para_adicionar = nomes_concessionarias - existentes

            if not novas_para_adicionar:
                return

            for nome in novas_para_adicionar:
                session.add(Concessionaria(nome=nome))
            session.commit()

    async def async_get_all_concessionarias(self) -> list[str]:
        with self.session_factory() as session:
            stmt = select(Concessionaria.nome).order_by(Concessionaria.nome)
            return session.scalars(stmt).all()

    async def async_get_latest_bandeira_competencia(self) -> date | None:
        with self.session_factory() as session:
            stmt = (
                select(BandeiraTarifaria.data_competencia).order_by(BandeiraTarifaria.data_competencia.desc()).limit(1)
            )
            return session.execute(stmt).scalar_one_or_none()

    async def async_get_latest_bandeira(self) -> tuple[str, float, date] | None:
        with self.session_factory() as session:
            stmt = (
                select(
                    BandeiraTarifaria.nome_bandeira,
                    BandeiraTarifaria.valor_adicional,
                    BandeiraTarifaria.data_competencia,
                )
                .order_by(BandeiraTarifaria.data_competencia.desc())
                .limit(1)
            )
            row = session.execute(stmt).one_or_none()
            return (row.nome_bandeira, row.valor_adicional, row.data_competencia) if row else None

    async def async_insert_bandeira_csv_row_if_newer(
        self, data_geracao_conjunto: date, data_competencia: date, nome_bandeira: str, valor_adicional: float
    ) -> bool:
        with self.session_factory() as session:
            latest = (
                session.query(BandeiraTarifaria.data_competencia)
                .order_by(BandeiraTarifaria.data_competencia.desc())
                .limit(1)
                .scalar()
            )
            if latest is not None and data_competencia <= latest:
                return False

            session.add(
                BandeiraTarifaria(
                    data_geracao_conjunto=data_geracao_conjunto,
                    data_competencia=data_competencia,
                    nome_bandeira=nome_bandeira,
                    valor_adicional=valor_adicional,
                )
            )
            session.commit()
            return True

    async def async_save_tarifa_snapshot(
        self,
        concessionaria_nome: str,
        bandeira_vigente: str,
        tarifa_te: float,
        tarifa_tusd: float,
        dat_competencia: date,
        api_status: str = "online",
        impostos: dict = None,
    ) -> dict:
        impostos = impostos or {}
        tarifa_vigente_final = tarifa_te + tarifa_tusd  # base simplificada, calculo real fica no coordinator

        with self.session_factory() as session:
            stmt = select(Concessionaria).where(Concessionaria.nome == concessionaria_nome)
            concessionaria = session.execute(stmt).scalar_one_or_none()

            if not concessionaria:
                concessionaria = Concessionaria(nome=concessionaria_nome)
                session.add(concessionaria)
                session.flush()

            snapshot = HistoricoTarifa(
                concessionaria_id=concessionaria.id,
                bandeira_vigente=bandeira_vigente,
                tarifa_base_te=tarifa_te,
                tarifa_base_tusd=tarifa_tusd,
                tarifa_vigente=tarifa_vigente_final,
                dat_competencia=dat_competencia,
                api_status=api_status,
                timestamp=datetime.now(),
                aliquota_pis=impostos.get("pis"),
                aliquota_cofins=impostos.get("cofins"),
                aliquota_icms=impostos.get("icms"),
            )
            session.add(snapshot)
            session.commit()

            return self._format_snapshot(snapshot)

    async def async_get_latest_tarifa_snapshot(self, concessionaria_nome: str) -> dict | None:
        with self.session_factory() as session:
            stmt = (
                select(HistoricoTarifa)
                .join(Concessionaria, HistoricoTarifa.concessionaria_id == Concessionaria.id)
                .where(Concessionaria.nome == concessionaria_nome)
                .order_by(HistoricoTarifa.timestamp.desc())
                .limit(1)
            )
            snapshot = session.execute(stmt).scalar_one_or_none()
            if not snapshot:
                return None
            return self._format_snapshot(snapshot)

    def _format_snapshot(self, snapshot) -> dict:
        return {
            "bandeira_vigente": snapshot.bandeira_vigente,
            "tarifa_base_te": snapshot.tarifa_base_te,
            "tarifa_base_tusd": snapshot.tarifa_base_tusd,
            "tarifa_vigente": snapshot.tarifa_vigente,
            "dat_competencia": snapshot.dat_competencia.isoformat() if snapshot.dat_competencia else None,
            "api_status": snapshot.api_status,
            "timestamp": snapshot.timestamp.isoformat(),
            "aliquota_pis": snapshot.aliquota_pis,
            "aliquota_cofins": snapshot.aliquota_cofins,
            "aliquota_icms": snapshot.aliquota_icms,
        }

    async def async_get_local_data(self, entry_id: str) -> dict:
        """Puxa dados armazenados como JSON (ex: saldos SCEE, dados do mes atual)."""
        with self.session_factory() as session:
            stmt = select(StorageDadosLocal).where(StorageDadosLocal.entry_id == entry_id)
            storage = session.execute(stmt).scalar_one_or_none()
            if storage:
                return storage.get_dados()
            return {}

    async def async_set_local_data(self, entry_id: str, dados: dict):
        """Salva dados em formato JSON atrelados ao entry_id."""
        with self.session_factory() as session:
            stmt = select(StorageDadosLocal).where(StorageDadosLocal.entry_id == entry_id)
            storage = session.execute(stmt).scalar_one_or_none()
            if not storage:
                storage = StorageDadosLocal(entry_id=entry_id)
                session.add(storage)
            storage.set_dados(dados)
            session.commit()
