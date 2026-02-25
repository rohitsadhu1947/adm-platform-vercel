"""
Authentication routes for the ADM Platform.
Simple JWT-based auth with admin vs ADM roles.
"""

from datetime import datetime, timedelta
from typing import Optional

import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database import get_db
from models import User, ADM
from config import settings
from schemas import LoginRequest, LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using simple SHA-256 hash (demo only)."""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def get_password_hash(password: str) -> str:
    """Hash password using simple SHA-256 (demo only)."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    # jose requires 'sub' to be a string
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Get current user from JWT token. Returns None if no token or invalid token."""
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        user = db.query(User).filter(User.id == int(user_id_str)).first()
        return user
    except (JWTError, ValueError):
        return None


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get current user from JWT token. Raises 401 if not authenticated."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user = db.query(User).filter(User.id == int(user_id_str)).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    token = create_access_token(
        data={"sub": user.id, "role": user.role, "adm_id": user.adm_id}
    )

    return LoginResponse(
        token=token,
        user={
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "role": user.role,
            "adm_id": user.adm_id,
        },
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return current_user


@router.post("/register-adm")
def register_adm(request: dict, db: Session = Depends(get_db)):
    """Register a new ADM user. Creates both ADM record and login credentials."""
    from models import ADM

    required = ["name", "phone", "username", "password"]
    for field in required:
        if not request.get(field):
            raise HTTPException(status_code=400, detail=f"Field '{field}' is required")

    # Check username not taken
    if db.query(User).filter(User.username == request["username"]).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create ADM record
    adm = ADM(
        name=request["name"],
        phone=request["phone"],
        email=request.get("email", ""),
        region=request.get("region", ""),
        language=request.get("language", "Hindi,English"),
        max_capacity=request.get("max_capacity", 50),
        telegram_chat_id=request.get("telegram_chat_id"),
    )
    db.add(adm)
    db.flush()

    # Create user login
    user = User(
        username=request["username"],
        password_hash=get_password_hash(request["password"]),
        role="adm",
        name=request["name"],
        adm_id=adm.id,
    )
    db.add(user)
    db.commit()

    return {
        "message": f"ADM '{request['name']}' registered successfully",
        "adm_id": adm.id,
        "username": request["username"],
    }
