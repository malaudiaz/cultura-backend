"""Esquemas de representación y administración de usuarios."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.roles import Role


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: str
    role: Role
    created_at: datetime


class RoleUpdate(BaseModel):
    role: Role
