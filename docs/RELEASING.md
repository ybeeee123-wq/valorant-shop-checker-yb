# Releasing VALSHOP

`companion/version.py` is the authoritative desktop version. The executable metadata and Inno Setup version are derived from it.

## Build configuration

Set these before building a production artifact:

- `VALSHOP_API_BASE_URL` — public HTTPS FastAPI origin
- `VALSHOP_PUBLIC_SITE_URL` — public HTTPS React origin
- `VALSHOP_UPDATE_METADATA_URL` — HTTPS JSON endpoint containing `version` and optionally `download_url`
- `VALSHOP_UPDATE_DOWNLOAD_URL` — trusted release/download page fallback

Optional signing variables:

- `WINDOWS_CERTIFICATE` — path to a real `.pfx`
- `WINDOWS_CERTIFICATE_PASSWORD`

Backend production variables: `DATABASE_URL`, `PUBLIC_SITE_URL`, `ALLOWED_ORIGINS`, `ENCRYPTION_KEY`, `ENVIRONMENT=production`, and optional `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`. Frontend uses `VITE_API_URL`.

## Build

Install Python 3.12, Node.js, and Inno Setup 6 on a Windows build host, then run:

```bat
scripts\build_windows.bat
```

Expected outputs are `dist\VALSHOP\VALSHOP.exe` and, when Inno Setup is available, `release\VALSHOP-Setup.exe`. The script must finish its packaged executable smoke run before an artifact is published. Install the generated setup into a clean test location, launch it, inspect tray/startup behavior and shortcuts, then uninstall it.

For a GitHub release, tag the same version as `vX.Y.Z`. The Windows workflow validates all layers and uploads build artifacts. Signing is optional for development but strongly recommended for public releases.

## Deployment order

1. Provision Postgres/Supabase and apply `backend/migrations/001_persistent_features.sql`.
2. Configure and deploy the backend Docker image; verify `/health` over HTTPS.
3. Build/deploy the frontend with `VITE_API_URL`; add its exact origin to backend CORS.
4. Configure update metadata and download URLs.
5. Build/sign/test the Windows installer with the production endpoints embedded.
6. Publish the installer and update metadata together.
