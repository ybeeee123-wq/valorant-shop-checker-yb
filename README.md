# VALSHOP

VALSHOP is a personal VALORANT shop tracker with a polished website and an installable Windows companion. It shows the Daily Shop, bundles, wallet, Night Market, wishlist, and history, then checks again after the next rotation and can send native Windows, Web Push, or Discord notifications.

VALSHOP is independent and is not affiliated with or endorsed by Riot Games. Riot credentials are entered only on Riot's sign-in page; VALSHOP never stores a Riot password. The product relies on unofficial Riot client APIs, so authentication can occasionally require reconnecting.

## Install on Windows

1. Download `VALSHOP-Setup.exe`.
2. Install and launch VALSHOP.
3. Complete the graphical onboarding and click **Connect Riot**.
4. Sign in in the browser. VALSHOP captures the callback automatically.
5. Add skins to your wishlist and close the window; VALSHOP continues in the tray.

No terminal, Python, Node.js, token copying, or configuration files are required for normal users. Unsigned development builds may trigger a Windows SmartScreen warning.

## Architecture

- `companion/`: PySide6 Windows app. It talks directly to Riot, keeps Riot and device credentials in Windows Credential Manager, and stores only non-sensitive cache/preferences under `%LOCALAPPDATA%\VALSHOP`.
- `backend/`: FastAPI cloud service for identity, pairing, normalized snapshots, wishlist/history, devices, and notification dedupe. Production uses Postgres; SQLite remains available for development.
- `frontend/`: React/Vite website, including `/connect-companion` approval.
- `installer/`: per-user Inno Setup installer.

Details: [architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md), [releasing](docs/RELEASING.md), and [deployment](DEPLOYMENT.md).

## Development

Requirements: Python 3.12+, Node.js 18+, and Windows for the companion UI.

Run all local services on Windows:

```bat
scripts\run_dev.bat
```

Or run each layer independently:

```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -e "backend[dev]" -e "companion[dev]"
backend\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload

cd frontend
npm ci
npm run dev
```

Build and validate a Windows release:

```bat
scripts\build_windows.bat
```

The script runs backend/companion tests, static checks, frontend lint/build, PyInstaller, a packaged executable smoke test, optional Authenticode signing, and Inno Setup when installed.

## Production configuration

Backend variables are documented in `backend/.env.example`; the frontend uses `VITE_API_URL`. Desktop release endpoints are embedded at build time with `VALSHOP_API_BASE_URL`, `VALSHOP_PUBLIC_SITE_URL`, `VALSHOP_UPDATE_METADATA_URL`, and `VALSHOP_UPDATE_DOWNLOAD_URL`. The companion synchronizes Daily Shop, Bundles, Wallet and Night Market metadata; Riot credentials never leave the device. See [releasing](docs/RELEASING.md) for exact steps.
