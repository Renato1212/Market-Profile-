from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Boolean, Integer, DateTime, Text, Index
from datetime import datetime
from typing import Optional
from config import settings


engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class DailySession(Base):
    """One row per ES cash session (09:30–16:00 ET)"""
    __tablename__ = "daily_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), unique=True, index=True)  # YYYY-MM-DD
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Mon
    month: Mapped[int] = mapped_column(Integer)
    week_of_month: Mapped[int] = mapped_column(Integer)

    # OHLCV cash session
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)

    # Prior session reference
    prior_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prior_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prior_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prior_open: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Market Profile Value Area (computed from TPO / 5-min bars)
    vah: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    val: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    poc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Overnight high/low (Globex 16:00–09:30)
    on_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    on_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Gap fields
    gap_size_pts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gap_size_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gap_direction: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)  # up/down/none
    filled_same_session: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    fill_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mae_before_fill_pts: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    partial_fill_25pct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    partial_fill_50pct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    partial_fill_75pct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    gap_context: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    consecutive_gap_streak: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Prior day type
    prior_day_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Macro context
    vix_prior_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vix_current: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trend_regime: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # Bull/Bear/Mixed

    # Calendar flags
    is_fomc_day: Mapped[bool] = mapped_column(Boolean, default=False)
    is_fomc_eve: Mapped[bool] = mapped_column(Boolean, default=False)
    is_opex_friday: Mapped[bool] = mapped_column(Boolean, default=False)
    is_quarter_end: Mapped[bool] = mapped_column(Boolean, default=False)
    is_expiry_week: Mapped[bool] = mapped_column(Boolean, default=False)

    # A Period fields
    a_open: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_range: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_close_position: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    a_body_vs_range: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    a_direction: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    a_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    a_high_held_eod: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    a_low_held_eod: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    a_extension_direction: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    gap_filled_in_a_period: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Day type
    day_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Data quality
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    exclusion_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    has_intraday: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IntradayBar(Base):
    """5-minute bars for ES cash session"""
    __tablename__ = "intraday_bars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    timestamp: Mapped[str] = mapped_column(String(25), index=True)  # ISO8601
    bar_index: Mapped[int] = mapped_column(Integer)  # 0 = 09:30 bar
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)

    __table_args__ = (Index("ix_intraday_date_ts", "date", "timestamp"),)


class GEXSnapshot(Base):
    """Gamma exposure snapshots every 15 min"""
    __tablename__ = "gex_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[str] = mapped_column(String(25), index=True)
    spy_price: Mapped[float] = mapped_column(Float)
    es_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_gex: Mapped[float] = mapped_column(Float)
    call_wall_spy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    put_wall_spy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    zero_gamma_spy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    call_wall_es: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    put_wall_es: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    zero_gamma_es: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    regime: Mapped[str] = mapped_column(String(10))  # long/short/neutral
    gex_data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON strike-level data
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AIBriefing(Base):
    """Cached AI pre-market plans"""
    __tablename__ = "ai_briefings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    user_tier: Mapped[str] = mapped_column(String(20), default="pro")
    content: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str] = mapped_column(String(50))
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DataCache(Base):
    """Generic key-value cache for API responses"""
    __tablename__ = "data_cache"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
