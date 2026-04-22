"""Esquemas Pydantic para la API."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from patrimonio.models import TipoTransaccion, Frecuencia, PeriodoPresupuesto


# ==================== BANCO ====================

class BancoBase(BaseModel):
    nombre: str
    tipo_cuenta: str
    saldo_inicial: Decimal = Decimal("0")
    moneda: str = "EUR"
    notas: Optional[str] = None


class BancoCreate(BancoBase):
    pass


class BancoUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo_cuenta: Optional[str] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None


class BancoResponse(BancoBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    activo: bool
    saldo_actual: Optional[Decimal] = None


# ==================== TRANSACCION ====================

class TransaccionBase(BaseModel):
    banco_id: int
    tipo: TipoTransaccion
    cantidad: Decimal
    descripcion: str
    categoria: str
    fecha: Optional[date] = None
    notas: Optional[str] = None


class TransaccionCreate(TransaccionBase):
    pass


class TransaccionResponse(TransaccionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    banco_nombre: Optional[str] = None


# ==================== SUSCRIPCION ====================

class SuscripcionBase(BaseModel):
    banco_id: int
    nombre: str
    cantidad: Decimal
    frecuencia: Frecuencia
    fecha_inicio: Optional[date] = None
    categoria: str = "suscripciones"
    notas: Optional[str] = None


class SuscripcionCreate(SuscripcionBase):
    pass


class SuscripcionUpdate(BaseModel):
    nombre: Optional[str] = None
    cantidad: Optional[Decimal] = None
    frecuencia: Optional[Frecuencia] = None
    notas: Optional[str] = None


class SuscripcionResponse(SuscripcionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    activa: bool
    fecha_fin: Optional[date] = None
    costo_mensual: Optional[Decimal] = None
    banco_nombre: Optional[str] = None


# ==================== PATRIMONIO ====================

class PatrimonioBase(BaseModel):
    nombre: str
    tipo: str  # activo o pasivo
    valor: Decimal
    descripcion: Optional[str] = None
    fecha_adquisicion: Optional[date] = None


class PatrimonioCreate(PatrimonioBase):
    pass


class PatrimonioUpdate(BaseModel):
    nombre: Optional[str] = None
    valor: Optional[Decimal] = None
    descripcion: Optional[str] = None


class PatrimonioResponse(PatrimonioBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int


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
    notas: Optional[str] = None


class PresupuestoCreate(PresupuestoBase):
    pass


class PresupuestoUpdate(BaseModel):
    nombre: Optional[str] = None
    limite: Optional[Decimal] = None
    color: Optional[str] = None
    icono: Optional[str] = None
    notas: Optional[str] = None


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
