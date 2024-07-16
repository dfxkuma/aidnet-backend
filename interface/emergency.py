from pydantic import BaseModel


class AmbulanceCallRequest(BaseModel):
    name: str
    symptom: str
    location_x: str
    location_y: str
