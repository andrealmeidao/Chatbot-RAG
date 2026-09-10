import hashlib
import hmac
import secrets
from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.db import create_session, create_user, get_session, get_user_by_username

PBKDF_ROUNDS = 120_000


@dataclass
class AuthUser:
    id: str
    username: str


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF_ROUNDS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, stored)


def _validate_credentials(username: str, password: str) -> str:
    username = (username or "").strip()
    password = password or ""
    if len(username) < 3 or len(username) > 40:
        raise HTTPException(status_code=400, detail="Usuario deve ter entre 3 e 40 caracteres")
    cleaned = username.replace("_", "").replace(".", "").replace("-", "")
    if not cleaned.isalnum():
        raise HTTPException(status_code=400, detail="Use apenas letras, numeros, ponto, hifen ou underline")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter ao menos 6 caracteres")
    if len(password) > 128:
        raise HTTPException(status_code=400, detail="Senha muito longa")
    return username


def register_user(username: str, password: str) -> dict:
    username = _validate_credentials(username, password)
    if get_user_by_username(username):
        raise HTTPException(status_code=409, detail="Usuario ja existe")
    user = create_user(username, hash_password(password))
    token = secrets.token_urlsafe(32)
    create_session(token, user["id"])
    return {"token": token, "user": {"id": user["id"], "username": user["username"]}}


def login_user(username: str, password: str) -> dict:
    username = _validate_credentials(username, password)
    user = get_user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais invalidas")
    token = secrets.token_urlsafe(32)
    create_session(token, user["id"])
    return {"token": token, "user": {"id": user["id"], "username": user["username"]}}


def current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Autenticacao obrigatoria")
    token = authorization.split(" ", 1)[1].strip()
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Sessao invalida")
    return AuthUser(id=session["user_id"], username=session["username"])
