"""REST API for FastFinance."""

from datetime import date
from decimal import Decimal
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select

from patrimonio.database import GestorDB, last_months
from patrimonio.models import (
    Banco,
    Presupuesto,
    Suscripcion,
    TipoTransaccion,
    Transaccion,
)
from patrimonio.models import (
    Patrimonio as PatrimonioModel,
)
from patrimonio.web.schemas import (
    BancoCreate,
    BancoResponse,
    BancoUpdate,
    EstadoPresupuesto,
    EvolucionMensual,
    GastosPorCategoria,
    InsightsResponse,
    PatrimonioCreate,
    PatrimonioResponse,
    PresupuestoCreate,
    PresupuestoResponse,
    PresupuestoUpdate,
    ResumenGeneral,
    ResumenMensual,
    StatementImportResponse,
    SuscripcionCreate,
    SuscripcionResponse,
    TransaccionCreate,
    TransaccionResponse,
)

router = APIRouter(prefix="/api", tags=["api"])


@lru_cache
def get_db() -> GestorDB:
    """Shared database manager, created on first use (overridable in tests)."""
    return GestorDB()


DB = Annotated[GestorDB, Depends(get_db)]


def _bank_response(banco: Banco, saldo: Decimal) -> BancoResponse:
    return BancoResponse.model_validate(banco).model_copy(update={"saldo_actual": saldo})


def _transaction_response(t: Transaccion, banco_nombre: str | None) -> TransaccionResponse:
    return TransaccionResponse.model_validate(t).model_copy(update={"banco_nombre": banco_nombre})


def _subscription_response(s: Suscripcion, banco_nombre: str | None) -> SuscripcionResponse:
    # Built explicitly: the ORM `costo_mensual` is a method, not a column.
    return SuscripcionResponse(
        id=s.id,
        banco_id=s.banco_id,
        nombre=s.nombre,
        cantidad=s.cantidad,
        frecuencia=s.frecuencia,
        fecha_inicio=s.fecha_inicio,
        fecha_fin=s.fecha_fin,
        categoria=s.categoria,
        notas=s.notas,
        activa=s.activa,
        costo_mensual=s.costo_mensual(),
        banco_nombre=banco_nombre,
    )


def _budget_response(p: Presupuesto) -> PresupuestoResponse:
    return PresupuestoResponse.model_validate(p)


# ==================== BANKS ====================


@router.get("/bancos", response_model=list[BancoResponse])
def list_banks(db: DB, solo_activos: bool = True):
    """Lists all bank accounts."""
    saldos = db.bank_balances(solo_activos=solo_activos)
    return [
        _bank_response(banco, saldos[banco.id])
        for banco in db.list_banks(solo_activos=solo_activos)
    ]


@router.post("/bancos", response_model=BancoResponse)
def create_bank(db: DB, banco: BancoCreate):
    """Creates a new bank account."""
    nuevo = db.create_bank(**banco.model_dump())
    return _bank_response(nuevo, nuevo.saldo_inicial)


@router.get("/bancos/{banco_id}", response_model=BancoResponse)
def get_bank(db: DB, banco_id: int):
    """Gets a bank account by ID."""
    banco = db.get_bank(banco_id)
    if not banco:
        raise HTTPException(status_code=404, detail="Bank not found")
    return _bank_response(banco, db.calculate_bank_balance(banco_id))


@router.put("/bancos/{banco_id}", response_model=BancoResponse)
def update_bank(db: DB, banco_id: int, datos: BancoUpdate):
    """Updates a bank account."""
    banco = db.update_bank(banco_id, **datos.model_dump(exclude_unset=True))
    if not banco:
        raise HTTPException(status_code=404, detail="Bank not found")
    return _bank_response(banco, db.calculate_bank_balance(banco_id))


@router.delete("/bancos/{banco_id}")
def delete_bank(db: DB, banco_id: int):
    """Deactivates a bank account."""
    if not db.update_bank(banco_id, activo=False):
        raise HTTPException(status_code=404, detail="Bank not found")
    return {"message": "Bank deactivated"}


# ==================== TRANSACTIONS ====================


@router.get("/transacciones", response_model=list[TransaccionResponse])
def list_transactions(
    db: DB,
    banco_id: int | None = None,
    tipo: TipoTransaccion | None = None,
    categoria: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limite: int = Query(50, le=500),
):
    """Lists transactions with optional filters."""
    transacciones = db.list_transactions(
        banco_id=banco_id,
        tipo=tipo,
        categoria=categoria,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limite=limite,
    )
    return [_transaction_response(t, t.banco.nombre if t.banco else None) for t in transacciones]


@router.post("/transacciones", response_model=TransaccionResponse)
def create_transaction(db: DB, trans: TransaccionCreate):
    """Creates a new transaction."""
    banco = db.get_bank(trans.banco_id)
    if not banco:
        raise HTTPException(status_code=404, detail="Bank not found")

    nueva = db.create_transaction(**trans.model_dump())
    return _transaction_response(nueva, banco.nombre)


@router.post("/transactions/import-expenses", response_model=StatementImportResponse)
@router.post(
    "/transacciones/importar-gastos",
    response_model=StatementImportResponse,
    include_in_schema=False,
)
async def import_expenses_from_statement(
    db: DB,
    banco_id: int = Form(...),
    statement_file: UploadFile = File(...),
    categoria_default: str = Form("otros"),
):
    """Import expense transactions from CSV/XLSX bank statements."""
    content = await statement_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        result = db.import_statement_expenses(
            bank_id=banco_id,
            file_name=statement_file.filename or "statement.csv",
            file_bytes=content,
            default_category=categoria_default,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StatementImportResponse(**result)


@router.delete("/transacciones/{transaccion_id}")
def delete_transaction(db: DB, transaccion_id: int):
    """Deletes a transaction."""
    if db.delete_transaction(transaccion_id):
        return {"message": "Transaction deleted"}
    raise HTTPException(status_code=404, detail="Transaction not found")


# ==================== SUBSCRIPTIONS ====================


@router.get("/suscripciones", response_model=list[SuscripcionResponse])
def list_subscriptions(db: DB, solo_activas: bool = True):
    """Lists all subscriptions."""
    return [
        _subscription_response(s, s.banco.nombre if s.banco else None)
        for s in db.list_subscriptions(solo_activas=solo_activas)
    ]


@router.post("/suscripciones", response_model=SuscripcionResponse)
def create_subscription(db: DB, sub: SuscripcionCreate):
    """Creates a new subscription."""
    banco = db.get_bank(sub.banco_id)
    if not banco:
        raise HTTPException(status_code=404, detail="Bank not found")

    nueva = db.create_subscription(**sub.model_dump())
    return _subscription_response(nueva, banco.nombre)


@router.delete("/suscripciones/{suscripcion_id}")
def cancel_subscription(db: DB, suscripcion_id: int):
    """Cancels a subscription."""
    if db.cancel_subscription(suscripcion_id):
        return {"message": "Subscription canceled"}
    raise HTTPException(status_code=404, detail="Subscription not found")


# ==================== NET WORTH ====================


@router.get("/patrimonio", response_model=list[PatrimonioResponse])
def list_net_worth_items(db: DB, tipo: str | None = None):
    """Lists all assets and liabilities."""
    return [PatrimonioResponse.model_validate(p) for p in db.list_net_worth_items(tipo=tipo)]


@router.post("/patrimonio", response_model=PatrimonioResponse)
def create_net_worth_item(db: DB, pat: PatrimonioCreate):
    """Creates a new asset or liability."""
    return PatrimonioResponse.model_validate(db.create_net_worth_item(**pat.model_dump()))


@router.delete("/patrimonio/{patrimonio_id}")
def delete_net_worth_item(db: DB, patrimonio_id: int):
    """Deletes a net worth item."""
    with db.get_session() as session:
        item = session.get(PatrimonioModel, patrimonio_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        session.delete(item)
        session.commit()
    return {"message": "Item deleted"}


# ==================== SUMMARY AND STATS ====================


@router.get("/resumen", response_model=ResumenGeneral)
def get_summary(db: DB):
    """Gets the overall financial summary."""
    hoy = date.today()

    totales = db.net_worth_breakdown()
    gasto_suscripciones = db.calculate_monthly_subscription_cost()
    resumen_mes = db.monthly_summary(hoy.month, hoy.year)

    return ResumenGeneral(
        patrimonio_neto=totales["neto"],
        total_bancos=totales["bancos"],
        total_activos=totales["activos"],
        total_pasivos=totales["pasivos"],
        gasto_mensual_suscripciones=gasto_suscripciones,
        resumen_mes_actual=ResumenMensual(**resumen_mes),
    )


@router.get("/estadisticas/gastos-por-categoria", response_model=list[GastosPorCategoria])
def expenses_by_category(
    db: DB,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
):
    """Obtiene los gastos agrupados por categoría."""
    with db.get_session() as session:
        query = (
            select(Transaccion.categoria, func.sum(Transaccion.cantidad).label("total"))
            .where(Transaccion.tipo == TipoTransaccion.GASTO)
            .group_by(Transaccion.categoria)
        )

        if fecha_desde:
            query = query.where(Transaccion.fecha >= fecha_desde)
        if fecha_hasta:
            query = query.where(Transaccion.fecha <= fecha_hasta)

        resultados = session.execute(query).all()

    total_general = sum((r.total for r in resultados), Decimal("0"))
    return [
        GastosPorCategoria(
            categoria=r.categoria,
            total=r.total,
            porcentaje=float(r.total / total_general * 100) if total_general else 0,
        )
        for r in resultados
    ]


@router.get("/estadisticas/evolucion-mensual", response_model=list[EvolucionMensual])
def monthly_evolution(db: DB, meses: int = Query(12, ge=1, le=24)):
    """Obtiene la evolución de ingresos y gastos por mes."""
    months = last_months(date.today(), meses)
    totals = db.monthly_totals(months)
    return [
        EvolucionMensual(
            mes=f"{año}-{mes:02d}",
            ingresos=totals[(año, mes)]["ingresos"],
            gastos=totals[(año, mes)]["gastos"],
            balance=totals[(año, mes)]["ingresos"] - totals[(año, mes)]["gastos"],
        )
        for año, mes in months
    ]


@router.get("/estadisticas/saldo-bancos")
def balance_by_bank(db: DB):
    """Obtiene el saldo de cada banco para gráficas."""
    saldos = db.bank_balances()
    return [
        {
            "nombre": b.nombre,
            "saldo": float(saldos[b.id]),
            "tipo": b.tipo_cuenta,
        }
        for b in db.list_banks()
    ]


# ==================== BUDGETS ====================


@router.get("/presupuestos", response_model=list[PresupuestoResponse])
def list_budgets(db: DB, solo_activos: bool = True):
    """Lists all budgets."""
    return [_budget_response(p) for p in db.list_budgets(solo_activos=solo_activos)]


@router.post("/presupuestos", response_model=PresupuestoResponse)
def create_budget(db: DB, presupuesto: PresupuestoCreate):
    """Creates a new budget."""
    return _budget_response(db.create_budget(**presupuesto.model_dump()))


@router.put("/presupuestos/{presupuesto_id}", response_model=PresupuestoResponse)
def update_budget(db: DB, presupuesto_id: int, datos: PresupuestoUpdate):
    """Updates an existing budget."""
    presupuesto = db.update_budget(presupuesto_id, **datos.model_dump())
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Budget not found")
    return _budget_response(presupuesto)


@router.delete("/presupuestos/{presupuesto_id}")
def delete_budget(db: DB, presupuesto_id: int):
    """Deletes a budget."""
    if not db.delete_budget(presupuesto_id):
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"message": "Budget deleted"}


@router.get("/presupuestos/estado", response_model=list[EstadoPresupuesto])
def get_budget_status(db: DB):
    """Gets current status for all budgets."""
    return [EstadoPresupuesto(**e) for e in db.get_budget_status()]


# ==================== INSIGHTS ====================


@router.get("/insights", response_model=InsightsResponse)
def get_insights(db: DB):
    """Gets financial insights and analytics."""
    return InsightsResponse(**db.get_insights())
