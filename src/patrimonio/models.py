"""Data models for personal finance management."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TipoTransaccion(str, Enum):
    """Transaction type values stored in the database."""

    INGRESO = "ingreso"
    GASTO = "gasto"
    TRANSFERENCIA = "transferencia"


class Frecuencia(str, Enum):
    """Subscription frequency values stored in the database."""

    DIARIA = "diaria"
    SEMANAL = "semanal"
    MENSUAL = "mensual"
    ANUAL = "anual"


class CategoriaGasto(str, Enum):
    """Expense category values."""

    ALIMENTACION = "alimentacion"
    TRANSPORTE = "transporte"
    VIVIENDA = "vivienda"
    SERVICIOS = "servicios"
    ENTRETENIMIENTO = "entretenimiento"
    SALUD = "salud"
    EDUCACION = "educacion"
    ROPA = "ropa"
    TECNOLOGIA = "tecnologia"
    SUSCRIPCIONES = "suscripciones"
    OTROS = "otros"


class CategoriaIngreso(str, Enum):
    """Income category values."""

    SALARIO = "salario"
    FREELANCE = "freelance"
    INVERSIONES = "inversiones"
    ALQUILER = "alquiler"
    REGALO = "regalo"
    REEMBOLSO = "reembolso"
    OTROS = "otros"


class Banco(Base):
    """Represents a bank account or financial institution."""

    __tablename__ = "bancos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    tipo_cuenta: Mapped[str] = mapped_column(String(50))
    saldo_inicial: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    moneda: Mapped[str] = mapped_column(String(3), default="EUR")
    notas: Mapped[str | None] = mapped_column(String(500), nullable=True)
    activo: Mapped[bool] = mapped_column(default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    transacciones: Mapped[list["Transaccion"]] = relationship(
        back_populates="banco", cascade="all, delete-orphan"
    )
    suscripciones: Mapped[list["Suscripcion"]] = relationship(
        back_populates="banco", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Banco(id={self.id}, nombre='{self.nombre}', tipo='{self.tipo_cuenta}')"


class Transaccion(Base):
    """Represents a transaction (income or expense)."""

    __tablename__ = "transacciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[TipoTransaccion] = mapped_column(SQLEnum(TipoTransaccion))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    descripcion: Mapped[str] = mapped_column(String(200))
    categoria: Mapped[str] = mapped_column(String(50))
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    notas: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Foreign keys
    banco_id: Mapped[int] = mapped_column(ForeignKey("bancos.id"))

    # Relationships
    banco: Mapped["Banco"] = relationship(back_populates="transacciones")

    def __repr__(self) -> str:
        signo = "+" if self.tipo == TipoTransaccion.INGRESO else "-"
        return f"Transaccion({signo}{self.cantidad}€ - {self.descripcion})"


class Suscripcion(Base):
    """Represents a recurring subscription."""

    __tablename__ = "suscripciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    frecuencia: Mapped[Frecuencia] = mapped_column(SQLEnum(Frecuencia))
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    categoria: Mapped[str] = mapped_column(String(50), default=CategoriaGasto.SUSCRIPCIONES.value)
    activa: Mapped[bool] = mapped_column(default=True)
    notas: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Foreign keys
    banco_id: Mapped[int] = mapped_column(ForeignKey("bancos.id"))

    # Relationships
    banco: Mapped["Banco"] = relationship(back_populates="suscripciones")

    def __repr__(self) -> str:
        return f"Suscripcion('{self.nombre}' - {self.cantidad}€/{self.frecuencia.value})"

    def costo_mensual(self) -> Decimal:
        """Calculate the approximate monthly subscription cost."""
        match self.frecuencia:
            case Frecuencia.DIARIA:
                return self.cantidad * 30
            case Frecuencia.SEMANAL:
                return self.cantidad * Decimal("4.33")
            case Frecuencia.MENSUAL:
                return self.cantidad
            case Frecuencia.ANUAL:
                return self.cantidad / 12


class Patrimonio(Base):
    """Represents an asset or liability item."""

    __tablename__ = "patrimonio"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    tipo: Mapped[str] = mapped_column(String(50))
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fecha_adquisicion: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def __repr__(self) -> str:
        return f"Patrimonio('{self.nombre}' - {self.valor}€)"


class PeriodoPresupuesto(str, Enum):
    """Budget period values stored in the database."""

    SEMANAL = "semanal"
    MENSUAL = "mensual"
    ANUAL = "anual"


class Presupuesto(Base):
    """Represents a budget for an expense category."""

    __tablename__ = "presupuestos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    categoria: Mapped[str] = mapped_column(String(50))
    limite: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    periodo: Mapped[PeriodoPresupuesto] = mapped_column(
        SQLEnum(PeriodoPresupuesto), default=PeriodoPresupuesto.MENSUAL
    )
    activo: Mapped[bool] = mapped_column(default=True)
    color: Mapped[str] = mapped_column(String(7), default="#8B5CF6")
    icono: Mapped[str] = mapped_column(String(50), default="fa-wallet")
    notas: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def __repr__(self) -> str:
        return f"Presupuesto('{self.nombre}' - {self.limite}€/{self.periodo.value})"

    def limite_mensual(self) -> Decimal:
        """Return the equivalent monthly limit."""
        match self.periodo:
            case PeriodoPresupuesto.SEMANAL:
                return self.limite * Decimal("4.33")
            case PeriodoPresupuesto.MENSUAL:
                return self.limite
            case PeriodoPresupuesto.ANUAL:
                return self.limite / 12


# English compatibility aliases
TransactionType = TipoTransaccion
Frequency = Frecuencia
ExpenseCategory = CategoriaGasto
IncomeCategory = CategoriaIngreso
Bank = Banco
Transaction = Transaccion
Subscription = Suscripcion
NetWorthItem = Patrimonio
BudgetPeriod = PeriodoPresupuesto
Budget = Presupuesto
