import os
import jwt
import aiohttp
from json import dumps, loads
from dotenv import load_dotenv
import redis.asyncio as redis

from app.redispool import RedisPool

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    status,
    WebSocket,
    WebSocketException,
)
from fastapi_utils.cbv import cbv
from jwt.exceptions import InvalidTokenError

from fastapi.security import OAuth2PasswordBearer
from database.user import User as DatabaseUser
from database.ambulance import Ambulance

from app.bitflag import UserFlag, UserBitflag
from interface.emergency import (
    AmbulanceCallRequest,
    EmergencyTour,
    EmergencyTourStatus,
    EmergencyTourOPCode,
)
from interface.response import JSONResponse, WebsocketResponse

load_dotenv(verbose=True)

router = APIRouter(tags=["call", "emergency"], prefix="/emergency")


async def get_redis_pool() -> redis.Redis:
    redis_pool = RedisPool(
        host=os.environ["REDIS_HOST"], port=int(os.environ["REDIS_PORT"]), db=0
    )
    redis_connection = await redis_pool.get_connection()
    return redis_connection


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.update({user_id: websocket})

    def disconnect(self, user_id: str):
        self.active_connections[user_id].close()
        del self.active_connections[user_id]

    async def send_each(self, user_id: str, data: dict):
        connection = self.active_connections[user_id]
        await connection.send_json(data)

    async def broadcast(self, data: dict):
        for connection in self.active_connections.values():
            await connection.send_json(data)


@cbv(router)
class Emergency:
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
    redis_pool: redis.Redis = Depends(get_redis_pool)
    websocket_manager: ConnectionManager = ConnectionManager()

    @staticmethod
    async def update_tour(redis_pool: redis.Redis, user_id: str, data: dict):
        await redis_pool.hset("emergency", user_id, dumps(data))

    @staticmethod
    async def delete_tour(redis_pool: redis.Redis, user_id: str):
        await redis_pool.hdel("emergency", user_id)

    @staticmethod
    async def get_tour(redis_pool: redis.Redis, user_id: str):
        data = await redis_pool.hget("emergency", user_id)
        return loads(data)

    @staticmethod
    def get_user_id_from(token: str) -> str:
        return jwt.decode(
            token, os.environ["JWT_SECRET_KEY"], algorithms=["HS256"]
        ).get("sub")

    @staticmethod
    async def get_current_user(token: str = Depends(oauth2_scheme)) -> DatabaseUser:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token, os.environ["JWT_SECRET_KEY"], algorithms=["HS256"]
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except InvalidTokenError:
            raise credentials_exception
        user = await DatabaseUser.get(id=user_id)
        if user is None:
            raise credentials_exception
        user_flag = UserBitflag.unzip(user.flags)
        if not user_flag.has(UserFlag.USE_EMERGENCY_CALL):
            raise HTTPException(
                status_code=401,
                detail="FLAG: USE_EMERGENCY_CALL, insufficient permissions",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    @router.post("/new")
    async def new_tour(
        self,
        patient_data: AmbulanceCallRequest,
        current_user: "DatabaseUser" = Depends(get_current_user),
    ):
        current_user = await current_user
        if await self.redis_pool.hexists("emergency", current_user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This user's tour is already in progress.",
            )
        ambulance = await Ambulance.get(login_id=current_user.id)
        tour = EmergencyTour(
            patient_name=patient_data.name,
            symptom=patient_data.symptom,
            license_number=ambulance.license_number,
            status=EmergencyTourStatus.READY,
            hospital=None,
            remain_distance=None,
            current_location=None,
        )
        await self.update_tour(self.redis_pool, current_user.id, tour.model_dump())
        return JSONResponse(
            code=200,
            message="Success",
            data=tour.model_dump(),
            errors=[],
        )

    @router.websocket("/live")
    async def live_tour(
        self, websocket: WebSocket, token: str = Depends(oauth2_scheme)
    ):
        if not await self.redis_pool.hexists("emergency", self.get_user_id_from(token)):
            raise WebSocketException(
                code=4000,
                reason="This user's tour is not in progress.",
            )

        await self.websocket_manager.connect(self.get_user_id_from(token), websocket)
        while True:
            data: WebsocketResponse = await websocket.receive_json()
            if data.op == EmergencyTourOPCode.HELLO:
                await websocket.send_json(
                    WebsocketResponse(
                        op=EmergencyTourOPCode.HELLO, data=None
                    ).model_dump()
                )

    # @router.post("/call")
    # async def emergency(
    #     self,
    #     patient_data: AmbulanceCallRequest,
    #     current_user: "DatabaseUser" = Depends(get_current_user),
    # ):
    #     url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    #     params = {
    #         "y": patient_data.location_y,
    #         "x": patient_data.location_x,
    #         "radius": "20000",
    #         "query": "응급의료센터",
    #     }
    #     headers = {"Authorization": "KakaoAK " + os.environ["KAKAO_REST_API_KEY"]}
    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(url, headers=headers, params=params) as response:
    #             result = await response.json()
    #     hospital = [
    #         item for item in result["documents"] if not "산부인과" in item["place_name"]
    #     ]
    #     return JSONResponse(
    #         code=200,
    #         message="Success",
    #         data={
    #             "name": hospital[0]["place_name"],
    #             "address": hospital[0]["address_name"],
    #             "distance": hospital[0]["distance"],
    #         },
    #         errors=[],
    #     )
