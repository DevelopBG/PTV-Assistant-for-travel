"""
Service Alert Parser - Phase 9

Parses GTFS Realtime service alert feeds and provides methods
to query alerts by route, stop, or trip.
"""

import logging
import time
from typing import Dict, List, Optional

from .models import (
    ServiceAlert,
    ServiceAlertSummary,
    InformedEntity,
    ActivePeriod,
    AlertCause,
    AlertEffect,
    AlertSeverity,
)
from .feed_fetcher import GTFSRealtimeFetcher
from .modes import has_service_alerts, is_valid_mode, ALL_MODES

logger = logging.getLogger(__name__)


class ServiceAlertParser:
    """
    Parses and queries GTFS Realtime service alert feeds.

    Provides methods to fetch alerts and filter by route, stop, trip,
    or active time period.
    """

    # Mapping from protobuf cause enum to our AlertCause
    CAUSE_MAP = {
        1: AlertCause.UNKNOWN_CAUSE,
        2: AlertCause.OTHER_CAUSE,
        3: AlertCause.TECHNICAL_PROBLEM,
        4: AlertCause.STRIKE,
        5: AlertCause.DEMONSTRATION,
        6: AlertCause.ACCIDENT,
        7: AlertCause.HOLIDAY,
        8: AlertCause.WEATHER,
        9: AlertCause.MAINTENANCE,
        10: AlertCause.CONSTRUCTION,
        11: AlertCause.POLICE_ACTIVITY,
        12: AlertCause.MEDICAL_EMERGENCY,
    }

    # Mapping from protobuf effect enum to our AlertEffect
    EFFECT_MAP = {
        1: AlertEffect.NO_SERVICE,
        2: AlertEffect.REDUCED_SERVICE,
        3: AlertEffect.SIGNIFICANT_DELAYS,
        4: AlertEffect.DETOUR,
        5: AlertEffect.ADDITIONAL_SERVICE,
        6: AlertEffect.MODIFIED_SERVICE,
        7: AlertEffect.OTHER_EFFECT,
        8: AlertEffect.UNKNOWN_EFFECT,
        9: AlertEffect.STOP_MOVED,
        10: AlertEffect.NO_EFFECT,
        11: AlertEffect.ACCESSIBILITY_ISSUE,
    }

    # Mapping from protobuf severity enum to our AlertSeverity
    SEVERITY_MAP = {
        1: AlertSeverity.UNKNOWN_SEVERITY,
        2: AlertSeverity.INFO,
        3: AlertSeverity.WARNING,
        4: AlertSeverity.SEVERE,
    }

    def __init__(self, fetcher: Optional[GTFSRealtimeFetcher] = None):
        """
        Initialize the service alert parser.

        Args:
            fetcher: GTFSRealtimeFetcher instance for fetching feed data
        """
        self.fetcher = fetcher
        self._cache: Dict[str, List[ServiceAlert]] = {}  # mode → alerts

    def parse_feed(self, feed) -> List[ServiceAlert]:
        """
        Parse a GTFS Realtime FeedMessage into ServiceAlert objects.

        Args:
            feed: FeedMessage protobuf from GTFS Realtime

        Returns:
            List of ServiceAlert objects
        """
        alerts = []

        for entity in feed.entity:
            if not entity.HasField('alert'):
                continue

            alert = self._parse_alert_entity(entity.alert, entity.id)

            if alert:
                alerts.append(alert)

        logger.info(f"Parsed {len(alerts)} service alerts from feed")
        return alerts

    def _parse_alert_entity(self, alert, entity_id: str) -> Optional[ServiceAlert]:
        """
        Parse a single alert entity from the feed.

        Args:
            alert: Alert protobuf message
            entity_id: Entity ID from the feed

        Returns:
            ServiceAlert object or None if invalid
        """
        # Parse active periods
        active_periods = []
        for period in alert.active_period:
            start = period.start if period.HasField('start') else None
            end = period.end if period.HasField('end') else None
            active_periods.append(ActivePeriod(start=start, end=end))

        # Parse informed entities
        informed_entities = []
        for entity in alert.informed_entity:
            informed = InformedEntity(
                agency_id=entity.agency_id if entity.HasField('agency_id') else None,
                route_id=entity.route_id if entity.HasField('route_id') else None,
                route_type=entity.route_type if entity.HasField('route_type') else None,
                stop_id=entity.stop_id if entity.HasField('stop_id') else None,
                direction_id=entity.trip.direction_id if entity.HasField('trip') and entity.trip.HasField('direction_id') else None,
            )
            # Handle trip descriptor
            if entity.HasField('trip'):
                if entity.trip.HasField('trip_id'):
                    informed.trip_id = entity.trip.trip_id
            informed_entities.append(informed)

        # Parse cause
        cause = AlertCause.UNKNOWN_CAUSE
        if alert.HasField('cause'):
            cause = self.CAUSE_MAP.get(alert.cause, AlertCause.UNKNOWN_CAUSE)

        # Parse effect
        effect = AlertEffect.UNKNOWN_EFFECT
        if alert.HasField('effect'):
            effect = self.EFFECT_MAP.get(alert.effect, AlertEffect.UNKNOWN_EFFECT)

        # Parse severity (GTFS Realtime extension, may not be present)
        severity = AlertSeverity.UNKNOWN_SEVERITY
        if alert.HasField('severity_level'):
            severity = self.SEVERITY_MAP.get(alert.severity_level, AlertSeverity.UNKNOWN_SEVERITY)

        # Parse text content
        header_text = self._extract_translated_text(alert.header_text) if alert.HasField('header_text') else None
        description_text = self._extract_translated_text(alert.description_text) if alert.HasField('description_text') else None
        url = self._extract_translated_text(alert.url) if alert.HasField('url') else None

        return ServiceAlert(
            alert_id=entity_id,
            cause=cause,
            effect=effect,
            severity=severity,
            header_text=header_text,
            description_text=description_text,
            url=url,
            active_periods=active_periods,
            informed_entities=informed_entities,
            timestamp=int(time.time())
        )

    def _extract_translated_text(self, translated_string) -> Optional[str]:
        """
        Extract text from a TranslatedString protobuf.

        Prefers English translation if available, otherwise returns first.

        Args:
            translated_string: TranslatedString protobuf

        Returns:
            Text string or None
        """
        if not translated_string.translation:
            return None

        # Look for English translation first
        for translation in translated_string.translation:
            if translation.language == 'en' or not translation.language:
                return translation.text

        # Return first available translation
        return translated_string.translation[0].text if translated_string.translation else None

    def fetch_alerts(self, mode: str = 'metro') -> List[ServiceAlert]:
        """
        Fetch and parse service alerts for a transport mode.

        Note: Service alerts are only available for 'metro' and 'tram'.
        V/Line and bus do not have service alert feeds and will return
        an empty list gracefully.

        Args:
            mode: Transport mode ('metro', 'vline', 'tram', or 'bus')

        Returns:
            List of ServiceAlert objects (empty for modes without alerts)

        Raises:
            ValueError: If fetcher is not available or mode is invalid
        """
        if not self.fetcher:
            raise ValueError("Fetcher not available. Initialize parser with a GTFSRealtimeFetcher.")

        # Validate mode
        if not is_valid_mode(mode):
            raise ValueError(f"Unknown mode: {mode}. Must be one of {list(ALL_MODES)}")

        # Return empty list gracefully for modes without service alerts
        if not has_service_alerts(mode):
            logger.info(f"Service alerts not available for mode: {mode}. Returning empty list.")
            self._cache[mode] = []
            return []

        logger.info(f"Fetching service alerts for mode: {mode}")

        try:
            feed = self.fetcher.fetch_service_alerts(mode=mode)
            alerts = self.parse_feed(feed)
            self._cache[mode] = alerts
            return alerts
        except Exception as e:
            logger.error(f"Failed to fetch service alerts: {e}")
            raise

    def get_alerts_for_route(
        self,
        route_id: str,
        alerts: Optional[List[ServiceAlert]] = None
    ) -> List[ServiceAlert]:
        """
        Filter alerts affecting a specific route.

        Args:
            route_id: Route ID to filter by
            alerts: List of alerts to filter (uses cache if not provided)

        Returns:
            List of ServiceAlert objects affecting the route
        """
        if alerts is None:
            alerts = self._get_cached_alerts()

        return [a for a in alerts if a.affects_route(route_id)]

    def get_alerts_for_stop(
        self,
        stop_id: str,
        alerts: Optional[List[ServiceAlert]] = None
    ) -> List[ServiceAlert]:
        """
        Filter alerts affecting a specific stop.

        Args:
            stop_id: Stop ID to filter by
            alerts: List of alerts to filter (uses cache if not provided)

        Returns:
            List of ServiceAlert objects affecting the stop
        """
        if alerts is None:
            alerts = self._get_cached_alerts()

        return [a for a in alerts if a.affects_stop(stop_id)]

    def get_alerts_for_trip(
        self,
        trip_id: str,
        alerts: Optional[List[ServiceAlert]] = None
    ) -> List[ServiceAlert]:
        """
        Filter alerts affecting a specific trip.

        Args:
            trip_id: Trip ID to filter by
            alerts: List of alerts to filter (uses cache if not provided)

        Returns:
            List of ServiceAlert objects affecting the trip
        """
        if alerts is None:
            alerts = self._get_cached_alerts()

        return [a for a in alerts if a.affects_trip(trip_id)]

    def get_active_alerts(
        self,
        alerts: Optional[List[ServiceAlert]] = None,
        current_time: Optional[int] = None
    ) -> List[ServiceAlert]:
        """
        Filter alerts that are currently active.

        Args:
            alerts: List of alerts to filter (uses cache if not provided)
            current_time: Unix timestamp to check (defaults to now)

        Returns:
            List of currently active ServiceAlert objects
        """
        if alerts is None:
            alerts = self._get_cached_alerts()

        if current_time is None:
            current_time = int(time.time())

        return [a for a in alerts if a.is_active(current_time)]

    def get_alert_by_id(
        self,
        alert_id: str,
        alerts: Optional[List[ServiceAlert]] = None
    ) -> Optional[ServiceAlert]:
        """
        Get a single alert by its ID.

        Args:
            alert_id: Alert ID to look up
            alerts: List of alerts to search (uses cache if not provided)

        Returns:
            ServiceAlert or None if not found
        """
        if alerts is None:
            alerts = self._get_cached_alerts()

        for alert in alerts:
            if alert.alert_id == alert_id:
                return alert
        return None

    def get_alerts_by_severity(
        self,
        severity: AlertSeverity,
        alerts: Optional[List[ServiceAlert]] = None
    ) -> List[ServiceAlert]:
        """
        Filter alerts by severity level.

        Args:
            severity: Severity level to filter by
            alerts: List of alerts to filter (uses cache if not provided)

        Returns:
            List of ServiceAlert objects with matching severity
        """
        if alerts is None:
            alerts = self._get_cached_alerts()

        return [a for a in alerts if a.severity == severity]

    def get_alerts_by_effect(
        self,
        effect: AlertEffect,
        alerts: Optional[List[ServiceAlert]] = None
    ) -> List[ServiceAlert]:
        """
        Filter alerts by effect type.

        Args:
            effect: Effect type to filter by
            alerts: List of alerts to filter (uses cache if not provided)

        Returns:
            List of ServiceAlert objects with matching effect
        """
        if alerts is None:
            alerts = self._get_cached_alerts()

        return [a for a in alerts if a.effect == effect]

    def _get_cached_alerts(self) -> List[ServiceAlert]:
        """Get alerts from cache, returning empty list if none cached."""
        for mode_alerts in self._cache.values():
            return mode_alerts
        return []

    def get_summary(
        self,
        alerts: List[ServiceAlert],
        mode: Optional[str] = None
    ) -> ServiceAlertSummary:
        """
        Generate a summary of service alerts.

        Args:
            alerts: List of alerts to summarize
            mode: Transport mode label

        Returns:
            ServiceAlertSummary with aggregated statistics
        """
        by_severity: Dict[str, int] = {}
        by_effect: Dict[str, int] = {}
        affected_routes: List[str] = []
        affected_stops: List[str] = []

        for alert in alerts:
            # Count by severity
            sev_key = alert.severity.value
            by_severity[sev_key] = by_severity.get(sev_key, 0) + 1

            # Count by effect
            eff_key = alert.effect.value
            by_effect[eff_key] = by_effect.get(eff_key, 0) + 1

            # Collect affected entities
            affected_routes.extend(alert.get_affected_routes())
            affected_stops.extend(alert.get_affected_stops())

        # Deduplicate
        affected_routes = list(set(affected_routes))
        affected_stops = list(set(affected_stops))

        return ServiceAlertSummary(
            total_alerts=len(alerts),
            by_severity=by_severity,
            by_effect=by_effect,
            affected_routes=affected_routes,
            affected_stops=affected_stops,
            timestamp=int(time.time()),
            mode=mode
        )

    def clear_cache(self) -> None:
        """Clear the service alerts cache."""
        self._cache.clear()
        logger.debug("Service alert cache cleared")
