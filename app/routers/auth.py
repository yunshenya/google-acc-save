from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from datetime import datetime

from app.dependencies.auth_middleware import (
    authenticate_user,
    create_access_token,
    verify_token,
)

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int  # 新增：过期时间（秒）
    expires_at: str  # 新增：过期时间戳


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user["username"]})

    # 计算过期时间
    from app.dependencies.auth_middleware import ACCESS_TOKEN_EXPIRE_MINUTES
    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 转换为秒
    from datetime import timedelta
    expires_at = (datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).isoformat()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "expires_at": expires_at
    }


@router.get("/verify")
async def verify_token_endpoint(current_user: str = Depends(verify_token)):
    return {"username": current_user, "status": "authenticated"}


@router.post("/refresh")
async def refresh_token(current_user: str = Depends(verify_token)):
    """刷新token"""
    access_token = create_access_token(data={"sub": current_user})

    from app.dependencies.auth_middleware import ACCESS_TOKEN_EXPIRE_MINUTES
    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    from datetime import timedelta
    expires_at = (datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).isoformat()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "expires_at": expires_at
    }