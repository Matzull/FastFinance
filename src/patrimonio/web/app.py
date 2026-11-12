"""FastAPI web application for FastFinance."""

import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from patrimonio.web.api import router as api_router

# Configure paths
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

basic_auth = HTTPBasic(auto_error=False)


def require_password(credentials: HTTPBasicCredentials | None = Depends(basic_auth)) -> None:
    """Protect every route with HTTP Basic auth when FASTFINANCE_PASSWORD is set.

    Any username is accepted; only the password is checked.
    """
    expected = os.environ.get("FASTFINANCE_PASSWORD")
    if not expected:
        return
    if credentials is None or not secrets.compare_digest(
        credentials.password.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": 'Basic realm="FastFinance"'},
        )


# Create app
app = FastAPI(
    title="Patrimonio",
    description="Gestor de Patrimonio Personal",
    version="1.0.0",
    dependencies=[Depends(require_password)],
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
    import dotenv
    import uvicorn

    dotenv.load_dotenv()
    host = os.environ.get("FASTFINANCE_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "localhost"} and not os.environ.get("FASTFINANCE_PASSWORD"):
        print(
            f"⚠️  Serving on {host} without FASTFINANCE_PASSWORD: anyone on the network can access it"
        )

    uvicorn.run(
        "patrimonio.web.app:app",
        host=host,
        port=int(os.environ.get("FASTFINANCE_PORT", "8000")),
        reload=os.environ.get("FASTFINANCE_RELOAD", "").lower() in {"1", "true", "yes"},
    )


if __name__ == "__main__":
    main()
