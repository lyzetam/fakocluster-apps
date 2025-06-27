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
