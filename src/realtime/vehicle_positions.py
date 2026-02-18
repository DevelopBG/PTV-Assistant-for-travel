"""
Vehicle Position Parser - Phase 8

Parses GTFS Realtime vehicle position feeds and provides methods
to query vehicle locations by route, trip, or proximity to stops.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from math import radians, sin, cos, sqrt, atan2

from .models import (
    VehiclePosition,
    VehiclePositionSummary,
    VehicleStopStatus,
    CongestionLevel,
    OccupancyStatus
)
from .feed_fetcher import GTFSRealtimeFetcher

logger = logging.getLogger(__name__)


class VehiclePositionParser:
    """
    Parses and queries GTFS Realtime vehicle position feeds.

    Provides methods to fetch vehicle positions and filter by route,
    trip, or proximity to stops.
    """

    def __init__(self, fetcher: Optional[GTFSRealtimeFetcher] = None):
        """
        Initialize the vehicle position parser.

        Args:
            fetcher: GTFSRealtimeFetcher instance for fetching feed data
        """
        self.fetcher = fetcher
        self._cache: Dict[str, List[VehiclePosition]] = {}  # mode → positions

    def parse_feed(self, feed) -> List[VehiclePosition]:
        """
        Parse a GTFS Realtime FeedMessage into VehiclePosition objects.

        Args:
            feed: FeedMessage protobuf from GTFS Realtime

        Returns:
            List of VehiclePosition objects
        """
        positions = []

        for entity in feed.entity:
            if not entity.HasField('vehicle'):
                continue

            vehicle = entity.vehicle
            position = self._parse_vehicle_entity(vehicle, entity.id)

            if position:
                positions.append(position)

        logger.info(f"Parsed {len(positions)} vehicle positions from feed")
        return positions

    def _parse_vehicle_entity(self, vehicle, entity_id: str) -> Optional[VehiclePosition]:
        """
        Parse a single vehicle entity from the feed.

        Args:
            vehicle: VehiclePosition protobuf message
            entity_id: Entity ID from the feed

        Returns:
            VehiclePosition object or None if invalid
        """
        # Position is required
        if not vehicle.HasField('position'):
            logger.debug(f"Entity {entity_id} has no position data")
            return None

        pos = vehicle.position

        # Latitude and longitude are required
        if not pos.HasField('latitude') or not pos.HasField('longitude'):
            logger.debug(f"Entity {entity_id} missing lat/lon")
            return None

        # Extract vehicle ID
        vehicle_id = entity_id
        if vehicle.HasField('vehicle'):
            veh_desc = vehicle.vehicle
            if veh_desc.HasField('id'):
                vehicle_id = veh_desc.id
            elif veh_desc.HasField('label'):
                vehicle_id = veh_desc.label

        # Extract trip information
        trip_id = None
        route_id = None
        direction_id = None

        if vehicle.HasField('trip'):
            trip = vehicle.trip
            if trip.HasField('trip_id'):
                trip_id = trip.trip_id
            if trip.HasField('route_id'):
                route_id = trip.route_id
            if trip.HasField('direction_id'):
                direction_id = trip.direction_id

        # Extract vehicle descriptor
        label = None
        license_plate = None

        if vehicle.HasField('vehicle'):
            veh_desc = vehicle.vehicle
            if veh_desc.HasField('label'):
                label = veh_desc.label
            if veh_desc.HasField('license_plate'):
                license_plate = veh_desc.license_plate

        # Extract position details
        bearing = pos.bearing if pos.HasField('bearing') else None
        speed = pos.speed if pos.HasField('speed') else None
        odometer = pos.odometer if pos.HasField('odometer') else None

        # Extract stop relationship
        stop_id = vehicle.stop_id if vehicle.HasField('stop_id') else None
        stop_sequence = vehicle.current_stop_sequence if vehicle.HasField('current_stop_sequence') else None

        current_status = None
        if vehicle.HasField('current_status'):
            from google.transit import gtfs_realtime_pb2
            status_map = {
                gtfs_realtime_pb2.VehiclePosition.INCOMING_AT: VehicleStopStatus.INCOMING_AT,
                gtfs_realtime_pb2.VehiclePosition.STOPPED_AT: VehicleStopStatus.STOPPED_AT,
                gtfs_realtime_pb2.VehiclePosition.IN_TRANSIT_TO: VehicleStopStatus.IN_TRANSIT_TO,
            }
            current_status = status_map.get(vehicle.current_status)

        # Extract congestion level
        congestion_level = None
        if vehicle.HasField('congestion_level'):
            from google.transit import gtfs_realtime_pb2
            congestion_map = {
                gtfs_realtime_pb2.VehiclePosition.UNKNOWN_CONGESTION_LEVEL: CongestionLevel.UNKNOWN_CONGESTION_LEVEL,
                gtfs_realtime_pb2.VehiclePosition.RUNNING_SMOOTHLY: CongestionLevel.RUNNING_SMOOTHLY,
                gtfs_realtime_pb2.VehiclePosition.STOP_AND_GO: CongestionLevel.STOP_AND_GO,
                gtfs_realtime_pb2.VehiclePosition.CONGESTION: CongestionLevel.CONGESTION,
                gtfs_realtime_pb2.VehiclePosition.SEVERE_CONGESTION: CongestionLevel.SEVERE_CONGESTION,
            }
            congestion_level = congestion_map.get(vehicle.congestion_level)

        # Extract occupancy status
        occupancy_status = None
        occupancy_percentage = None

        if vehicle.HasField('occupancy_status'):
            from google.transit import gtfs_realtime_pb2
            occupancy_map = {
                gtfs_realtime_pb2.VehiclePosition.EMPTY: OccupancyStatus.EMPTY,
                gtfs_realtime_pb2.VehiclePosition.MANY_SEATS_AVAILABLE: OccupancyStatus.MANY_SEATS_AVAILABLE,
                gtfs_realtime_pb2.VehiclePosition.FEW_SEATS_AVAILABLE: OccupancyStatus.FEW_SEATS_AVAILABLE,
                gtfs_realtime_pb2.VehiclePosition.STANDING_ROOM_ONLY: OccupancyStatus.STANDING_ROOM_ONLY,
                gtfs_realtime_pb2.VehiclePosition.CRUSHED_STANDING_ROOM_ONLY: OccupancyStatus.CRUSHED_STANDING_ROOM_ONLY,
                gtfs_realtime_pb2.VehiclePosition.FULL: OccupancyStatus.FULL,
                gtfs_realtime_pb2.VehiclePosition.NOT_ACCEPTING_PASSENGERS: OccupancyStatus.NOT_ACCEPTING_PASSENGERS,
            }
            occupancy_status = occupancy_map.get(vehicle.occupancy_status)

        if vehicle.HasField('occupancy_percentage'):
            occupancy_percentage = vehicle.occupancy_percentage

        # Extract timestamp
        timestamp = vehicle.timestamp if vehicle.HasField('timestamp') else 0

        return VehiclePosition(
            vehicle_id=vehicle_id,
            latitude=pos.latitude,
            longitude=pos.longitude,
            timestamp=timestamp,
            trip_id=trip_id,
            route_id=route_id,
            direction_id=direction_id,
            label=label,
            license_plate=license_plate,
            bearing=bearing,
            speed=speed,
            odometer=odometer,
            stop_id=stop_id,
            current_stop_sequence=stop_sequence,
            current_status=current_status,
            congestion_level=congestion_level,
            occupancy_status=occupancy_status,
            occupancy_percentage=occupancy_percentage
        )

    def fetch_positions(self, mode: str = 'vline') -> List[VehiclePosition]:
        """
        Fetch and parse vehicle positions for a transport mode.

        Args:
            mode: Transport mode ('metro' or 'vline')

        Returns:
            List of VehiclePosition objects

        Raises:
            ValueError: If fetcher is not available or mode is invalid
        """
        if not self.fetcher:
            raise ValueError("Fetcher not available. Initialize parser with a GTFSRealtimeFetcher.")

        logger.info(f"Fetching vehicle positions for mode: {mode}")

        try:
            feed = self.fetcher.fetch_vehicle_positions(mode=mode)
            positions = self.parse_feed(feed)
            self._cache[mode] = positions
            return positions
        except Exception as e:
            logger.error(f"Failed to fetch vehicle positions: {e}")
            raise

    def get_vehicles_for_route(
        self,
        route_id: str,
        positions: Optional[List[VehiclePosition]] = None
    ) -> List[VehiclePosition]:
        """
        Filter vehicle positions by route ID.

        Args:
            route_id: Route ID to filter by
            positions: List of positions to filter (uses cache if not provided)

        Returns:
            List of VehiclePosition objects on the specified route
        """
        if positions is None:
            # Try to get from cache
            for mode_positions in self._cache.values():
                positions = mode_positions
                break
            if positions is None:
                return []

        return [p for p in positions if p.route_id == route_id]

    def get_vehicles_for_trip(
        self,
        trip_id: str,
        positions: Optional[List[VehiclePosition]] = None
    ) -> List[VehiclePosition]:
        """
        Filter vehicle positions by trip ID.

        Args:
            trip_id: Trip ID to filter by
            positions: List of positions to filter (uses cache if not provided)

        Returns:
            List of VehiclePosition objects for the specified trip (usually 0 or 1)
        """
        if positions is None:
            for mode_positions in self._cache.values():
                positions = mode_positions
                break
            if positions is None:
                return []

        return [p for p in positions if p.trip_id == trip_id]

    def get_vehicle_by_id(
        self,
        vehicle_id: str,
        positions: Optional[List[VehiclePosition]] = None
    ) -> Optional[VehiclePosition]:
        """
        Get a single vehicle position by vehicle ID.

        Args:
            vehicle_id: Vehicle ID to look up
            positions: List of positions to search (uses cache if not provided)

        Returns:
            VehiclePosition or None if not found
        """
        if positions is None:
            for mode_positions in self._cache.values():
                positions = mode_positions
                break
            if positions is None:
                return None

        for p in positions:
            if p.vehicle_id == vehicle_id:
                return p
        return None

    def get_vehicles_near_stop(
        self,
        stop_lat: float,
        stop_lon: float,
        radius_km: float = 1.0,
        positions: Optional[List[VehiclePosition]] = None
    ) -> List[VehiclePosition]:
        """
        Find vehicles within a radius of a location.

        Args:
            stop_lat: Latitude of the center point
            stop_lon: Longitude of the center point
            radius_km: Search radius in kilometers (default: 1.0)
            positions: List of positions to search (uses cache if not provided)

        Returns:
            List of VehiclePosition objects within the radius, sorted by distance
        """
        if positions is None:
            for mode_positions in self._cache.values():
                positions = mode_positions
                break
            if positions is None:
                return []

        nearby = []
        for p in positions:
            if not p.has_location():
                continue

            distance = self._haversine_distance(
                stop_lat, stop_lon,
                p.latitude, p.longitude
            )

            if distance <= radius_km:
                nearby.append((distance, p))

        # Sort by distance
        nearby.sort(key=lambda x: x[0])
        return [p for _, p in nearby]

    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        Calculate the great-circle distance between two points.

        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates

        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth's radius in km

        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)

        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    def get_summary(
        self,
        positions: List[VehiclePosition],
        mode: Optional[str] = None,
        route_id: Optional[str] = None
    ) -> VehiclePositionSummary:
        """
        Generate a summary of vehicle positions.

        Args:
            positions: List of vehicle positions to summarize
            mode: Transport mode label
            route_id: Route ID label

        Returns:
            VehiclePositionSummary with aggregated statistics
        """
        total = len(positions)
        with_trip = sum(1 for p in positions if p.trip_id)
        in_transit = sum(1 for p in positions if p.current_status == VehicleStopStatus.IN_TRANSIT_TO)
        at_stop = sum(1 for p in positions if p.current_status == VehicleStopStatus.STOPPED_AT)

        # Calculate average speed
        speeds = [p.get_speed_kmh() for p in positions if p.speed is not None]
        avg_speed = sum(speeds) / len(speeds) if speeds else None

        # Get most recent timestamp
        timestamps = [p.timestamp for p in positions if p.timestamp > 0]
        latest_timestamp = max(timestamps) if timestamps else None

        return VehiclePositionSummary(
            total_vehicles=total,
            vehicles_with_trip=with_trip,
            vehicles_in_transit=in_transit,
            vehicles_at_stop=at_stop,
            average_speed_kmh=round(avg_speed, 1) if avg_speed else None,
            timestamp=latest_timestamp,
            mode=mode,
            route_id=route_id
        )

    def clear_cache(self) -> None:
        """Clear the vehicle positions cache."""
        self._cache.clear()
        logger.debug("Vehicle position cache cleared")
