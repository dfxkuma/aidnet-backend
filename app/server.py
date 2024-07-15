import uvicorn

from fastapi import FastAPI
from interface.response import JSONResponse

app = FastAPI(
    title="UltraMedic Backend",
    description="Backend for UltraMedic",
    version="0.1",
    redoc_url="/redoc",
    docs_url="/docs"
)


@app.get("/")
async def root() -> JSONResponse:
    return JSONResponse(
        code=200,
        message="Hello World!",
    )

uvicorn.run(app, host="0.0.0.0", port=8000)
