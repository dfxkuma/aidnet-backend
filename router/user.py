import os
import jwt
import uuid
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import redis.asyncio as redis

from app.redispool import RedisPool

from fastapi import APIRouter, HTTPException, Depends, status, Body, Request
from fastapi_utils.cbv import cbv
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError

from app.bitflag import UserFlag, UserBitflag
from interface.user import RegisterUserRequest, LoginUserRequest
from database.user import User as DatabaseUser, UserRegisterCode
from interface.response import JSONResponse

load_dotenv(verbose=True)
router = APIRouter(tags=["user"], prefix="/user")


async def get_redis_pool() -> redis.Redis:
    redis_pool = RedisPool(
        host=os.environ["REDIS_HOST"], port=int(os.environ["REDIS_PORT"]), db=0
    )
    redis_connection = await redis_pool.get_connection()
    return redis_connection


@cbv(router)
class User:
    password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
    redis_pool: redis.Redis = Depends(get_redis_pool)

    @classmethod
    def verify_password(cls, plain_password, hashed_password):
        return cls.password_context.verify(plain_password, hashed_password)

    @classmethod
    def get_password_hash(cls, password):
        return cls.password_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta):
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        encoded_token = jwt.encode(
            to_encode, os.environ["JWT_SECRET_KEY"], algorithm="HS256"
        )
        return encoded_token

    @staticmethod
    async def register_token(
        redis_pool: redis.Redis, expire: timedelta, user_id: str, token: str
    ):
        await redis_pool.hset("user", token, user_id)
        await redis_pool.expire(token, expire)

    @staticmethod
    async def delete_token(redis_pool: redis.Redis, token: str):
        await redis_pool.hdel("user", token)

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
        return user

    @router.post("/register_code", description="인증 코드 생성하기")
    async def register_code(
        self,
        current_user: "DatabaseUser" = Depends(get_current_user),
        email: str = Body(...),
    ):
        current_user = await current_user
        user_flag = UserBitflag.unzip(current_user.flags)
        user_flag.add(UserFlag.CREATE_REGISTER_CODE)
        if not user_flag.has(UserFlag.CREATE_REGISTER_CODE):
            raise HTTPException(status_code=403, detail="Permission denied")

        new_register_code = uuid.uuid4().hex[:6]
        while await UserRegisterCode.exists(code=new_register_code):
            new_register_code = uuid.uuid4().hex[:6]

        await UserRegisterCode.create(
            id=uuid.uuid4(),
            email=email,
            code=new_register_code,
            expired_at=datetime.now(timezone.utc) + timedelta(days=2),
        )
        return JSONResponse(
            code=200,
            message="Register code generated",
            data={"register_code": new_register_code},
            errors=[],
        )

    @router.post("/register", description="인증 코드를 사용해 회원가입하기")
    async def register(self, user_data: RegisterUserRequest):
        if await DatabaseUser.exists(username=user_data.username):
            raise HTTPException(status_code=400, detail="Username already exists")
        if await DatabaseUser.exists(email=user_data.email):
            raise HTTPException(status_code=400, detail="Email already exists")
        find_register_code = await UserRegisterCode.exists(code=user_data.register_code)
        if not find_register_code:
            raise HTTPException(status_code=400, detail="Invalid register code")
        if not user_data.register_code:
            raise HTTPException(status_code=400, detail="Invalid register code")

        register_code_data = await UserRegisterCode.filter(
            code=user_data.register_code
        ).first()
        if register_code_data.email != user_data.email:
            raise HTTPException(status_code=400, detail="Invalid register code")

        new_user_id = uuid.uuid4()
        while await DatabaseUser.exists(id=str(uuid.uuid4())):
            new_user_id = uuid.uuid4()

        await DatabaseUser.create(
            id=new_user_id,
            username=user_data.username,
            password=user_data.password,
            email=user_data.email,
        )
        await register_code_data.delete()
        return JSONResponse(
            code=200,
            message="Register successful",
            data={"user_id": new_user_id},
            errors=[],
        )

    @router.post("/logout", description="로그아웃하기 (토큰 만료시키기)")
    async def logout(
        self,
        request: Request,
        current_user: "DatabaseUser" = Depends(get_current_user),
    ):
        _current_user = await current_user
        token = request.headers["Authorization"].split(" ")[1]
        await self.delete_token(redis_pool=self.redis_pool, token=token)
        return JSONResponse(code=200, message="Logout successful")

    @router.post("/login", description="로그인하기")
    async def login(
        self,
        login_data: LoginUserRequest,
    ):
        if not await DatabaseUser.exists(email=login_data.email):
            raise HTTPException(status_code=400, detail="User not found")

        database_user = await DatabaseUser.get(email=login_data.email)
        if not self.verify_password(login_data.password, database_user.hashed_password):
            raise HTTPException(status_code=400, detail="Invalid password")

        user_flag = UserBitflag.unzip(database_user.flags)
        if user_flag.has(UserFlag.USE_EMERGENCY_CALL):
            access_token_expires = timedelta(days=10)
        else:
            access_token_expires = timedelta(hours=4)

        access_token = self.create_access_token(
            {"sub": str(database_user.id), "username": database_user.username},
            expires_delta=access_token_expires,
        )
        try:
            await self.register_token(
                redis_pool=self.redis_pool,
                expire=access_token_expires,
                token=access_token,
                user_id=str(database_user.id),
            )
            return JSONResponse(
                code=200,
                message="Login successful",
                data={"token": access_token},
                errors=[],
            )
        except Exception as _e:
            raise HTTPException(
                status_code=500, detail="Internal Server Error, " + str(_e)
            )
