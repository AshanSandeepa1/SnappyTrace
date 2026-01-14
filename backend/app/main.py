from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import DATABASE_URL
from app.database import db
from app.db_schema import ensure_schema
from app.auth.routes import router as auth_router
from app.routes.upload import router as upload_router
from app.routes.verify import router as verify_router
from app.routes.files import router as files_router
from fastapi.staticfiles import StaticFiles
import asyncio
import logging

app = FastAPI()

# pyHanko + pyhanko-certvalidator can emit verbose stack traces when validating
# self-signed demo certificates. We treat trust as a separate concern from
# cryptographic integrity, so keep the logs quiet by default.
for _logger_name in (
    "pyhanko_certvalidator",
    "pyhanko.sign.validation",
    "pyhanko.sign.validation.generic_cms",
):
    _lg = logging.getLogger(_logger_name)
    _lg.setLevel(logging.CRITICAL)
    _lg.propagate = False

# Allow requests from your frontend (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://10.0.2.2:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # Postgres can take a moment to accept connections after container start.
    last_exc = None
    for _ in range(30):
        try:
            await db.connect(DATABASE_URL)
            last_exc = None
            break
        except Exception as e:
            last_exc = e
            await asyncio.sleep(1)

    if last_exc is not None:
        raise last_exc
    await ensure_schema()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

app.include_router(auth_router, prefix="/auth")

@app.get("/ping")
def ping():
    return {"message": "pong"}

app.include_router(upload_router)
app.include_router(verify_router)
app.include_router(files_router)
app.mount("/files", StaticFiles(directory="/tmp/snappy_uploads"), name="files")