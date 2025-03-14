#!/usr/bin/env python
"""
API Router Duplication Cleanup Script

This script helps identify and remove redundant API router files
that have been consolidated into the unified consolidated_chart router.
"""

import os
import sys
import shutil
from pathlib import Path

# Configuration
ROUTERS_DIR = "ai_service/api/routers"
BACKUP_DIR = "ai_service/api/routers_backup"
CONSOLIDATED_ROUTER_DIR = "ai_service/api/routers/consolidated_chart"

# Files and directories that should NOT be removed
KEEP_FILES = [
    "__init__.py",
    "ai_integration_test.py",
    "ai_status.py",
    "geocode.py",
    "health.py",
    "questionnaire.py",
    "session.py",
    "test_compatibility.py",
    "test_endpoints.py",
    "consolidated_chart", # Keep this directory
]

# Files and directories to be removed
REMOVE_FILES = [
    "chart.py",
    "chart_comparison.py",
    "charts.py",
    "validate.py",
    "rectify.py",
    "export.py",
    "chart",  # Remove this directory and its contents
    "chart_v2",  # Remove this directory and its contents
]

def create_backup():
    """
    Create a backup of all router files before making changes
    """
    print(f"Creating backup in {BACKUP_DIR}...")
    backup_dir = Path(BACKUP_DIR)

    # Create the backup directory if it doesn't exist
    if not backup_dir.exists():
        backup_dir.mkdir(parents=True)

    # Copy all files from ROUTERS_DIR to BACKUP_DIR
    for item in Path(ROUTERS_DIR).iterdir():
        if item.is_file():
            shutil.copy2(item, backup_dir)
        elif item.is_dir() and item.name != backup_dir.name:
            shutil.copytree(item, backup_dir / item.name, dirs_exist_ok=True)

    print("Backup created successfully.")

def cleanup(dry_run=True):
    """
    Identify and optionally remove redundant router files
    """
    if dry_run:
        print("DRY RUN: No files will be deleted.")

    # Get the absolute path to the routers directory
    routers_dir = Path(ROUTERS_DIR).absolute()

    # Verify that the consolidated router directory exists
    if not Path(CONSOLIDATED_ROUTER_DIR).exists():
        print(f"ERROR: Consolidated router directory {CONSOLIDATED_ROUTER_DIR} not found.")
        print("Aborting cleanup.")
        return

    # Find files to remove
    to_remove = []

    for item in routers_dir.iterdir():
        if item.name in REMOVE_FILES:
            to_remove.append(item)

    # Report findings
    if not to_remove:
        print("No redundant router files found.")
        return

    print(f"Found {len(to_remove)} redundant router files/directories:")
    for i, item in enumerate(to_remove, 1):
        item_type = "Directory" if item.is_dir() else "File"
        print(f"{i}. {item_type}: {item.relative_to(routers_dir)}")

    # If not a dry run, remove the files
    if not dry_run:
        # Create backup first
        create_backup()

        # Remove files
        print("\nRemoving redundant router files...")
        for item in to_remove:
            try:
                if item.is_file():
                    item.unlink()
                    print(f"✓ Removed file: {item.relative_to(routers_dir)}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    print(f"✓ Removed directory: {item.relative_to(routers_dir)}")
            except Exception as e:
                print(f"✗ Failed to remove {item}: {str(e)}")

        print("\nCleanup completed successfully.")
    else:
        print("\nTo remove these files, run with --execute")

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        cleanup(dry_run=False)
    else:
        cleanup(dry_run=True)
        print("\nTo execute the cleanup, run with --execute:")
        print("python scripts/cleanup-api-router-duplication.py --execute")
