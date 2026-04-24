"""Tests para el gestor de base de datos."""

from datetime import date
from decimal import Decimal

from patrimonio.models import Frecuencia, TipoTransaccion


class TestGestorDBBancos:
    """Tests para operaciones de bancos."""

    def test_create_bank(self, db_temp):
        """Puede crear un banco nuevo."""
        banco = db_temp.create_bank(
            nombre="Mi Banco",
            tipo_cuenta="ahorro",
            saldo_inicial=Decimal("500.00"),
            moneda="EUR",
        )
        assert banco.id is not None
        assert banco.nombre == "Mi Banco"
        assert banco.tipo_cuenta == "ahorro"
        assert banco.saldo_inicial == Decimal("500.00")
        assert banco.activo is True

    def test_list_banks(self, db_temp, banco_ejemplo):
        """Puede listar los bancos activos."""
        bancos = db_temp.list_banks()
        assert len(bancos) >= 1
        assert any(b.nombre == "Banco Test" for b in bancos)

    def test_list_banks_solo_activos(self, db_temp):
        """Por defecto solo lista bancos activos."""
        banco = db_temp.create_bank(
            nombre="Banco Inactivo",
            tipo_cuenta="corriente",
        )
        # Desactivar banco
        with db_temp.get_session() as session:
            from patrimonio.models import Banco

            b = session.get(Banco, banco.id)
            b.activo = False
            session.commit()

        bancos = db_temp.list_banks(solo_activos=True)
        assert not any(b.nombre == "Banco Inactivo" for b in bancos)

    def test_get_bank(self, db_temp, banco_ejemplo):
        """Puede obtener un banco por ID."""
        banco = db_temp.get_bank(banco_ejemplo.id)
        assert banco is not None
        assert banco.nombre == "Banco Test"

    def test_get_bank_inexistente(self, db_temp):
        """Retorna None si el banco no existe."""
        banco = db_temp.get_bank(99999)
        assert banco is None

    def test_calculate_bank_balance_inicial(self, db_temp, banco_ejemplo):
        """El saldo inicial se calcula correctamente."""
        saldo = db_temp.calculate_bank_balance(banco_ejemplo.id)
        assert saldo == Decimal("1000.00")

    def test_calculate_bank_balance_con_transacciones(self, db_temp, banco_ejemplo):
        """El saldo se calcula con ingresos y gastos."""
        db_temp.create_transaction(
            banco_id=banco_ejemplo.id,
            tipo=TipoTransaccion.INGRESO,
            cantidad=Decimal("200.00"),
            descripcion="Ingreso",
            categoria="otros",
        )
        db_temp.create_transaction(
            banco_id=banco_ejemplo.id,
            tipo=TipoTransaccion.GASTO,
            cantidad=Decimal("50.00"),
            descripcion="Gasto",
            categoria="otros",
        )

        saldo = db_temp.calculate_bank_balance(banco_ejemplo.id)
        # 1000 (inicial) + 200 (ingreso) - 50 (gasto) = 1150
        assert saldo == Decimal("1150.00")


class TestGestorDBTransacciones:
    """Tests para operaciones de transacciones."""

    def test_create_transaction_ingreso(self, db_temp, banco_ejemplo):
        """Puede crear una transacción de ingreso."""
        trans = db_temp.create_transaction(
            banco_id=banco_ejemplo.id,
            tipo=TipoTransaccion.INGRESO,
            cantidad=Decimal("100.00"),
            descripcion="Pago recibido",
            categoria="freelance",
        )
        assert trans.id is not None
        assert trans.tipo == TipoTransaccion.INGRESO
        assert trans.cantidad == Decimal("100.00")

    def test_create_transaction_gasto(self, db_temp, banco_ejemplo):
        """Puede crear una transacción de gasto."""
        trans = db_temp.create_transaction(
            banco_id=banco_ejemplo.id,
            tipo=TipoTransaccion.GASTO,
            cantidad=Decimal("25.00"),
            descripcion="Café",
            categoria="alimentacion",
        )
        assert trans.id is not None
        assert trans.tipo == TipoTransaccion.GASTO

    def test_list_transactions(self, db_temp, banco_ejemplo):
        """Puede listar transacciones."""
        # Crear algunas transacciones
        for i in range(5):
            db_temp.create_transaction(
                banco_id=banco_ejemplo.id,
                tipo=TipoTransaccion.GASTO,
                cantidad=Decimal("10.00"),
                descripcion=f"Gasto {i}",
                categoria="otros",
            )

        transacciones = db_temp.list_transactions()
        assert len(transacciones) >= 5

    def test_list_transactions_filtro_tipo(self, db_temp, transaccion_ingreso, transaccion_gasto):
        """Puede filtrar transacciones por tipo."""
        ingresos = db_temp.list_transactions(tipo=TipoTransaccion.INGRESO)
        gastos = db_temp.list_transactions(tipo=TipoTransaccion.GASTO)

        assert all(t.tipo == TipoTransaccion.INGRESO for t in ingresos)
        assert all(t.tipo == TipoTransaccion.GASTO for t in gastos)

    def test_list_transactions_filtro_banco(self, db_temp, banco_ejemplo):
        """Puede filtrar transacciones por banco."""
        # Crear otro banco
        otro_banco = db_temp.create_bank(nombre="Otro Banco", tipo_cuenta="ahorro")

        db_temp.create_transaction(
            banco_id=banco_ejemplo.id,
            tipo=TipoTransaccion.GASTO,
            cantidad=Decimal("10.00"),
            descripcion="En banco test",
            categoria="otros",
        )
        db_temp.create_transaction(
            banco_id=otro_banco.id,
            tipo=TipoTransaccion.GASTO,
            cantidad=Decimal("20.00"),
            descripcion="En otro banco",
            categoria="otros",
        )

        transacciones = db_temp.list_transactions(banco_id=banco_ejemplo.id)
        assert all(t.banco_id == banco_ejemplo.id for t in transacciones)

    def test_list_transactions_limite(self, db_temp, banco_ejemplo):
        """Respeta el límite de resultados."""
        for i in range(10):
            db_temp.create_transaction(
                banco_id=banco_ejemplo.id,
                tipo=TipoTransaccion.GASTO,
                cantidad=Decimal("5.00"),
                descripcion=f"Gasto {i}",
                categoria="otros",
            )

        transacciones = db_temp.list_transactions(limite=3)
        assert len(transacciones) == 3

    def test_delete_transaction(self, db_temp, transaccion_gasto):
        """Puede eliminar una transacción."""
        trans_id = transaccion_gasto.id
        resultado = db_temp.delete_transaction(trans_id)
        assert resultado is True

        # Verificar que ya no existe
        transacciones = db_temp.list_transactions()
        assert not any(t.id == trans_id for t in transacciones)

    def test_delete_transaction_inexistente(self, db_temp):
        """Retorna False al eliminar transacción inexistente."""
        resultado = db_temp.delete_transaction(99999)
        assert resultado is False


class TestGestorDBSuscripciones:
    """Tests para operaciones de suscripciones."""

    def test_create_subscription(self, db_temp, banco_ejemplo):
        """Puede crear una suscripción."""
        sub = db_temp.create_subscription(
            banco_id=banco_ejemplo.id,
            nombre="Spotify",
            cantidad=Decimal("9.99"),
            frecuencia=Frecuencia.MENSUAL,
        )
        assert sub.id is not None
        assert sub.nombre == "Spotify"
        assert sub.activa is True

    def test_list_subscriptions(self, db_temp, suscripcion_ejemplo):
        """Puede listar suscripciones activas."""
        suscripciones = db_temp.list_subscriptions()
        assert len(suscripciones) >= 1
        assert any(s.nombre == "Netflix Test" for s in suscripciones)

    def test_list_subscriptions_solo_activas(self, db_temp, banco_ejemplo):
        """Por defecto solo lista suscripciones activas."""
        sub = db_temp.create_subscription(
            banco_id=banco_ejemplo.id,
            nombre="Cancelada",
            cantidad=Decimal("5.00"),
            frecuencia=Frecuencia.MENSUAL,
        )
        db_temp.cancel_subscription(sub.id)

        suscripciones = db_temp.list_subscriptions(solo_activas=True)
        assert not any(s.nombre == "Cancelada" for s in suscripciones)

    def test_cancel_subscription(self, db_temp, suscripcion_ejemplo):
        """Puede cancelar una suscripción."""
        resultado = db_temp.cancel_subscription(suscripcion_ejemplo.id)
        assert resultado is True

    def test_cancel_subscription_inexistente(self, db_temp):
        """Retorna False al cancelar suscripción inexistente."""
        resultado = db_temp.cancel_subscription(99999)
        assert resultado is False

    def test_calculate_monthly_subscription_cost(self, db_temp, banco_ejemplo):
        """Calcula el gasto mensual total en suscripciones."""
        db_temp.create_subscription(
            banco_id=banco_ejemplo.id,
            nombre="Sub 1",
            cantidad=Decimal("10.00"),
            frecuencia=Frecuencia.MENSUAL,
        )
        db_temp.create_subscription(
            banco_id=banco_ejemplo.id,
            nombre="Sub 2",
            cantidad=Decimal("20.00"),
            frecuencia=Frecuencia.MENSUAL,
        )

        total = db_temp.calculate_monthly_subscription_cost()
        assert total >= Decimal("30.00")


class TestGestorDBPatrimonio:
    """Tests para operaciones de patrimonio."""

    def test_create_net_worth_item_activo(self, db_temp):
        """Puede crear un activo."""
        activo = db_temp.create_net_worth_item(
            nombre="Coche",
            tipo="activo",
            valor=Decimal("15000.00"),
            descripcion="Mi coche",
        )
        assert activo.id is not None
        assert activo.tipo == "activo"
        assert activo.valor == Decimal("15000.00")

    def test_create_net_worth_item_pasivo(self, db_temp):
        """Puede crear un pasivo."""
        pasivo = db_temp.create_net_worth_item(
            nombre="Préstamo",
            tipo="pasivo",
            valor=Decimal("5000.00"),
        )
        assert pasivo.id is not None
        assert pasivo.tipo == "pasivo"

    def test_list_net_worth_items(self, db_temp, patrimonio_activo, patrimonio_pasivo):
        """Puede listar todo el patrimonio."""
        items = db_temp.list_net_worth_items()
        assert len(items) >= 2

    def test_list_net_worth_items_filtro_tipo(self, db_temp, patrimonio_activo, patrimonio_pasivo):
        """Puede filtrar patrimonio por tipo."""
        activos = db_temp.list_net_worth_items(tipo="activo")
        pasivos = db_temp.list_net_worth_items(tipo="pasivo")

        assert all(p.tipo == "activo" for p in activos)
        assert all(p.tipo == "pasivo" for p in pasivos)

    def test_calculate_net_worth(
        self, db_temp, banco_ejemplo, patrimonio_activo, patrimonio_pasivo
    ):
        """Calcula el patrimonio neto correctamente."""
        # banco_ejemplo: 1000€
        # patrimonio_activo: 200000€
        # patrimonio_pasivo: 150000€
        # Patrimonio neto = 1000 + 200000 - 150000 = 51000

        neto = db_temp.calculate_net_worth()
        assert neto == Decimal("51000.00")


class TestGestorDBResumen:
    """Tests para resúmenes y estadísticas."""

    def test_monthly_summary(self, db_temp, banco_ejemplo):
        """Genera resumen mensual correcto."""
        hoy = date.today()

        # Crear transacciones del mes actual
        db_temp.create_transaction(
            banco_id=banco_ejemplo.id,
            tipo=TipoTransaccion.INGRESO,
            cantidad=Decimal("1000.00"),
            descripcion="Ingreso mes",
            categoria="salario",
            fecha=hoy,
        )
        db_temp.create_transaction(
            banco_id=banco_ejemplo.id,
            tipo=TipoTransaccion.GASTO,
            cantidad=Decimal("300.00"),
            descripcion="Gasto mes",
            categoria="otros",
            fecha=hoy,
        )

        resumen = db_temp.monthly_summary(hoy.month, hoy.year)

        assert resumen["mes"] == hoy.month
        assert resumen["año"] == hoy.year
        assert resumen["ingresos"] >= Decimal("1000.00")
        assert resumen["gastos"] >= Decimal("300.00")
        assert resumen["balance"] == resumen["ingresos"] - resumen["gastos"]

    def test_monthly_summary_sin_transacciones(self, db_temp):
        """El resumen sin transacciones tiene valores en cero."""
        resumen = db_temp.monthly_summary(1, 2020)

        assert resumen["ingresos"] == Decimal("0")
        assert resumen["gastos"] == Decimal("0")
        assert resumen["balance"] == Decimal("0")


class TestGestorDBPresupuestos:
    """Tests para operaciones de presupuestos."""

    def test_create_budget(self, db_temp):
        """Puede crear un presupuesto."""
        from patrimonio.models import PeriodoPresupuesto

        presupuesto = db_temp.create_budget(
            nombre="Alimentación",
            categoria="alimentacion",
            limite=Decimal("500.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )
        assert presupuesto.id is not None
        assert presupuesto.nombre == "Alimentación"
        assert presupuesto.categoria == "alimentacion"
        assert presupuesto.limite == Decimal("500.00")
        assert presupuesto.periodo == PeriodoPresupuesto.MENSUAL
        assert presupuesto.activo is True

    def test_create_budget_anual(self, db_temp):
        """Puede crear un presupuesto anual."""
        from patrimonio.models import PeriodoPresupuesto

        presupuesto = db_temp.create_budget(
            nombre="Ocio Anual",
            categoria="ocio",
            limite=Decimal("1200.00"),
            periodo=PeriodoPresupuesto.ANUAL,
        )
        assert presupuesto.periodo == PeriodoPresupuesto.ANUAL

    def test_list_budgets(self, db_temp):
        """Puede listar presupuestos."""
        from patrimonio.models import PeriodoPresupuesto

        db_temp.create_budget(
            nombre="Alimentación",
            categoria="alimentacion",
            limite=Decimal("500.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )
        db_temp.create_budget(
            nombre="Transporte",
            categoria="transporte",
            limite=Decimal("200.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )

        presupuestos = db_temp.list_budgets()
        assert len(presupuestos) == 2

    def test_list_budgets_solo_activos(self, db_temp):
        """Por defecto solo lista presupuestos activos."""
        from patrimonio.models import PeriodoPresupuesto, Presupuesto

        presupuesto = db_temp.create_budget(
            nombre="Ocio",
            categoria="ocio",
            limite=Decimal("300.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )

        # Desactivar presupuesto
        with db_temp.get_session() as session:
            p = session.get(Presupuesto, presupuesto.id)
            p.activo = False
            session.commit()

        presupuestos = db_temp.list_budgets(solo_activos=True)
        assert not any(p.categoria == "ocio" for p in presupuestos)

    def test_get_budget(self, db_temp):
        """Puede obtener un presupuesto por ID."""
        from patrimonio.models import PeriodoPresupuesto

        presupuesto = db_temp.create_budget(
            nombre="Alimentación",
            categoria="alimentacion",
            limite=Decimal("500.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )

        obtenido = db_temp.get_budget(presupuesto.id)
        assert obtenido is not None
        assert obtenido.categoria == "alimentacion"

    def test_get_budget_inexistente(self, db_temp):
        """Retorna None si el presupuesto no existe."""
        presupuesto = db_temp.get_budget(99999)
        assert presupuesto is None

    def test_update_budget(self, db_temp):
        """Puede actualizar un presupuesto."""
        from patrimonio.models import PeriodoPresupuesto

        presupuesto = db_temp.create_budget(
            nombre="Alimentación",
            categoria="alimentacion",
            limite=Decimal("500.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )

        actualizado = db_temp.update_budget(
            presupuesto.id,
            limite=Decimal("600.00"),
        )
        assert actualizado is not None
        assert actualizado.limite == Decimal("600.00")

    def test_delete_budget(self, db_temp):
        """Puede eliminar un presupuesto."""
        from patrimonio.models import PeriodoPresupuesto

        presupuesto = db_temp.create_budget(
            nombre="Alimentación",
            categoria="alimentacion",
            limite=Decimal("500.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )

        resultado = db_temp.delete_budget(presupuesto.id)
        assert resultado is True

        # Verificar que ya no existe
        presupuestos = db_temp.list_budgets()
        assert not any(p.id == presupuesto.id for p in presupuestos)

    def test_delete_budget_inexistente(self, db_temp):
        """Retorna False al eliminar presupuesto inexistente."""
        resultado = db_temp.delete_budget(99999)
        assert resultado is False

    def test_calculate_budget_spending(self, db_temp, banco_ejemplo):
        """Calcula el gasto de una categoría en el periodo."""
        from datetime import date

        from patrimonio.models import PeriodoPresupuesto

        # Crear presupuesto
        db_temp.create_budget(
            nombre="Alimentación",
            categoria="alimentacion",
            limite=Decimal("500.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )

        # Crear gastos
        db_temp.create_transaction(
            banco_id=banco_ejemplo.id,
            tipo=TipoTransaccion.GASTO,
            cantidad=Decimal("100.00"),
            descripcion="Compra supermercado",
            categoria="alimentacion",
            fecha=date.today(),
        )
        db_temp.create_transaction(
            banco_id=banco_ejemplo.id,
            tipo=TipoTransaccion.GASTO,
            cantidad=Decimal("50.00"),
            descripcion="Restaurante",
            categoria="alimentacion",
            fecha=date.today(),
        )

        gasto = db_temp.calculate_budget_spending("alimentacion")
        assert gasto == Decimal("150.00")

    def test_get_budget_status(self, db_temp, banco_ejemplo):
        """Obtiene el estado de todos los presupuestos."""
        from datetime import date

        from patrimonio.models import PeriodoPresupuesto

        # Crear presupuesto
        db_temp.create_budget(
            nombre="Alimentación",
            categoria="alimentacion",
            limite=Decimal("500.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )

        # Crear gasto
        db_temp.create_transaction(
            banco_id=banco_ejemplo.id,
            tipo=TipoTransaccion.GASTO,
            cantidad=Decimal("250.00"),
            descripcion="Compra",
            categoria="alimentacion",
            fecha=date.today(),
        )

        estados = db_temp.get_budget_status()
        assert len(estados) == 1

        estado = estados[0]
        assert estado["categoria"] == "alimentacion"
        assert estado["gastado"] == 250.0
        assert estado["limite"] == 500.0
        assert estado["porcentaje"] == 50.0
        assert estado["disponible"] == 250.0

    def test_get_insights(self, db_temp, banco_ejemplo):
        """Obtiene insights financieros."""
        from datetime import date

        # Crear algunas transacciones
        db_temp.create_transaction(
            banco_id=banco_ejemplo.id,
            tipo=TipoTransaccion.INGRESO,
            cantidad=Decimal("2000.00"),
            descripcion="Salario",
            categoria="salario",
            fecha=date.today(),
        )
        db_temp.create_transaction(
            banco_id=banco_ejemplo.id,
            tipo=TipoTransaccion.GASTO,
            cantidad=Decimal("500.00"),
            descripcion="Alquiler",
            categoria="vivienda",
            fecha=date.today(),
        )

        insights = db_temp.get_insights()
        assert isinstance(insights, dict)
        # Debería tener claves esperadas
        assert "promedio_gastos" in insights or "tasa_ahorro" in insights or len(insights) > 0
