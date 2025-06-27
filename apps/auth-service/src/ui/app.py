import os
import requests
import streamlit as st
from datetime import datetime

API_URL = os.environ.get("AUTH_API_URL", "http://localhost:8000/api/v1")
API_KEY_HEADER = os.environ.get("API_KEY_HEADER", "X-API-Key")

st.set_page_config(page_title="Auth Service Admin", layout="wide")

if "api_key" not in st.session_state:
    st.session_state.api_key = os.environ.get("ADMIN_API_KEY", "")

st.sidebar.header("Authentication")
st.sidebar.text_input("Admin API Key", key="api_key", type="password")


def request(method: str, path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    if st.session_state.api_key:
        headers[API_KEY_HEADER] = st.session_state.api_key
    try:
        resp = requests.request(method, f"{API_URL}{path}", headers=headers, **kwargs)
        if resp.status_code == 401:
            st.error("Unauthorized - check API key")
            return None
        resp.raise_for_status()
        if resp.content:
            return resp.json()
        return None
    except requests.RequestException as e:
        st.error(f"Request failed: {e}")
        return None

st.sidebar.text_input("Email", key="login_email")
st.sidebar.text_input("Password", key="login_password", type="password")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if st.sidebar.button("Login"):
    payload = {"email": st.session_state.login_email, "password": st.session_state.login_password}
    resp = request("POST", "/auth/login", json=payload)
    if resp and resp.get("authenticated") and resp.get("is_admin"):
        st.session_state.logged_in = True
        st.success("Logged in")
    else:
        st.error("Invalid credentials")

if not st.session_state.logged_in:
    st.stop()


section = st.sidebar.selectbox(
    "Section",
    ["Users", "Applications", "Permissions", "API Keys"],
)

st.title(f"Auth Service Admin - {section}")

if section == "Users":
    if st.button("Refresh Users"):
        st.experimental_rerun()
    users = request("GET", "/admin/users") or []
    if users:
        st.dataframe(users, use_container_width=True)
    with st.expander("Create User"):
        with st.form("create_user"):
            email = st.text_input("Email")
            full_name = st.text_input("Full Name")
            password = st.text_input("Password", type="password")
            is_admin = st.checkbox("Is Admin")
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Create")
            if submitted:
                payload = {
                    "email": email,
                    "full_name": full_name or None,
                    "password": password or None,
                    "is_admin": is_admin,
                    "notes": notes or None,
                }
                resp = request("POST", "/admin/users", json=payload)
                if resp:
                    st.success(f"User {resp['email']} created")
                    st.experimental_rerun()

elif section == "Applications":
    if st.button("Refresh Applications"):
        st.experimental_rerun()
    apps = request("GET", "/admin/applications") or []
    if apps:
        st.dataframe(apps, use_container_width=True)
    with st.expander("Create Application"):
        with st.form("create_app"):
            app_name = st.text_input("App Name")
            display_name = st.text_input("Display Name")
            description = st.text_area("Description")
            callbacks = st.text_input("Callback URLs (comma separated)")
            submitted = st.form_submit_button("Create")
            if submitted:
                payload = {
                    "app_name": app_name,
                    "display_name": display_name,
                    "description": description or None,
                    "callback_urls": [u.strip() for u in callbacks.split(",") if u.strip()] or None,
                }
                resp = request("POST", "/admin/applications", json=payload)
                if resp:
                    st.success(f"Application {resp['app_name']} created")
                    st.experimental_rerun()

elif section == "Permissions":
    with st.form("grant_perm"):
        user_email = st.text_input("User Email")
        app_name = st.text_input("Application Name")
        expires = st.date_input("Expires At", value=None)
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Grant Permission")
        if submitted:
            expires_at = datetime.combine(expires, datetime.min.time()) if expires else None
            payload = {
                "user_email": user_email,
                "app_name": app_name,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "notes": notes or None,
            }
            resp = request("POST", "/admin/permissions/grant", json=payload)
            if resp:
                st.success("Permission granted")

elif section == "API Keys":
    with st.form("create_key"):
        name = st.text_input("Key Name")
        description = st.text_input("Description")
        expires = st.date_input("Expires At", value=None)
        allowed_ips = st.text_input("Allowed IPs (comma separated)")
        submitted = st.form_submit_button("Create API Key")
        if submitted:
            expires_at = datetime.combine(expires, datetime.min.time()) if expires else None
            payload = {
                "name": name,
                "description": description or None,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "allowed_ips": [ip.strip() for ip in allowed_ips.split(",") if ip.strip()] or None,
            }
            resp = request("POST", "/admin/api-keys", json=payload)
            if resp:
                st.success("API key created. Save it now:")
                st.code(resp.get("api_key"))

