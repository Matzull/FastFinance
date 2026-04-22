# FastFinance

FastFinance is a personal finance manager with web, bot, and mobile modules.

## Run Web API/UI

```bash
uv run fastfinance-web
```

## Run Telegram Bot

```bash
uv run fastfinance-bot
```

## Run Mobile App (Kivy)

Install mobile extras:

```bash
uv pip install -e ".[mobile]"
```

Run the app:

```bash
uv run fastfinance-mobile
```

In the app settings screen, configure backend Base URL, for example:

- `http://127.0.0.1:8000` (local desktop testing)
- `http://<your-lan-ip>:8000` (Android device to local backend)

## Android Build (Debug)

A baseline `buildozer.spec` is included.

```bash
pip install buildozer cython
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH="$JAVA_HOME/bin:$PATH"
buildozer android debug
```

Notes:

- Buildozer in this project uses Gradle 8.0.2, which is not compatible with Java 21 for this build pipeline. Use Java 17.
- If you previously tried with Java 21, stop old Gradle daemons before retrying: `cd .buildozer/android/platform/build-arm64-v8a_armeabi-v7a/dists/fastfinance && ./gradlew --stop`.
- Mobile v1 consumes FastAPI endpoints.
- OCR remains server-side (Telegram flow), not in the mobile client.
- v1 has no auth token flow yet.
