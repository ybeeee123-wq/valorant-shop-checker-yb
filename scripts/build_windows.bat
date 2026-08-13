@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

if not exist backend\.venv\Scripts\python.exe (
  py -3.12 -m venv backend\.venv || exit /b 1
)
backend\.venv\Scripts\python.exe -m pip install -e "backend[dev]" -e "companion[dev]" || exit /b 1

if defined VALSHOP_API_BASE_URL powershell -NoProfile -Command "$p=Get-Content companion/release_config.json|ConvertFrom-Json;$p.api_base_url=$env:VALSHOP_API_BASE_URL;if($env:VALSHOP_PUBLIC_SITE_URL){$p.public_site_url=$env:VALSHOP_PUBLIC_SITE_URL};if($env:VALSHOP_UPDATE_METADATA_URL){$p.update_metadata_url=$env:VALSHOP_UPDATE_METADATA_URL};if($env:VALSHOP_UPDATE_DOWNLOAD_URL){$p.update_download_url=$env:VALSHOP_UPDATE_DOWNLOAD_URL};$p|ConvertTo-Json|Set-Content companion/release_config.json"

pushd backend
.venv\Scripts\python.exe -m pytest -q || exit /b 1
.venv\Scripts\python.exe -m ruff check app tests || exit /b 1
.venv\Scripts\python.exe -m mypy app || exit /b 1
popd
pushd companion
..\backend\.venv\Scripts\python.exe -m pytest -q || exit /b 1
..\backend\.venv\Scripts\python.exe -m ruff check . || exit /b 1
popd
pushd frontend
call npm.cmd ci || exit /b 1
call npm.cmd run lint || exit /b 1
call npm.cmd run build || exit /b 1
popd

if not exist companion\assets\valshop.ico backend\.venv\Scripts\python.exe -c "from PIL import Image; im=Image.open('frontend/public/favicon-v3.png').convert('RGBA'); im.save('companion/assets/valshop.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])" || exit /b 1
backend\.venv\Scripts\pyinstaller.exe --noconfirm --clean --distpath dist --workpath build companion\VALSHOP.spec || exit /b 1

if not defined VALSHOP_SMOKE_TEST set VALSHOP_SMOKE_TEST=1
dist\VALSHOP\VALSHOP.exe
if errorlevel 1 exit /b 1
set VALSHOP_SMOKE_TEST=

if defined WINDOWS_CERTIFICATE if exist "%WINDOWS_CERTIFICATE%" (
  where signtool.exe >nul 2>nul && signtool.exe sign /fd SHA256 /f "%WINDOWS_CERTIFICATE%" /p "%WINDOWS_CERTIFICATE_PASSWORD%" /tr http://timestamp.digicert.com /td SHA256 dist\VALSHOP\VALSHOP.exe
)

set ISCC=
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if defined ISCC "%ISCC%" installer\VALSHOP.iss || exit /b 1

echo.
echo Executable: dist\VALSHOP\VALSHOP.exe
if exist release\VALSHOP-Setup.exe echo Installer: release\VALSHOP-Setup.exe
if not defined ISCC echo Inno Setup 6 not found; installer source is ready but was not compiled.
