"""Tests para los modelos de datos."""

from decimal import Decimal


from patrimonio.models import (
    TipoTransaccion,
    Frecuencia,
    CategoriaGasto,
    CategoriaIngreso,
    PeriodoPresupuesto,
)


class TestEnums:
    """Tests para los enums."""

    def test_tipo_transaccion_valores(self):
        """Verifica los valores de TipoTransaccion."""
        assert TipoTransaccion.INGRESO.value == "ingreso"
        assert TipoTransaccion.GASTO.value == "gasto"
        assert TipoTransaccion.TRANSFERENCIA.value == "transferencia"

    def test_frecuencia_valores(self):
        """Verifica los valores de Frecuencia."""
        assert Frecuencia.DIARIA.value == "diaria"
        assert Frecuencia.SEMANAL.value == "semanal"
        assert Frecuencia.MENSUAL.value == "mensual"
        assert Frecuencia.ANUAL.value == "anual"

    def test_categoria_gasto_valores(self):
        """Verifica que existen todas las categorías de gasto."""
        categorias = [cat.value for cat in CategoriaGasto]
        assert "alimentacion" in categorias
        assert "transporte" in categorias
        assert "vivienda" in categorias
        assert "suscripciones" in categorias
        assert "otros" in categorias

    def test_categoria_ingreso_valores(self):
        """Verifica que existen todas las categorías de ingreso."""
        categorias = [cat.value for cat in CategoriaIngreso]
        assert "salario" in categorias
        assert "freelance" in categorias
        assert "inversiones" in categorias
        assert "otros" in categorias


class TestSuscripcionCostoMensual:
    """Tests para el cálculo de costo mensual de suscripciones."""

    def test_costo_mensual_frecuencia_mensual(self, suscripcion_ejemplo):
        """El costo mensual de una suscripción mensual es igual a la cantidad."""
        # La suscripción de ejemplo es mensual con cantidad 15.99
        assert suscripcion_ejemplo.costo_mensual() == Decimal("15.99")

    def test_costo_mensual_frecuencia_anual(self, db_temp, banco_ejemplo):
        """El costo mensual de una suscripción anual es cantidad/12."""
        sub = db_temp.create_subscription(
            banco_id=banco_ejemplo.id,
            nombre="Anual Test",
            cantidad=Decimal("120.00"),
            frecuencia=Frecuencia.ANUAL,
        )
        assert sub.costo_mensual() == Decimal("10.00")

    def test_costo_mensual_frecuencia_semanal(self, db_temp, banco_ejemplo):
        """El costo mensual de una suscripción semanal es cantidad * 4.33."""
        sub = db_temp.create_subscription(
            banco_id=banco_ejemplo.id,
            nombre="Semanal Test",
            cantidad=Decimal("10.00"),
            frecuencia=Frecuencia.SEMANAL,
        )
        expected = Decimal("10.00") * Decimal("4.33")
        assert sub.costo_mensual() == expected

    def test_costo_mensual_frecuencia_diaria(self, db_temp, banco_ejemplo):
        """El costo mensual de una suscripción diaria es cantidad * 30."""
        sub = db_temp.create_subscription(
            banco_id=banco_ejemplo.id,
            nombre="Diaria Test",
            cantidad=Decimal("1.00"),
            frecuencia=Frecuencia.DIARIA,
        )
        assert sub.costo_mensual() == Decimal("30.00")


class TestModeloRepr:
    """Tests para las representaciones string de los modelos."""

    def test_banco_repr(self, banco_ejemplo):
        """Verifica la representación del Banco."""
        repr_str = repr(banco_ejemplo)
        assert "Banco" in repr_str
        assert "Banco Test" in repr_str
        assert "corriente" in repr_str

    def test_transaccion_ingreso_repr(self, transaccion_ingreso):
        """Verifica la representación de un ingreso."""
        repr_str = repr(transaccion_ingreso)
        assert "+" in repr_str
        assert "500" in repr_str

    def test_transaccion_gasto_repr(self, transaccion_gasto):
        """Verifica la representación de un gasto."""
        repr_str = repr(transaccion_gasto)
        assert "-" in repr_str
        assert "100" in repr_str

    def test_suscripcion_repr(self, suscripcion_ejemplo):
        """Verifica la representación de una suscripción."""
        repr_str = repr(suscripcion_ejemplo)
        assert "Netflix Test" in repr_str
        assert "15.99" in repr_str
        assert "mensual" in repr_str

    def test_patrimonio_repr(self, patrimonio_activo):
        """Verifica la representación del patrimonio."""
        repr_str = repr(patrimonio_activo)
        assert "Casa Test" in repr_str


class TestPeriodoPresupuesto:
    """Tests para el enum PeriodoPresupuesto."""

    def test_periodo_presupuesto_valores(self):
        """Verifica los valores del periodo de presupuesto."""
        assert PeriodoPresupuesto.SEMANAL.value == "semanal"
        assert PeriodoPresupuesto.MENSUAL.value == "mensual"
        assert PeriodoPresupuesto.ANUAL.value == "anual"

    def test_periodos_disponibles(self):
        """Verifica que existen todos los periodos esperados."""
        periodos = [p.value for p in PeriodoPresupuesto]
        assert "semanal" in periodos
        assert "mensual" in periodos
        assert "anual" in periodos


class TestPresupuestoModelo:
    """Tests para el modelo Presupuesto."""

    def test_create_budget(self, db_temp):
        """Puede crear un presupuesto básico."""
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
        assert presupuesto.activo is True

    def test_presupuesto_periodo(self, db_temp):
        """El presupuesto tiene periodo configurado."""
        presupuesto = db_temp.create_budget(
            nombre="Ocio",
            categoria="ocio",
            limite=Decimal("300.00"),
            periodo=PeriodoPresupuesto.ANUAL,
        )
        assert presupuesto.periodo == PeriodoPresupuesto.ANUAL

    def test_presupuesto_repr(self, db_temp):
        """Verifica la representación del presupuesto."""
        presupuesto = db_temp.create_budget(
            nombre="Transporte",
            categoria="transporte",
            limite=Decimal("200.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )
        repr_str = repr(presupuesto)
        assert "Transporte" in repr_str
        assert "200" in repr_str
