"""
Authentication Router

Handles user registration, login, and token management.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.database import get_db
from app.config import settings
from app.models import User
from app.services.rate_limiter import limiter, AUTH_RATE_LIMIT, REGISTER_RATE_LIMIT
from app.services.cache import blacklist_token, is_token_blacklisted

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# Password validation constants
MIN_PASSWORD_LENGTH = 8
PASSWORD_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$'
)


# Pydantic schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None  # Accept 'name' from frontend
    full_name: Optional[str] = None
    company: Optional[str] = None

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password meets security requirements:
        - At least 8 characters
        - Contains at least one uppercase letter
        - Contains at least one lowercase letter
        - Contains at least one digit
        """
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f'Password must be at least {MIN_PASSWORD_LENGTH} characters long'
            )
        if not PASSWORD_PATTERN.match(v):
            raise ValueError(
                'Password must contain at least one uppercase letter, '
                'one lowercase letter, and one digit'
            )
        return v

    def get_full_name(self) -> Optional[str]:
        return self.full_name or self.name


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None  # Frontend expects 'name'
    full_name: Optional[str] = None
    company: Optional[str]
    plan: str
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    user: UserResponse
    token: str


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Check if token has been blacklisted (logged out)
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


# Routes
@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(REGISTER_RATE_LIMIT)
async def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.get_full_name(),
        company=user_data.company,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create access token with user_id for secure WebSocket connections
    access_token = create_access_token(data={"sub": user.email, "user_id": str(user.id)})

    return AuthResponse(
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.full_name,
            full_name=user.full_name,
            company=user.company,
            plan=user.plan.value,
            is_verified=user.is_verified,
            created_at=user.created_at,
        ),
        token=access_token,
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login and get access token."""
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is deactivated"
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # Create access token with user_id for secure WebSocket connections
    access_token = create_access_token(data={"sub": user.email, "user_id": str(user.id)})

    return AuthResponse(
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.full_name,
            full_name=user.full_name,
            company=user.company,
            plan=user.plan.value,
            is_verified=user.is_verified,
            created_at=user.created_at,
        ),
        token=access_token,
    )


@router.post("/login/form", response_model=Token)
@limiter.limit(AUTH_RATE_LIMIT)
async def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with form data (for OAuth2 compatibility)."""
    return await login(request, LoginRequest(email=form_data.username, password=form_data.password), db)


@router.post("/refresh", response_model=Token)
@limiter.limit(AUTH_RATE_LIMIT)
async def refresh_token(request: Request, refresh_data: RefreshRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    try:
        payload = jwt.decode(
            refresh_data.refresh_token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Create new tokens with user_id for secure WebSocket connections
    access_token = create_access_token(data={"sub": user.email, "user_id": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": user.email, "user_id": str(user.id)})

    return Token(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.full_name,
        full_name=current_user.full_name,
        company=current_user.company,
        plan=current_user.plan.value,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
    )


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
):
    """
    Logout and invalidate the current access token.

    The token is added to a blacklist in Redis until its natural expiry.
    Client should also discard stored tokens.
    """
    try:
        # Decode token to get expiry time
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        exp_timestamp = payload.get("exp", 0)
        current_timestamp = datetime.now(timezone.utc).timestamp()
        ttl_seconds = int(exp_timestamp - current_timestamp)

        # Blacklist the token for its remaining lifetime
        blacklist_token(token, ttl_seconds)

    except JWTError:
        # Token is invalid anyway, just return success
        pass

    return {"message": "Successfully logged out"}
