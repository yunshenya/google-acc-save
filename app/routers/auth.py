from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from app.dependencies.auth_middleware import authenticate_user, create_access_token, verify_token

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str

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
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/verify")
async def verify_token_endpoint(current_user: str = Depends(verify_token)):
    return {"username": current_user, "status": "authenticated"}