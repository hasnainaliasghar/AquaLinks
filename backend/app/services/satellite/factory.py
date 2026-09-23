"""Construct the satellite provider configured for the current environment."""

from __future__ import annotations

from app.core.config import get_settings
from app.services.satellite.base import SatelliteProvider
from app.services.satellite.planetary_provider import PlanetaryComputerProvider
from app.services.satellite.sample_provider import SampleProvider


def get_satellite_provider() -> SatelliteProvider:
    """Return the active satellite provider.

    The ``AQUALENS_USE_SAMPLE_PROVIDER`` flag short-circuits to the
    in-process sample provider; this is used by tests and the E2E
    Playwright job so they don't depend on outbound network.
    """
    settings = get_settings()
    if settings.aqualens_use_sample_provider:
        return SampleProvider()
    return PlanetaryComputerProvider(stac_url=settings.pc_stac_url)
