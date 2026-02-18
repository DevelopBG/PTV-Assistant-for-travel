"""
FastAPI dependencies for dependency injection.

Provides shared resources like GTFS parser, stop index, and journey planner.
"""

import os
import logging
from functools import lru_cache
from typing import Optional

from ..data.gtfs_parser import GTFSParser
from ..data.multimodal_parser import MultiModalGTFSParser
from ..data.stop_index import StopIndex
from ..graph.transit_graph import TransitGraph
from ..routing.journey_planner import JourneyPlanner
from ..routing.transfer_journey_planner import TransferJourneyPlanner
from ..realtime.feed_fetcher import GTFSRealtimeFetcher
from ..realtime.integration import RealtimeIntegrator
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

# Default GTFS data directory
DEFAULT_GTFS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "gtfs"
)


class TransitService:
    """
    Singleton service that holds all transit data and provides journey planning.

    This class is instantiated once and reused across all requests.
    """

    def __init__(self, gtfs_dir: Optional[str] = None, modes_to_load: Optional[list] = None):
        """
        Initialize transit service.

        Args:
            gtfs_dir: Path to GTFS data directory. Defaults to data/gtfs.
            modes_to_load: List of mode folders to load (e.g., ['1', '2', '3']).
                          Defaults to ['1', '2', '3'] for trains and trams.
        """
        self.gtfs_dir = gtfs_dir or DEFAULT_GTFS_DIR
        self.modes_to_load = modes_to_load or ['1', '2', '3']  # V/Line, Metro, Trams by default
        self._parser: Optional[MultiModalGTFSParser] = None
        self._stop_index: Optional[StopIndex] = None
        self._graph: Optional[TransitGraph] = None
        self._planner: Optional[TransferJourneyPlanner] = None
        self._realtime_fetcher: Optional[GTFSRealtimeFetcher] = None
        self._is_loaded = False

    def load(self) -> "TransitService":
        """
        Load all GTFS data and initialize services.

        Returns:
            Self for method chaining.
        """
        if self._is_loaded:
            logger.debug("Transit service already loaded")
            return self

        logger.info(f"Loading transit data from {self.gtfs_dir} (modes: {self.modes_to_load})")

        try:
            # Load GTFS data using MultiModalGTFSParser
            self._parser = MultiModalGTFSParser(
                base_gtfs_dir=self.gtfs_dir,
                modes_to_load=self.modes_to_load
            )
            self._parser.load_all()

            # Build indexes and graph
            self._stop_index = StopIndex(self._parser)
            self._graph = TransitGraph(self._parser)
            self._planner = TransferJourneyPlanner(self._parser)

            # Initialize realtime fetcher (optional - requires API key)
            api_key = os.environ.get("PTV_API_KEY")
            if api_key:
                self._realtime_fetcher = GTFSRealtimeFetcher(api_key)
                logger.info("Realtime fetcher initialized with API key")
            else:
                logger.warning("PTV_API_KEY not set - realtime features disabled")

            self._is_loaded = True
            logger.info(
                f"Transit service loaded: {len(self._parser.stops)} stops, "
                f"{len(self._parser.routes)} routes, {len(self._parser.trips)} trips"
            )

        except Exception as e:
            logger.error(f"Failed to load transit data: {e}")
            raise

        return self

    @property
    def is_loaded(self) -> bool:
        """Check if transit data is loaded."""
        return self._is_loaded

    @property
    def parser(self) -> Optional[MultiModalGTFSParser]:
        """Get GTFS parser."""
        return self._parser

    @property
    def stop_index(self) -> Optional[StopIndex]:
        """Get stop index."""
        return self._stop_index

    @property
    def graph(self) -> Optional[TransitGraph]:
        """Get transit graph."""
        return self._graph

    @property
    def planner(self) -> Optional[TransferJourneyPlanner]:
        """Get journey planner."""
        return self._planner

    @property
    def realtime_fetcher(self) -> Optional[GTFSRealtimeFetcher]:
        """Get realtime fetcher."""
        return self._realtime_fetcher

    def get_realtime_fetcher(self) -> Optional[GTFSRealtimeFetcher]:
        """
        Get the realtime fetcher instance.

        Returns:
            GTFSRealtimeFetcher if API key is available, None otherwise.
        """
        return self._realtime_fetcher

    def get_realtime_integrator(self) -> Optional[RealtimeIntegrator]:
        """
        Get a new realtime integrator instance.

        Returns:
            RealtimeIntegrator if API key is available, None otherwise.
        """
        if self._realtime_fetcher and self._parser:
            return RealtimeIntegrator(self._realtime_fetcher, self._parser)
        return None


# Global transit service instance
_transit_service: Optional[TransitService] = None


def get_transit_service() -> TransitService:
    """
    Get the global transit service instance.

    This function is used as a FastAPI dependency.

    Returns:
        Loaded TransitService instance.
    """
    global _transit_service

    if _transit_service is None:
        # Get modes to load from environment variable or use default
        modes_env = os.environ.get('GTFS_MODES_TO_LOAD', '1,2,3')
        modes_to_load = [m.strip() for m in modes_env.split(',')]

        logger.info(f"Initializing transit service with modes: {modes_to_load}")
        _transit_service = TransitService(modes_to_load=modes_to_load)
        _transit_service.load()

    return _transit_service


def reset_transit_service() -> None:
    """
    Reset the global transit service.

    Used primarily for testing.
    """
    global _transit_service
    _transit_service = None
