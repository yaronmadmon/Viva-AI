"""
Authentication endpoints.
"""

from fastapi import APIRouter, HTTPException, Request, status

from src.api.deps import DbSession, CurrentUser, get_client_ip, get_user_agent
from src.schemas.auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    UserProfileUpdate,
)
from src.schemas.common import SuccessResponse
from src.kernel.identity.identity_service import IdentityService

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: UserCreate,
    db: DbSession,
):
    """
    Register a new user account.
    
    Returns access and refresh tokens on successful registration.
    """
    identity_service = IdentityService(db)
    ip_address = get_client_ip(request)
    
    try:
        user = await identity_service.register_user(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            ip_address=ip_address,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Authenticate to get tokens
    result = await identity_service.authenticate(
        email=data.email,
        password=data.password,
        ip_address=ip_address,
        user_agent=get_user_agent(request),
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to authenticate after registration",
        )
    
    user, token_pair = result
    
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: UserLogin,
    db: DbSession,
):
    """
    Authenticate user and return tokens.
    """
    identity_service = IdentityService(db)
    
    result = await identity_service.authenticate(
        email=data.email,
        password=data.password,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    user, token_pair = result
    
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    data: RefreshTokenRequest,
    db: DbSession,
):
    """
    Refresh access token using refresh token.
    
    Implements refresh token rotation - old refresh token is invalidated.
    """
    identity_service = IdentityService(db)
    
    result = await identity_service.refresh_tokens(
        refresh_token=data.refresh_token,
        ip_address=get_client_ip(request),
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user, token_pair = result
    
    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    request: Request,
    user: CurrentUser,
    db: DbSession,
    data: RefreshTokenRequest = None,
):
    """
    Log out user by revoking refresh token(s).
    
    If refresh_token is provided, only that token is revoked.
    Otherwise, all user's refresh tokens are revoked.
    """
    identity_service = IdentityService(db)
    
    await identity_service.logout(
        user_id=user.id,
        refresh_token=data.refresh_token if data else None,
        revoke_all=data is None,
        ip_address=get_client_ip(request),
    )
    
    return SuccessResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(user: CurrentUser):
    """Get current user's profile."""
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: Request,
    data: UserProfileUpdate,
    user: CurrentUser,
    db: DbSession,
):
    """Update current user's profile."""
    identity_service = IdentityService(db)
    
    try:
        updated_user = await identity_service.update_user(
            user_id=user.id,
            full_name=data.full_name,
            email=data.email,
            ip_address=get_client_ip(request),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    return UserResponse.model_validate(updated_user)


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    user: CurrentUser,
    db: DbSession,
):
    """
    Change user's password.
    
    Revokes all refresh tokens on success.
    """
    identity_service = IdentityService(db)
    
    success = await identity_service.change_password(
        user_id=user.id,
        current_password=data.current_password,
        new_password=data.new_password,
        ip_address=get_client_ip(request),
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    return SuccessResponse(message="Password changed successfully. Please log in again.")
