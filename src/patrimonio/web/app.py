"""FastAPI web application for FastFinance."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from patrimonio.web.api import router as api_router

# Configure paths
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

# Create app
app = FastAPI(
    title="Patrimonio",
    description="Gestor de Patrimonio Personal",
    version="1.0.0",
)

# Configure templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API routes
app.include_router(api_router)


# ==================== PAGE ROUTES ====================


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"active_page": "dashboard"},
    )


@app.get("/bancos", response_class=HTMLResponse)
async def banks_page(request: Request):
    """Bank management page."""
    return templates.TemplateResponse(
        request,
        "bancos.html",
        {"active_page": "bancos"},
    )


@app.get("/transacciones", response_class=HTMLResponse)
async def transactions_page(request: Request):
    """Transaction management page."""
    return templates.TemplateResponse(
        request,
        "transacciones.html",
        {"active_page": "transacciones"},
    )


@app.get("/suscripciones", response_class=HTMLResponse)
async def subscriptions_page(request: Request):
    """Subscription management page."""
    return templates.TemplateResponse(
        request,
        "suscripciones.html",
        {"active_page": "suscripciones"},
    )


@app.get("/patrimonio", response_class=HTMLResponse)
async def net_worth_page(request: Request):
    """Net worth management page."""
    return templates.TemplateResponse(
        request,
        "patrimonio.html",
        {"active_page": "patrimonio"},
    )


@app.get("/presupuestos", response_class=HTMLResponse)
async def budgets_page(request: Request):
    """Budget management page."""
    return templates.TemplateResponse(
        request,
        "presupuestos.html",
        {"active_page": "presupuestos"},
    )


@app.get("/insights", response_class=HTMLResponse)
async def insights_page(request: Request):
    """Financial insights page."""
    return templates.TemplateResponse(
        request,
        "insights.html",
        {"active_page": "insights"},
    )


def main():
    """Entry point to run the web server."""
    import uvicorn

    uvicorn.run(
        "patrimonio.web.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
