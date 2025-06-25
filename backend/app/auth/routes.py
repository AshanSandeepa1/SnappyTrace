# app/auth/routes.py
from fastapi import APIRouter, HTTPException, Depends
from app.auth.schemas import RegisterRequest, LoginRequest, Token
from app.auth.utils import hash_password, verify_password
from app.auth.jwt import create_access_token
from app.database import db

router = APIRouter()

@router.post("/register", response_model=Token)
async def register(data: RegisterRequest):
    user = await db.fetch_one("SELECT * FROM users WHERE email=$1", data.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")

    password_hash = hash_password(data.password)
    await db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES ($1, $2, $3)",
        data.name, data.email, password_hash
    )
    user = await db.fetch_one("SELECT * FROM users WHERE email=$1", data.email)
    token = create_access_token({"sub": str(user["id"]), "email": user["email"]})
    return {"access_token": token}

@router.post("/login", response_model=Token)
async def login(data: LoginRequest):
    user = await db.fetch_one("SELECT * FROM users WHERE email=$1", data.email)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": str(user["id"]), "email": user["email"]})
    return {"access_token": token}
