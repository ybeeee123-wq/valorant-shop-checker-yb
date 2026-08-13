# VALSHOP Windows Companion

The companion checks the storefront after reset and uploads only resolved shop metadata. Riot access tokens stay on the PC in Windows Credential Manager and are never uploaded; VALSHOP never receives or stores a Riot password. The dedicated cloud device token is also stored by `keyring` in Windows Credential Manager.

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

Complete Riot sign-in in the companion, pair the device once through the website, and leave it running in the tray. Daily Shop, Bundles, Wallet and Night Market data are synchronized to the website. When Riot's short-lived session expires, the companion reports `reauth_required`; reconnect Riot locally and it resumes on the next retry.

## Windows startup

This is opt-in and uses the current user’s `HKCU` Run key, so it does not require administrator access:

```powershell
.venv\Scripts\python app.py startup enable
.venv\Scripts\python app.py startup disable
```

Successful checks schedule shortly after Riot’s reset boundary with jitter. Failures use exponential backoff capped at one hour. For development only, set `COMPANION_DEV_INTERVAL_SECONDS=60`.

The unofficial Riot session cannot be refreshed indefinitely. VALSHOP deliberately uses graceful reauthentication rather than storing credentials or pretending refresh is possible.
