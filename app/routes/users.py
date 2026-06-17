import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, Driver
from app.schemas.user import BindUserRequest, BindUserResponse, DriverInfo, LoginRequest, LoginResponse

router = APIRouter()

WX_APPID = os.getenv("WX_APPID", "")
WX_SECRET = os.getenv("WX_SECRET", "")
WX_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    微信小程序登录接口。

    接收前端传来的 wx.login() 返回的 code，
    调用微信 code2Session 接口换取 openid。

    - 若 openid 对应已有用户，返回已有 user_id
    - 若 openid 为新用户，创建用户记录并返回 user_id
    """
    # 调用微信 code2Session 换取 openid
    params = {
        "appid": WX_APPID,
        "secret": WX_SECRET,
        "js_code": body.code,
        "grant_type": "authorization_code",
    }

    try:
        resp = httpx.get(WX_CODE2SESSION_URL, params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="微信服务请求失败，请稍后重试")

    # 检查微信返回的错误码
    if "errcode" in data and data["errcode"] != 0:
        errmsg = data.get("errmsg", "未知错误")
        raise HTTPException(
            status_code=400,
            detail=f"微信登录失败: {errmsg}"
        )

    openid = data.get("openid")
    if not openid:
        raise HTTPException(status_code=400, detail="未能获取到 openid")

    # 检查是否已有该 openid 的用户
    user = db.query(User).filter(User.openid == openid).first()

    is_new_user = False
    if user:
        # 已有用户，直接返回
        return LoginResponse(
            openid=openid,
            user_id=user.user_id,
            is_new_user=False,
        )
    else:
        # 新用户，创建用户记录
        new_user = User(openid=openid)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        is_new_user = True
        return LoginResponse(
            openid=openid,
            user_id=new_user.user_id,
            is_new_user=True,
        )


@router.post("/bind", response_model=BindUserResponse)
def bind_user(
    body: BindUserRequest,
    db: Session = Depends(get_db)
):
    """
    绑定用户与车手数据。

    逻辑：
    1. 先检查 users 表是否已存在该 openid 的用户
       - 若存在且已绑定 driver，直接返回 driver 信息
       - 若存在但未绑定 driver，走绑定流程
    2. 若不存在该 openid，则根据 steam_guid 查找 driver
       - 找到 driver → 创建 user 并绑定 → 返回 driver 信息
       - 未找到 driver → 返回 404 错误
    """

    # 1. 检查是否已有该 openid 的用户
    user = db.query(User).filter(User.openid == body.openid).first()

    if user and user.driver_id:
        # 已有绑定记录，直接返回
        driver = db.query(Driver).filter(Driver.driver_id == user.driver_id).first()
        return BindUserResponse(
            user_id=user.user_id,
            openid=user.openid,
            wechat_name=user.wechat_name,
            driver=DriverInfo(
                driver_id=driver.driver_id,
                driver_name=driver.driver_name,
                team_name=driver.team_name or "",
                nation=driver.nation or "",
                steam_guid=driver.steam_guid,
            )
        )

    # 2. 根据 steam_guid 查找 driver
    driver = db.query(Driver).filter(Driver.steam_guid == body.steam_guid).first()

    if not driver:
        raise HTTPException(
            status_code=404,
            detail="绑定失败：未找到对应 steam_guid 的车手信息"
        )

    # 3. 创建或更新 user 绑定
    if user:
        # openid 已存在但未绑定 driver，更新绑定
        user.driver_id = driver.driver_id
    else:
        # 新用户，创建并绑定
        user = User(
            openid=body.openid,
            driver_id=driver.driver_id,
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    return BindUserResponse(
        user_id=user.user_id,
        openid=user.openid,
        wechat_name=user.wechat_name,
        driver=DriverInfo(
            driver_id=driver.driver_id,
            driver_name=driver.driver_name,
            team_name=driver.team_name or "",
            nation=driver.nation or "",
            steam_guid=driver.steam_guid,
        )
    )


@router.get("/{openid}/driver", response_model=BindUserResponse)
def get_user_driver(
    openid: str,
    db: Session = Depends(get_db)
):
    """
    通过 openid 获取已绑定的车手信息。
    若用户不存在或未绑定 driver，返回 404。
    """
    user = db.query(User).filter(User.openid == openid).first()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not user.driver_id:
        raise HTTPException(status_code=404, detail="该用户尚未绑定车手")

    driver = db.query(Driver).filter(Driver.driver_id == user.driver_id).first()

    if not driver:
        raise HTTPException(status_code=404, detail="绑定的车手信息不存在")

    return BindUserResponse(
        user_id=user.user_id,
        openid='',
        wechat_name=user.wechat_name,
        driver=DriverInfo(
            driver_id=driver.driver_id,
            driver_name=driver.driver_name,
            team_name=driver.team_name or "",
            nation=driver.nation or "",
            steam_guid=driver.steam_guid,
        )
    )
