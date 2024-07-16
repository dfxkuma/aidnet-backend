import os
import uvicorn
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import load_dotenv

from tortoise.contrib.fastapi import RegisterTortoise
from interface.response import JSONResponse

from router.user import router as user_router
from router.emergency import router as emergency_router

load_dotenv(verbose=True)
logging.getLogger("passlib").setLevel(logging.ERROR)


@asynccontextmanager
async def lifespan(server: FastAPI):
    async with RegisterTortoise(
        server,
        db_url=os.environ["DATABASE_URI"],
        modules={"models": ["database.user"]},
        generate_schemas=True,
        add_exception_handlers=True,
    ):
        yield


app = FastAPI(
    lifespan=lifespan,
    title="UltraMedic Backend",
    description="Backend for UltraMedic",
    version="0.1",
    redoc_url="/redoc",
    docs_url="/docs",
)

app.include_router(user_router)
app.include_router(emergency_router)


@app.get("/")
async def root() -> JSONResponse:
    return JSONResponse(
        code=200,
        message="Hello World!",
        data={},
        errors=[],
    )


uvicorn.run(app, host="0.0.0.0", port=8001)
