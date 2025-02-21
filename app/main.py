from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import router
from app.settings import settings
# from app.db import create_tables, drop_tables


@asynccontextmanager
async def lifespan(_app: FastAPI):
    print("Server started!")
    # await create_tables()
    yield
    print("Server stopped!")
app = FastAPI(lifespan=lifespan)

app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def main():
    return {
        "message": "test!",
        "debug": settings.DEBUG,
        "test": 1,
    }
