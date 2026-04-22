[app]

title = FastFinance Mobile
package.name = fastfinance
package.domain = org.fastfinance

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = src/patrimonio/__init__.py,src/patrimonio/mobile/**

version = 0.1.0

# Keep Cython < 3 to avoid pyjnius build failures on some p4a/buildozer combos.
# Build against KivyMD 2.x from GitHub; the PyPI 1.2.x release is missing MDButton.
requirements = python3,kivy==2.3.1,https://github.com/kivymd/KivyMD/archive/master.zip,cython==0.29.36

orientation = portrait
fullscreen = 0

android.permissions = INTERNET

# Android 16 target (API 36)
android.api = 36
android.minapi = 21

# If you need camera/file access later, add permissions here.

[buildozer]
log_level = 2
warn_on_root = 1
