"""
API route modules.
"""

from .journey import router as journey_router
from .stops import router as stops_router
from .health import router as health_router
from .vehicles import router as vehicles_router
from .alerts import router as alerts_router

__all__ = ["journey_router", "stops_router", "health_router", "vehicles_router", "alerts_router"]
