from pydantic import BaseModel
from enum import Enum


class EmergencyTourOPCode(Enum):
    HELLO = 1  # 연결 확인 (클라이언트, 서버)
    UPDATE_DATA = 2  # 데이터 업데이트 (클라이언트, 서버)
    UPDATE_LOCATION = 3  # 위치 업데이트 (클라이언트)
    UPDATE_STATUS = 4  # 상태 업데이트 (서버)


class EmergencyTourStatus(Enum):
    READY = 0
    RIDE = 1
    ARRIVE = 2


class Hospital(Enum):
    name: str
    address: str


class AmbulanceCallRequest(BaseModel):
    name: str
    symptom: str
    location_x: str
    location_y: str


class EmergencyTour(BaseModel):
    patient_name: str
    symptom: str
    license_number: str
    status: EmergencyTourStatus
    hospital: Hospital | None
    remain_distance: int | None  # m 단위
    current_location: str | None
