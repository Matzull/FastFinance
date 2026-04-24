"""Configuración de pytest y fixtures compartidas."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from patrimonio.database import GestorDB
from patrimonio.models import Frecuencia, TipoTransaccion


@pytest.fixture
def db_temp():
    """Crea una base de datos temporal para tests."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "test_patrimonio.db"
        db = GestorDB(db_path=db_path)
        yield db
        # Cerrar conexión explícitamente
        db.engine.dispose()


@pytest.fixture
def banco_ejemplo(db_temp):
    """Crea un banco de ejemplo."""
    return db_temp.create_bank(
        nombre="Banco Test",
        tipo_cuenta="corriente",
        saldo_inicial=Decimal("1000.00"),
        moneda="EUR",
        notas="Banco para tests",
    )


@pytest.fixture
def transaccion_ingreso(db_temp, banco_ejemplo):
    """Crea una transacción de ingreso de ejemplo."""
    return db_temp.create_transaction(
        banco_id=banco_ejemplo.id,
        tipo=TipoTransaccion.INGRESO,
        cantidad=Decimal("500.00"),
        descripcion="Ingreso test",
        categoria="salario",
        fecha=date.today(),
    )


@pytest.fixture
def transaccion_gasto(db_temp, banco_ejemplo):
    """Crea una transacción de gasto de ejemplo."""
    return db_temp.create_transaction(
        banco_id=banco_ejemplo.id,
        tipo=TipoTransaccion.GASTO,
        cantidad=Decimal("100.00"),
        descripcion="Gasto test",
        categoria="alimentacion",
        fecha=date.today(),
    )


@pytest.fixture
def suscripcion_ejemplo(db_temp, banco_ejemplo):
    """Crea una suscripción de ejemplo."""
    return db_temp.create_subscription(
        banco_id=banco_ejemplo.id,
        nombre="Netflix Test",
        cantidad=Decimal("15.99"),
        frecuencia=Frecuencia.MENSUAL,
        fecha_inicio=date.today(),
        categoria="suscripciones",
    )


@pytest.fixture
def patrimonio_activo(db_temp):
    """Crea un activo de ejemplo."""
    return db_temp.create_net_worth_item(
        nombre="Casa Test",
        tipo="activo",
        valor=Decimal("200000.00"),
        descripcion="Casa de prueba",
    )


@pytest.fixture
def patrimonio_pasivo(db_temp):
    """Crea un pasivo de ejemplo."""
    return db_temp.create_net_worth_item(
        nombre="Hipoteca Test",
        tipo="pasivo",
        valor=Decimal("150000.00"),
        descripcion="Hipoteca de prueba",
    )
