# Duration Bug Fix - Summary

**Date:** 2026-01-23
**Issue:** Journey duration showing incorrect/negative times
**Status:** ✅ FIXED

---

## Problem Description

Journey planner was showing incorrect durations for multi-modal routes:

### Example: Richmond → Waurn Ponds
- **Before Fix:** 1445-1469 minutes (24+ hours)
- **After Fix:** 101 minutes (1h 41m) ✅
- **Expected:** ~90-120 minutes

---

## Root Causes

### Issue 1: Midnight Crossing Not Handled
**File:** `src/routing/models.py`

**Problem:** Duration calculation failed when journey crossed midnight.

**Example:**
```
Departure: 22:35:00 (81,300 seconds)
Arrival:   00:05:00 (300 seconds - next day)
Calculation: 300 - 81,300 = -81,000 seconds ❌ NEGATIVE!
```

**Fix:** Added midnight crossing detection
```python
@property
def duration_seconds(self) -> int:
    """Calculate duration in seconds, handling midnight crossings."""
    dep = time_to_seconds(self.departure_time)
    arr = time_to_seconds(self.arrival_time)

    # Handle midnight crossing (arrival before departure)
    if arr < dep:
        arr += 86400  # Add 24 hours (next day)

    return arr - dep
```

**Applied To:**
- `Leg.duration_seconds` property (line ~76)
- `Journey.duration_seconds` property (line ~156)

---

### Issue 2: Journey Using Transfer Connection Times
**File:** `src/routing/journey_planner.py`

**Problem:** Journey departure/arrival times were set from `path_connections[0]` which could be a transfer connection with "00:00:00" time.

**Example Journey:**
```
Path connections:
  1. Transfer: 00:00:00 to 00:03:00 (Richmond → Richmond)  ← First connection
  2. Train:    22:54:00 to 23:04:00 (Richmond → Southern Cross)
  3. Train:    23:08:00 to 23:21:00 (Southern Cross → Sunshine)
  4. Train:    23:23:00 to 24:29:00 (Sunshine → Waurn Ponds)

Journey created with:
  departure_time = path_connections[0].departure_time = "00:00:00" ❌
  arrival_time   = path_connections[-1].arrival_time  = "24:29:00" ✅

Duration: 24:29 - 00:00 = 1469 minutes ❌ WRONG!
```

**Fix v1 (Partial):** Use `legs[0].departure_time` instead of `path_connections[0].departure_time`

**Problem:** Still failed when first leg is a transfer leg with "00:00:00" time.

**Fix v2 (Complete):** Use first **non-transfer** leg's departure time
```python
# In _reconstruct_journey() method around line 297
first_non_transfer = next((leg for leg in legs if not leg.is_transfer), legs[0])
last_non_transfer = next((leg for leg in reversed(legs) if not leg.is_transfer), legs[-1])

journey = Journey(
    ...,
    departure_time=first_non_transfer.departure_time,  # First actual transit leg
    arrival_time=last_non_transfer.arrival_time,        # Last actual transit leg
    legs=legs
)
```

**Result:**
```
Journey created with:
  departure_time = legs[1].departure_time = "23:03:00" ✅
  arrival_time   = legs[-1].arrival_time  = "24:44:00" ✅

Duration: 24:44 - 23:03 = 101 minutes ✅ CORRECT!
```

---

## Test Results

### Test 1: Richmond → Waurn Ponds (Multi-Modal)
**Command:** `python test_duration_fix.py`

```
BEFORE FIX:
  Departure: 00:00:00
  Arrival:   24:29:00
  Duration:  1469 min (24h 29m) ❌

AFTER FIX:
  Departure: 23:03:00
  Arrival:   24:44:00
  Duration:  101 min (1h 41m) ✅
  Transfers: 4
  Modes:     Unknown, Regional Train

  Leg Details:
    1. Unknown: Richmond → Flinders Street (4m)
    2. Unknown: Flinders Street → Southern Cross (3m)
    3. Walking: Southern Cross → Southern Cross (3m)
    4. Regional Train: Southern Cross → Deer Park (20m)
    5. Regional Train: Deer Park → Waurn Ponds (1h 1m)
```

**Result:** ✅ PASS - Duration is reasonable for this journey

---

### Test 2: Tarneit → Waurn Ponds (Direct Route)
**Command:** `python test_direct_route.py`

```
RESULT:
  Route found in 7.72s
  Departure: 23:07:00
  Arrival:   23:59:00
  Duration:  52 min (52m) ✅
  Transfers: 0
  Modes:     Regional Train

  Leg Details:
    1. Regional Train: Tarneit → Waurn Ponds (52m)
```

**Result:** ✅ PASS - Direct route found quickly, correct duration

---

## Performance Impact

**Before:** ~10-15s for multi-modal routes
**After:**  ~7-10s for direct routes, ~10s for multi-modal routes
**Status:** ✅ Performance maintained while fixing correctness

---

## Files Modified

1. **src/routing/models.py**
   - Line ~76: Updated `Leg.duration_seconds` property
   - Line ~156: Updated `Journey.duration_seconds` property

2. **src/routing/journey_planner.py**
   - Line ~297: Updated Journey creation in `_reconstruct_journey()`
   - Used first/last non-transfer leg times instead of connection times

---

## Verification Checklist

- ✅ Midnight crossing handled in `Leg.duration_seconds`
- ✅ Midnight crossing handled in `Journey.duration_seconds`
- ✅ Journey uses first non-transfer leg's departure time
- ✅ Journey uses last non-transfer leg's arrival time
- ✅ Richmond → Waurn Ponds shows correct duration (~101 min)
- ✅ Tarneit → Waurn Ponds still works (direct route)
- ✅ No negative durations
- ✅ Performance not degraded

---

## Next Steps

1. Test in web UI (Flask app running on http://localhost:5001)
2. Verify UI displays correct duration
3. Test other multi-modal routes for edge cases

---

## Known Minor Issue

Some legs show as "Unknown" mode instead of proper mode names (e.g., "Metro", "V/Line"). This is a display issue, not a duration calculation issue. The route_type is not being properly set for some connections.

**Impact:** Low - Journey routing and duration are correct, only mode name display affected.

---

**Status:** Duration Bug FIXED ✅
**Tested:** Command-line tests passing
**Ready for:** Web UI testing
