#!/usr/bin/env python3
"""
GTFS Update CLI Tool

Command-line interface for managing GTFS data updates.

Usage:
    python scripts/gtfs_update.py --update-all
    python scripts/gtfs_update.py --modes 1,2,3
    python scripts/gtfs_update.py --status
    python scripts/gtfs_update.py --history
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.gtfs_downloader import GTFSDownloader
from src.data.gtfs_scheduler import initialize_gtfs_scheduler
from src.data.service_manager import get_service_manager


def update_command(args):
    """Execute GTFS update."""
    print("GTFS Data Update Tool")
    print("="*60)

    # Initialize scheduler (which includes downloader)
    scheduler = initialize_gtfs_scheduler()

    if args.modes:
        modes = [m.strip() for m in args.modes.split(',')]
        print(f"Updating modes: {', '.join(modes)}\n")
    else:
        modes = None
        print(f"Updating all configured modes\n")

    # Run update
    result = scheduler.run_update_now(modes=modes)

    # Print results
    print("\nUpdate Results:")
    print("-" * 60)

    for mode, mode_result in result.items():
        status = "✓" if mode_result['success'] else "✗"
        mode_name = mode_result.get('mode_name', f"Mode {mode}")
        print(f"{status} {mode_name}")

        if not mode_result['success']:
            print(f"  Error: {mode_result.get('error', 'Unknown error')}")
        else:
            if 'download_time' in mode_result:
                print(f"  Download time: {mode_result['download_time']:.2f}s")
            if 'extract_time' in mode_result:
                print(f"  Extract time: {mode_result['extract_time']:.2f}s")

    print("-" * 60)

    # Exit with appropriate code
    success_count = sum(1 for r in result.values() if r['success'])
    if success_count == len(result):
        print("\n✅ All updates completed successfully!")
        sys.exit(0)
    elif success_count > 0:
        print(f"\n⚠️  Partial success: {success_count}/{len(result)} modes updated")
        sys.exit(1)
    else:
        print("\n✗ All updates failed")
        sys.exit(1)


def status_command(args):
    """Show update status."""
    scheduler = initialize_gtfs_scheduler()

    print("GTFS Update Status")
    print("="*60)

    # Last update time
    last_update = scheduler.get_last_update_time()
    if last_update:
        time_ago = datetime.now() - last_update
        days_ago = time_ago.days
        hours_ago = time_ago.seconds // 3600

        print(f"Last update: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        if days_ago > 0:
            print(f"             ({days_ago} days ago)")
        elif hours_ago > 0:
            print(f"             ({hours_ago} hours ago)")
        else:
            print(f"             ({time_ago.seconds // 60} minutes ago)")
    else:
        print("Last update: Never")

    # Next scheduled update
    next_update = scheduler.get_next_update_time()
    if next_update:
        time_until = next_update - datetime.now()
        days_until = time_until.days
        hours_until = time_until.seconds // 3600

        print(f"\nNext update: {next_update.strftime('%Y-%m-%d %H:%M:%S')}")
        if days_until > 0:
            print(f"             (in {days_until} days)")
        elif hours_until > 0:
            print(f"             (in {hours_until} hours)")
        else:
            print(f"             (in {time_until.seconds // 60} minutes)")
    else:
        print("\nNext update: Not scheduled (auto-update disabled)")

    # Configuration
    print(f"\nConfiguration:")
    print(f"  Auto-update: {'Enabled' if scheduler.auto_update_enabled else 'Disabled'}")
    print(f"  Interval: {scheduler.update_interval}")
    if scheduler.update_interval == 'daily':
        print(f"  Time: {scheduler.update_hour:02d}:00")
    elif scheduler.update_interval == 'weekly':
        print(f"  Day: {scheduler.update_day.capitalize()}")
        print(f"  Time: {scheduler.update_hour:02d}:00")
    print(f"  Modes: {', '.join(scheduler.modes_to_update)}")
    print(f"  Rate limit delay: {scheduler.rate_limit_delay}s between downloads")
    print(f"  Max retries: {scheduler.max_retries}")
    print(f"  Retry delay: {scheduler.retry_delay}s")

    # Data versions
    print(f"\nCurrent Data Versions:")
    service_manager = get_service_manager()
    versions = service_manager.get_data_version()

    if versions:
        for mode, version_time in sorted(versions.items()):
            print(f"  Mode {mode}: {version_time}")
    else:
        print("  No data found")

    print("="*60)


def history_command(args):
    """Show update history."""
    scheduler = initialize_gtfs_scheduler()

    print("GTFS Update History")
    print("="*60)

    history = scheduler.get_update_history(limit=args.limit)

    if not history:
        print("No update history found")
        return

    for i, entry in enumerate(history, 1):
        timestamp = entry.get('timestamp', 'Unknown')
        success = entry.get('success', False)
        trigger = entry.get('trigger', 'unknown')
        modes = entry.get('modes_updated', [])

        status_icon = "✓" if success else "✗"

        print(f"\n{i}. {status_icon} {timestamp}")
        print(f"   Trigger: {trigger}")
        print(f"   Modes: {', '.join(modes)}")

        # Show individual mode results if available
        results = entry.get('results', {})
        if results:
            failed_modes = [m for m, r in results.items() if not r.get('success')]
            if failed_modes:
                print(f"   Failed: {', '.join(failed_modes)}")

    print("\n" + "="*60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="GTFS Data Update Tool for PTV Transit Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update all configured modes
  python scripts/gtfs_update.py --update-all

  # Update specific modes
  python scripts/gtfs_update.py --modes 1,2,3

  # Check update status
  python scripts/gtfs_update.py --status

  # View update history
  python scripts/gtfs_update.py --history

  # View last 20 history entries
  python scripts/gtfs_update.py --history --limit 20
        """
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Update command
    update_parser = parser.add_argument_group('Update Commands')
    update_parser.add_argument(
        '--update-all',
        action='store_true',
        help='Update all configured GTFS modes'
    )
    update_parser.add_argument(
        '--modes',
        type=str,
        help='Comma-separated list of modes to update (e.g., 1,2,3)'
    )

    # Status command
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show update status and configuration'
    )

    # History command
    parser.add_argument(
        '--history',
        action='store_true',
        help='Show update history'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Number of history entries to show (default: 10)'
    )

    # Verbosity
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Execute appropriate command
    if args.update_all or args.modes:
        update_command(args)
    elif args.status:
        status_command(args)
    elif args.history:
        history_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
