# VALSHOP Windows Companion

The companion triggers a shop check after reset and uploads only resolved offer metadata. It never receives or stores Riot access tokens or passwords. Its dedicated device token is stored by `keyring` in Windows Credential Manager.

## Install and connect

```powershell
cd companion
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e .
Copy-Item .env.example .env
```

In VALSHOP, open **Settings → Create device token**. Copy the token once, then:

```powershell
.venv\Scripts\python app.py configure --device-token YOUR_DEVICE_TOKEN
.venv\Scripts\python app.py run
```

The browser must have completed the normal Riot login. If that short-lived in-memory Riot session expires, the companion reports `reauth_required`; sign in through VALSHOP normally and it resumes on a later retry.

## Windows startup

This is opt-in and uses the current user’s `HKCU` Run key, so it does not require administrator access:

```powershell
.venv\Scripts\python app.py startup enable
.venv\Scripts\python app.py startup disable
```

Successful checks schedule shortly after Riot’s reset boundary with jitter. Failures use exponential backoff capped at one hour. For development only, set `COMPANION_DEV_INTERVAL_SECONDS=60`.

The unofficial Riot session cannot be refreshed indefinitely. VALSHOP deliberately uses graceful reauthentication rather than storing credentials or pretending refresh is possible.
