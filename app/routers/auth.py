from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import (
    AuthUser,
    authenticate_user,
    create_access_token,
    get_current_user,
    serialize_user,
)
from app.schemas import LoginRequest, LoginResponse, UserSession

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": serialize_user(user),
    }


@router.get("/me", response_model=UserSession)
def me(user: AuthUser = Depends(get_current_user)):
    return serialize_user(user)
