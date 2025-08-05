from fastapi import APIRouter

router = APIRouter()

# Import all routers to register routes
from app.routers import accounts, proxy, server