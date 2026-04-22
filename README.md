# FastFinance (Patrimonio)

FastFinance is a personal finance tracker built in Python.
It includes a FastAPI web app, CLI tooling, a Telegram bot (with OCR support), and a Kivy mobile client.

## Features

- Bank accounts and balances
- Income and expense tracking
- Subscription management
- Net worth tracking (assets and liabilities)
- Budgets and financial insights
- Statement import for expenses (CSV/XLSX)
- Telegram bot support with OCR pipeline
- Mobile app for Android/Desktop (Kivy/KivyMD)

## Tech Stack

- Python 3.12+
- FastAPI + Jinja2 templates
- SQLAlchemy
- Typer + Rich (CLI)
- Python Telegram Bot
- PaddleOCR / OpenAI Vision fallback paths
- Kivy + KivyMD (mobile)
- `uv` for dependency management and running scripts

## Project Structure

```text
src/patrimonio/
	cli.py            # CLI entrypoint
	database.py       # DB access layer
	models.py         # SQLAlchemy models
	web/              # FastAPI app, API routes, templates
	telegram/         # Telegram bot + OCR flow
	mobile/           # Kivy mobile client
tests/              # API/DB/model/bot/mobile tests
```

## Quick Start

### 1) Install dependencies

```bash
uv sync
```

### 2) Run the web app

```bash
uv run fastfinance-web
```

Open `http://127.0.0.1:8000`.

### 3) (Optional) Run all local services

```bash
uv run python run.py
```

This starts the web server and, if configured, the Telegram bot.

## Available Commands

- `uv run fastfinance-web`: run FastAPI + web UI
- `uv run fastfinance-bot`: run Telegram bot
- `uv run fastfinance-mobile`: run Kivy mobile client
- `uv run fastfinance --help`: CLI help

## CLI Examples

```bash
# Add bank account
uv run fastfinance banco añadir --nombre "Main" --tipo corriente --saldo 1200

# Register expense
uv run fastfinance transaccion gasto --banco 1 --cantidad 54.20 --descripcion "Groceries" --categoria alimentacion

# List recent transactions
uv run fastfinance transaccion listar --limite 10
```

## Telegram Bot Setup

Set bot token in your environment:

```bash
export TELEGRAM_BOT_TOKEN="<your-token>"
```

Optional OCR fallback key:

```bash
export OPENAI_API_KEY="<your-openai-key>"
```

Then run:

```bash
uv run fastfinance-bot
```

## Mobile App

Install mobile extras:

```bash
uv pip install -e ".[mobile]"
```

Run the app:

```bash
uv run fastfinance-mobile
```

Set backend base URL in the app settings:

- `http://127.0.0.1:8000` for local desktop testing
- `http://<your-lan-ip>:8000` for Android device testing on local network

## Android Debug Build

`buildozer.spec` is included.

```bash
pip install buildozer cython
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH="$JAVA_HOME/bin:$PATH"
buildozer android debug
```

Notes:

- Use Java 17 for this pipeline (Gradle compatibility).
- If Java 21 was used before, stop old Gradle daemons and retry.
- Mobile v1 consumes FastAPI endpoints.
- OCR stays server-side in the Telegram flow.

## Testing

Run the full test suite:

```bash
uv run pytest
```

## GitHub Pages Demo

This repository includes a static demo page at `docs/index.html`.

- Workflow file: `.github/workflows/deploy-pages.yml`
- Publish source: `docs/`
- Trigger: pushes to `main` (and manual workflow dispatch)

After pushing to GitHub:

1. Open repository `Settings` -> `Pages`.
2. Ensure `Source` is set to `GitHub Actions`.
3. Let the `Deploy Demo to GitHub Pages` workflow run.
4. Your demo is available at:
	 - `https://<your-user>.github.io/<your-repo>/`

## License

Add your preferred license file (`LICENSE`) if you want to make distribution terms explicit.
