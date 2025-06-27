from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import DATABASE_URL
from app.database import db
from app.auth.routes import router as auth_router
from app.routes.upload import router as upload_router
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# 🔧 Allow requests from your frontend (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await db.connect(DATABASE_URL)

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

app.include_router(auth_router, prefix="/auth")

@app.get("/ping")
def ping():
    return {"message": "pong"}

app.include_router(upload_router, prefix="/file")
app.mount("/files", StaticFiles(directory="/tmp/snappy_uploads"), name="files")