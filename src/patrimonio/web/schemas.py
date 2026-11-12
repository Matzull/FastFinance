"""Esquemas Pydantic para la API."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from patrimonio.models import Frecuencia, PeriodoPresupuesto, TipoTransaccion

PositiveAmount = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]
CurrencyCode = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
TipoPatrimonio = Literal["activo", "pasivo"]

# ==================== BANCO ====================


class BancoBase(BaseModel):
    nombre: str
    tipo_cuenta: str
    saldo_inicial: Decimal = Decimal("0")
    moneda: str = "EUR"
    notas: str | None = None


class BancoCreate(BancoBase):
    moneda: CurrencyCode = "EUR"


class BancoUpdate(BaseModel):
    nombre: str | None = None
    tipo_cuenta: str | None = None
    saldo_inicial: Decimal | None = None
    moneda: CurrencyCode | None = None
    notas: str | None = None
    activo: bool | None = None


class BancoResponse(BancoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activo: bool
    saldo_actual: Decimal | None = None


# ==================== TRANSACCION ====================


class TransaccionBase(BaseModel):
    banco_id: int
    tipo: TipoTransaccion
    cantidad: Decimal
    descripcion: str
    categoria: str
    fecha: date | None = None
    notas: str | None = None


class TransaccionCreate(TransaccionBase):
    cantidad: PositiveAmount

    @field_validator("tipo")
    @classmethod
    def reject_transfers(cls, value: TipoTransaccion) -> TipoTransaccion:
        # Transfers need a source and a destination account, which the model lacks.
        if value == TipoTransaccion.TRANSFERENCIA:
            raise ValueError("Transfers are not supported yet")
        return value


class TransaccionResponse(TransaccionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    banco_nombre: str | None = None


# ==================== SUSCRIPCION ====================


class SuscripcionBase(BaseModel):
    banco_id: int
    nombre: str
    cantidad: Decimal
    frecuencia: Frecuencia
    fecha_inicio: date | None = None
    categoria: str = "suscripciones"
    notas: str | None = None


class SuscripcionCreate(SuscripcionBase):
    cantidad: PositiveAmount


class SuscripcionUpdate(BaseModel):
    nombre: str | None = None
    cantidad: Decimal | None = None
    frecuencia: Frecuencia | None = None
    notas: str | None = None


class SuscripcionResponse(SuscripcionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activa: bool
    fecha_fin: date | None = None
    costo_mensual: Decimal | None = None
    banco_nombre: str | None = None


# ==================== PATRIMONIO ====================


class PatrimonioBase(BaseModel):
    nombre: str
    tipo: TipoPatrimonio
    valor: Decimal
    descripcion: str | None = None
    fecha_adquisicion: date | None = None


class PatrimonioCreate(PatrimonioBase):
    valor: PositiveAmount


class PatrimonioUpdate(BaseModel):
    nombre: str | None = None
    valor: Decimal | None = None
    descripcion: str | None = None


class PatrimonioResponse(PatrimonioBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str  # free text in rows created before validation existed


# ==================== RESUMEN ====================


class ResumenMensual(BaseModel):
    mes: int
    año: int
    ingresos: Decimal
    gastos: Decimal
    balance: Decimal


class ResumenGeneral(BaseModel):
    patrimonio_neto: Decimal
    total_bancos: Decimal
    total_activos: Decimal
    total_pasivos: Decimal
    gasto_mensual_suscripciones: Decimal
    resumen_mes_actual: ResumenMensual


class GastosPorCategoria(BaseModel):
    categoria: str
    total: Decimal
    porcentaje: float


class EvolucionMensual(BaseModel):
    mes: str
    ingresos: Decimal
    gastos: Decimal
    balance: Decimal


# ==================== PRESUPUESTOS ====================


class PresupuestoBase(BaseModel):
    nombre: str
    categoria: str
    limite: Decimal
    periodo: PeriodoPresupuesto = PeriodoPresupuesto.MENSUAL
    color: str = "#8B5CF6"
    icono: str = "fa-wallet"
    notas: str | None = None


class PresupuestoCreate(PresupuestoBase):
    limite: PositiveAmount


class PresupuestoUpdate(BaseModel):
    nombre: str | None = None
    limite: PositiveAmount | None = None
    color: str | None = None
    icono: str | None = None
    notas: str | None = None


class PresupuestoResponse(PresupuestoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activo: bool


class EstadoPresupuesto(BaseModel):
    id: int
    nombre: str
    categoria: str
    limite: float
    gastado: float
    disponible: float
    porcentaje: float
    color: str
    icono: str
    excedido: bool


# ==================== INSIGHTS ====================


class AlertaInsight(BaseModel):
    tipo: str  # success, warning, danger
    icono: str
    titulo: str
    mensaje: str


class InsightsResponse(BaseModel):
    resumen_mes: dict
    promedios: dict
    comparacion_mes_anterior: dict
    proyecciones: dict
    tasa_ahorro: float
    categoria_mayor_gasto: dict
    gastos_por_categoria: list[dict]
    presupuestos: dict
    alertas: list[AlertaInsight]


class StatementImportResponse(BaseModel):
    imported_count: int
    skipped_count: int
    errors: list[str]
    detected_columns: dict[str, str]
