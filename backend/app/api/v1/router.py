"""API v1 router aggregating every endpoint module."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import evidence, health, report, sessions, water_bodies

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(water_bodies.router)
api_router.include_router(sessions.router)
api_router.include_router(evidence.router)
api_router.include_router(report.router)
