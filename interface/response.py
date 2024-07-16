from pydantic import BaseModel


class JSONResponse(BaseModel):
    code: int
    message: str
    data: dict | None
    errors: list[dict] | None


class WebsocketResponse(BaseModel):
    op: str
    data: dict | None
