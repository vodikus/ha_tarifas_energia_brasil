"""Modelos de dados (ORM) para o banco de dados da integração."""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

Base = declarative_base()

class Concessionaria(Base):
    """Modelo para representar uma concessionária de energia."""
    __tablename__ = "concessionarias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    historico_tarifas: Mapped[list["HistoricoTarifa"]] = relationship(
        "HistoricoTarifa", back_populates="concessionaria"
    )

    def __repr__(self):
        return f"<Concessionaria(nome='{self.nome}')>"


class BandeiraTarifaria(Base):
    """Histórico de bandeiras tarifárias (mantido para compatibilidade de schema)."""
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
    """Histórico de leituras de tarifa por concessionária (cache local)."""
    __tablename__ = "historico_tarifas"

    id: Mapped[int] = mapped_column(primary_key=True)
    bandeira_vigente: Mapped[str] = mapped_column(String(50), nullable=False)
    tarifa_vigente: Mapped[float] = mapped_column(Float, nullable=False)
    dat_competencia: Mapped[Date] = mapped_column(Date, nullable=False)
    api_status: Mapped[str] = mapped_column(String(20), nullable=False, default="online")
    timestamp: Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    # Campos adicionados na v1.2 (migração automática em database.py)
    tarifa_base_te = Column(Float, nullable=True)
    tarifa_base_tusd = Column(Float, nullable=True)
    dat_inicio_vigencia = Column(String(20), nullable=True)
    dat_fim_vigencia = Column(String(20), nullable=True)
    dat_competencia_bandeira = Column(String(20), nullable=True)
    valor_adicional_bandeira = Column(Float, nullable=True)

    concessionaria_id: Mapped[int] = mapped_column(ForeignKey("concessionarias.id"), nullable=False)
    concessionaria: Mapped["Concessionaria"] = relationship("Concessionaria", back_populates="historico_tarifas")

    def __repr__(self):
        return (
            f"<HistoricoTarifa(concessionaria_id={self.concessionaria_id}, "
            f"bandeira_vigente='{self.bandeira_vigente}', tarifa_vigente={self.tarifa_vigente}, "
            f"api_status='{self.api_status}', timestamp='{self.timestamp}')>"
        )
