"""
Transfer-Aware Multi-Modal Journey Planner.

Coordinates journey planning across multiple transport modes with
intelligent transfer handling and multiple route alternatives.
"""

from typing import List, Optional
from datetime import datetime
import logging

from ..data.multimodal_parser import MultiModalGTFSParser
from ..graph.unified_transit_graph import UnifiedTransitGraph
from .journey_planner import JourneyPlanner
from .models import Journey, Leg

logger = logging.getLogger(__name__)


class TransferJourneyPlanner:
    """
    High-level journey planner that finds multi-modal routes with transfers.

    Uses UnifiedTransitGraph to search across all transport modes simultaneously,
    finding routes that may combine trains, trams, and buses with transfers.
    """

    def __init__(self, multimodal_parser: MultiModalGTFSParser):
        """
        Initialize transfer-aware journey planner.

        Args:
            multimodal_parser: MultiModalGTFSParser with loaded data for all modes
        """
        self.parser = multimodal_parser

        logger.info("Building unified multi-modal transit graph...")
        self.unified_graph = UnifiedTransitGraph(multimodal_parser)

        logger.info("Initializing base journey planner...")
        self.base_planner = JourneyPlanner(
            multimodal_parser,  # Uses merged data from all modes
            self.unified_graph   # Uses unified graph with transfers
        )

        logger.info("Transfer Journey Planner ready!")
        logger.info(f"  Transfer hubs: {len(self.unified_graph.get_transfer_hubs())}")
        logger.info(f"  Total stops: {len(multimodal_parser.stops)}")

    def find_best_journey(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        departure_time: Optional[str] = None,
        max_transfers: int = 4
    ) -> Optional[Journey]:
        """
        Find single best journey using two-tier search strategy.

        Strategy:
        1. Try direct route first (same mode, no transfers) - FAST
        2. If no direct route, try multi-modal with transfers - SLOWER but necessary

        This provides excellent performance for most queries while still
        handling complex multi-modal journeys when needed.

        Args:
            origin_stop_id: Origin stop ID
            destination_stop_id: Destination stop ID
            departure_time: Departure time (HH:MM:SS). If None, uses current time.
            max_transfers: Maximum number of transfers allowed

        Returns:
            Single best Journey, or None if no route found
        """
        # Use current time if not specified
        if departure_time is None:
            departure_time = datetime.now().strftime("%H:%M:%S")

        logger.info(f"Finding best journey: {origin_stop_id} → {destination_stop_id} at {departure_time}")

        # TIER 1: Try direct route (same mode, fast search)
        logger.debug("Tier 1: Trying direct route (same mode only)...")
        direct_journey = self.base_planner.find_journey(
            origin_stop_id,
            destination_stop_id,
            departure_time
        )

        if direct_journey:
            logger.info(f"✓ Found direct route: {direct_journey.duration_minutes}m, "
                       f"{direct_journey.num_transfers} transfers")
            self._enhance_transfer_info(direct_journey)
            return direct_journey

        # TIER 2: Try multi-modal with transfers (slower)
        logger.debug("Tier 1 failed. Tier 2: Trying multi-modal with transfers...")

        # Use find_journey which already has the iterative transfer logic
        multi_journey = self.base_planner.find_journey(
            origin_stop_id,
            destination_stop_id,
            departure_time
        )

        if multi_journey:
            logger.info(f"✓ Found multi-modal route: {multi_journey.duration_minutes}m, "
                       f"{multi_journey.num_transfers} transfers, "
                       f"modes: {', '.join(multi_journey.get_modes_used())}")
            self._enhance_transfer_info(multi_journey)
            return multi_journey

        logger.info("✗ No route found")
        return None

    def find_journeys(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        departure_time: Optional[str] = None,
        num_routes: int = 3,
        max_transfers: int = 4
    ) -> List[Journey]:
        """
        Find multiple multi-modal journeys with transfers.

        Returns up to num_routes alternative routes, sorted by total duration.
        Routes may combine different transport modes (train, tram, bus) with
        walking transfers between modes.

        Args:
            origin_stop_id: Origin stop ID
            destination_stop_id: Destination stop ID
            departure_time: Departure time (HH:MM:SS). If None, uses current time.
            num_routes: Maximum number of alternative routes to return
            max_transfers: Maximum number of transfers allowed per journey

        Returns:
            List of Journey objects, sorted by duration (fastest first)

        Example:
            >>> planner = TransferJourneyPlanner(parser)
            >>> journeys = planner.find_journeys('12253', '47641', num_routes=3)
            >>> for i, journey in enumerate(journeys, 1):
            ...     print(f"Route {i}: {journey.duration_minutes} min, "
            ...           f"{journey.num_transfers} transfers")
        """
        # Use current time if not specified
        if departure_time is None:
            departure_time = datetime.now().strftime("%H:%M:%S")
            logger.debug(f"Using current time: {departure_time}")

        logger.info(
            f"Finding journeys: {origin_stop_id} → {destination_stop_id} "
            f"at {departure_time} (max {num_routes} routes, {max_transfers} transfers)"
        )

        # Find multiple alternative routes using extended CSA
        journeys = self.base_planner.find_multiple_journeys(
            origin_stop_id,
            destination_stop_id,
            departure_time,
            max_results=num_routes,
            max_transfers=max_transfers
        )

        if not journeys:
            logger.info("No journeys found")
            return []

        # Post-process: enhance transfer information
        for journey in journeys:
            self._enhance_transfer_info(journey)

        # Sort by duration (fastest first)
        journeys.sort(key=lambda j: j.duration_minutes)

        logger.info(f"Found {len(journeys)} alternative journeys")
        for i, journey in enumerate(journeys, 1):
            modes = journey.get_modes_used()
            logger.info(
                f"  Route {i}: {journey.duration_minutes}m, "
                f"{journey.num_transfers} transfers, "
                f"modes: {', '.join(modes)}"
            )

        return journeys

    def _enhance_transfer_info(self, journey: Journey):
        """
        Add additional transfer information to journey legs.

        Enhances transfer legs with:
        - Walking distance/time
        - Platform information (if available)
        - Transfer hub name

        Args:
            journey: Journey to enhance (modified in place)
        """
        for i, leg in enumerate(journey.legs):
            if leg.is_transfer:
                # Get stop information
                from_stop = self.parser.get_stop(leg.from_stop_id)
                to_stop = self.parser.get_stop(leg.to_stop_id)

                if from_stop and to_stop:
                    # Add platform codes if available
                    if hasattr(from_stop, 'platform_code') and from_stop.platform_code:
                        leg.from_platform = from_stop.platform_code

                    if hasattr(to_stop, 'platform_code') and to_stop.platform_code:
                        leg.to_platform = to_stop.platform_code

                    # Check if this is at a known transfer hub
                    hub_name = self.unified_graph.get_hub_for_stop(leg.from_stop_id)
                    if hub_name:
                        leg.transfer_hub_name = hub_name

    def get_transfer_hubs(self) -> dict:
        """
        Get all identified transfer hubs.

        Returns:
            Dictionary mapping hub names to lists of stop IDs
        """
        return self.unified_graph.get_transfer_hubs()

    def is_stop_at_hub(self, stop_id: str) -> bool:
        """
        Check if a stop is part of a transfer hub.

        Args:
            stop_id: Stop ID to check

        Returns:
            True if stop is part of a transfer hub
        """
        return self.unified_graph.is_transfer_hub(stop_id)
