from pydantic import BaseModel


class JSONResponse(BaseModel):
    code: int
    message: str
    data: dict | None
    errors: list[dict] | None
