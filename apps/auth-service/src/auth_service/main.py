"""Simple authentication service using FastAPI."""
from typing import Dict
import os
import json
import hashlib

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Auth Service")

# Load user database from JSON file specified by USER_DB env var
USER_DB_PATH = os.getenv("USER_DB", "users.json")

try:
    with open(USER_DB_PATH, "r", encoding="utf-8") as f:
        user_db: Dict[str, str] = json.load(f)
except FileNotFoundError:
    user_db = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/login")
def login(req: LoginRequest):
    if req.username not in user_db:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    stored_hash = user_db[req.username]
    if hash_password(req.password) != stored_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"authenticated": True}


@app.get("/users")
def list_users():
    return {"users": list(user_db.keys())}
