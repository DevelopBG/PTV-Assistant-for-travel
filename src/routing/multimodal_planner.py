"""
Multi-Modal Journey Planner

Plans journeys across different transport modes and returns
results organized by mode (trains, trams, buses).
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from ..data.multimodal_parser import MultiModalGTFSParser
from ..data.stop_index import StopIndex
from ..graph.transit_graph import TransitGraph
from .journey_planner import JourneyPlanner
from .models import Journey

logger = logging.getLogger(__name__)


class MultiModalJourneyPlanner:
    """
    Journey planner that searches across multiple transport modes.

    For each mode, attempts to find a journey and returns results
    organized by transport type (train, tram, bus).
    """

    def __init__(self, multimodal_parser: MultiModalGTFSParser):
        """
        Initialize multi-modal journey planner.

        Args:
            multimodal_parser: MultiModalGTFSParser with loaded data
        """
        self.parser = multimodal_parser
        self.mode_planners: Dict[str, JourneyPlanner] = {}

        # Create a journey planner for each loaded mode
        logger.info("Initializing journey planners for each mode...")
        for mode_id in self.parser.get_loaded_modes():
            mode_parser = self.parser.mode_parsers[mode_id]
            try:
                graph = TransitGraph(mode_parser)
                planner = JourneyPlanner(mode_parser, graph)
                self.mode_planners[mode_id] = planner
                mode_info = self.parser.get_mode_info(mode_id)
                logger.info(f"  ✓ {mode_info['name']} planner ready")
            except Exception as e:
                logger.warning(f"  ✗ Could not create planner for mode {mode_id}: {e}")

    def find_journeys_by_mode(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        departure_time: Optional[str] = None,
        max_transfers: int = 3
    ) -> Dict[str, Optional[Journey]]:
        """
        Find journeys for each transport mode.

        Args:
            origin_stop_id: Origin stop ID
            destination_stop_id: Destination stop ID
            departure_time: Departure time (HH:MM:SS). If None, uses current time.
            max_transfers: Maximum transfers allowed

        Returns:
            Dictionary mapping transport type ('train', 'tram', 'bus') to Journey or None
        """
        # Use current time if not specified
        if departure_time is None:
            departure_time = datetime.now().strftime("%H:%M:%S")

        logger.info(
            f"Planning multi-modal journey: {origin_stop_id} -> {destination_stop_id} "
            f"at {departure_time}"
        )

        # Results organized by transport type
        results_by_type: Dict[str, Optional[Journey]] = {
            'train': None,
            'tram': None,
            'bus': None
        }

        # Try each mode
        for mode_id, planner in self.mode_planners.items():
            mode_info = self.parser.get_mode_info(mode_id)
            mode_type = mode_info['type']
            mode_name = mode_info['name']

            try:
                # Check if both stops exist in this mode's data
                mode_parser = self.parser.mode_parsers[mode_id]
                has_origin = origin_stop_id in mode_parser.stops
                has_destination = destination_stop_id in mode_parser.stops

                if not has_origin or not has_destination:
                    logger.debug(
                        f"  - {mode_name}: Stops not in this mode "
                        f"(origin: {has_origin}, dest: {has_destination})"
                    )
                    continue

                logger.debug(f"  Searching {mode_name}...")
                journey = planner.find_journey(
                    origin_stop_id,
                    destination_stop_id,
                    departure_time,
                    max_transfers
                )

                if journey:
                    logger.info(
                        f"  ✓ {mode_name}: Found journey "
                        f"({journey.duration_minutes}m, {journey.num_transfers} transfers)"
                    )
                    # Store the best journey for this transport type
                    if results_by_type[mode_type] is None:
                        results_by_type[mode_type] = journey
                    else:
                        # Keep the faster journey
                        existing = results_by_type[mode_type]
                        if journey.duration_minutes < existing.duration_minutes:
                            results_by_type[mode_type] = journey
                else:
                    logger.debug(f"  - {mode_name}: No route found")

            except ValueError as e:
                # Stop not found in this mode
                logger.debug(f"  - {mode_name}: {e}")
            except Exception as e:
                logger.error(f"  ✗ {mode_name}: Error planning journey - {e}")

        return results_by_type

    def find_all_journeys(
        self,
        origin_stop_id: str,
        destination_stop_id: str,
        departure_time: Optional[str] = None,
        max_transfers: int = 3,
        num_departures: int = 3
    ) -> Dict[str, List[Journey]]:
        """
        Find multiple journey options for each transport mode.

        Args:
            origin_stop_id: Origin stop ID
            destination_stop_id: Destination stop ID
            departure_time: Initial departure time. If None, uses current time.
            max_transfers: Maximum transfers allowed
            num_departures: Number of departure times to search

        Returns:
            Dictionary mapping transport type to list of Journeys
        """
        # Use current time if not specified
        if departure_time is None:
            departure_time = datetime.now().strftime("%H:%M:%S")

        results_by_type: Dict[str, List[Journey]] = {
            'train': [],
            'tram': [],
            'bus': []
        }

        # Search multiple departure times (every 30 minutes)
        search_times = self._generate_search_times(departure_time, num_departures)

        for search_time in search_times:
            journeys = self.find_journeys_by_mode(
                origin_stop_id,
                destination_stop_id,
                search_time,
                max_transfers
            )

            for mode_type, journey in journeys.items():
                if journey:
                    # Avoid duplicates
                    if not any(j.departure_time == journey.departure_time
                              for j in results_by_type[mode_type]):
                        results_by_type[mode_type].append(journey)

        return results_by_type

    def _generate_search_times(self, base_time: str, count: int, interval_minutes: int = 30) -> List[str]:
        """
        Generate multiple search times starting from base_time.

        Args:
            base_time: Starting time (HH:MM:SS)
            count: Number of times to generate
            interval_minutes: Minutes between each time

        Returns:
            List of time strings (HH:MM:SS)
        """
        times = []
        parts = base_time.split(':')
        base_hour = int(parts[0])
        base_minute = int(parts[1])
        base_second = int(parts[2]) if len(parts) > 2 else 0

        for i in range(count):
            total_minutes = base_hour * 60 + base_minute + (i * interval_minutes)
            hour = (total_minutes // 60) % 24
            minute = total_minutes % 60
            times.append(f"{hour:02d}:{minute:02d}:{base_second:02d}")

        return times
