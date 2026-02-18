# Phase 4: Multi-Modal Routing API Reference

## Overview

Phase 4 adds transport mode tracking and analysis to the journey planning system. Every journey leg now knows what type of transport it represents (train, tram, bus, etc.).

## Quick Example

```python
from src.routing.models import Leg, Journey

# Create a leg with mode information
leg = Leg(
    from_stop_id="1001",
    from_stop_name="Tarneit Station",
    to_stop_id="1002",
    to_stop_name="Flinders Street",
    departure_time="08:00:00",
    arrival_time="08:35:00",
    trip_id="T123",
    route_id="R1",
    route_name="Geelong - Melbourne",
    route_type=2  # NEW IN PHASE 4: GTFS route type code
)

# Get human-readable mode name
mode = leg.get_mode_name()  # Returns: "Regional Train"

# Create journey
journey = Journey(
    origin_stop_id="1001",
    origin_stop_name="Tarneit Station",
    destination_stop_id="1002",
    destination_stop_name="Flinders Street",
    departure_time="08:00:00",
    arrival_time="08:35:00",
    legs=[leg]
)

# Analyze transport modes used
modes = journey.get_modes_used()     # Returns: ['Regional Train']
multi = journey.is_multi_modal()     # Returns: False
```

## New Fields

### Leg Dataclass

**New fields added in Phase 4:**

```python
@dataclass
class Leg:
    # ... existing fields ...

    route_type: Optional[int] = None    # GTFS route type code
    is_transfer: bool = False           # True for walking transfers
```

**GTFS Route Type Codes:**
- `0` = Tram
- `1` = Metro (subway/underground)
- `2` = Regional Train (rail)
- `3` = Bus
- `4` = Ferry
- `700` = Bus (PTV-specific code)
- `900` = Tram (PTV-specific code)

### Connection Dataclass

```python
@dataclass
class Connection:
    # ... existing fields ...

    route_type: Optional[int] = None    # GTFS route type code
    is_transfer: bool = False           # True for walking transfers
```

## New Methods

### Leg.get_mode_name()

Get human-readable transport mode name.

**Signature:**
```python
def get_mode_name(self) -> str:
```

**Returns:**
- `"Tram"` for route_type 0 or 900
- `"Metro"` for route_type 1
- `"Regional Train"` for route_type 2
- `"Bus"` for route_type 3 or 700
- `"Ferry"` for route_type 4
- `"Walking"` if is_transfer=True
- `"Unknown"` for unrecognized codes

**Example:**
```python
leg = Leg(..., route_type=2)
print(leg.get_mode_name())  # Output: "Regional Train"

transfer_leg = Leg(..., is_transfer=True)
print(transfer_leg.get_mode_name())  # Output: "Walking"
```

---

### Journey.get_modes_used()

Get list of all transport modes used in the journey (excluding walking).

**Signature:**
```python
def get_modes_used(self) -> List[str]:
```

**Returns:**
List of unique mode names in order of appearance.

**Example:**
```python
# Single-mode journey
journey = Journey(legs=[train_leg])
modes = journey.get_modes_used()
# Output: ['Regional Train']

# Multi-modal journey
journey = Journey(legs=[train_leg, tram_leg])
modes = journey.get_modes_used()
# Output: ['Regional Train', 'Tram']

# Journey with walking transfer
journey = Journey(legs=[metro_leg, walk_leg, tram_leg])
modes = journey.get_modes_used()
# Output: ['Metro', 'Tram']  # Walking excluded!
```

---

### Journey.is_multi_modal()

Check if journey uses multiple transport modes.

**Signature:**
```python
def is_multi_modal(self) -> bool:
```

**Returns:**
- `True` if journey uses 2+ different transport modes (excluding walking)
- `False` if journey uses only one transport mode

**Example:**
```python
# Single mode
journey1 = Journey(legs=[train_leg])
journey1.is_multi_modal()  # Returns: False

# Multi-modal
journey2 = Journey(legs=[train_leg, bus_leg])
journey2.is_multi_modal()  # Returns: True

# With walking transfer (still multi-modal)
journey3 = Journey(legs=[train_leg, walk_leg, tram_leg])
journey3.is_multi_modal()  # Returns: True (train + tram)
```

---

### Connection.get_mode_name()

Same as `Leg.get_mode_name()` but for Connection objects.

**Signature:**
```python
def get_mode_name(self) -> str:
```

**Example:**
```python
from src.graph.transit_graph import Connection

conn = Connection(
    from_stop_id="1001",
    to_stop_id="1002",
    trip_id="T1",
    departure_time="08:00:00",
    arrival_time="08:10:00",
    travel_time_seconds=600,
    route_id="R1",
    route_type=1
)

print(conn.get_mode_name())  # Output: "Metro"
```

## Journey Summary Output

The `Journey.format_summary()` method now includes mode information:

**Example Output:**
```
Journey: Tarneit Station → St Kilda Beach
Departure: 08:00:00
Arrival: 09:05:00
Duration: 1h 5m
Transfers: 1

Leg 1:
  Tarneit Station → Flinders Street Station
  Mode: Regional Train        ← NEW IN PHASE 4
  Depart: 08:00:00  Arrive: 08:35:00
  Duration: 35m
  Route: Geelong - Melbourne
  Stops: 12

Leg 2:
  Flinders Street Station → St Kilda Beach
  Mode: Tram                  ← NEW IN PHASE 4
  Depart: 08:45:00  Arrive: 09:05:00
  Duration: 20m
  Route: Route 96
  Stops: 15
```

## Use Cases

### 1. Display Mode Icons in UI

```python
mode_icons = {
    "Metro": "🚇",
    "Regional Train": "🚆",
    "Tram": "🚊",
    "Bus": "🚌",
    "Ferry": "⛴️",
    "Walking": "🚶"
}

for leg in journey.legs:
    icon = mode_icons.get(leg.get_mode_name(), "🚉")
    print(f"{icon} {leg.from_stop_name} → {leg.to_stop_name}")
```

### 2. Filter Journeys by Mode Preference

```python
def uses_preferred_modes(journey, preferred_modes):
    """Check if journey only uses preferred transport modes."""
    journey_modes = journey.get_modes_used()
    return all(mode in preferred_modes for mode in journey_modes)

# User only wants train/metro
preferred = ["Metro", "Regional Train"]
if uses_preferred_modes(journey, preferred):
    print("✓ This journey matches your preferences")
```

### 3. Warn About Multi-Modal Complexity

```python
if journey.is_multi_modal():
    modes = journey.get_modes_used()
    print(f"⚠️ This journey requires changing between {len(modes)} transport types:")
    print(f"   {' → '.join(modes)}")
    print(f"   Allow extra time for transfers!")
```

### 4. Apply Mode-Specific Delays (Phase 5 Preview)

```python
# Future Phase 5 functionality
for leg in journey.legs:
    mode = leg.get_mode_name()

    if mode == "Metro":
        # Apply metro-specific delays
        delay = get_metro_delay(leg.trip_id)
    elif mode == "Tram":
        # Apply tram-specific delays
        delay = get_tram_delay(leg.trip_id)
    # etc.
```

## Testing

Run the multi-modal tests:

```bash
# All multi-modal tests
pytest tests/test_routing/test_multimodal.py -v

# Specific test
pytest tests/test_routing/test_multimodal.py::TestJourneyMultiModal::test_journey_is_multi_modal_true -v
```

Run the demonstration:

```bash
PYTHONPATH=. python examples/simple_multimodal_demo.py
```

## Migration Notes

### Breaking Changes
None - Phase 4 is fully backward compatible.

### New Optional Fields
- `Leg.route_type` defaults to `None`
- `Leg.is_transfer` defaults to `False`
- `Connection.route_type` defaults to `None`
- `Connection.is_transfer` defaults to `False`

### Existing Code Compatibility
All existing code continues to work. The new fields are optional and default to sensible values.

```python
# Old code still works
leg = Leg(
    from_stop_id="1001",
    from_stop_name="Stop A",
    to_stop_id="1002",
    to_stop_name="Stop B",
    departure_time="08:00:00",
    arrival_time="08:10:00",
    trip_id="T1",
    route_id="R1"
    # route_type not specified - defaults to None
)

leg.get_mode_name()  # Returns: "Unknown"
```

## Future Enhancements (Next Phases)

### Phase 5: Realtime Integration
- Apply mode-specific delays
- Filter cancelled services per mode
- Show platform information

### Phase 6: Web API
- Mode filtering in API queries
- Mode-based journey preferences
- Multi-modal journey optimization

### Phase 7: Performance
- Mode-specific caching strategies
- Optimize multi-modal transfer calculations

## Implementation Details

### Route Type Mapping Logic

The `get_mode_name()` method uses this mapping:

```python
def get_mode_name(self) -> str:
    """Get human-readable mode name."""
    if self.is_transfer:
        return "Walking"

    mode_map = {
        0: "Tram",
        1: "Metro",
        2: "Regional Train",
        3: "Bus",
        4: "Ferry",
        700: "Bus",   # PTV-specific
        900: "Tram"   # PTV-specific
    }
    return mode_map.get(self.route_type, "Unknown")
```

### Mode List Filtering

The `get_modes_used()` method excludes walking transfers:

```python
def get_modes_used(self) -> List[str]:
    """Get list of transport modes used."""
    modes = []
    seen = set()
    for leg in self.legs:
        mode = leg.get_mode_name()
        if mode not in seen and mode != "Walking":  # Exclude walking
            modes.append(mode)
            seen.add(mode)
    return modes
```

This ensures walking transfers don't count as a "mode" when determining if a journey is multi-modal.

## See Also

- [DEVELOPMENT_STATUS.md](../DEVELOPMENT_STATUS.md) - Full Phase 4 implementation details
- [src/routing/models.py](../src/routing/models.py) - Source code for Leg and Journey
- [tests/test_routing/test_multimodal.py](../tests/test_routing/test_multimodal.py) - Test suite
- [examples/simple_multimodal_demo.py](simple_multimodal_demo.py) - Working examples
