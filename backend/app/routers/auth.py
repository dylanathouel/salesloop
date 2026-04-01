from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Schémas Pydantic (ce que l'API attend/retourne) ---

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone: str | None = None
    role: str = "commercial"
    tenant_id: str
    manager_id: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str
    tenant_id: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str


# --- Routes ---

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Vérifier si l'email existe déjà dans ce tenant
    result = await db.execute(
        select(User).where(User.email == data.email, User.tenant_id == data.tenant_id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cet email est déjà utilisé dans cette organisation",
        )

    # Créer le user
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=data.role,
        tenant_id=data.tenant_id,
        manager_id=data.manager_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Générer le token
    token = create_access_token({"sub": str(user.id), "role": user.role, "tenant_id": str(user.tenant_id)})

    return AuthResponse(access_token=token, user_id=str(user.id), role=user.role)


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Chercher le user
    result = await db.execute(
        select(User).where(User.email == data.email, User.tenant_id == data.tenant_id)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )

    token = create_access_token({"sub": str(user.id), "role": user.role, "tenant_id": str(user.tenant_id)})

    return AuthResponse(access_token=token, user_id=str(user.id), role=user.role)