"""REST API for FastFinance."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select

from patrimonio.database import GestorDB
from patrimonio.models import (
    Banco,
    TipoTransaccion,
    Transaccion,
)
from patrimonio.models import (
    Patrimonio as PatrimonioModel,
)
from patrimonio.web.schemas import (
    BancoCreate,
    BancoResponse,
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
db = GestorDB()


# ==================== BANKS ====================


@router.get("/bancos", response_model=list[BancoResponse])
def list_banks(solo_activos: bool = True):
    """Lists all bank accounts."""
    bancos = db.list_banks(solo_activos=solo_activos)
    result = []
    for banco in bancos:
        saldo = db.calculate_bank_balance(banco.id)
        result.append(
            BancoResponse(
                id=banco.id,
                nombre=banco.nombre,
                tipo_cuenta=banco.tipo_cuenta,
                saldo_inicial=banco.saldo_inicial,
                moneda=banco.moneda,
                notas=banco.notas,
                activo=banco.activo,
                saldo_actual=saldo,
            )
        )
    return result


@router.post("/bancos", response_model=BancoResponse)
def create_bank(banco: BancoCreate):
    """Creates a new bank account."""
    nuevo = db.create_bank(
        nombre=banco.nombre,
        tipo_cuenta=banco.tipo_cuenta,
        saldo_inicial=banco.saldo_inicial,
        moneda=banco.moneda,
        notas=banco.notas,
    )
    return BancoResponse(
        id=nuevo.id,
        nombre=nuevo.nombre,
        tipo_cuenta=nuevo.tipo_cuenta,
        saldo_inicial=nuevo.saldo_inicial,
        moneda=nuevo.moneda,
        notas=nuevo.notas,
        activo=nuevo.activo,
        saldo_actual=nuevo.saldo_inicial,
    )


@router.get("/bancos/{banco_id}", response_model=BancoResponse)
def get_bank(banco_id: int):
    """Gets a bank account by ID."""
    banco = db.get_bank(banco_id)
    if not banco:
        raise HTTPException(status_code=404, detail="Bank not found")
    saldo = db.calculate_bank_balance(banco_id)
    return BancoResponse(
        id=banco.id,
        nombre=banco.nombre,
        tipo_cuenta=banco.tipo_cuenta,
        saldo_inicial=banco.saldo_inicial,
        moneda=banco.moneda,
        notas=banco.notas,
        activo=banco.activo,
        saldo_actual=saldo,
    )


@router.delete("/bancos/{banco_id}")
def delete_bank(banco_id: int):
    """Deactivates a bank account."""
    with db.get_session() as session:
        banco = session.get(Banco, banco_id)
        if not banco:
            raise HTTPException(status_code=404, detail="Bank not found")
        banco.activo = False
        session.commit()
    return {"message": "Bank deactivated"}


# ==================== TRANSACTIONS ====================


@router.get("/transacciones", response_model=list[TransaccionResponse])
def list_transactions(
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
    result = []
    for t in transacciones:
        banco = db.get_bank(t.banco_id)
        result.append(
            TransaccionResponse(
                id=t.id,
                banco_id=t.banco_id,
                tipo=t.tipo,
                cantidad=t.cantidad,
                descripcion=t.descripcion,
                categoria=t.categoria,
                fecha=t.fecha,
                notas=t.notas,
                banco_nombre=banco.nombre if banco else None,
            )
        )
    return result


@router.post("/transacciones", response_model=TransaccionResponse)
def create_transaction(trans: TransaccionCreate):
    """Creates a new transaction."""
    banco = db.get_bank(trans.banco_id)
    if not banco:
        raise HTTPException(status_code=404, detail="Bank not found")

    nueva = db.create_transaction(
        banco_id=trans.banco_id,
        tipo=trans.tipo,
        cantidad=trans.cantidad,
        descripcion=trans.descripcion,
        categoria=trans.categoria,
        fecha=trans.fecha,
        notas=trans.notas,
    )
    return TransaccionResponse(
        id=nueva.id,
        banco_id=nueva.banco_id,
        tipo=nueva.tipo,
        cantidad=nueva.cantidad,
        descripcion=nueva.descripcion,
        categoria=nueva.categoria,
        fecha=nueva.fecha,
        notas=nueva.notas,
        banco_nombre=banco.nombre,
    )


@router.post("/transactions/import-expenses", response_model=StatementImportResponse)
@router.post(
    "/transacciones/importar-gastos",
    response_model=StatementImportResponse,
    include_in_schema=False,
)
async def import_expenses_from_statement(
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
def delete_transaction(transaccion_id: int):
    """Deletes a transaction."""
    if db.delete_transaction(transaccion_id):
        return {"message": "Transaction deleted"}
    raise HTTPException(status_code=404, detail="Transaction not found")


# ==================== SUBSCRIPTIONS ====================


@router.get("/suscripciones", response_model=list[SuscripcionResponse])
def list_subscriptions(solo_activas: bool = True):
    """Lists all subscriptions."""
    suscripciones = db.list_subscriptions(solo_activas=solo_activas)
    result = []
    for s in suscripciones:
        banco = db.get_bank(s.banco_id)
        result.append(
            SuscripcionResponse(
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
                banco_nombre=banco.nombre if banco else None,
            )
        )
    return result


@router.post("/suscripciones", response_model=SuscripcionResponse)
def create_subscription(sub: SuscripcionCreate):
    """Creates a new subscription."""
    banco = db.get_bank(sub.banco_id)
    if not banco:
        raise HTTPException(status_code=404, detail="Bank not found")

    nueva = db.create_subscription(
        banco_id=sub.banco_id,
        nombre=sub.nombre,
        cantidad=sub.cantidad,
        frecuencia=sub.frecuencia,
        fecha_inicio=sub.fecha_inicio,
        categoria=sub.categoria,
        notas=sub.notas,
    )
    return SuscripcionResponse(
        id=nueva.id,
        banco_id=nueva.banco_id,
        nombre=nueva.nombre,
        cantidad=nueva.cantidad,
        frecuencia=nueva.frecuencia,
        fecha_inicio=nueva.fecha_inicio,
        fecha_fin=nueva.fecha_fin,
        categoria=nueva.categoria,
        notas=nueva.notas,
        activa=nueva.activa,
        costo_mensual=nueva.costo_mensual(),
        banco_nombre=banco.nombre,
    )


@router.delete("/suscripciones/{suscripcion_id}")
def cancel_subscription(suscripcion_id: int):
    """Cancels a subscription."""
    if db.cancel_subscription(suscripcion_id):
        return {"message": "Subscription canceled"}
    raise HTTPException(status_code=404, detail="Subscription not found")


# ==================== NET WORTH ====================


@router.get("/patrimonio", response_model=list[PatrimonioResponse])
def list_net_worth_items(tipo: str | None = None):
    """Lists all assets and liabilities."""
    items = db.list_net_worth_items(tipo=tipo)
    return [
        PatrimonioResponse(
            id=p.id,
            nombre=p.nombre,
            tipo=p.tipo,
            valor=p.valor,
            descripcion=p.descripcion,
            fecha_adquisicion=p.fecha_adquisicion,
        )
        for p in items
    ]


@router.post("/patrimonio", response_model=PatrimonioResponse)
def create_net_worth_item(pat: PatrimonioCreate):
    """Creates a new asset or liability."""
    nuevo = db.create_net_worth_item(
        nombre=pat.nombre,
        tipo=pat.tipo,
        valor=pat.valor,
        descripcion=pat.descripcion,
        fecha_adquisicion=pat.fecha_adquisicion,
    )
    return PatrimonioResponse(
        id=nuevo.id,
        nombre=nuevo.nombre,
        tipo=nuevo.tipo,
        valor=nuevo.valor,
        descripcion=nuevo.descripcion,
        fecha_adquisicion=nuevo.fecha_adquisicion,
    )


@router.delete("/patrimonio/{patrimonio_id}")
def delete_net_worth_item(patrimonio_id: int):
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
def get_summary():
    """Gets the overall financial summary."""
    hoy = date.today()

    # Calculate totals
    bancos = db.list_banks()
    total_bancos = sum(db.calculate_bank_balance(b.id) for b in bancos)

    with db.get_session() as session:
        total_activos = session.scalar(
            select(func.sum(PatrimonioModel.valor)).where(PatrimonioModel.tipo == "activo")
        ) or Decimal("0")

        total_pasivos = session.scalar(
            select(func.sum(PatrimonioModel.valor)).where(PatrimonioModel.tipo == "pasivo")
        ) or Decimal("0")

    patrimonio_neto = total_bancos + total_activos - total_pasivos
    gasto_suscripciones = db.calculate_monthly_subscription_cost()
    resumen_mes = db.monthly_summary(hoy.month, hoy.year)

    return ResumenGeneral(
        patrimonio_neto=patrimonio_neto,
        total_bancos=total_bancos,
        total_activos=total_activos,
        total_pasivos=total_pasivos,
        gasto_mensual_suscripciones=gasto_suscripciones,
        resumen_mes_actual=ResumenMensual(**resumen_mes),
    )


@router.get("/estadisticas/gastos-por-categoria", response_model=list[GastosPorCategoria])
def expenses_by_category(
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

        total_general = sum(r.total for r in resultados) if resultados else Decimal("1")

        return [
            GastosPorCategoria(
                categoria=r.categoria,
                total=r.total,
                porcentaje=float(r.total / total_general * 100) if total_general else 0,
            )
            for r in resultados
        ]


@router.get("/estadisticas/evolucion-mensual", response_model=list[EvolucionMensual])
def monthly_evolution(meses: int = Query(12, le=24)):
    """Obtiene la evolución de ingresos y gastos por mes."""
    hoy = date.today()
    resultado = []

    for i in range(meses - 1, -1, -1):
        # Calcular mes
        mes = hoy.month - i
        año = hoy.year
        while mes <= 0:
            mes += 12
            año -= 1

        resumen = db.monthly_summary(mes, año)
        resultado.append(
            EvolucionMensual(
                mes=f"{año}-{mes:02d}",
                ingresos=resumen["ingresos"],
                gastos=resumen["gastos"],
                balance=resumen["balance"],
            )
        )

    return resultado


@router.get("/estadisticas/saldo-bancos")
def balance_by_bank():
    """Obtiene el saldo de cada banco para gráficas."""
    bancos = db.list_banks()
    return [
        {
            "nombre": b.nombre,
            "saldo": float(db.calculate_bank_balance(b.id)),
            "tipo": b.tipo_cuenta,
        }
        for b in bancos
    ]


# ==================== BUDGETS ====================


@router.get("/presupuestos", response_model=list[PresupuestoResponse])
def list_budgets(solo_activos: bool = True):
    """Lists all budgets."""
    presupuestos = db.list_budgets(solo_activos=solo_activos)
    return [
        PresupuestoResponse(
            id=p.id,
            nombre=p.nombre,
            categoria=p.categoria,
            limite=p.limite,
            periodo=p.periodo,
            color=p.color,
            icono=p.icono,
            notas=p.notas,
            activo=p.activo,
        )
        for p in presupuestos
    ]


@router.post("/presupuestos", response_model=PresupuestoResponse)
def create_budget(presupuesto: PresupuestoCreate):
    """Creates a new budget."""
    nuevo = db.create_budget(
        nombre=presupuesto.nombre,
        categoria=presupuesto.categoria,
        limite=presupuesto.limite,
        periodo=presupuesto.periodo,
        color=presupuesto.color,
        icono=presupuesto.icono,
        notas=presupuesto.notas,
    )
    return PresupuestoResponse(
        id=nuevo.id,
        nombre=nuevo.nombre,
        categoria=nuevo.categoria,
        limite=nuevo.limite,
        periodo=nuevo.periodo,
        color=nuevo.color,
        icono=nuevo.icono,
        notas=nuevo.notas,
        activo=nuevo.activo,
    )


@router.put("/presupuestos/{presupuesto_id}", response_model=PresupuestoResponse)
def update_budget(presupuesto_id: int, datos: PresupuestoUpdate):
    """Updates an existing budget."""
    presupuesto = db.update_budget(
        presupuesto_id,
        nombre=datos.nombre,
        limite=datos.limite,
        color=datos.color,
        icono=datos.icono,
        notas=datos.notas,
    )
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Budget not found")
    return PresupuestoResponse(
        id=presupuesto.id,
        nombre=presupuesto.nombre,
        categoria=presupuesto.categoria,
        limite=presupuesto.limite,
        periodo=presupuesto.periodo,
        color=presupuesto.color,
        icono=presupuesto.icono,
        notas=presupuesto.notas,
        activo=presupuesto.activo,
    )


@router.delete("/presupuestos/{presupuesto_id}")
def delete_budget(presupuesto_id: int):
    """Deletes a budget."""
    if not db.delete_budget(presupuesto_id):
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"message": "Budget deleted"}


@router.get("/presupuestos/estado", response_model=list[EstadoPresupuesto])
def get_budget_status():
    """Gets current status for all budgets."""
    statuses = db.get_budget_status()
    return [EstadoPresupuesto(**e) for e in statuses]


# ==================== INSIGHTS ====================


@router.get("/insights", response_model=InsightsResponse)
def get_insights():
    """Gets financial insights and analytics."""
    insights = db.get_insights()
    return InsightsResponse(**insights)
