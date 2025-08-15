# app/models.py
from datetime import datetime, date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    String, Integer, BigInteger, Boolean, Date, DateTime,
    ForeignKey, Float, UniqueConstraint, Index
)

class Base(DeclarativeBase):
    pass

class Participant(Base):
    __tablename__ = "participants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    tz: Mapped[str] = mapped_column(String(64), default="Europe/Amsterdam")
    consent_version: Mapped[str] = mapped_column(String(32), default="v1")

    strava_athlete_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    strava_access_token: Mapped[str | None] = mapped_column(String(512))
    strava_refresh_token: Mapped[str | None] = mapped_column(String(512))
    strava_token_expires_at: Mapped[int | None] = mapped_column(Integer)

    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Activity(Base):
    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(32), default="strava")
    athlete_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)

    strava_activity_id: Mapped[int] = mapped_column(BigInteger)
    start_date_local: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    distance_m: Mapped[float] = mapped_column(Float)
    moving_time_s: Mapped[int] = mapped_column(Integer)
    sport_type: Mapped[str] = mapped_column(String(64))
    trainer: Mapped[bool] = mapped_column(Boolean, default=False)
    is_virtual: Mapped[bool] = mapped_column(Boolean, default=False)
    is_ebike: Mapped[bool] = mapped_column(Boolean, default=False)

    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_json: Mapped[str | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("source", "strava_activity_id", name="uq_source_activity"),
        Index("idx_activities_date", "start_date_local"),
    )

class DailyRollup(Base):
    __tablename__ = "daily_rollups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)

    km_total: Mapped[float] = mapped_column(Float, default=0)
    km_outdoor: Mapped[float] = mapped_column(Float, default=0)
    km_indoor: Mapped[float] = mapped_column(Float, default=0)
    met_25km: Mapped[bool] = mapped_column(Boolean, default=False)
    first_start_time_local: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    early_bird: Mapped[bool] = mapped_column(Boolean, default=False)
    night_owl: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("athlete_id", "date", name="uq_rollup_day"),
    )

class Award(Base):
    __tablename__ = "awards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(String(64))
    athlete_id: Mapped[int] = mapped_column(ForeignKey("participants.id"))
    value_num: Mapped[float] = mapped_column(Float)

class Points(Base):
    __tablename__ = "points"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("participants.id"))
    daily_points: Mapped[int] = mapped_column(Integer, default=0)
    cumulative_points: Mapped[int] = mapped_column(Integer, default=0)
