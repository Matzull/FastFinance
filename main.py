"""Android entrypoint for FastFinance mobile build."""

from __future__ import annotations

import os
import sys
import tempfile
import traceback
from pathlib import Path


def main() -> None:
    """Run the Kivy mobile app when the APK starts."""
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"

    # On Android, app/ is read-only after unpacking. Force Kivy to use a
    # writable directory under the app private files folder.
    # Use a fresh per-launch Kivy home under cache to avoid stale permission
    # issues from previous installs/runs.
    kivy_home = Path(tempfile.mkdtemp(prefix="fastfinance_kivy_"))
    os.environ["KIVY_HOME"] = str(kivy_home)
    os.environ["KIVY_NO_FILELOG"] = "1"
    os.environ["KIVY_NO_CONFIG"] = "1"
    (kivy_home / "icon").mkdir(parents=True, exist_ok=True)
    (kivy_home / "logs").mkdir(parents=True, exist_ok=True)

    # Buildozer copies source under app/, so add app/src for imports.
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))

    try:
        from patrimonio.mobile.app import main as run_mobile_app

        print(f"FastFinance Android boot with KIVY_HOME={kivy_home}", flush=True)
        run_mobile_app()
    except Exception as exc:
        tb = traceback.format_exc()
        print(f"FastFinance startup error: {exc!r}\n{tb}", flush=True)
        crash_file = Path(tempfile.gettempdir()) / "fastfinance_startup_error.log"
        try:
            crash_file.write_text(tb, encoding="utf-8")
            print(f"Crash traceback saved to {crash_file}", flush=True)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
