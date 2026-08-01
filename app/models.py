from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SchemaMeta(Base):
    __tablename__ = "schema_meta"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(100), nullable=False)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    workstream: Mapped[str] = mapped_column(String(100), default="Operations", nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="P1", nullable=False)
    revenue_impact: Mapped[str] = mapped_column(String(20), default="Medium", nullable=False)
    due_date: Mapped[str | None] = mapped_column(String(10))
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Opportunity(Base):
    __tablename__ = "opportunities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account: Mapped[str] = mapped_column(String(200), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    next_action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    next_date: Mapped[str | None] = mapped_column(String(10))


class ResearchProgram(Base):
    __tablename__ = "research"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    commercial_output: Mapped[str] = mapped_column(Text, nullable=False)
    next_action: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Milestone(Base):
    __tablename__ = "milestones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    target_date: Mapped[str] = mapped_column(String(10), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    owner: Mapped[str] = mapped_column(String(120), default="Founder", nullable=False)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class KPI(Base):
    __tablename__ = "kpis"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    target: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    actual: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), default="count", nullable=False)
