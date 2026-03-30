#!/usr/bin/env python
"""Import devices from Excel file into TinyOps database.

Usage:
    # Dry run (preview changes)
    python scripts/import_devices.py "20260311_AOP_Device List.xlsx" --dry-run
    
    # Actual import
    python scripts/import_devices.py "20260311_AOP_Device List.xlsx"
    
    # With JSON report output
    python scripts/import_devices.py "20260311_AOP_Device List.xlsx" --report report.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.services.device_import_service import DeviceImportService


def print_result(result, dry_run: bool = False):
    """Print import result in readable format."""
    print("\n" + "=" * 70)
    print(f"{'DRY RUN - ' if dry_run else ''}DEVICE IMPORT SUMMARY")
    print("=" * 70)
    
    print(f"\nTotal rows processed: {result.total_rows}")
    print(f"✓ Inserted:  {result.inserted:4d}")
    print(f"✓ Updated:   {result.updated:4d}")
    print(f"⊘ Skipped:   {result.skipped:4d}")
    print(f"✗ Errors:    {result.errors:4d}")
    print(f"\nSuccess rate: {result.success_rate:.1f}%")
    
    if result.changes_log:
        print(f"\n{'-' * 70}")
        print(f"CHANGES DETAIL ({len(result.changes_log)} devices updated)")
        print("-" * 70)
        
        for change in result.changes_log[:10]:  # Show first 10
            print(f"\n{change.hostname} ({change.mgmt_ip}):")
            for field, (old, new) in change.field_changes.items():
                print(f"  {field:20s}: {old!r:30s} → {new!r}")
        
        if len(result.changes_log) > 10:
            print(f"\n... and {len(result.changes_log) - 10} more devices with changes")
    
    if result.error_details:
        print(f"\n{'-' * 70}")
        print(f"ERRORS ({len(result.error_details)} rows failed)")
        print("-" * 70)
        
        for error in result.error_details[:10]:  # Show first 10
            print(f"\nRow {error.row_number}: {error.hostname or '(no hostname)'} / {error.mgmt_ip or '(no IP)'}")
            print(f"  Error: {error.error}")
        
        if len(result.error_details) > 10:
            print(f"\n... and {len(result.error_details) - 10} more errors")
    
    print("\n" + "=" * 70 + "\n")


def save_report(result, report_path: Path):
    """Save detailed report as JSON."""
    report = {
        "summary": {
            "total_rows": result.total_rows,
            "inserted": result.inserted,
            "updated": result.updated,
            "skipped": result.skipped,
            "errors": result.errors,
            "success_rate": result.success_rate,
        },
        "changes": [
            {
                "mgmt_ip": c.mgmt_ip,
                "hostname": c.hostname,
                "field_changes": {
                    field: {"old": old, "new": new}
                    for field, (old, new) in c.field_changes.items()
                },
                "timestamp": c.timestamp.isoformat(),
            }
            for c in result.changes_log
        ],
        "errors": [
            {
                "row_number": e.row_number,
                "hostname": e.hostname,
                "mgmt_ip": e.mgmt_ip,
                "error": e.error,
            }
            for e in result.error_details
        ],
    }
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"✓ Detailed report saved to: {report_path}")


async def main():
    parser = argparse.ArgumentParser(
        description="Import devices from Excel file into TinyOps database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "excel_file",
        type=Path,
        help="Path to Excel file (e.g., '20260311_AOP_Device List.xlsx')"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without committing to database"
    )
    parser.add_argument(
        "--report",
        type=Path,
        metavar="FILE",
        help="Save detailed JSON report to file"
    )
    parser.add_argument(
        "--performed-by",
        type=str,
        metavar="USERNAME",
        help="Username of person performing import (for audit trail)"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not args.excel_file.exists():
        print(f"✗ Error: File not found: {args.excel_file}", file=sys.stderr)
        return 1
    
    if not args.excel_file.suffix.lower() in [".xlsx", ".xls"]:
        print(f"✗ Error: File must be Excel format (.xlsx or .xls)", file=sys.stderr)
        return 1
    
    print(f"Importing from: {args.excel_file}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be committed)")
    else:
        print("Mode: LIVE IMPORT")
        response = input("\nProceed with import? [y/N]: ").strip().lower()
        if response != "y":
            print("Import cancelled.")
            return 0
    
    # Run import
    async with SessionLocal() as db:
        service = DeviceImportService(db)
        
        try:
            result = await service.import_from_excel(
                file_path=args.excel_file,
                dry_run=args.dry_run,
                performed_by=args.performed_by,
            )
        except Exception as e:
            print(f"\n✗ Import failed: {e}", file=sys.stderr)
            return 1
    
    # Display results
    print_result(result, dry_run=args.dry_run)
    
    # Save report if requested
    if args.report:
        save_report(result, args.report)
    
    # Return exit code based on errors
    return 0 if result.errors == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
