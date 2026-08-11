# VALSHOP deployment and persistent features

## Supabase/Postgres

1. Create a Supabase project.
2. In **SQL Editor**, run `backend/migrations/001_persistent_features.sql` once.
3. Copy the connection string from **Project Settings → Database**. The session pooler is suitable for small container deployments.
4. Set backend `DATABASE_URL` to it. Both `postgresql://` and `postgresql+psycopg://` are accepted.

Local development defaults to `sqlite:///./valshop.db`, keeping the existing root `npm run dev` usable without cloud credentials. Production should use Postgres.

## Web Push / VAPID

After installing backend dependencies, generate keys from `backend/`:

```powershell
.venv\Scripts\vapid.exe --gen
.venv\Scripts\vapid.exe --private-key private_key.pem --applicationServerKey
```

Set `VAPID_PRIVATE_KEY=private_key.pem`, set `VAPID_PUBLIC_KEY` to the second command’s output, set `VAPID_SUBJECT` to a monitored `mailto:` URI, and set `PUBLIC_SITE_URL` to the HTTPS frontend origin. PEM files are ignored by Git; provide the private key to production through its secret/file mechanism.

Deploy the frontend over HTTPS, sign in, open **Settings**, enable Web Push, and use **Send test**. The service worker opens `PUBLIC_SITE_URL` when clicked.

## Discord

Generate a Fernet key for `ENCRYPTION_KEY`:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste a `https://discord.com/api/webhooks/...` URL in Settings. The backend validates and encrypts it and never returns it to the frontend. Use **Send test** to verify delivery.

## Production variables

```text
DATABASE_URL
ENCRYPTION_KEY
ALLOWED_ORIGINS
ENVIRONMENT=production
PUBLIC_SITE_URL
VAPID_PUBLIC_KEY
VAPID_PRIVATE_KEY
VAPID_SUBJECT
```

The existing backend Dockerfile works with VPS, Railway, Render, and Fly.io-style containers. The Vite frontend is Vercel-compatible; set `VITE_API_URL` to the public backend origin. Never commit populated `.env` files.

## Local commands

```powershell
npm run dev

cd backend
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check app tests
.venv\Scripts\python -m mypy app

cd ..\frontend
npm run build
npm run lint

cd ..\companion
..\backend\.venv\Scripts\python -m pytest -q
```

## Security boundaries and limitations

- Riot passwords are never requested or stored.
- Riot access and entitlement tokens remain only in the existing in-memory backend session.
- Device tokens are shown once, hashed in Postgres, stored in Windows Credential Manager, and revocable.
- Discord webhooks are encrypted with `ENCRYPTION_KEY`.
- The callback remains `http://localhost/redirect`; `riot_callback.py` is unchanged.
- The unofficial Riot flow has no reliable long-lived refresh. Users must sign in again when the backend session expires or the backend restarts.
