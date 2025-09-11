"""Modelos de dados (ORM) para o banco de dados da integração."""
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

Base = declarative_base()

class Concessionaria(Base):
    """Modelo para representar uma concessionária de energia."""
    __tablename__ = "concessionarias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    
    # Relacionamento: Uma concessionária tem várias tarifas
    tarifas: Mapped[list["Tarifa"]] = relationship("Tarifa", back_populates="concessionaria")

    def __repr__(self):
        return f"<Concessionaria(nome='{self.nome}')>"

class Tarifa(Base):
    """Modelo para representar uma tarifa de uma concessionária."""
    __tablename__ = "tarifas"

    id: Mapped[int] = mapped_column(primary_key=True)
    bandeira: Mapped[str] = mapped_column(String(50), nullable=False)
    valor: Mapped[float] = mapped_column(Float, nullable=False)
    unidade: Mapped[str] = mapped_column(String(20), default="R$/kWh")

    concessionaria_id: Mapped[int] = mapped_column(ForeignKey("concessionarias.id"))
    
    # Relacionamento: Uma tarifa pertence a uma concessionária
    concessionaria: Mapped["Concessionaria"] = relationship("Concessionaria", back_populates="tarifas")

    # Garante que não haja duplicatas de bandeira para a mesma concessionária
    __table_args__ = (
        UniqueConstraint("concessionaria_id", "bandeira", name="_concessionaria_bandeira_uc"),
    )

    def __repr__(self):
        return f"<Tarifa(bandeira='{self.bandeira}', valor={self.valor})>"
