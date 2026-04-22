"""Tests para la API REST."""

from io import BytesIO
import tempfile
from pathlib import Path
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

# Necesitamos configurar la DB antes de importar la app


@pytest.fixture
def client():
    """Crea un cliente de test con DB temporal."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test_api.db"

        # Reemplazar el gestor de DB global
        from patrimonio.database import GestorDB

        test_db = GestorDB(db_path=db_path)

        # Importar y parchear
        from patrimonio.web import api

        original_db = api.db
        api.db = test_db

        from patrimonio.web.app import app

        with TestClient(app) as c:
            yield c, test_db

        # Cerrar conexión y restaurar
        test_db.engine.dispose()
        api.db = original_db


class TestAPIBancos:
    """Tests para endpoints de bancos."""

    def test_list_banks_vacio(self, client):
        """Lista vacía cuando no hay bancos."""
        client, db = client
        response = client.get("/api/bancos")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_bank(self, client):
        """Puede crear un banco."""
        client, db = client
        response = client.post(
            "/api/bancos",
            json={
                "nombre": "BBVA",
                "tipo_cuenta": "corriente",
                "saldo_inicial": "1000.00",
                "moneda": "EUR",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "BBVA"
        assert data["tipo_cuenta"] == "corriente"
        assert data["id"] is not None

    def test_list_banks_con_datos(self, client):
        """Lista bancos existentes."""
        client, db = client
        # Crear banco
        db.create_bank(
            nombre="Test Bank", tipo_cuenta="ahorro", saldo_inicial=Decimal("500")
        )

        response = client.get("/api/bancos")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "Test Bank"

    def test_get_bank(self, client):
        """Puede obtener un banco por ID."""
        client, db = client
        banco = db.create_bank(nombre="Mi Banco", tipo_cuenta="corriente")

        response = client.get(f"/api/bancos/{banco.id}")
        assert response.status_code == 200
        assert response.json()["nombre"] == "Mi Banco"

    def test_get_bank_inexistente(self, client):
        """Retorna 404 si el banco no existe."""
        client, db = client
        response = client.get("/api/bancos/99999")
        assert response.status_code == 404

    def test_eliminar_banco(self, client):
        """Puede eliminar (desactivar) un banco."""
        client, db = client
        banco = db.create_bank(nombre="A Eliminar", tipo_cuenta="corriente")

        response = client.delete(f"/api/bancos/{banco.id}")
        assert response.status_code == 200

        # Verificar que ya no aparece en la lista
        response = client.get("/api/bancos")
        assert len(response.json()) == 0


class TestAPITransacciones:
    """Tests para endpoints de transacciones."""

    def test_list_transactions_vacio(self, client):
        """Lista vacía cuando no hay transacciones."""
        client, db = client
        response = client.get("/api/transacciones")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_transaction_ingreso(self, client):
        """Puede crear un ingreso."""
        client, db = client
        banco = db.create_bank(nombre="Banco", tipo_cuenta="corriente")

        response = client.post(
            "/api/transacciones",
            json={
                "banco_id": banco.id,
                "tipo": "ingreso",
                "cantidad": "500.00",
                "descripcion": "Nómina",
                "categoria": "salario",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tipo"] == "ingreso"
        assert data["cantidad"] == "500.00"

    def test_create_transaction_gasto(self, client):
        """Puede crear un gasto."""
        client, db = client
        banco = db.create_bank(nombre="Banco", tipo_cuenta="corriente")

        response = client.post(
            "/api/transacciones",
            json={
                "banco_id": banco.id,
                "tipo": "gasto",
                "cantidad": "50.00",
                "descripcion": "Supermercado",
                "categoria": "alimentacion",
            },
        )
        assert response.status_code == 200
        assert response.json()["tipo"] == "gasto"

    def test_create_transaction_banco_inexistente(self, client):
        """Error 404 si el banco no existe."""
        client, db = client
        response = client.post(
            "/api/transacciones",
            json={
                "banco_id": 99999,
                "tipo": "gasto",
                "cantidad": "10.00",
                "descripcion": "Test",
                "categoria": "otros",
            },
        )
        assert response.status_code == 404

    def test_filtrar_transacciones_por_tipo(self, client):
        """Puede filtrar transacciones por tipo."""
        client, db = client
        from patrimonio.models import TipoTransaccion

        banco = db.create_bank(nombre="Banco", tipo_cuenta="corriente")
        db.create_transaction(
            banco_id=banco.id,
            tipo=TipoTransaccion.INGRESO,
            cantidad=Decimal("100"),
            descripcion="Ingreso",
            categoria="otros",
        )
        db.create_transaction(
            banco_id=banco.id,
            tipo=TipoTransaccion.GASTO,
            cantidad=Decimal("50"),
            descripcion="Gasto",
            categoria="otros",
        )

        response = client.get("/api/transacciones?tipo=ingreso")
        data = response.json()
        assert all(t["tipo"] == "ingreso" for t in data)

    def test_delete_transaction(self, client):
        """Puede eliminar una transacción."""
        client, db = client
        from patrimonio.models import TipoTransaccion

        banco = db.create_bank(nombre="Banco", tipo_cuenta="corriente")
        trans = db.create_transaction(
            banco_id=banco.id,
            tipo=TipoTransaccion.GASTO,
            cantidad=Decimal("10"),
            descripcion="A eliminar",
            categoria="otros",
        )

        response = client.delete(f"/api/transacciones/{trans.id}")
        assert response.status_code == 200

    def test_delete_transaction_inexistente(self, client):
        """Error 404 al eliminar transacción inexistente."""
        client, db = client
        response = client.delete("/api/transacciones/99999")
        assert response.status_code == 404

    def test_importar_gastos_extracto_csv(self, client):
        """Importa gastos desde CSV deduciendo columnas por nombre."""
        client, db = client
        banco = db.create_bank(nombre="Banco Import", tipo_cuenta="corriente")

        csv_content = (
            "Fecha,Descripción,Importe\n"
            "2026-03-01,Café,-3.50\n"
            "2026-03-02,Supermercado,-40.25\n"
            "2026-03-03,Nómina,1200.00\n"
        )
        response = client.post(
            "/api/transactions/import-expenses",
            data={"banco_id": str(banco.id), "categoria_default": "otros"},
            files={"statement_file": ("extracto.csv", csv_content, "text/csv")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["imported_count"] == 2
        assert data["skipped_count"] >= 1
        assert "Fecha" in data["detected_columns"].values()

        transacciones = db.list_transactions(banco_id=banco.id, limite=10)
        assert len(transacciones) == 2
        assert all(t.tipo.value == "gasto" for t in transacciones)

    def test_importar_gastos_extracto_excel(self, client):
        """Importa gastos desde un archivo Excel (.xlsx)."""
        client, db = client
        banco = db.create_bank(nombre="Banco Excel", tipo_cuenta="corriente")

        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["fecha operación", "concepto", "cargo"])
        sheet.append(["01/03/2026", "Restaurante", "25,00"])
        sheet.append(["02/03/2026", "Farmacia", "14,10"])

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        response = client.post(
            "/api/transactions/import-expenses",
            data={"banco_id": str(banco.id), "categoria_default": "salud"},
            files={
                "statement_file": (
                    "extracto.xlsx",
                    buffer.getvalue(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["imported_count"] == 2

        transacciones = db.list_transactions(banco_id=banco.id, limite=10)
        assert len(transacciones) == 2
        assert all(t.categoria == "salud" for t in transacciones)

    def test_importar_gastos_extracto_columnas_invalidas(self, client):
        """Devuelve 400 cuando no se pueden deducir columnas mínimas."""
        client, db = client
        banco = db.create_bank(nombre="Banco Error", tipo_cuenta="corriente")

        csv_content = "foo,bar,baz\n1,2,3\n"
        response = client.post(
            "/api/transactions/import-expenses",
            data={"banco_id": str(banco.id)},
            files={"statement_file": ("sin_columnas.csv", csv_content, "text/csv")},
        )

        assert response.status_code == 400


class TestAPISuscripciones:
    """Tests para endpoints de suscripciones."""

    def test_list_subscriptions_vacio(self, client):
        """Lista vacía cuando no hay suscripciones."""
        client, db = client
        response = client.get("/api/suscripciones")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_subscription(self, client):
        """Puede crear una suscripción."""
        client, db = client
        banco = db.create_bank(nombre="Banco", tipo_cuenta="corriente")

        response = client.post(
            "/api/suscripciones",
            json={
                "banco_id": banco.id,
                "nombre": "Netflix",
                "cantidad": "15.99",
                "frecuencia": "mensual",
                "categoria": "entretenimiento",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "Netflix"
        assert data["activa"] is True

    def test_create_subscription_banco_inexistente(self, client):
        """Error 404 si el banco no existe."""
        client, db = client
        response = client.post(
            "/api/suscripciones",
            json={
                "banco_id": 99999,
                "nombre": "Test",
                "cantidad": "10.00",
                "frecuencia": "mensual",
            },
        )
        assert response.status_code == 404

    def test_cancel_subscription(self, client):
        """Puede cancelar una suscripción."""
        client, db = client
        from patrimonio.models import Frecuencia

        banco = db.create_bank(nombre="Banco", tipo_cuenta="corriente")
        sub = db.create_subscription(
            banco_id=banco.id,
            nombre="Cancelar",
            cantidad=Decimal("10"),
            frecuencia=Frecuencia.MENSUAL,
        )

        response = client.delete(f"/api/suscripciones/{sub.id}")
        assert response.status_code == 200

    def test_cancel_subscription_inexistente(self, client):
        """Error 404 al cancelar suscripción inexistente."""
        client, db = client
        response = client.delete("/api/suscripciones/99999")
        assert response.status_code == 404


class TestAPIPatrimonio:
    """Tests para endpoints de patrimonio."""

    def test_list_net_worth_items_vacio(self, client):
        """Lista vacía cuando no hay patrimonio."""
        client, db = client
        response = client.get("/api/patrimonio")
        assert response.status_code == 200
        assert response.json() == []

    def test_crear_activo(self, client):
        """Puede crear un activo."""
        client, db = client
        response = client.post(
            "/api/patrimonio",
            json={
                "nombre": "Casa",
                "tipo": "activo",
                "valor": "200000.00",
                "descripcion": "Mi casa",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "Casa"
        assert data["tipo"] == "activo"

    def test_crear_pasivo(self, client):
        """Puede crear un pasivo."""
        client, db = client
        response = client.post(
            "/api/patrimonio",
            json={"nombre": "Hipoteca", "tipo": "pasivo", "valor": "150000.00"},
        )
        assert response.status_code == 200
        assert response.json()["tipo"] == "pasivo"

    def test_filtrar_patrimonio_por_tipo(self, client):
        """Puede filtrar patrimonio por tipo."""
        client, db = client
        db.create_net_worth_item(nombre="Activo", tipo="activo", valor=Decimal("1000"))
        db.create_net_worth_item(nombre="Pasivo", tipo="pasivo", valor=Decimal("500"))

        response = client.get("/api/patrimonio?tipo=activo")
        data = response.json()
        assert all(p["tipo"] == "activo" for p in data)

    def test_eliminar_patrimonio(self, client):
        """Puede eliminar un elemento del patrimonio."""
        client, db = client
        pat = db.create_net_worth_item(
            nombre="Eliminar", tipo="activo", valor=Decimal("100")
        )

        response = client.delete(f"/api/patrimonio/{pat.id}")
        assert response.status_code == 200

    def test_eliminar_patrimonio_inexistente(self, client):
        """Error 404 al eliminar patrimonio inexistente."""
        client, db = client
        response = client.delete("/api/patrimonio/99999")
        assert response.status_code == 404


class TestAPIResumen:
    """Tests para endpoints de resumen."""

    def test_obtener_resumen(self, client):
        """Puede obtener el resumen general."""
        client, db = client
        response = client.get("/api/resumen")
        assert response.status_code == 200
        data = response.json()
        assert "patrimonio_neto" in data
        assert "total_bancos" in data
        assert "gasto_mensual_suscripciones" in data
        assert "resumen_mes_actual" in data

    def test_gastos_por_categoria(self, client):
        """Puede obtener gastos por categoría."""
        client, db = client
        response = client.get("/api/estadisticas/gastos-por-categoria")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_evolucion_mensual(self, client):
        """Puede obtener la evolución mensual."""
        client, db = client
        response = client.get("/api/estadisticas/evolucion-mensual?meses=6")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 6

    def test_saldo_por_banco(self, client):
        """Puede obtener el saldo por banco."""
        client, db = client
        db.create_bank(
            nombre="Banco 1", tipo_cuenta="corriente", saldo_inicial=Decimal("1000")
        )

        response = client.get("/api/estadisticas/saldo-bancos")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert "nombre" in data[0]
        assert "saldo" in data[0]


class TestAPIPaginasHTML:
    """Tests para las páginas HTML."""

    def test_dashboard_page(self, client):
        """La página de dashboard carga correctamente."""
        client, db = client
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_bancos_page(self, client):
        """La página de bancos carga correctamente."""
        client, db = client
        response = client.get("/bancos")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_transacciones_page(self, client):
        """La página de transacciones carga correctamente."""
        client, db = client
        response = client.get("/transacciones")
        assert response.status_code == 200

    def test_suscripciones_page(self, client):
        """La página de suscripciones carga correctamente."""
        client, db = client
        response = client.get("/suscripciones")
        assert response.status_code == 200

    def test_patrimonio_page(self, client):
        """La página de patrimonio carga correctamente."""
        client, db = client
        response = client.get("/patrimonio")
        assert response.status_code == 200

    def test_presupuestos_page(self, client):
        """La página de presupuestos carga correctamente."""
        client, db = client
        response = client.get("/presupuestos")
        assert response.status_code == 200

    def test_insights_page(self, client):
        """La página de insights carga correctamente."""
        client, db = client
        response = client.get("/insights")
        assert response.status_code == 200


class TestAPIPresupuestos:
    """Tests para endpoints de presupuestos."""

    def test_list_budgets_vacio(self, client):
        """Lista vacía cuando no hay presupuestos."""
        client, db = client
        response = client.get("/api/presupuestos")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_budget(self, client):
        """Puede crear un presupuesto."""
        client, db = client
        response = client.post(
            "/api/presupuestos",
            json={
                "nombre": "Comida",
                "categoria": "alimentacion",
                "limite": "500.00",
                "periodo": "mensual",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "Comida"
        assert data["categoria"] == "alimentacion"
        assert float(data["limite"]) == 500.00
        assert data["periodo"] == "mensual"
        assert data["id"] is not None

    def test_list_budgets_con_datos(self, client):
        """Lista presupuestos existentes."""
        client, db = client
        from patrimonio.models import PeriodoPresupuesto

        db.create_budget(
            nombre="Transporte",
            categoria="transporte",
            limite=Decimal("200.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )

        response = client.get("/api/presupuestos")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "Transporte"

    def test_update_budget(self, client):
        """Puede actualizar un presupuesto."""
        client, db = client
        from patrimonio.models import PeriodoPresupuesto

        presupuesto = db.create_budget(
            nombre="Alimentación",
            categoria="alimentacion",
            limite=Decimal("500.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )

        response = client.put(
            f"/api/presupuestos/{presupuesto.id}", json={"limite": "600.00"}
        )
        assert response.status_code == 200
        assert float(response.json()["limite"]) == 600.00

    def test_delete_budget(self, client):
        """Puede eliminar un presupuesto."""
        client, db = client
        from patrimonio.models import PeriodoPresupuesto

        presupuesto = db.create_budget(
            nombre="Transporte",
            categoria="transporte",
            limite=Decimal("200.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )

        response = client.delete(f"/api/presupuestos/{presupuesto.id}")
        assert response.status_code == 200

        # Verificar que ya no aparece en la lista
        response = client.get("/api/presupuestos")
        assert len(response.json()) == 0

    def test_delete_budget_inexistente(self, client):
        """Retorna 404 al eliminar presupuesto inexistente."""
        client, db = client
        response = client.delete("/api/presupuestos/99999")
        assert response.status_code == 404

    def test_estado_presupuestos(self, client):
        """Puede obtener el estado de presupuestos."""
        client, db = client
        from patrimonio.models import PeriodoPresupuesto

        db.create_budget(
            nombre="Alimentación",
            categoria="alimentacion",
            limite=Decimal("500.00"),
            periodo=PeriodoPresupuesto.MENSUAL,
        )

        response = client.get("/api/presupuestos/estado")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "gastado" in data[0]
        assert "porcentaje" in data[0]
        assert "disponible" in data[0]


class TestAPIInsights:
    """Tests para endpoints de insights."""

    def test_get_insights(self, client):
        """Puede obtener insights financieros."""
        client, db = client
        response = client.get("/api/insights")
        assert response.status_code == 200
        data = response.json()
        # Verifica estructura según InsightsResponse
        assert "tasa_ahorro" in data
        assert "resumen_mes" in data
        assert "alertas" in data

    def test_insights_con_transacciones(self, client):
        """Los insights incluyen datos con transacciones."""
        client, db = client
        from patrimonio.models import TipoTransaccion
        from datetime import date

        # Crear banco y transacciones
        banco = db.create_bank(nombre="Test", tipo_cuenta="corriente")
        db.create_transaction(
            banco_id=banco.id,
            tipo=TipoTransaccion.INGRESO,
            cantidad=Decimal("2000.00"),
            descripcion="Salario",
            categoria="salario",
            fecha=date.today(),
        )
        db.create_transaction(
            banco_id=banco.id,
            tipo=TipoTransaccion.GASTO,
            cantidad=Decimal("500.00"),
            descripcion="Compra",
            categoria="alimentacion",
            fecha=date.today(),
        )

        response = client.get("/api/insights")
        assert response.status_code == 200
        data = response.json()
        # Verificar estructura básica
        assert "tasa_ahorro" in data
        assert "resumen_mes" in data
