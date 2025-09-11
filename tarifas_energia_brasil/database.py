"""Módulo para gerenciar a interação com o banco de dados SQLite via SQLAlchemy async."""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from .models import Base, Concessionaria, Tarifa

_LOGGER = logging.getLogger(__name__)

class DatabaseManager:
    """Gerencia a conexão e operações com o banco de dados."""

    def __init__(self, hass, db_path):
        """Inicializa o gerenciador do banco de dados."""
        self.db_url = f"sqlite+aiosqlite:///{db_path}"
        self.engine = create_async_engine(self.db_url, echo=False)
        self.async_session_factory = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        self.hass = hass

    async def async_setup_database(self):
        """Cria as tabelas no banco de dados se não existirem."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _LOGGER.info("Banco de dados e tabelas verificados/criados com sucesso.")
    
    async def async_update_concessionarias(self, nomes_concessionarias: set[str]):
        """
        Atualiza a tabela de concessionárias com uma nova lista, inserindo apenas as que não existem.
        """
        async with self.async_session_factory() as session:
            async with session.begin():
                # Busca todos os nomes de concessionárias existentes
                stmt = select(Concessionaria.nome)
                result = await session.execute(stmt)
                existentes = set(result.scalars().all())

                # Determina quais concessionárias da nova lista ainda não existem no banco
                novas_para_adicionar = nomes_concessionarias - existentes

                if not novas_para_adicionar:
                    _LOGGER.info("Nenhuma nova concessionária para adicionar.")
                    return

                _LOGGER.info(f"Adicionando {len(novas_para_adicionar)} novas concessionárias.")
                
                # Adiciona as novas concessionárias
                for nome in novas_para_adicionar:
                    session.add(Concessionaria(nome=nome))
            
            await session.commit()


    async def async_update_tarifas(self, concessionaria_nome, tarifas_data):
        """
        Atualiza ou insere as tarifas de uma concessionária.
        'tarifas_data' deve ser um dicionário, ex: {"Bandeira Verde": 0.50, ...}
        """
        async with self.async_session_factory() as session:
            async with session.begin():
                # Primeiro, busca ou cria a concessionária
                stmt = select(Concessionaria).where(Concessionaria.nome == concessionaria_nome)
                result = await session.execute(stmt)
                concessionaria = result.scalar_one_or_none()

                if not concessionaria:
                    _LOGGER.info(f"Criando nova concessionária: {concessionaria_nome}")
                    concessionaria = Concessionaria(nome=concessionaria_nome)
                    session.add(concessionaria)
                    await session.flush() # Para obter o ID da nova concessionária

                # Agora, atualiza ou cria as tarifas
                for bandeira, valor in tarifas_data.items():
                    stmt = select(Tarifa).where(
                        Tarifa.concessionaria_id == concessionaria.id,
                        Tarifa.bandeira == bandeira,
                    )
                    result = await session.execute(stmt)
                    tarifa_existente = result.scalar_one_or_none()

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
            
            await session.commit()
            
    async def async_get_tarifas(self, concessionaria_nome):
        """Busca todas as tarifas de uma concessionária."""
        async with self.async_session_factory() as session:
            stmt = select(Tarifa).join(Concessionaria).where(Concessionaria.nome == concessionaria_nome)
            result = await session.execute(stmt)
            tarifas = result.scalars().all()
            return {tarifa.bandeira: tarifa.valor for tarifa in tarifas}
    
    async def async_get_all_concessionarias(self) -> list[str]:
        """Busca o nome de todas as concessionárias no banco de dados."""
        async with self.async_session_factory() as session:
            stmt = select(Concessionaria.nome).order_by(Concessionaria.nome)
            result = await session.execute(stmt)
            return result.scalars().all()

