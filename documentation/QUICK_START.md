# Quick Start Guide - PTV Transit Assistant

## 🚀 Find a Journey Right Now

The easiest way to use the PTV Transit Assistant:

```bash
python find_journey.py "Tarneit" "Waurn Ponds"
```

This will find the next available journey from Tarneit to Waurn Ponds.

## 📝 Usage

### Basic Usage (Next Available Journey)
```bash
python find_journey.py "Origin Station" "Destination Station"
```

### Specify Departure Time
```bash
python find_journey.py "Origin Station" "Destination Station" "14:00:00"
```

## 🎯 Examples

### Example 1: Right Now
```bash
python find_journey.py "Tarneit" "Waurn Ponds"
```

**Output:**
```
✅ JOURNEY FOUND!

Journey: Tarneit Station → Waurn Ponds Station
Departure: 22:22:00
Arrival: 23:14:00
Duration: 52m
Transfers: 0

Leg 1:
  Tarneit Station → Waurn Ponds Station
  Mode: Regional Train
  Depart: 22:22:00  Arrive: 23:14:00
  Duration: 52m
  Route: Geelong - Melbourne Via Geelong

✓ Direct journey - no transfers needed!
```

### Example 2: At 2 PM
```bash
python find_journey.py "Tarneit" "Waurn Ponds" "14:00:00"
```

**Output:**
```
✅ JOURNEY FOUND!

Journey: Tarneit Station → Waurn Ponds Station
Departure: 14:17:00
Arrival: 15:08:00
Duration: 51m
Transfers: 1

Leg 1:
  Tarneit Station → Geelong Station
  Mode: Regional Train
  Depart: 14:17:00  Arrive: 14:51:00

Leg 2:
  Geelong Station → Waurn Ponds Station
  Mode: Regional Train
  Depart: 14:54:00  Arrive: 15:08:00

⚠️  This journey has 1 transfer(s).
```

### Example 3: Morning Commute
```bash
python find_journey.py "Tarneit" "Waurn Ponds" "08:00:00"
```

### Example 4: Different Route
```bash
python find_journey.py "Tarneit" "Geelong"
```

## 🗺️ Available Stations

The current dataset includes **497 V/Line regional train stations**, including:

**Major Stations:**
- Tarneit Station
- Waurn Ponds Station
- Geelong Station
- Southern Cross Station
- North Melbourne Station
- Footscray Station
- Werribee Station
- Wyndham Vale Station

**To see all stations**, check `data/gtfs/stops.txt`

## 📊 What You Get

Each journey shows:

1. **Basic Information:**
   - Departure time
   - Arrival time
   - Total duration
   - Number of transfers

2. **Detailed Legs:**
   - Each leg of the journey
   - Transport mode (🚆 Regional Train)
   - Departure/arrival times
   - Duration
   - Route name
   - Number of stops

3. **Multi-Modal Analysis (Phase 4):**
   - What transport modes you'll use
   - Whether it's a multi-modal journey
   - Transfer warnings

## 🔧 Advanced Usage

### Run the Full Demo
See journey planning at multiple departure times:
```bash
python examples/find_real_journey.py
```

### Test the API
Try the multi-modal routing features:
```bash
PYTHONPATH=. python examples/simple_multimodal_demo.py
```

### Run Tests
Verify everything works:
```bash
pytest
```

## 💡 Tips

1. **Station Names**: Use partial names - fuzzy matching will find the station
   - "Tarneit" finds "Tarneit Station"
   - "Waurn" finds "Waurn Ponds Station"
   - "Geelong" finds "Geelong Station"

2. **Time Format**: Use HH:MM:SS format
   - "08:00:00" for 8 AM
   - "14:00:00" for 2 PM
   - "20:30:00" for 8:30 PM

3. **No Journey Found?**
   - Try a different time
   - Check if the route exists in the V/Line network
   - Some routes may not run at all times

## 🎓 How It Works

Behind the scenes, the system:

1. **Loads GTFS data** (497 stops, 8,096 trips, 107,790 stop times)
2. **Builds a transit network graph** (99,694 connections)
3. **Uses fuzzy matching** to find your stations
4. **Runs the Connection Scan Algorithm** to find the optimal journey
5. **Analyzes transport modes** (Phase 4 feature)
6. **Formats and displays** your journey

All of this happens in **less than 2 seconds**!

## 📖 More Information

- **[README.md](README.md)** - Project overview and roadmap
- **[DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)** - Technical details
- **[examples/PHASE4_API_REFERENCE.md](examples/PHASE4_API_REFERENCE.md)** - API documentation
- **[examples/README.md](examples/README.md)** - More examples

## 🐛 Troubleshooting

### "No journey found"
- The route might not exist in the V/Line network
- Try a different departure time
- Check that both stations exist in the data

### "Could not find station"
- Check spelling
- Use partial names (fuzzy matching is forgiving)
- See available stations in `data/gtfs/stops.txt`

### Module import errors
Make sure you're in the project root directory:
```bash
cd /Users/mohammed/Downloads/PTV_Assistant-main
python find_journey.py "Tarneit" "Waurn Ponds"
```

## 🚀 What's Next?

Current capabilities (Phases 0-4):
- ✅ Find optimal journeys
- ✅ Show transport modes
- ✅ Calculate durations and transfers

Coming soon (Phase 5+):
- ⏳ Real-time delays and cancellations
- ⏳ Web API interface
- ⏳ Command-line interface
- ⏳ Performance optimizations

## 🎉 Try It Now!

```bash
# Find your journey
python find_journey.py "Tarneit" "Waurn Ponds"

# Or specify a time
python find_journey.py "Tarneit" "Waurn Ponds" "14:00:00"
```

Happy traveling! 🚆
