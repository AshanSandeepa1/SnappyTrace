# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
# If docker-compose passes SECRET_KEY as an empty string, os.getenv returns "".
# That would silently change the watermark/auth secret and break verification.
SECRET_KEY = os.getenv("SECRET_KEY") or "supersecret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
