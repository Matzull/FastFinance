"""Command-line interface for FastFinance."""

from datetime import date
from decimal import Decimal

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from patrimonio.database import GestorDB
from patrimonio.models import (
    CategoriaGasto,
    CategoriaIngreso,
    Frecuencia,
    TipoTransaccion,
)

app = typer.Typer(help="💰 Personal Finance Manager")
console = Console()
db = GestorDB()


# ==================== BANKS ====================

banco_app = typer.Typer(help="Bank account management")
app.add_typer(banco_app, name="banco")


@banco_app.command("añadir")
def add_bank(
    nombre: str = typer.Option(..., "--nombre", "-n", help="Nombre del banco/cuenta"),
    tipo: str = typer.Option(
        ..., "--tipo", "-t", help="Tipo: corriente, ahorro, inversión"
    ),
    saldo: float = typer.Option(0.0, "--saldo", "-s", help="Saldo inicial"),
    moneda: str = typer.Option("EUR", "--moneda", "-m", help="Moneda"),
):
    """Adds a new bank account."""
    banco = db.create_bank(
        nombre=nombre,
        tipo_cuenta=tipo,
        saldo_inicial=Decimal(str(saldo)),
        moneda=moneda,
    )
    console.print(
        f"✅ Account '[bold green]{banco.nombre}[/]' created successfully (ID: {banco.id})"
    )


@banco_app.command("listar")
def list_banks():
    """Lists all bank accounts."""
    bancos = db.list_banks()

    if not bancos:
        console.print("[yellow]No bank accounts registered.[/]")
        return

    table = Table(title="🏦 Bank Accounts")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Name", style="green")
    table.add_column("Type", style="blue")
    table.add_column("Current Balance", style="yellow", justify="right")
    table.add_column("Currency")

    for banco in bancos:
        saldo = db.calculate_bank_balance(banco.id)
        color = "green" if saldo >= 0 else "red"
        table.add_row(
            str(banco.id),
            banco.nombre,
            banco.tipo_cuenta,
            f"[{color}]{saldo:,.2f}[/]",
            banco.moneda,
        )

    console.print(table)


# ==================== TRANSACTIONS ====================

transaccion_app = typer.Typer(help="Income and expense management")
app.add_typer(transaccion_app, name="transaccion")


@transaccion_app.command("ingreso")
def add_income_transaction(
    banco_id: int = typer.Option(..., "--banco", "-b", help="ID del banco"),
    cantidad: float = typer.Option(..., "--cantidad", "-c", help="Cantidad"),
    descripcion: str = typer.Option(..., "--descripcion", "-d", help="Descripción"),
    categoria: str = typer.Option("otros", "--categoria", "-cat", help="Categoría"),
):
    """Registers a new income transaction."""
    db.create_transaction(
        banco_id=banco_id,
        tipo=TipoTransaccion.INGRESO,
        cantidad=Decimal(str(cantidad)),
        descripcion=descripcion,
        categoria=categoria,
    )
    console.print(f"✅ Income [bold green]+{cantidad}€[/] registered")


@transaccion_app.command("gasto")
def add_expense_transaction(
    banco_id: int = typer.Option(..., "--banco", "-b", help="ID del banco"),
    cantidad: float = typer.Option(..., "--cantidad", "-c", help="Cantidad"),
    descripcion: str = typer.Option(..., "--descripcion", "-d", help="Descripción"),
    categoria: str = typer.Option("otros", "--categoria", "-cat", help="Categoría"),
):
    """Registers a new expense transaction."""
    db.create_transaction(
        banco_id=banco_id,
        tipo=TipoTransaccion.GASTO,
        cantidad=Decimal(str(cantidad)),
        descripcion=descripcion,
        categoria=categoria,
    )
    console.print(f"✅ Expense [bold red]-{cantidad}€[/] registered")


@transaccion_app.command("listar")
def list_transactions_cli(
    banco_id: int | None = typer.Option(
        None, "--banco", "-b", help="Filtrar por banco"
    ),
    limite: int = typer.Option(
        20, "--limite", "-l", help="Número máximo de transacciones"
    ),
):
    """Lists recent transactions."""
    transacciones = db.list_transactions(banco_id=banco_id, limite=limite)

    if not transacciones:
        console.print("[yellow]No transactions registered.[/]")
        return

    table = Table(title="📊 Transacciones")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Date", style="blue")
    table.add_column("Type", style="magenta")
    table.add_column("Amount", justify="right")
    table.add_column("Description", style="white")
    table.add_column("Category", style="dim")

    for t in transacciones:
        if t.tipo == TipoTransaccion.INGRESO:
            cantidad_str = f"[green]+{t.cantidad:,.2f}€[/]"
            tipo_str = "[green]Income[/]"
        else:
            cantidad_str = f"[red]-{t.cantidad:,.2f}€[/]"
            tipo_str = "[red]Expense[/]"

        table.add_row(
            str(t.id),
            str(t.fecha),
            tipo_str,
            cantidad_str,
            t.descripcion[:30],
            t.categoria,
        )

    console.print(table)


# ==================== SUBSCRIPTIONS ====================

suscripcion_app = typer.Typer(help="Recurring subscription management")
app.add_typer(suscripcion_app, name="suscripcion")


@suscripcion_app.command("añadir")
def add_subscription(
    banco_id: int = typer.Option(..., "--banco", "-b", help="ID del banco"),
    nombre: str = typer.Option(..., "--nombre", "-n", help="Nombre de la suscripción"),
    cantidad: float = typer.Option(..., "--cantidad", "-c", help="Cantidad"),
    frecuencia: str = typer.Option(
        "mensual",
        "--frecuencia",
        "-f",
        help="Frecuencia: diaria, semanal, mensual, anual",
    ),
):
    """Adds a new subscription."""
    freq = Frecuencia(frecuencia.lower())
    db.create_subscription(
        banco_id=banco_id,
        nombre=nombre,
        cantidad=Decimal(str(cantidad)),
        frecuencia=freq,
    )
    console.print(
        f"✅ Subscription '[bold cyan]{nombre}[/]' added ({cantidad}€/{frecuencia})"
    )


@suscripcion_app.command("listar")
def list_subscriptions_cli():
    """Lists all active subscriptions."""
    suscripciones = db.list_subscriptions()

    if not suscripciones:
        console.print("[yellow]No active subscriptions.[/]")
        return

    table = Table(title="🔄 Active Subscriptions")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Name", style="green")
    table.add_column("Amount", style="yellow", justify="right")
    table.add_column("Frequency", style="blue")
    table.add_column("Monthly Cost", style="red", justify="right")
    table.add_column("Since", style="dim")

    total_mensual = Decimal("0")
    for s in suscripciones:
        costo_mensual = s.costo_mensual()
        total_mensual += costo_mensual
        table.add_row(
            str(s.id),
            s.nombre,
            f"{s.cantidad:,.2f}€",
            s.frecuencia.value,
            f"{costo_mensual:,.2f}€",
            str(s.fecha_inicio),
        )

    console.print(table)
    console.print(
        f"\n💸 [bold red]Total monthly subscription cost: {total_mensual:,.2f}€[/]"
    )


@suscripcion_app.command("cancelar")
def cancel_subscription_cli(
    suscripcion_id: int = typer.Argument(..., help="ID de la suscripción a cancelar"),
):
    """Cancels a subscription."""
    if db.cancel_subscription(suscripcion_id):
        console.print(f"✅ Subscription {suscripcion_id} canceled")
    else:
        console.print(f"[red]❌ Subscription {suscripcion_id} not found[/]")


# ==================== NET WORTH ====================

patrimonio_app = typer.Typer(help="Assets and liabilities management")
app.add_typer(patrimonio_app, name="patrimonio")


@patrimonio_app.command("añadir")
def add_net_worth_item(
    nombre: str = typer.Option(..., "--nombre", "-n", help="Nombre del activo/pasivo"),
    tipo: str = typer.Option(..., "--tipo", "-t", help="Tipo: activo o pasivo"),
    valor: float = typer.Option(..., "--valor", "-v", help="Valor"),
    descripcion: str | None = typer.Option(
        None, "--descripcion", "-d", help="Descripción"
    ),
):
    """Adds a new asset or liability."""
    db.create_net_worth_item(
        nombre=nombre,
        tipo=tipo.lower(),
        valor=Decimal(str(valor)),
        descripcion=descripcion,
    )
    emoji = "📈" if tipo.lower() == "activo" else "📉"
    console.print(
        f"✅ {emoji} {tipo.capitalize()} '[bold]{nombre}[/]' added ({valor:,.2f}€)"
    )


@patrimonio_app.command("listar")
def list_net_worth_items_cli():
    """Lists all assets and liabilities."""
    activos = db.list_net_worth_items(tipo="activo")
    pasivos = db.list_net_worth_items(tipo="pasivo")

    if activos:
        table = Table(title="📈 Assets")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Name", style="green")
        table.add_column("Value", style="yellow", justify="right")
        table.add_column("Description", style="dim")

        for a in activos:
            table.add_row(
                str(a.id),
                a.nombre,
                f"{a.valor:,.2f}€",
                (a.descripcion or "")[:30],
            )
        console.print(table)

    if pasivos:
        table = Table(title="📉 Liabilities")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Name", style="red")
        table.add_column("Value", style="yellow", justify="right")
        table.add_column("Description", style="dim")

        for p in pasivos:
            table.add_row(
                str(p.id),
                p.nombre,
                f"{p.valor:,.2f}€",
                (p.descripcion or "")[:30],
            )
        console.print(table)


# ==================== SUMMARY ====================


@app.command("resumen")
def summary():
    """Shows an overall financial summary."""
    console.print(Panel.fit("💰 [bold]Net Worth Summary[/]", style="blue"))

    # Bank accounts
    bancos = db.list_banks()
    total_bancos = Decimal("0")

    if bancos:
        console.print("\n[bold]🏦 Bank Accounts:[/]")
        for banco in bancos:
            saldo = db.calculate_bank_balance(banco.id)
            total_bancos += saldo
            color = "green" if saldo >= 0 else "red"
            console.print(f"  • {banco.nombre}: [{color}]{saldo:,.2f}€[/]")
        console.print(f"  [bold]Total across bank accounts: {total_bancos:,.2f}€[/]")

    # Subscriptions
    gasto_suscripciones = db.calculate_monthly_subscription_cost()
    console.print(
        f"\n[bold]🔄 Monthly subscription cost:[/] [red]{gasto_suscripciones:,.2f}€[/]"
    )

    # Net worth
    patrimonio_neto = db.calculate_net_worth()
    color = "green" if patrimonio_neto >= 0 else "red"
    console.print(f"\n[bold]💎 Net Worth:[/] [{color}]{patrimonio_neto:,.2f}€[/]")

    # Current month summary
    hoy = date.today()
    resumen_mes = db.monthly_summary(hoy.month, hoy.year)
    console.print(f"\n[bold]📅 Monthly Summary ({hoy.strftime('%B %Y')}):[/]")
    console.print(f"  • Income: [green]+{resumen_mes['ingresos']:,.2f}€[/]")
    console.print(f"  • Expenses: [red]-{resumen_mes['gastos']:,.2f}€[/]")
    balance_color = "green" if resumen_mes["balance"] >= 0 else "red"
    console.print(f"  • Balance: [{balance_color}]{resumen_mes['balance']:,.2f}€[/]")


@app.command("categorias")
def show_categories():
    """Shows available categories."""
    console.print("[bold]📂 Expense Categories:[/]")
    for cat in CategoriaGasto:
        console.print(f"  • {cat.value}")

    console.print("\n[bold]📂 Income Categories:[/]")
    for cat in CategoriaIngreso:
        console.print(f"  • {cat.value}")


def main():
    app()


if __name__ == "__main__":
    main()
