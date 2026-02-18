# PTV Assistant

A Python-based multi-modal journey planner for Melbourne's public transport network (trains, trams, and buses) using Public Transport Victoria's (PTV) GTFS datasets.

## 🚀 Project Status

**Current Phase**: Phase 5 Complete ✅
**Next Milestone**: Phase 6 - Web API & CLI
**Progress**: 6/8 phases complete (75%)

## 📋 Overview

PTV Assistant finds optimal routes between stations using real-time and scheduled data from PTV's GTFS feeds. The system supports:

- 🚆 Metro trains
- 🚊 Trams
- 🚌 Metro & regional buses
- 🚂 V/Line regional trains

## 🎯 Current Capabilities

### Phase 0: Foundation ✅
- ✅ Fetch real-time trip updates from PTV GTFS feeds
- ✅ Parse protocol buffer data
- ✅ Display arrival/departure predictions with delays
- ✅ 21 tests, 100% test coverage

### Phase 1: Data Layer ✅
- ✅ Parse GTFS static data (stops, routes, trips, schedules)
- ✅ Type-safe data models for all GTFS entities
- ✅ Fast stop lookup with fuzzy name matching
- ✅ Extracted V/Line GTFS (497 stops, 13 routes, 8,096 trips)
- ✅ 62 tests, 97% test coverage
- ✅ Successfully query trips between stations (e.g., Tarneit to Waurn Ponds)

### Phase 2: Graph Construction ✅
- ✅ Build transit network graph with NetworkX
- ✅ Nodes for stops with metadata (name, coordinates)
- ✅ Edges for connections with travel times
- ✅ Support for trip connections and transfers
- ✅ Query methods (neighbors, travel times, routes, connections)
- ✅ 36 tests, 95% test coverage

### Phase 3: Single-Mode Routing ✅
- ✅ Connection Scan Algorithm (CSA) implementation
- ✅ Find optimal journeys between stations
- ✅ Support for departure time constraints
- ✅ Journey reconstruction with legs and transfers
- ✅ Journey and Leg dataclasses with time formatting
- ✅ 41 tests, 98% test coverage
- ✅ Can now answer: "How do I get from Tarneit to Waurn Ponds at 2 PM?"

### Phase 4: Multi-Modal Routing ✅
- ✅ Route type tracking for all transport modes (train, tram, bus, ferry)
- ✅ Mode identification in Connection and Leg dataclasses
- ✅ Multi-modal journey support with mode changes
- ✅ Walking transfer detection
- ✅ Journey mode analysis (get_modes_used, is_multi_modal)
- ✅ Mode-aware journey summaries
- ✅ 58 tests (17 new), 97% test coverage
- ✅ Ready for multi-modal GTFS data when extracted

### Phase 5: Realtime Integration ✅
- ✅ Apply real-time delays to journey times
- ✅ Detect and filter cancelled services
- ✅ Validate transfers remain feasible after delays
- ✅ Platform information extraction
- ✅ Time conversion utilities (Unix ↔ HH:MM:SS)
- ✅ Graceful fallback when realtime unavailable
- ✅ Enhanced journey display (scheduled → actual times)
- ✅ 53 tests (33 time_utils + 20 integration), 95%+ test coverage
- ✅ CLI integration with --realtime flag

## 🚦 Quick Start

### Prerequisites

- Python 3.9+
- PTV API key from [PTV Open Data Portal](https://opendata.transport.vic.gov.au/) (for real-time features)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/DevelopBG/PTV-Assistant-for-travel.git
   cd PTV_Assistant
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download GTFS data (REQUIRED)**

   The application requires real transit schedule data from PTV:

   - Visit: https://opendata.transport.vic.gov.au/dataset/gtfs-schedule
   - Download the latest GTFS Schedule ZIP file (~242MB)
   - Extract ALL files to `data/gtfs/` directory

   Expected files: `stops.txt`, `routes.txt`, `trips.txt`, `stop_times.txt`, `calendar.txt`, etc.

   See [data/gtfs/README.md](data/gtfs/README.md) for detailed instructions.

5. **(Optional) Set up PTV API key for real-time features**
   ```bash
   export PTV_API_KEY='your-api-key'  # On Windows: set PTV_API_KEY=your-api-key
   # Or create a .env file with: PTV_API_KEY=your-api-key
   ```

6. **(Windows Only) Fix console encoding for emoji display**

   Before running scripts, enable UTF-8:
   ```bash
   chcp 65001
   ```

   Or the encoding fix has been added automatically to find_journey.py

### Find a Journey

```bash
# Find next available journey
python find_journey.py "Tarneit" "Waurn Ponds"

# Find journey at specific time
python find_journey.py "Tarneit" "Waurn Ponds" "14:00:00"

# NEW: With real-time delays and cancellations (Phase 5)
export PTV_API_KEY='your-api-key'
python find_journey.py "Tarneit" "Waurn Ponds" "14:00:00" --realtime

# Run comprehensive demo
python examples/find_real_journey.py
```

**Example output:**
```
✅ JOURNEY FOUND!

Journey: Tarneit Station → Waurn Ponds Station
Departure: 14:17:00
Arrival: 15:08:00
Duration: 51m
Transfers: 1

Leg 1: Regional Train
  Tarneit Station → Geelong Station
  14:17:00 - 14:51:00 (34m)

Leg 2: Regional Train
  Geelong Station → Waurn Ponds Station
  14:54:00 - 15:08:00 (14m)
```

### Other Usage

```bash
# Show real-time trip updates
python read_gtfs_feed.py

# Show 10 trip updates
python read_gtfs_feed.py --max-display 10
```

## 💡 What Can It Do?

The journey planner currently supports:

✅ **Find Optimal Routes** - Uses Connection Scan Algorithm (CSA) to find fastest journeys
✅ **Multi-Modal Support** - Track transport modes (train, tram, bus, ferry)
✅ **Real GTFS Data** - Works with V/Line data (497 stops, 8,096 trips, 99,694 connections)
✅ **Fuzzy Station Search** - "Tarneit" finds "Tarneit Station"
✅ **Transfer Handling** - Calculates wait times and transfer locations
✅ **Time-Based Queries** - Find journeys departing after specific times
✅ **Journey Statistics** - Duration, transfers, modes used, stops count
✅ **Fast Performance** - Complete journey planning in <2 seconds
✅ **Real-Time Delays** - Apply live delays and cancellations (Phase 5)
✅ **Platform Information** - Show platform numbers when available
✅ **Transfer Validation** - Verify transfers still work after delays

**Coming in Phase 6:**
⏳ Web API endpoints
⏳ CLI enhancements
⏳ Journey preferences

## 📚 Documentation

### Getting Started
- **[QUICK_START.md](QUICK_START.md)** - Quick guide to finding journeys
- **[examples/README.md](examples/README.md)** - Working examples and demos
- **[examples/PHASE4_API_REFERENCE.md](examples/PHASE4_API_REFERENCE.md)** - Multi-modal routing API

### Technical Documentation
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and components
- **[FEASIBILITY.md](docs/FEASIBILITY.md)** - Feasibility analysis (9/10 score)
- **[ROADMAP.md](docs/ROADMAP.md)** - Week-by-week implementation plan
- **[DATA_SOURCES.md](docs/DATA_SOURCES.md)** - Complete GTFS data reference
- **[DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)** - Detailed progress tracking
- **[CONTEXT.md](CONTEXT.md)** - Development session resume point

## 🗺️ Development Roadmap

| Phase | Description | Status | Tests | Coverage |
|-------|-------------|--------|-------|----------|
| Phase 0 | Foundation - Realtime GTFS Feed | ✅ Complete | 21 | 100% |
| Phase 1 | Data Layer - GTFS Parser & Models | ✅ Complete | 62 | 97% |
| Phase 2 | Graph Construction - Transit Network | ✅ Complete | 36 | 95% |
| Phase 3 | Single-Mode Routing - CSA Algorithm | ✅ Complete | 41 | 98% |
| Phase 4 | Multi-Modal Routing - Mode Tracking | ✅ Complete | 58 | 97% |
| Phase 5 | Realtime Integration | ✅ Complete | 230 | 95% |
| Phase 6 | Web API & CLI | ⏳ Not Started | - | - |
| Phase 7 | Performance Optimization | ⏳ Not Started | - | - |

**Total**: 230 tests passing, 96% overall coverage

## 📝 License

MIT License - Data from PTV under CC BY 4.0

## 🔗 Resources

- [PTV Open Data Portal](https://opendata.transport.vic.gov.au/)
- [GTFS Specification](https://gtfs.org/)

---

**Last Updated**: 2026-01-14


----
