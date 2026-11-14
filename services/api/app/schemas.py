"""Request and response shapes. They also become the OpenAPI schema for the client."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models import Role

HouseholdName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class CreateHouseholdIn(BaseModel):
    name: HouseholdName
    display_name: DisplayName


class AcceptInviteIn(BaseModel):
    display_name: DisplayName


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    role: Role
    joined_at: datetime


class HouseholdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime


class HouseholdDetailOut(HouseholdOut):
    members: list[MemberOut]


class MeOut(BaseModel):
    member: MemberOut
    household: HouseholdOut


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    expires_at: datetime


class ErrorOut(BaseModel):
    code: str
    detail: str
