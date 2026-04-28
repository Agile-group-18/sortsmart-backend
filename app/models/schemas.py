from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class StationStatus(str, Enum):
    operational = "operational"
    full = "full"
    not_working = "not_working"
    unknown = "unknown"


class FilterMode(str, Enum):
    any = "any"
    all = "all"


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    # TODO: enforce password strenght requirements?
    # @field_validator("password")
    # @classmethod
    # def password_strength(cls, v: str) -> str:
    #     if not any(c.isupper() for c in v):
    #         raise ValueError("Password must contain at least one uppercase letter")
    #     if not any(c.isdigit() for c in v):
    #         raise ValueError("Password must contain at least one digit")
    #     return v


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    username_or_email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ProfileResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_verified: bool
    created_at: datetime
    report_count: int = 0

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    username: Optional[str] = Field(
        None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$"
    )


class StationSummary(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    distance_km: Optional[float] = None
    waste_types: list[str] = []
    reported_status: StationStatus = StationStatus.unknown
    address: Optional[str] = None


class StationDetail(StationSummary):
    municipality: Optional[str] = None
    opening_hours: Optional[str] = None
    operator: Optional[str] = None
    last_synced: Optional[datetime] = None
    report_count: int = 0


class NearbyResponse(BaseModel):
    total: int
    stations: list[StationSummary]
    query_lat: float
    query_lon: float


class CategoryResponse(BaseModel):
    categories: list[str]
    total_stations_per_category: dict[str, int]


class ReportRequest(BaseModel):
    status: StationStatus
    note: Optional[str] = Field(None, max_length=280)


class ReportResponse(BaseModel):
    station_id: str
    status: StationStatus
    report_count: int
    message: str
