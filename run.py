#!/usr/bin/env python
"""Script to run all FastFinance services."""

import pty

import dotenv
import subprocess
import os
import time
import threading
from pathlib import Path


def print_banner():
    """Print startup banner."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                 🏦 FASTFINANCE                            ║
║           Gestor de Finanzas Personales                   ║
╠═══════════════════════════════════════════════════════════╣
║  Web:      http://127.0.0.1:8000                          ║
║  API Docs: http://127.0.0.1:8000/docs                     ║
╚═══════════════════════════════════════════════════════════╝
""")


def check_telegram_config():
    """Checks Telegram configuration."""
    dotenv.load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token:
        print("✅ TELEGRAM_BOT_TOKEN configured")
        return True
    else:
        print("⚠️  TELEGRAM_BOT_TOKEN is not configured (bot disabled)")
        print("   To enable: export TELEGRAM_BOT_TOKEN='your_token'")
        return False


def check_openai_config():
    """Checks OpenAI configuration for OCR fallback."""
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        print("✅ OPENAI_API_KEY configured (OCR with Vision)")
    else:
        print("ℹ️  OPENAI_API_KEY not configured (OCR will use local PaddleOCR)")


def stream_output(fd, name):
    while True:
        try:
            data = os.read(fd, 4096)
            if not data:
                break
            print(f"[{name}] {data.decode(errors='replace')}", end="")
        except OSError:
            break


def run_all():
    """Runs all services."""
    print_banner()

    print("🔍 Checking configuration...\n")
    telegram_enabled = check_telegram_config()
    check_openai_config()
    print()

    processes = []
    threads = []

    project_dir = Path(__file__).parent

    try:
        print("🌐 Starting web server...")
        master_web, slave_web = pty.openpty()
        web_process = subprocess.Popen(
            ["uv", "run", "fastfinance-web"],
            cwd=project_dir,
            stdout=slave_web,
            stderr=slave_web,
            text=True,
        )
        processes.append(("Web", web_process))
        print(f"   PID: {web_process.pid}")
        web_thread = threading.Thread(
            target=stream_output, args=(master_web, "WEB"), daemon=True
        )
        web_thread.start()
        threads.append(web_thread)

        time.sleep(2)

        if telegram_enabled:
            print("🤖 Starting Telegram bot...")
            master_bot, slave_bot = pty.openpty()
            bot_process = subprocess.Popen(
                ["uv", "run", "fastfinance-bot"],
                cwd=project_dir,
                stdout=slave_bot,
                stderr=slave_bot,
                text=True,
            )
            processes.append(("Bot", bot_process))
            print(f"   PID: {bot_process.pid}")

            bot_thread = threading.Thread(
                target=stream_output, args=(master_bot, "BOT"), daemon=True
            )
            bot_thread.start()
            threads.append(bot_thread)

        print("\n" + "=" * 60)
        print("✅ Services started successfully")
        print("   Press Ctrl+C to stop all services")
        print("=" * 60 + "\n")

        import webbrowser

        webbrowser.open("http://127.0.0.1:8000")

        while True:
            all_running = True
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"⚠️  {name} exited with code {proc.returncode}")
                    all_running = False
            if not all_running:
                break
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping services...")

    finally:
        for name, proc in processes:
            if proc.poll() is None:
                print(f"   Stopping {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("✅ All services stopped")


if __name__ == "__main__":
    run_all()
