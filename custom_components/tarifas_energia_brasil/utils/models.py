"""Modelos de dados (ORM) para o banco de dados da integração."""

import json

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

Base = declarative_base()


class Concessionaria(Base):
    """Modelo para representar uma concessionária de energia."""

    __tablename__ = "concessionarias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    historico_tarifas: Mapped[list[HistoricoTarifa]] = relationship("HistoricoTarifa", back_populates="concessionaria")

    def __repr__(self):
        return f"<Concessionaria(nome='{self.nome}')>"


class BandeiraTarifaria(Base):
    """Modelo para armazenar o histórico de bandeiras tarifárias por competência."""

    __tablename__ = "bandeiras_tarifarias"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_geracao_conjunto: Mapped[Date] = mapped_column(Date, nullable=False)
    data_competencia: Mapped[Date] = mapped_column(Date, nullable=False, unique=True)
    nome_bandeira: Mapped[str] = mapped_column(String(30), nullable=False)
    valor_adicional: Mapped[float] = mapped_column(Float, nullable=False)

    def __repr__(self):
        return (
            f"<BandeiraTarifaria(data_competencia='{self.data_competencia}', "
            f"nome_bandeira='{self.nome_bandeira}', valor_adicional={self.valor_adicional})>"
        )


class HistoricoTarifa(Base):
    """Modelo para armazenar histórico das últimas leituras de tarifa por concessionária."""

    __tablename__ = "historico_tarifas"

    id: Mapped[int] = mapped_column(primary_key=True)
    bandeira_vigente: Mapped[str] = mapped_column(String(50), nullable=False)
    tarifa_base_te: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    tarifa_base_tusd: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)

    tarifa_vigente: Mapped[float] = mapped_column(Float, nullable=False)  # tarifa antiga simplificada ou soma final
    dat_competencia: Mapped[Date] = mapped_column(Date, nullable=False)
    api_status: Mapped[str] = mapped_column(String(20), nullable=False, default="online")
    timestamp: Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    # Impostos
    aliquota_pis: Mapped[float] = mapped_column(Float, nullable=True)
    aliquota_cofins: Mapped[float] = mapped_column(Float, nullable=True)
    aliquota_icms: Mapped[float] = mapped_column(Float, nullable=True)

    concessionaria_id: Mapped[int] = mapped_column(ForeignKey("concessionarias.id"), nullable=False)
    concessionaria: Mapped[Concessionaria] = relationship("Concessionaria", back_populates="historico_tarifas")


class StorageDadosLocal(Base):
    """Modelo para armazenar dados genéricos como saldo de créditos por entry_id."""

    __tablename__ = "storage_dados_local"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    dados_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    def get_dados(self) -> dict:
        try:
            return json.loads(self.dados_json)
        except:
            return {}

    def set_dados(self, dados: dict):
        self.dados_json = json.dumps(dados)
