from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class MarketRecord(Base):
    __tablename__ = "markets"
    __table_args__ = (UniqueConstraint("provider", "external_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(255))
    question: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    prices: Mapped[list["MarketPriceRecord"]] = relationship(back_populates="market")


class MarketPriceRecord(Base):
    __tablename__ = "market_prices"
    __table_args__ = (Index("ix_market_prices_market_observed", "market_id", "observed_at"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    market_id: Mapped[UUID] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"))
    yes_price: Mapped[Decimal] = mapped_column(Numeric(12, 10))
    no_price: Mapped[Decimal] = mapped_column(Numeric(12, 10))
    liquidity: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=0)
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=0)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    market: Mapped[MarketRecord] = relationship(back_populates="prices")


class SourceRecord(Base):
    __tablename__ = "sources"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    url: Mapped[str] = mapped_column(Text, unique=True)
    publisher: Mapped[str] = mapped_column(String(255))
    historical_accuracy: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))


class ResearchRecord(Base):
    __tablename__ = "research"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    market_id: Mapped[UUID] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvidenceRecord(Base):
    __tablename__ = "evidence"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    research_id: Mapped[UUID] = mapped_column(ForeignKey("research.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id"))
    claim: Mapped[str] = mapped_column(Text)
    citation: Mapped[str] = mapped_column(Text)
    supports_yes: Mapped[bool] = mapped_column(Boolean)
    reliability: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    freshness: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    importance: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    independence_group: Mapped[str] = mapped_column(String(255))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PredictionRecord(Base):
    __tablename__ = "predictions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    market_id: Mapped[UUID] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"), index=True)
    prior: Mapped[Decimal] = mapped_column(Numeric(12, 10))
    posterior: Mapped[Decimal] = mapped_column(Numeric(12, 10))
    lower_bound: Mapped[Decimal] = mapped_column(Numeric(12, 10))
    upper_bound: Mapped[Decimal] = mapped_column(Numeric(12, 10))
    explanation: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PortfolioRecord(Base):
    __tablename__ = "portfolios"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    bankroll: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PositionRecord(Base):
    __tablename__ = "positions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), index=True)
    market_id: Mapped[UUID] = mapped_column(ForeignKey("markets.id"), index=True)
    side: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    average_price: Mapped[Decimal] = mapped_column(Numeric(12, 10))
    status: Mapped[str] = mapped_column(String(16))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AlertRecord(Base):
    __tablename__ = "alerts"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    market_id: Mapped[UUID] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(32))
    edge_threshold: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HistoricalResultRecord(Base):
    __tablename__ = "historical_results"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    market_id: Mapped[UUID] = mapped_column(ForeignKey("markets.id"), unique=True)
    outcome: Mapped[bool] = mapped_column(Boolean)
    brier_score: Mapped[Decimal] = mapped_column(Numeric(12, 10))
    log_loss: Mapped[Decimal] = mapped_column(Numeric(16, 12))
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
