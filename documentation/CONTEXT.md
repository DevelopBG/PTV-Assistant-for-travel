# Project Context - Resume Point

**Date**: 2026-01-14
**Repository**: https://github.com/caprihan/PTV_Assistant
**Branch**: main
**Last Commit**: `b04e70c` - "Update find_journey.py with Phase 5 realtime integration"

---

## Current State Summary

You are building a **PTV Transit Assistant** - a journey planner for Melbourne's public transport network. The project follows a phased approach with comprehensive test coverage.

### What's Complete ✅

1. **Phase 0: Foundation** (100% complete, 21 tests, 100% coverage)
   - Real-time GTFS feed fetcher
   - Protobuf parsing
   - PTV API integration

2. **Phase 1: Data Layer** (100% complete, 62 tests, 97% coverage)
   - GTFS static data parser
   - Type-safe data models
   - Stop index with fuzzy search
   - Successfully answered: "Tarneit to Waurn Ponds - what trips are available?" (1,989 trips found)

3. **Phase 2: Graph Construction** (100% complete, 36 tests, 95% coverage)
   - Transit network graph using NetworkX
   - Nodes for stops with metadata
   - Edges for connections with travel times
   - Transfer edge support
   - Query methods for graph exploration

4. **Phase 3: Single-Mode Routing** (100% complete, 41 tests, 98% coverage)
   - Connection Scan Algorithm (CSA) implementation
   - Journey planning with optimal routes
   - Journey and Leg dataclasses
   - Time-based constraints and formatting
   - Successfully answered: "How do I get from Tarneit to Waurn Ponds at 2 PM?"

5. **Phase 4: Multi-Modal Routing** (100% complete, 58 tests, 97% coverage)
   - Route type tracking for all transport modes
   - Mode identification in Connection and Leg dataclasses
   - Multi-modal journey support with mode changes
   - Walking transfer detection
   - Journey mode analysis methods
   - Mode-aware journey summaries

6. **Phase 5: Realtime Integration** (100% complete, 53 tests, 96% coverage)
   - Enhanced data models with realtime fields
   - Time conversion utilities (Unix ↔ HH:MM:SS)
   - RealtimeIntegrator for applying delays to journeys
   - Transfer validation after delays
   - Cancellation detection and journey invalidation
   - CLI integration with --realtime flag
   - Successfully answered: "How do I get from Tarneit to Waurn Ponds at 2 PM with live delays?"

### What's Next ⏳

**Phase 6: Web API & CLI** - RESTful API and command-line interface
- FastAPI for REST endpoints
- JSON response formatting
- API documentation
- Command-line interface for queries

---

## Key Project Information

### Repository Structure
```
PTV_Assistant-main/
├── src/
│   ├── data/           ✅ Complete - GTFS parser, models, stop index
│   ├── realtime/       ✅ Complete - Feed fetcher, integration, time utils
│   ├── graph/          ✅ Complete - Transit graph with NetworkX
│   ├── routing/        ✅ Complete - Journey planner with CSA
│   ├── api/            ⏳ Empty - Future phase
│   └── cli/            ⏳ Empty - Future phase
├── tests/
│   ├── test_data/      ✅ 62 tests
│   ├── test_realtime/  ✅ 74 tests (21 fetcher + 33 time_utils + 20 integration)
│   ├── test_graph/     ✅ 36 tests
│   └── test_routing/   ✅ 58 tests (41 + 17 multimodal)
├── data/
│   └── gtfs/           ✅ V/Line data extracted (497 stops, 13 routes, 8,096 trips)
└── docs/               ✅ Documentation files
```

### Important Files

**Source Code:**
- `src/data/models.py` - GTFS dataclasses (Stop, Route, Trip, StopTime, etc.)
- `src/data/gtfs_parser.py` - CSV parser for GTFS files
- `src/data/stop_index.py` - Fast stop lookup with fuzzy matching
- `src/realtime/feed_fetcher.py` - Real-time feed fetcher
- `src/realtime/time_utils.py` - Time conversion utilities
- `src/realtime/integration.py` - Realtime integration module
- `src/graph/transit_graph.py` - Transit network graph with NetworkX
- `src/routing/journey_planner.py` - Journey planner using CSA
- `src/routing/models.py` - Journey and Leg dataclasses with realtime fields

**Tests:**
- `tests/test_data/` - 62 tests for Phase 1
- `tests/test_realtime/` - 74 tests for Phase 0 and Phase 5
- `tests/test_graph/` - 36 tests for Phase 2
- `tests/test_routing/` - 58 tests for Phase 3 and Phase 4
- `tests/test_data/fixtures/` - Sample GTFS CSV files

**Documentation:**
- `README.md` - Project overview and roadmap
- `DEVELOPMENT_STATUS.md` - Detailed progress report
- `CLAUDE.md` - Instructions for Claude Code
- `docs/` - Architecture, feasibility, data sources

**Data:**
- `data/gtfs/` - Extracted V/Line GTFS data

---

## Test Coverage Status

| Component | Tests | Coverage | Status |
|-----------|-------|----------|--------|
| Phase 0: Realtime | 21 | 100% | ✅ Complete |
| Phase 1: Data Layer | 62 | 97% | ✅ Complete |
| Phase 2: Graph | 36 | 95% | ✅ Complete |
| Phase 3: Routing | 41 | 98% | ✅ Complete |
| Phase 4: Multi-Modal | 58 | 97% | ✅ Complete |
| Phase 5: Realtime Integration | 53 | 96% | ✅ Complete |
| **Total** | **230** | **96%** | **6/8 phases done** |

Run tests:
```bash
pytest                                      # All tests (230)
pytest tests/test_data/                     # Phase 1 only (62 tests)
pytest tests/test_graph/                    # Phase 2 only (36 tests)
pytest tests/test_realtime/                 # Phase 0 and 5 (74 tests)
pytest --cov=src --cov-report=term-missing  # With coverage
```

---

## Key Technical Decisions

### GTFS Data Extraction
- **What**: Extracted only V/Line regional train data (route_type=1)
- **Why**: Full extraction with all modes (metro, tram, bus) had performance issues on 17M rows
- **Result**: 497 stops, 13 routes, 8,096 trips - sufficient for development
- **Future**: May need to extract all modes for full Melbourne network

### Test Fixtures
- **Location**: `tests/test_data/fixtures/`
- **Files**: 8 CSV files (stops.txt, routes.txt, trips.txt, etc.)
- **Encoding**: UTF-8 with BOM (matches real GTFS files)
- **Size**: 2-4 sample records per file for fast testing

### Fuzzy Matching
- **Library**: fuzzywuzzy with python-Levenshtein
- **Scorer**: `token_sort_ratio` (handles word order)
- **Default threshold**: 60% similarity
- **Example**: "Waurn Pond" → "Waurn Ponds Station" (95% match)

---

## Important Data

### Sample Stations (for testing queries)
- **Tarneit Station**: stop_id `47648`, lat `-37.832`, lon `144.694`
- **Waurn Ponds Station**: stop_id `47641`, lat `-38.216`, lon `144.306`
- **Example route**: Geelong - Melbourne Via Geelong line
- **Example trip**: Departs Tarneit 14:57, arrives Waurn Ponds 15:48 (51 min)

### GTFS Data Stats
- 497 stops
- 13 routes
- 8,096 trips
- 1,989 trips serve both Tarneit and Waurn Ponds

---

## Git Status

### Recent Commits
```
b04e70c Update find_journey.py with Phase 5 realtime integration
1186a9b Phase 5: Realtime Integration Core (Steps 1-7) ✅
373870c Add journey finder examples and Phase 5 planning
3ecf2ed Update README.md with journey finder examples
6dc1ec8 Update CONTEXT.md and DEVELOPMENT_STATUS.md for Phase 4
d51f06b Phase 4: Multi-Modal Routing Support ✅
```

### Remote Repository
- **URL**: https://github.com/caprihan/PTV_Assistant.git
- **Status**: All commits pushed
- **Branch**: main (tracking origin/main)

### Working Directory
- **Status**: Clean (no uncommitted changes)
- **Untracked files**: `scripts/extract_all_gtfs.py` (extraction script, not committed)

---

## Environment Setup

### Python Environment
```bash
# Virtual environment location
source venv/bin/activate  # or: source .venv/bin/activate

# Check Python version
python --version  # Should be 3.9+
```

### Dependencies
```bash
# Production
requests>=2.31.0
protobuf>=4.23.0
gtfs-realtime-bindings>=1.0.0
pandas>=2.1.0
fuzzywuzzy>=0.18.0
python-Levenshtein>=0.20.0

# Development
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.1
requests-mock>=1.11.0

# Install
pip install -r requirements.txt
```

### PTV API Key
- **Required**: For real-time feed fetcher
- **Get from**: https://opendata.transport.vic.gov.au/
- **Set via**: `export PTV_API_KEY='your-key-here'` or `.env` file

---

## How to Resume Work

### Quick Context Refresh
1. **Read this file** (CONTEXT.md) - You're doing it now! ✅
2. **Check git status**: `git status` and `git log --oneline -5`
3. **Run tests**: `pytest` to verify everything works
4. **Review**: `DEVELOPMENT_STATUS.md` for detailed progress

### Next Steps - Phase 6: Web API & CLI

**Goal**: Build RESTful API and command-line interface

**Tasks**:
1. Set up FastAPI application structure
2. Create API endpoints for journey queries
3. Implement JSON response formatting
4. Add input validation and error handling
5. Create command-line interface for queries
6. Add API documentation with Swagger/OpenAPI
7. Write comprehensive tests for API endpoints
8. Target: 95%+ test coverage
9. Commit and push to GitHub

**Success Criteria**:
- RESTful API responds to journey queries
- JSON format for responses
- CLI accepts user queries
- API documentation available
- All tests passing

### Common Commands

```bash
# Testing
pytest                                      # Run all tests
pytest tests/test_data/ -v                  # Run Phase 1 tests verbosely
pytest --cov=src --cov-report=term-missing  # Coverage report

# Git
git status                                  # Check status
git log --oneline -5                        # Recent commits
git add <files>                             # Stage changes
git commit -m "message"                     # Commit
git push                                    # Push to GitHub

# GTFS Data
ls data/gtfs/                              # View extracted files
head -5 data/gtfs/stops.txt                # Preview stops data

# Python
python read_gtfs_feed.py                   # Run real-time feed viewer
```

---

## Known Issues & Technical Debt

1. **Limited to V/Line data**: Need to extract metro, tram, bus for full network
2. **No service calendar filtering**: All trips loaded regardless of which days they run
3. **No direction filtering**: Trips in both directions included in results
4. **Missing optional files**: Calendar and transfers files may not exist in all feeds

These are intentional simplifications for Phase 1. Will be addressed in future phases.

---

## Key Questions You Asked

1. **"Explain what you mean by a trip?"**
   - A trip = one vehicle's complete journey on a route at a specific time
   - Example: The 8:00 AM train from Geelong to Melbourne is one trip
   - The same route may have 100+ trips per day at different times

2. **"Is Phase 1 done?"**
   - Yes! ✅ 62 tests, 97% coverage, committed to Git

3. **"Is Phase 2 done?"**
   - No, not started yet. Phase 2 is next.

4. **"Did my progress commit on GitHub repository?"**
   - Yes! ✅ All pushed to https://github.com/caprihan/PTV_Assistant

---

## Important Concepts

### GTFS (General Transit Feed Specification)
- **Static GTFS**: CSV files with schedules (stops.txt, routes.txt, trips.txt, etc.)
- **Realtime GTFS**: Protobuf API with live delays and positions
- **Our data**: 242 MB ZIP from PTV Open Data Portal

### Data Models
- **Stop**: A station/stop with location (lat/lon)
- **Route**: A transit line (e.g., "Geelong - Melbourne")
- **Trip**: One vehicle journey on a route with specific times
- **StopTime**: Arrival/departure time at a specific stop for a trip

### Testing Philosophy
- **Target**: 95%+ coverage on all new code
- **Approach**: Test-driven development, write tests first
- **Fixtures**: Use minimal sample data for fast tests
- **Real data**: Separate fixtures for integration testing

---

## Project Vision

### End Goal
A journey planner that answers queries like:
- "How do I get from Tarneit to Waurn Ponds leaving at 2 PM?"
- "What's the fastest route from Flinders Street to Geelong?"
- "Show me all trains from Southern Cross in the next hour"

### Current Capability
- ✅ Can parse GTFS data
- ✅ Can find stations by name
- ✅ Can list all trips between two stations
- ✅ Can find optimal routes (Phase 3 complete!)
- ✅ Can track transport modes in journeys (Phase 4 complete!)
- ✅ Can apply real-time delays and cancellations (Phase 5 complete!)
- ❌ No web API or CLI yet (Phase 6)

---

## Contact & Resources

- **Repository**: https://github.com/caprihan/PTV_Assistant
- **PTV Data**: https://opendata.transport.vic.gov.au/
- **GTFS Spec**: https://gtfs.org/
- **GTFS Realtime**: https://developers.google.com/transit/gtfs-realtime

---

## Quick Checklist for Next Session

- [ ] Read this CONTEXT.md file
- [ ] Check git status and recent commits
- [ ] Run `pytest` to verify tests pass (should be 230 tests passing)
- [ ] Review DEVELOPMENT_STATUS.md
- [ ] Decide: Continue with Phase 6 or work on something else?
- [ ] If Phase 6: Build RESTful API and CLI
- [ ] Commit and push all work before ending session

---

**This file captures everything you need to resume work. Read it at the start of your next session!**

**Last Updated**: 2026-01-14
**Next Phase**: Phase 6 - Web API & CLI
**Status**: Phase 5 complete! Ready for Phase 6! 🚀
