"""
Simple demonstration of Phase 4 Multi-Modal Routing features.

This shows the key capabilities added in Phase 4 using test data.
"""

from src.routing.models import Leg, Journey


def main():
    print("=" * 70)
    print("Phase 4: Multi-Modal Routing Features - Simple Demo")
    print("=" * 70)
    print()

    # =========================================================================
    # Example 1: Creating a journey leg with mode information (NEW IN PHASE 4)
    # =========================================================================
    print("Example 1: Single-Mode Journey")
    print("-" * 70)
    print()

    # Create a Regional Train leg
    train_leg = Leg(
        from_stop_id="47648",
        from_stop_name="Tarneit Station",
        to_stop_id="47641",
        to_stop_name="Waurn Ponds Station",
        departure_time="14:57:00",
        arrival_time="15:48:00",
        trip_id="T123",
        route_id="R1",
        route_name="Geelong - Melbourne Via Geelong",
        route_type=2,  # **NEW IN PHASE 4**: Route type (2 = Regional Train)
        num_stops=5
    )

    # **NEW IN PHASE 4**: Get human-readable mode name
    mode_name = train_leg.get_mode_name()
    print(f"Leg: {train_leg.from_stop_name} → {train_leg.to_stop_name}")
    print(f"Transport Mode: {mode_name}")  # Output: "Regional Train"
    print(f"Route Type Code: {train_leg.route_type}")  # Output: 2
    print(f"Duration: {train_leg.format_duration()}")
    print()

    # Create journey with this leg
    journey1 = Journey(
        origin_stop_id="47648",
        origin_stop_name="Tarneit Station",
        destination_stop_id="47641",
        destination_stop_name="Waurn Ponds Station",
        departure_time="14:57:00",
        arrival_time="15:48:00",
        legs=[train_leg]
    )

    # **NEW IN PHASE 4**: Analyze journey modes
    modes_used = journey1.get_modes_used()
    is_multimodal = journey1.is_multi_modal()

    print("Journey Analysis (Phase 4 Features):")
    print(f"  Modes used: {modes_used}")  # Output: ['Regional Train']
    print(f"  Multi-modal? {is_multimodal}")  # Output: False
    print()
    print()

    # =========================================================================
    # Example 2: Multi-Modal Journey (Train + Tram)
    # =========================================================================
    print("Example 2: Multi-Modal Journey (Train + Tram)")
    print("-" * 70)
    print()

    # Leg 1: Regional Train
    leg1_train = Leg(
        from_stop_id="1001",
        from_stop_name="Tarneit Station",
        to_stop_id="1002",
        to_stop_name="Flinders Street Station",
        departure_time="08:00:00",
        arrival_time="08:35:00",
        trip_id="TRAIN_T1",
        route_id="R1",
        route_name="Geelong - Melbourne",
        route_type=2,  # Regional Train
        num_stops=12
    )

    # Leg 2: Tram
    leg2_tram = Leg(
        from_stop_id="1002",
        from_stop_name="Flinders Street Station",
        to_stop_id="1003",
        to_stop_name="St Kilda Beach",
        departure_time="08:45:00",
        arrival_time="09:05:00",
        trip_id="TRAM_96",
        route_id="R96",
        route_name="Route 96",
        route_type=0,  # Tram
        num_stops=15
    )

    # Create multi-modal journey
    journey2 = Journey(
        origin_stop_id="1001",
        origin_stop_name="Tarneit Station",
        destination_stop_id="1003",
        destination_stop_name="St Kilda Beach",
        departure_time="08:00:00",
        arrival_time="09:05:00",
        legs=[leg1_train, leg2_tram]
    )

    print("Journey: Tarneit Station → St Kilda Beach")
    print()

    # Show each leg with mode
    for i, leg in enumerate(journey2.legs, 1):
        print(f"Leg {i}: {leg.from_stop_name} → {leg.to_stop_name}")
        print(f"  🚆 Mode: {leg.get_mode_name()}")
        print(f"  ⏰ {leg.departure_time} → {leg.arrival_time} ({leg.format_duration()})")
        print(f"  📋 Route: {leg.route_name}")
        print()

    # **NEW IN PHASE 4**: Multi-modal analysis
    print("Journey Analysis (Phase 4 Features):")
    modes_used = journey2.get_modes_used()
    is_multimodal = journey2.is_multi_modal()

    print(f"  Modes used: {', '.join(modes_used)}")  # Output: "Regional Train, Tram"
    print(f"  Multi-modal? {is_multimodal}")  # Output: True
    print(f"  Transfers: {journey2.num_transfers}")
    print()
    print()

    # =========================================================================
    # Example 3: Journey with Walking Transfer
    # =========================================================================
    print("Example 3: Journey with Walking Transfer")
    print("-" * 70)
    print()

    # Leg 1: Metro train
    leg3_metro = Leg(
        from_stop_id="2001",
        from_stop_name="Melbourne Central",
        to_stop_id="2002",
        to_stop_name="Parliament",
        departure_time="10:00:00",
        arrival_time="10:03:00",
        trip_id="METRO_T1",
        route_id="M1",
        route_name="City Loop",
        route_type=1,  # Metro
        num_stops=2
    )

    # Leg 2: Walking transfer
    leg3_walk = Leg(
        from_stop_id="2002",
        from_stop_name="Parliament Station",
        to_stop_id="2003",
        to_stop_name="Parliament Tram Stop",
        departure_time="10:03:00",
        arrival_time="10:08:00",
        trip_id="WALK",
        route_id="",
        is_transfer=True  # **NEW IN PHASE 4**: Mark as walking transfer
    )

    # Leg 3: Tram
    leg3_tram = Leg(
        from_stop_id="2003",
        from_stop_name="Parliament Tram Stop",
        to_stop_id="2004",
        to_stop_name="Victoria Market",
        departure_time="10:10:00",
        arrival_time="10:15:00",
        trip_id="TRAM_58",
        route_id="R58",
        route_name="Route 58",
        route_type=0,  # Tram
        num_stops=3
    )

    journey3 = Journey(
        origin_stop_id="2001",
        origin_stop_name="Melbourne Central",
        destination_stop_id="2004",
        destination_stop_name="Victoria Market",
        departure_time="10:00:00",
        arrival_time="10:15:00",
        legs=[leg3_metro, leg3_walk, leg3_tram]
    )

    print("Journey: Melbourne Central → Victoria Market")
    print()

    for i, leg in enumerate(journey3.legs, 1):
        print(f"Leg {i}: {leg.from_stop_name} → {leg.to_stop_name}")
        print(f"  🚶 Mode: {leg.get_mode_name()}")
        if leg.is_transfer:
            print(f"  ⚠️  Walking transfer (5 min)")
        print()

    # **NEW IN PHASE 4**: Walking is excluded from modes list
    print("Journey Analysis (Phase 4 Features):")
    modes_used = journey3.get_modes_used()
    print(f"  Modes used: {', '.join(modes_used)}")  # Output: "Metro, Tram" (no Walking!)
    print(f"  Multi-modal? {journey3.is_multi_modal()}")  # Output: True
    print(f"  Note: Walking transfers are excluded from mode count")
    print()
    print()

    # =========================================================================
    # Example 4: All Supported Transport Modes
    # =========================================================================
    print("Example 4: All Supported Transport Modes (Phase 4)")
    print("-" * 70)
    print()

    mode_examples = [
        (0, "Tram", "Route 86 to Bundoora"),
        (1, "Metro", "Frankston Line"),
        (2, "Regional Train", "V/Line Geelong"),
        (3, "Bus", "SmartBus Route 901"),
        (4, "Ferry", "Ferry to Williamstown"),
        (700, "Bus", "PTV Bus (code 700)"),
        (900, "Tram", "PTV Tram (code 900)"),
    ]

    for route_type, mode_name, example in mode_examples:
        leg = Leg(
            from_stop_id="0",
            from_stop_name="Stop A",
            to_stop_id="1",
            to_stop_name="Stop B",
            departure_time="12:00:00",
            arrival_time="12:10:00",
            trip_id="T",
            route_id="R",
            route_type=route_type
        )
        detected_mode = leg.get_mode_name()
        print(f"  Route Type {route_type:3d} → {detected_mode:15s} (e.g., {example})")

    print()
    print()

    # =========================================================================
    # Summary: What Phase 4 Enables
    # =========================================================================
    print("=" * 70)
    print("Phase 4 Summary: What's New")
    print("=" * 70)
    print()

    print("✅ BEFORE Phase 4:")
    print("  - Could find optimal routes between stops")
    print("  - Could show departure/arrival times")
    print("  - ❌ Couldn't tell WHAT transport to catch")
    print()

    print("✅ AFTER Phase 4:")
    print("  - ✓ Track transport mode for each leg (train, tram, bus, ferry)")
    print("  - ✓ Get human-readable mode names")
    print("  - ✓ Identify multi-modal journeys")
    print("  - ✓ List all modes used in a journey")
    print("  - ✓ Distinguish walking transfers")
    print("  - ✓ Ready for mode-specific real-time updates (Phase 5)")
    print()

    print("Key Methods Added:")
    print("  - leg.get_mode_name()         → 'Regional Train', 'Tram', etc.")
    print("  - journey.get_modes_used()    → ['Metro', 'Tram']")
    print("  - journey.is_multi_modal()    → True/False")
    print()

    print("This enables:")
    print("  → Phase 5: Apply mode-specific real-time delays")
    print("  → Phase 6: Let users filter by preferred transport modes")
    print("  → Future: Calculate mode-specific fares")
    print()


if __name__ == "__main__":
    main()
