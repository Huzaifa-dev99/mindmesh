import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import LoginRequest, TokenResponse, UserCreate, UserResponse, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession):
        self.repository = UserRepository(session)

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        existing = await self.repository.get_by_email(user_data.email)
        if existing:
            raise HTTPException(status_code=409, detail="Email is already registered")
        user = await self.repository.create(user_data, hash_password(user_data.password))
        return UserResponse.model_validate(user)

    async def get_user(self, user_id: uuid.UUID) -> UserResponse:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse.model_validate(user)

    async def authenticate(self, data: LoginRequest) -> TokenResponse:
        user = await self.repository.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = create_access_token(str(user.id))
        return TokenResponse(access_token=token, user=UserResponse.model_validate(user))

    async def update_user(self, user_id: uuid.UUID, data: UserUpdate) -> UserResponse:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        updated = await self.repository.update(user, data)
        return UserResponse.model_validate(updated)
