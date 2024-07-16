from enum import Enum


class UserFlag(Enum):
    USE_EMERGENCY_CALL = 1  # 라즈베리파이 클라이언트 > 비상 호출 사용
    VIEW_EMERGENCY_CALL = 2  # 대시보드 관리 > 호출 목록 보기
    TAKE_EMERGENCY_CALL = 3  # 대시보드 관리 > 호출 수락 (병원 클라이언트)
    MANAGER_EMERGENCY_CALL = 4  # 대시보드 관리 > 호출 관리 (다른 호출 수동 매칭 등)
    MANAGE_USERS = 5  # 등록된 유저 관리
    USE_PRIVATE_FEATURE = 6  # 테스트용 FLAG (비공개 기능 사용)
    CREATE_REGISTER_CODE = 7  # 회원가입 코드 생성


class UserBitflag:
    def __init__(self) -> None:
        self.current_permissions: int = 0

    def add(self, flag: UserFlag) -> None:
        self.current_permissions |= 1 << flag.value

    def remove(self, flag: UserFlag) -> None:
        self.current_permissions &= ~(1 << flag.value)

    def zip(self):
        return self.current_permissions

    @staticmethod
    def unzip(permissions: int) -> "UserBitflag":
        bitflag = UserBitflag()
        bitflag.current_permissions = permissions
        return bitflag

    def has(self, flag) -> bool:
        return (self.current_permissions & (1 << flag.value)) != 0

    def to_list(self) -> list[UserFlag]:
        flags: list[UserFlag] = []
        for flag in UserFlag:
            if self.has(flag):
                flags.append(flag)
        return flags
