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

## Auth Service Setup

Run the provided scripts to create the database schema and an initial admin user.

1. Initialize the database tables:

   ```bash
   python apps/auth-service/src/scripts/init_database.py --create-db
   ```

2. Seed an admin user (replace the email and password as needed):

   ```bash
   python apps/auth-service/src/scripts/seed_users.py --email admin@example.com --password mypassword
   ```

The seeding script retrieves database credentials from AWS Secrets Manager by default. A connection string can be supplied with `--connection-string` to override this behaviour.
