import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    email_tokens: Mapped[list["EmailToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reports: Mapped[list["StatusReport"]] = relationship(back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class EmailToken(Base):
    __tablename__ = "email_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="email_tokens")


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    municipality: Mapped[str | None] = mapped_column(String, nullable=False)
    opening_hours: Mapped[str | None] = mapped_column(String, nullable=True)
    operator: Mapped[str | None] = mapped_column(String, nullable=True)
    station_type: Mapped[str | None] = mapped_column(String(3), nullable=False)  # "avs" | "avc"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    waste_types: Mapped[list["StationWasteType"]] = relationship(
        back_populates="station", cascade="all, delete-orphan"
    )
    reports: Mapped[list["StatusReport"]] = relationship(back_populates="station")

    __table_args__ = (
        Index("ix_stations_lat", "latitude"),
        Index("ix_stations_lon", "longitude"),
    )


class StationWasteType(Base):
    __tablename__ = "station_waste_types"

    station_id: Mapped[str] = mapped_column(
        String, ForeignKey("stations.id", ondelete="CASCADE"), primary_key=True
    )
    waste_type: Mapped[str] = mapped_column(String(100), primary_key=True)

    station: Mapped["Station"] = relationship(back_populates="waste_types")

    __table_args__ = (Index("ix_swt_waste_type", "waste_type"),)


class StatusReport(Base):
    __tablename__ = "status_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[str] = mapped_column(
        String, ForeignKey("stations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    station: Mapped["Station"] = relationship(back_populates="reports")
    user: Mapped["User | None"] = relationship(back_populates="reports")

    __table_args__ = (Index("ix_sr_station_id", "station_id"),)


class SyncMeta(Base):
    __tablename__ = "sync_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    station_count: Mapped[int] = mapped_column(Integer, default=0)
