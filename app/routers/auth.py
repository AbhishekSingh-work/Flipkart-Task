from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import (
    AuthUser,
    authenticate_user,
    create_access_token,
    create_user,
    get_current_user,
    list_users,
    require_permissions,
    serialize_user,
)
from app.schemas import LoginRequest, LoginResponse, UserCreateRequest, UserSession

router = APIRouter(prefix="/api/auth", tags=["auth"])
require_user_admin = require_permissions(["users"])


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


@router.get("/users", response_model=list[UserSession])
def users(_: AuthUser = Depends(require_user_admin)):
    return [serialize_user(user) for user in list_users()]


@router.post("/users", response_model=UserSession, status_code=status.HTTP_201_CREATED)
def create_app_user(
    payload: UserCreateRequest,
    _: AuthUser = Depends(require_user_admin),
):
    try:
        user = create_user(
            username=payload.username,
            password=payload.password,
            role=payload.role,
            display_name=payload.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return serialize_user(user)
