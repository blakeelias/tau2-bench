#!/usr/bin/env python3
import json
import os
from pathlib import Path

simulations_dir = Path("data/simulations")

# Get all JSON files
json_files = sorted([f for f in simulations_dir.glob("*.json")])

renames = []

for file_path in json_files:
    file_name = file_path.name

    # Skip if this is already a task-specific trial
    if "_task_" in file_name:
        continue

    # Try to get task IDs from the file
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        task_ids = set()

        # Check for 'tasks' key (main structure)
        if "tasks" in data:
            tasks_data = data["tasks"]
            if isinstance(tasks_data, list):
                for task in tasks_data:
                    if isinstance(task, dict) and "id" in task:
                        task_id = task["id"]
                        try:
                            task_ids.add(int(task_id))
                        except (ValueError, TypeError):
                            task_ids.add(task_id)
            elif isinstance(tasks_data, dict):
                for key in tasks_data.keys():
                    try:
                        task_ids.add(int(key))
                    except (ValueError, TypeError):
                        task_ids.add(key)

        # Fallback: Check for 'results' key
        elif "results" in data and isinstance(data["results"], list):
            for item in data["results"]:
                if isinstance(item, dict) and "task_id" in item:
                    task_id = item["task_id"]
                    try:
                        task_ids.add(int(task_id))
                    except (ValueError, TypeError):
                        task_ids.add(task_id)

        task_count = len(task_ids)

        # Check if it has all 50 tasks
        has_all_50_zero_indexed = task_count == 50 and task_ids == set(range(0, 50))
        has_all_50_one_indexed = task_count == 50 and task_ids == set(range(1, 51))
        has_all_50 = has_all_50_zero_indexed or has_all_50_one_indexed

        # Only rename if it doesn't have all 50 tasks
        if not has_all_50 and task_count > 0:
            # Sort the task IDs for consistent naming
            sorted_ids = sorted(task_ids)

            # Create the new filename
            # Remove .json extension
            base_name = file_name[:-5]
            # Append task IDs
            task_ids_str = str(sorted_ids).replace(" ", "")
            new_name = f"{base_name}_tasks_{task_ids_str}.json"

            renames.append({
                "old": file_name,
                "new": new_name,
                "task_count": task_count,
                "task_ids": sorted_ids
            })

    except Exception as e:
        print(f"Error processing {file_name}: {e}")
        continue

# Print summary
print("=" * 120)
print(f"{'Original Filename':<80} {'Task Count':<12} {'Action':<28}")
print("=" * 120)

for rename in renames:
    print(f"{rename['old']:<80} {rename['task_count']:<12} RENAME")

print("=" * 120)
print(f"\nTotal files to rename: {len(renames)}")
print("\n" + "=" * 120)
print("RENAME COMMANDS:")
print("=" * 120)

for rename in renames:
    old_path = simulations_dir / rename['old']
    new_path = simulations_dir / rename['new']
    print(f"\nOld: {rename['old']}")
    print(f"New: {rename['new']}")
    print(f"Command: mv \"{old_path}\" \"{new_path}\"")

# Ask for confirmation
print("\n" + "=" * 120)
response = input("Do you want to proceed with renaming these files? (yes/no): ")

if response.lower() in ['yes', 'y']:
    print("\nRenaming files...")
    for rename in renames:
        old_path = simulations_dir / rename['old']
        new_path = simulations_dir / rename['new']
        os.rename(old_path, new_path)
        print(f"✓ Renamed: {rename['old']}")
    print(f"\n✓ Successfully renamed {len(renames)} files!")
else:
    print("\nRename operation cancelled.")
