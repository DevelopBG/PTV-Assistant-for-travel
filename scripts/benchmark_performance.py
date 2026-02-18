#!/usr/bin/env python3
"""
Performance benchmarking script for PTV Transit Assistant.

This script profiles and benchmarks:
1. GTFS data loading
2. Stop index construction
3. Graph construction
4. Journey planning queries
5. Fuzzy search queries

Run with: python scripts/benchmark_performance.py
"""

import time
import sys
import os
import cProfile
import pstats
from io import StringIO
from functools import wraps
from typing import Callable, Any, Dict, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.gtfs_parser import GTFSParser
from src.data.stop_index import StopIndex
from src.graph.transit_graph import TransitGraph
from src.routing.journey_planner import JourneyPlanner


def timer(func: Callable) -> Callable:
    """Decorator to time function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"  {func.__name__}: {end - start:.4f}s")
        return result
    return wrapper


def profile_function(func: Callable, *args, **kwargs) -> tuple:
    """Profile a function and return result with timing."""
    profiler = cProfile.Profile()
    profiler.enable()

    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()

    profiler.disable()

    # Get profiler stats
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')
    stats.print_stats(10)

    return result, end - start, stream.getvalue()


class PerformanceBenchmark:
    """Performance benchmarking suite."""

    def __init__(self, gtfs_dir: str):
        self.gtfs_dir = gtfs_dir
        self.results: Dict[str, Dict] = {}

    def run_all(self, verbose: bool = True) -> Dict:
        """Run all benchmarks."""
        print("=" * 60)
        print("PTV Transit Assistant - Performance Benchmark")
        print("=" * 60)
        print(f"GTFS Directory: {self.gtfs_dir}")
        print()

        # 1. GTFS Parsing Benchmark
        parser = self._benchmark_gtfs_parsing(verbose)

        # 2. Stop Index Benchmark
        stop_index = self._benchmark_stop_index(parser, verbose)

        # 3. Graph Construction Benchmark
        graph = self._benchmark_graph_construction(parser, verbose)

        # 4. Journey Planning Benchmark
        planner = self._benchmark_journey_planning(parser, graph, verbose)

        # 5. Fuzzy Search Benchmark
        self._benchmark_fuzzy_search(stop_index, verbose)

        # Summary
        self._print_summary()

        return self.results

    def _benchmark_gtfs_parsing(self, verbose: bool) -> GTFSParser:
        """Benchmark GTFS data parsing."""
        print("\n[1/5] GTFS Data Parsing")
        print("-" * 40)

        parser = GTFSParser(self.gtfs_dir)

        # Time individual load operations
        timings = {}

        start = time.perf_counter()
        parser.load_agencies()
        timings['agencies'] = time.perf_counter() - start

        start = time.perf_counter()
        parser.load_stops()
        timings['stops'] = time.perf_counter() - start

        start = time.perf_counter()
        parser.load_routes()
        timings['routes'] = time.perf_counter() - start

        start = time.perf_counter()
        parser.load_trips()
        timings['trips'] = time.perf_counter() - start

        start = time.perf_counter()
        parser.load_stop_times()
        timings['stop_times'] = time.perf_counter() - start

        start = time.perf_counter()
        parser.load_calendar()
        timings['calendar'] = time.perf_counter() - start

        start = time.perf_counter()
        parser.load_calendar_dates()
        timings['calendar_dates'] = time.perf_counter() - start

        start = time.perf_counter()
        parser.load_transfers()
        timings['transfers'] = time.perf_counter() - start

        total_time = sum(timings.values())

        self.results['gtfs_parsing'] = {
            'total_time': total_time,
            'timings': timings,
            'counts': {
                'stops': len(parser.stops),
                'routes': len(parser.routes),
                'trips': len(parser.trips),
                'stop_times': sum(len(st) for st in parser.stop_times.values()),
            }
        }

        if verbose:
            for name, t in timings.items():
                print(f"  load_{name}: {t:.4f}s")
            print(f"  TOTAL: {total_time:.4f}s")
            print(f"\n  Data loaded:")
            print(f"    - {len(parser.stops)} stops")
            print(f"    - {len(parser.routes)} routes")
            print(f"    - {len(parser.trips)} trips")
            print(f"    - {self.results['gtfs_parsing']['counts']['stop_times']} stop_times")

        return parser

    def _benchmark_stop_index(self, parser: GTFSParser, verbose: bool) -> StopIndex:
        """Benchmark stop index construction."""
        print("\n[2/5] Stop Index Construction")
        print("-" * 40)

        start = time.perf_counter()
        stop_index = StopIndex(parser)
        construction_time = time.perf_counter() - start

        self.results['stop_index'] = {
            'construction_time': construction_time,
            'num_stops': len(stop_index.stops),
        }

        if verbose:
            print(f"  Construction time: {construction_time:.4f}s")
            print(f"  Indexed {len(stop_index.stops)} stops")

        return stop_index

    def _benchmark_graph_construction(self, parser: GTFSParser, verbose: bool) -> TransitGraph:
        """Benchmark graph construction."""
        print("\n[3/5] Transit Graph Construction")
        print("-" * 40)

        start = time.perf_counter()
        graph = TransitGraph(parser)
        construction_time = time.perf_counter() - start

        stats = graph.get_stats()

        self.results['graph_construction'] = {
            'construction_time': construction_time,
            'stats': stats,
        }

        if verbose:
            print(f"  Construction time: {construction_time:.4f}s")
            print(f"  Graph statistics:")
            print(f"    - {stats['num_stops']} nodes (stops)")
            print(f"    - {stats['num_connections']} edges")
            print(f"    - {stats['num_total_connections']} total connections")
            print(f"    - {stats['avg_degree']:.2f} avg degree")

        return graph

    def _benchmark_journey_planning(
        self,
        parser: GTFSParser,
        graph: TransitGraph,
        verbose: bool
    ) -> JourneyPlanner:
        """Benchmark journey planning queries."""
        print("\n[4/5] Journey Planning Queries")
        print("-" * 40)

        planner = JourneyPlanner(parser, graph)

        # Get actual stop IDs from parser
        stop_ids = list(parser.stops.keys())

        if len(stop_ids) < 2:
            print("  Not enough stops for journey planning test")
            self.results['journey_planning'] = {
                'query_times': [],
                'avg_query_time': 0,
                'min_query_time': 0,
                'max_query_time': 0,
            }
            return planner

        # Generate test queries using actual stops
        # Try production stops first, fall back to whatever is available
        production_queries = [
            ("47648", "47641", "08:00:00"),  # Tarneit to Waurn Ponds
            ("47648", "47641", "14:00:00"),  # Tarneit to Waurn Ponds (afternoon)
            ("47641", "47648", "06:00:00"),  # Reverse direction (morning)
        ]

        # Check if production stops exist
        if all(s in parser.stops for s, _, _ in production_queries[:1]):
            test_queries = production_queries
        else:
            # Use available stops
            test_queries = [
                (stop_ids[0], stop_ids[1], "08:00:00"),
                (stop_ids[0], stop_ids[1], "14:00:00"),
                (stop_ids[1], stop_ids[0], "06:00:00"),
            ]

        query_times = []

        for origin, dest, time_str in test_queries:
            start = time.perf_counter()
            journey = planner.find_journey(origin, dest, time_str)
            query_time = time.perf_counter() - start
            query_times.append(query_time)

            if verbose:
                if journey:
                    print(f"  Query {origin}->{dest} @ {time_str}: {query_time:.4f}s "
                          f"(found: {journey.departure_time}->{journey.arrival_time})")
                else:
                    print(f"  Query {origin}->{dest} @ {time_str}: {query_time:.4f}s (no route)")

        avg_query_time = sum(query_times) / len(query_times) if query_times else 0

        self.results['journey_planning'] = {
            'query_times': query_times,
            'avg_query_time': avg_query_time,
            'min_query_time': min(query_times) if query_times else 0,
            'max_query_time': max(query_times) if query_times else 0,
        }

        if verbose:
            print(f"\n  Query Performance:")
            print(f"    - Avg: {avg_query_time:.4f}s")
            print(f"    - Min: {min(query_times):.4f}s")
            print(f"    - Max: {max(query_times):.4f}s")

        return planner

    def _benchmark_fuzzy_search(self, stop_index: StopIndex, verbose: bool):
        """Benchmark fuzzy search queries."""
        print("\n[5/5] Fuzzy Search Queries")
        print("-" * 40)

        test_queries = [
            "Tarneit",
            "Waurn Ponds",
            "Melbourne",
            "Geelong",
            "Tarn",  # Partial match
            "Worn Ponds",  # Typo
        ]

        query_times = []

        for query in test_queries:
            start = time.perf_counter()
            results = stop_index.find_stop_fuzzy(query, limit=5)
            query_time = time.perf_counter() - start
            query_times.append(query_time)

            if verbose:
                top_match = results[0][0].stop_name if results else "No match"
                score = results[0][1] if results else 0
                print(f"  '{query}': {query_time:.6f}s -> {top_match} ({score}%)")

        avg_query_time = sum(query_times) / len(query_times) if query_times else 0

        self.results['fuzzy_search'] = {
            'query_times': query_times,
            'avg_query_time': avg_query_time,
            'queries_per_second': 1 / avg_query_time if avg_query_time > 0 else 0,
        }

        if verbose:
            print(f"\n  Fuzzy Search Performance:")
            print(f"    - Avg: {avg_query_time:.6f}s ({1/avg_query_time:.0f} queries/sec)")

    def _print_summary(self):
        """Print benchmark summary."""
        print("\n" + "=" * 60)
        print("PERFORMANCE SUMMARY")
        print("=" * 60)

        # Calculate totals
        total_load_time = (
            self.results['gtfs_parsing']['total_time'] +
            self.results['stop_index']['construction_time'] +
            self.results['graph_construction']['construction_time']
        )

        print(f"\nStartup Performance (one-time):")
        print(f"  GTFS Parsing:       {self.results['gtfs_parsing']['total_time']:.4f}s")
        print(f"  Stop Index:         {self.results['stop_index']['construction_time']:.4f}s")
        print(f"  Graph Construction: {self.results['graph_construction']['construction_time']:.4f}s")
        print(f"  TOTAL STARTUP:      {total_load_time:.4f}s")

        print(f"\nQuery Performance:")
        print(f"  Journey Planning:   {self.results['journey_planning']['avg_query_time']:.4f}s avg")
        print(f"  Fuzzy Search:       {self.results['fuzzy_search']['avg_query_time']:.6f}s avg")

        # Success criteria check
        print(f"\n--- Success Criteria Check ---")

        gtfs_ok = self.results['gtfs_parsing']['total_time'] < 1.0
        print(f"  GTFS parsing < 1s:     {'✓ PASS' if gtfs_ok else '✗ FAIL'} ({self.results['gtfs_parsing']['total_time']:.4f}s)")

        startup_ok = total_load_time < 3.0
        print(f"  Total startup < 3s:    {'✓ PASS' if startup_ok else '✗ FAIL'} ({total_load_time:.4f}s)")

        query_ok = self.results['journey_planning']['avg_query_time'] < 0.5
        print(f"  Journey query < 0.5s:  {'✓ PASS' if query_ok else '✗ FAIL'} ({self.results['journey_planning']['avg_query_time']:.4f}s)")

        search_ok = self.results['fuzzy_search']['avg_query_time'] < 0.01
        print(f"  Fuzzy search < 10ms:   {'✓ PASS' if search_ok else '✗ FAIL'} ({self.results['fuzzy_search']['avg_query_time']*1000:.2f}ms)")


def main():
    """Run performance benchmarks."""
    # Default to production GTFS directory
    gtfs_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "gtfs"
    )

    # Fall back to test fixtures if production data not available
    if not os.path.exists(gtfs_dir):
        gtfs_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tests", "test_data", "fixtures"
        )
        print(f"Note: Using test fixtures (production data not found)")
        print()

    if not os.path.exists(gtfs_dir):
        print(f"Error: GTFS directory not found: {gtfs_dir}")
        sys.exit(1)

    benchmark = PerformanceBenchmark(gtfs_dir)
    results = benchmark.run_all(verbose=True)

    return results


if __name__ == "__main__":
    main()
