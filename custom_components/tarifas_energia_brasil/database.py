"""Módulo para gerenciar a interação com o banco de dados SQLite via SQLAlchemy."""
import logging
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, Concessionaria, Tarifa

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
        """Cria as tabelas no banco de dados se não existirem."""
        Base.metadata.create_all(self.engine)
        _LOGGER.info("Banco de dados e tabelas verificados/criados com sucesso.")
    
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


    async def async_update_tarifas(self, concessionaria_nome, tarifas_data):
        """
        Atualiza ou insere as tarifas de uma concessionária.
        'tarifas_data' deve ser um dicionário, ex: {"Bandeira Verde": 0.50, ...}
        """
        with self.session_factory() as session:
            # Primeiro, busca ou cria a concessionária
            stmt = select(Concessionaria).where(Concessionaria.nome == concessionaria_nome)
            concessionaria = session.execute(stmt).scalar_one_or_none()

            if not concessionaria:
                _LOGGER.info(f"Criando nova concessionária: {concessionaria_nome}")
                concessionaria = Concessionaria(nome=concessionaria_nome)
                session.add(concessionaria)
                session.flush()  # Para obter o ID da nova concessionária

            # Agora, atualiza ou cria as tarifas
            for bandeira, valor in tarifas_data.items():
                stmt = select(Tarifa).where(
                    Tarifa.concessionaria_id == concessionaria.id,
                    Tarifa.bandeira == bandeira,
                )
                tarifa_existente = session.execute(stmt).scalar_one_or_none()

                if tarifa_existente:
                    if tarifa_existente.valor != valor:
                        _LOGGER.debug(f"Atualizando tarifa {bandeira} para {valor}")
                        tarifa_existente.valor = valor
                else:
                    _LOGGER.debug(f"Criando nova tarifa {bandeira} com valor {valor}")
                    nova_tarifa = Tarifa(
                        bandeira=bandeira,
                        valor=valor,
                        concessionaria_id=concessionaria.id,
                    )
                    session.add(nova_tarifa)

            session.commit()
            
    async def async_get_tarifas(self, concessionaria_nome):
        """Busca todas as tarifas de uma concessionária."""
        with self.session_factory() as session:
            stmt = select(Tarifa).join(Concessionaria).where(Concessionaria.nome == concessionaria_nome)
            tarifas = session.execute(stmt).scalars().all()
            return {tarifa.bandeira: tarifa.valor for tarifa in tarifas}
    
    async def async_get_all_concessionarias(self) -> list[str]:
        """Busca o nome de todas as concessionárias no banco de dados."""
        with self.session_factory() as session:
            stmt = select(Concessionaria.nome).order_by(Concessionaria.nome)
            return session.scalars(stmt).all()

