from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import re
import uuid
import logging
import httpx

from app.core.config import settings
from app.core.db import get_db
from sqlalchemy.orm import Session
from app.models import User, VerifyCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["鉴权与用户"])


# ========== 简易存储（演示用；生产请替换为数据库/缓存） ==========
# 使用数据库持久化验证码与用户；token 仍以内存演示
_token_store: Dict[str, str] = {}
# 邮箱注册占位存储，避免引用未定义
_user_store: Dict[str, Dict[str, Any]] = {}
# 与前端一致的管理员直通令牌，支持无登录调试
ADMIN_BOOTSTRAP_TOKEN = "admin-token-PbwEQUSPXLY"


def _now() -> datetime:
    return datetime.utcnow()


def _save_code_db(db: Session, scene: str, target: str, code: str, ttl_seconds: int = 300):
    expire_at = _now() + timedelta(seconds=ttl_seconds)
    # 清理同 scene+target 未过期的旧码
    db.query(VerifyCode).filter(VerifyCode.scene == scene, VerifyCode.target == target).delete()
    db.add(VerifyCode(scene=scene, target=target, code=code, expire_at=expire_at, verified=False))
    db.commit()


def _verify_code_db(db: Session, scene: str, target: str, code: str) -> bool:
    rec = db.query(VerifyCode).filter(VerifyCode.scene == scene, VerifyCode.target == target).order_by(VerifyCode.id.desc()).first()
    if not rec:
        return False
    if rec.expire_at < _now():
        db.delete(rec)
        db.commit()
        return False
    ok = str(rec.code) == str(code)
    if ok:
        rec.verified = True
        db.add(rec)
        db.commit()
    return ok


def _consume_code_db(db: Session, scene: str, target: str):
    db.query(VerifyCode).filter(VerifyCode.scene == scene, VerifyCode.target == target).delete()
    db.commit()


PHONE_RE = re.compile(r"^\+?\d{6,15}$")


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SendSmsCodeBody(BaseModel):
    phone: str
    scene: str = Field(default="register")


class RegisterPhoneBody(BaseModel):
    username: str
    password: str
    phone: str
    code: str


class LoginBody(BaseModel):
    username: str
    password: str


class UpdateProfileBody(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None


class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str


class AdminUserCreateBody(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None


class AdminUserUpdateBody(BaseModel):
    password: Optional[str] = Field(default=None, min_length=6, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None


async def _send_sms_via_spug(phone: str, code: str) -> bool:
    """调用外部短信推送服务。配置 settings.sms_push_url，形如：
    https://push.spug.cc/send/<TOKEN>
    """
    if not settings.__dict__.get("sms_push_url"):
        logger.warning("SMS push url not configured; skip real sending.")
        return True
    url = settings.sms_push_url.strip()
    payload = {
        "name": getattr(settings, "sms_push_name", "推送助手"),
        "code": code,
        "targets": phone,
    }
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            logger.info("SMS push resp: %s", data)
            return True
        except Exception as e:
            logger.error("Failed to send SMS: %s", e)
            return False


def _require_auth(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="未认证")
    token = authorization.split(" ", 1)[1]
    if token == ADMIN_BOOTSTRAP_TOKEN:
        return "admin"
    username = _token_store.get(token)
    if not username:
        raise HTTPException(status_code=401, detail="无效令牌")
    return username


def _require_admin(username: str = Depends(_require_auth)) -> str:
    if username != "admin":
        raise HTTPException(status_code=403, detail="无权限执行此操作")
    return username


def _serialize_user(user: User) -> Dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
    }


@router.post("/send-sms-code", response_model=ApiResponse)
async def send_sms_code(body: SendSmsCodeBody, db: Session = Depends(get_db)):
    if not PHONE_RE.match(body.phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    code = f"{uuid.uuid4().int % 1000000:06d}"
    _save_code_db(db, body.scene, body.phone, code, ttl_seconds=300)
    ok = await _send_sms_via_spug(body.phone, code)
    if not ok:
        raise HTTPException(status_code=502, detail="短信服务调用失败")
    return ApiResponse(success=True, message="验证码已发送", data={"ttl": 300})


@router.post("/register/phone", response_model=ApiResponse)
async def register_phone(body: RegisterPhoneBody, db: Session = Depends(get_db)):
    if not PHONE_RE.match(body.phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确")
    if not _verify_code_db(db, "register", body.phone, body.code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    existed = db.query(User).filter(User.username == body.username).first()
    if existed:
        raise HTTPException(status_code=400, detail="用户名已存在")
    db.add(User(username=body.username, password=body.password, phone=body.phone, email=None))
    db.commit()
    _consume_code_db(db, "register", body.phone)
    return ApiResponse(success=True, message="注册成功", data=None)


@router.post("/login", response_model=ApiResponse)
async def login(body: LoginBody, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == body.username).first()
    if not u or u.password != body.password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = uuid.uuid4().hex
    _token_store[token] = body.username
    return ApiResponse(success=True, message="登录成功", data={
        "token": token,
        "user": {"username": u.username, "email": u.email, "phone": u.phone}
    })


@router.get("/me", response_model=ApiResponse)
async def get_me(username: str = Depends(_require_auth), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == username).first()
    return ApiResponse(success=True, message="OK", data={
        "username": u.username,
        "email": u.email,
        "phone": u.phone,
    })


@router.patch("/me", response_model=ApiResponse)
async def update_me(body: UpdateProfileBody, username: str = Depends(_require_auth), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == username).first()
    if body.email is not None:
        u.email = body.email
    if body.phone is not None:
        u.phone = body.phone
    db.add(u)
    db.commit()
    return ApiResponse(success=True, message="资料已更新", data={
        "username": u.username,
        "email": u.email,
        "phone": u.phone,
    })


@router.post("/change-password", response_model=ApiResponse)
async def change_password(body: ChangePasswordBody, username: str = Depends(_require_auth), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == username).first()
    if u.password != body.old_password:
        raise HTTPException(status_code=400, detail="当前密码不正确")
    u.password = body.new_password
    db.add(u)
    db.commit()
    return ApiResponse(success=True, message="密码已更新", data=None)


@router.get("/admin/users", response_model=ApiResponse, summary="管理员-获取用户列表")
async def admin_list_users(_: str = Depends(_require_admin), db: Session = Depends(get_db)):
    users: List[User] = db.query(User).order_by(User.id.asc()).all()
    return ApiResponse(success=True, message="ok", data={"users": [_serialize_user(u) for u in users]})


@router.post("/admin/users", response_model=ApiResponse, summary="管理员-创建用户")
async def admin_create_user(body: AdminUserCreateBody, _: str = Depends(_require_admin), db: Session = Depends(get_db)):
    existed = db.query(User).filter(User.username == body.username).first()
    if existed:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=body.username,
        password=body.password,
        email=body.email,
        phone=body.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return ApiResponse(success=True, message="ok", data={"user": _serialize_user(user)})


@router.patch("/admin/users/{user_id}", response_model=ApiResponse, summary="管理员-更新用户")
async def admin_update_user(user_id: int, body: AdminUserUpdateBody, _: str = Depends(_require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if body.password:
        user.password = body.password
    if body.email is not None:
        user.email = body.email
    if body.phone is not None:
        user.phone = body.phone
    db.add(user)
    db.commit()
    return ApiResponse(success=True, message="ok", data={"user": _serialize_user(user)})


@router.delete("/admin/users/{user_id}", response_model=ApiResponse, summary="管理员-删除用户")
async def admin_delete_user(user_id: int, _: str = Depends(_require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="禁止删除管理员账户")
    db.delete(user)
    db.commit()
    return ApiResponse(success=True, message="ok", data=None)


# 可选：邮箱验证码接口（占位，若未配置真实服务则直接返回成功）
class SendEmailCodeBody(BaseModel):
    email: str
    scene: str = Field(default="register")


@router.post("/send-email-code", response_model=ApiResponse)
async def send_email_code(_body: SendEmailCodeBody):
    # 未接入真实服务时，直接返回成功，方便前端流程打通
    return ApiResponse(success=True, message="验证码已发送（模拟）", data={"ttl": 300})


class RegisterEmailBody(BaseModel):
    username: str
    password: str
    email: str
    code: str


@router.post("/register/email", response_model=ApiResponse)
async def register_email(_body: RegisterEmailBody):
    # 未接入真实服务时，直接返回失败提示或模拟；这里模拟成功并写入用户
    if _body.username in _user_store:
        raise HTTPException(status_code=400, detail="用户名已存在")
    _user_store[_body.username] = {
        "username": _body.username,
        "password": _body.password,
        "phone": None,
        "email": _body.email,
    }
    return ApiResponse(success=True, message="注册成功（模拟）", data=None)


