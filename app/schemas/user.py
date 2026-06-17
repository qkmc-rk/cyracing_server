from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    code: str


class LoginResponse(BaseModel):
    openid: str
    user_id: Optional[int] = None
    is_new_user: bool = False


class BindUserRequest(BaseModel):
    openid: str
    steam_guid: str


class DriverInfo(BaseModel):
    driver_id: int
    driver_name: str
    team_name: str
    nation: str
    steam_guid: str


class BindUserResponse(BaseModel):
    user_id: int
    openid: str
    wechat_name: Optional[str] = None
    driver: Optional[DriverInfo] = None
