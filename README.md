## Oura Dashboard Authentication

The dashboard under `apps/oura-dashboard` now supports optional username and
password authentication using [`streamlit-authenticator`](https://github.com/mkhorasani/streamlit-authenticator).
Set the following environment variables to enable authentication:

* `REQUIRE_AUTH` – set to `true` to require login.
* `DASHBOARD_USERNAME` – login username (default `admin`).
* `DASHBOARD_PASSWORD` – plain text password used to generate a hash on start.
* `DASHBOARD_NAME` – full name shown in the UI (optional).
* `DASHBOARD_EMAIL` – email address displayed in account info (optional).
* `AUTH_COOKIE_KEY` – secret key for the login cookie.

If `REQUIRE_AUTH` is not set or is `false`, the dashboard behaves as before and
does not ask for credentials.

## Auth Service

A simple FastAPI service is provided under `apps/auth-service`. It validates user
credentials against a JSON file. By default it reads `users.json` in the same directory.

The service exposes two endpoints:

- `POST /login` – verify a username and password
- `GET /users` – list available usernames

To start the service locally:

```bash
uvicorn auth_service.main:app --reload
```

You can populate `users.json` with SHA256 password hashes. For example:

```python
import hashlib, json
password_hash = hashlib.sha256("changeme".encode()).hexdigest()
with open("users.json", "w") as f:
    json.dump({"admin": password_hash}, f)
```
