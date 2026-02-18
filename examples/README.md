# Examples - PTV Transit Assistant

This directory contains working demonstrations of the PTV Transit Assistant journey planning system.

## 🎯 Available Demonstrations

### 1. Simple Multi-Modal Demo
**File**: `simple_multimodal_demo.py`

A simple demonstration showing Phase 4's multi-modal routing features using test data.

**Run it:**
```bash
PYTHONPATH=. python examples/simple_multimodal_demo.py
```

**What it shows:**
- Creating journeys with transport mode information
- Single-mode vs multi-modal journeys
- Walking transfers
- All supported transport types (train, tram, bus, ferry)

---

### 2. Real Journey Finder ⭐
**File**: `find_real_journey.py`

**The complete demo using real GTFS data!** This demonstrates all phases (0-4) working together to find actual journeys between Tarneit and Waurn Ponds stations.

**Run it:**
```bash
python examples/find_real_journey.py
```

**What it does:**
1. ✓ Loads 497 stops from V/Line GTFS data
2. ✓ Builds transit network graph (99,694 connections)
3. ✓ Finds stations using fuzzy name matching
4. ✓ Plans journeys at 6 different departure times
5. ✓ Shows detailed journey breakdowns
6. ✓ Displays multi-modal analysis

**Sample Output:**
```
Journey Details: Tarneit Station → Waurn Ponds Station
Requested departure: 14:00:00

Journey: Tarneit Station → Waurn Ponds Station
Departure: 14:17:00
Arrival: 15:08:00
Duration: 51m
Transfers: 1

Leg 1:
  Tarneit Station → Geelong Station
  Mode: Regional Train
  Depart: 14:17:00  Arrive: 14:51:00
  Duration: 34m
  Route: Geelong - Melbourne Via Geelong

Leg 2:
  Geelong Station → Waurn Ponds Station
  Mode: Regional Train
  Depart: 14:54:00  Arrive: 15:08:00
  Duration: 14m
```

---

### 3. Original Multi-Modal Demo
**File**: `demo_multimodal.py`

Intended to demonstrate multi-modal routing with real data, but requires some adjustments to work with the parser API.

---

## 📚 Documentation

### Phase 4 API Reference
**File**: `PHASE4_API_REFERENCE.md`

Complete API documentation for Phase 4's multi-modal routing features:
- New fields added to Leg and Connection
- Methods: `get_mode_name()`, `get_modes_used()`, `is_multi_modal()`
- GTFS route type codes
- Use cases and code examples
- Migration notes

## 🎓 What You Can Learn

### From simple_multimodal_demo.py:
- How to create journeys programmatically
- Using Phase 4's mode tracking features
- Understanding multi-modal vs single-mode journeys

### From find_real_journey.py:
- Complete journey planning workflow
- Loading and parsing real GTFS data
- Building transit network graphs
- Finding stations with fuzzy matching
- Planning optimal routes with CSA
- Analyzing journey modes

## 🚀 Quick Start

**Want to see real journeys?**
```bash
python examples/find_real_journey.py
```

**Want to understand the API?**
```bash
PYTHONPATH=. python examples/simple_multimodal_demo.py
```

**Want to read the docs?**
```bash
cat examples/PHASE4_API_REFERENCE.md
```

## 💡 Tips

1. **Understanding the output**: The journey finder shows:
   - When to depart and arrive
   - How long each leg takes
   - Which stations to transfer at
   - What transport mode to catch

2. **Phase 4 features**: Look for:
   - `Mode: Regional Train` in journey legs
   - `Modes: Regional Train` in journey summaries
   - Multi-modal analysis section

3. **Modifying the demos**:
   - Change departure times in `find_real_journey.py`
   - Try different station pairs (must be in V/Line data)
   - Adjust test scenarios in `simple_multimodal_demo.py`

## 📊 Performance

From `find_real_journey.py` with real V/Line data:

- **Data loading**: Instant
- **Graph building**: ~1-2 seconds (99,694 connections)
- **Journey planning**: <0.1 seconds per query
- **Success rate**: 100% (6/6 journeys found)

## 🔮 What's Next?

These examples demonstrate Phases 0-4. Coming in future phases:

- **Phase 5**: Real-time delays and cancellations
- **Phase 6**: Web API and CLI interface
- **Phase 7**: Performance optimization

## 🤝 Contributing

When adding new examples:
1. Use descriptive filenames
2. Include docstrings explaining what the example does
3. Add error handling
4. Update this README
5. Test with real data if possible

## ❓ Questions?

See the main project documentation:
- [README.md](../README.md) - Project overview
- [DEVELOPMENT_STATUS.md](../DEVELOPMENT_STATUS.md) - Detailed progress
- [CONTEXT.md](../CONTEXT.md) - Quick resume guide
