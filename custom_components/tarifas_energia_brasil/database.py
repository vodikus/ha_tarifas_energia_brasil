"""Módulo para gerenciar a interação com o banco de dados SQLite via SQLAlchemy."""
import logging
from datetime import date, datetime
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, Concessionaria, BandeiraTarifaria, HistoricoTarifa

_LOGGER = logging.getLogger(__name__)

class DatabaseManager:
    """Gerencia a conexão e operações com o banco de dados."""

    def __init__(self, hass, db_path):
        """Inicializa o gerenciador do banco de dados."""
        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url, echo=False)
        self.session_factory = sessionmaker(
            self.engine, expire_on_commit=False, class_=Session
        )
        self.async_session_factory = self.session_factory
        self.hass = hass

    async def async_setup_database(self):
        """Cria as tabelas no banco de dados se não existirem e aplica migrações necessárias."""
        Base.metadata.create_all(self.engine)
        self._migrate_database()
        _LOGGER.info("Banco de dados e tabelas verificados/criados com sucesso.")

    def _migrate_database(self):
        """Aplica migrações incrementais no banco de dados existente."""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("PRAGMA table_info(historico_tarifas)")
            )
            colunas = {row[1] for row in result}
            if "dat_competencia" not in colunas:
                conn.execute(
                    text(
                        "ALTER TABLE historico_tarifas ADD COLUMN dat_competencia DATE"
                    )
                )
                conn.commit()
                _LOGGER.info("Migração aplicada: coluna 'dat_competencia' adicionada à tabela 'historico_tarifas'.")
    
    async def async_update_concessionarias(self, nomes_concessionarias: set[str]):
        """
        Atualiza a tabela de concessionárias com uma nova lista, inserindo apenas as que não existem.
        """
        with self.session_factory() as session:
            # Busca todos os nomes de concessionárias existentes
            stmt = select(Concessionaria.nome)
            existentes = set(session.scalars(stmt).all())

            # Determina quais concessionárias da nova lista ainda não existem no banco
            novas_para_adicionar = nomes_concessionarias - existentes

            if not novas_para_adicionar:
                _LOGGER.info("Nenhuma nova concessionária para adicionar.")
                return

            _LOGGER.info(f"Adicionando {len(novas_para_adicionar)} novas concessionárias.")

            # Adiciona as novas concessionárias
            for nome in novas_para_adicionar:
                session.add(Concessionaria(nome=nome))

            session.commit()


    async def async_get_all_concessionarias(self) -> list[str]:
        """Busca o nome de todas as concessionárias no banco de dados."""
        with self.session_factory() as session:
            stmt = select(Concessionaria.nome).order_by(Concessionaria.nome)
            return session.scalars(stmt).all()

    async def async_get_latest_bandeira_competencia(self) -> date | None:
        """Retorna a competência mais recente salva na tabela de bandeiras tarifárias."""
        with self.session_factory() as session:
            stmt = (
                select(BandeiraTarifaria.data_competencia)
                .order_by(BandeiraTarifaria.data_competencia.desc())
                .limit(1)
            )
            return session.execute(stmt).scalar_one_or_none()

    async def async_get_latest_bandeira(self) -> tuple[str, float, date] | None:
        """Retorna o nome, valor adicional e data de competência da bandeira mais recente salva no banco."""
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
        self,
        data_geracao_conjunto: date,
        data_competencia: date,
        nome_bandeira: str,
        valor_adicional: float,
    ) -> bool:
        """
        Insere a linha do CSV apenas se a competência for mais recente que a última salva.
        Retorna True quando inseriu e False quando não foi necessário inserir.
        """
        with self.session_factory() as session:
            latest = (
                session.query(BandeiraTarifaria.data_competencia)
                .order_by(BandeiraTarifaria.data_competencia.desc())
                .limit(1)
                .scalar()
            )

            if latest is not None and data_competencia <= latest:
                _LOGGER.info(
                    "Competência %s não é mais recente que a última salva (%s).",
                    data_competencia,
                    latest,
                )
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
            _LOGGER.info(
                "Nova linha de bandeira inserida para competência %s (%s).",
                data_competencia,
                nome_bandeira,
            )
            return True

    async def async_save_tarifa_snapshot(
        self,
        concessionaria_nome: str,
        bandeira_vigente: str,
        tarifa_vigente: float,
        dat_competencia: date,
        api_status: str = "online",
    ) -> dict:
        """Insere no histórico apenas se dat_competencia for mais recente que o último registro."""
        with self.session_factory() as session:
            stmt = select(Concessionaria).where(Concessionaria.nome == concessionaria_nome)
            concessionaria = session.execute(stmt).scalar_one_or_none()

            if not concessionaria:
                _LOGGER.info("Criando nova concessionária para histórico: %s", concessionaria_nome)
                concessionaria = Concessionaria(nome=concessionaria_nome)
                session.add(concessionaria)
                session.flush()

            # Verifica a competência do último registro desta concessionária
            latest_stmt = (
                select(HistoricoTarifa.dat_competencia)
                .where(HistoricoTarifa.concessionaria_id == concessionaria.id)
                .order_by(HistoricoTarifa.dat_competencia.desc())
                .limit(1)
            )
            ultima_competencia = session.execute(latest_stmt).scalar_one_or_none()

            if ultima_competencia is not None and dat_competencia <= ultima_competencia:
                _LOGGER.info(
                    "Histórico não atualizado: competência %s já registrada para %s (última: %s).",
                    dat_competencia,
                    concessionaria_nome,
                    ultima_competencia,
                )
                # Retorna o registro existente mais recente
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
                )
                session.add(snapshot)
                session.commit()
                _LOGGER.info(
                    "Novo registro inserido no histórico para %s (competência: %s).",
                    concessionaria_nome,
                    dat_competencia,
                )

            return {
                "bandeira_vigente": snapshot.bandeira_vigente,
                "tarifa_vigente": snapshot.tarifa_vigente,
                "dat_competencia": snapshot.dat_competencia.isoformat(),
                "api_status": snapshot.api_status,
                "timestamp": snapshot.timestamp.isoformat(),
            }

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

            if not snapshot:
                return None

            return {
                "bandeira_vigente": snapshot.bandeira_vigente,
                "tarifa_vigente": snapshot.tarifa_vigente,
                "dat_competencia": snapshot.dat_competencia.isoformat() if snapshot.dat_competencia else None,
                "api_status": snapshot.api_status,
                "timestamp": snapshot.timestamp.isoformat(),
            }

