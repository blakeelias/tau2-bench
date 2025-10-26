#!/usr/bin/env python3
import json
import os
import argparse
from pathlib import Path
from collections import defaultdict

def get_task_ids(data):
    """Extract task IDs from simulation data."""
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

    return task_ids


def get_trial_counts(data):
    """Get the unique trial counts across all tasks."""
    # Group simulations by task_id and count trials
    task_trials = defaultdict(set)

    if "simulations" in data and isinstance(data["simulations"], list):
        for sim in data["simulations"]:
            if isinstance(sim, dict) and "task_id" in sim and "trial" in sim:
                task_id = sim["task_id"]
                trial = sim["trial"]
                task_trials[task_id].add(trial)

    # Get the count of trials for each task
    trial_counts = [len(trials) for trials in task_trials.values()]

    # Get unique trial counts
    unique_trial_counts = sorted(set(trial_counts))

    return unique_trial_counts, dict(task_trials)


def analyze_files(simulations_dir, rename_tasks=False, rename_trials=False):
    """Analyze files and generate rename operations."""
    # Get all JSON files
    json_files = sorted([f for f in simulations_dir.glob("*.json")])

    renames = []

    for file_path in json_files:
        file_name = file_path.name

        # Skip if this is already a task-specific trial
        if "_task_" in file_name and not rename_trials:
            continue

        # Try to analyze the file
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Start with the base filename (remove .json)
            base_name = file_name[:-5]
            new_name = base_name
            rename_info = {"old": file_name}

            # Task presence renaming
            if rename_tasks and "_task_" not in file_name:
                task_ids = get_task_ids(data)
                task_count = len(task_ids)

                # Check if it has all 50 tasks
                has_all_50_zero_indexed = task_count == 50 and task_ids == set(range(0, 50))
                has_all_50_one_indexed = task_count == 50 and task_ids == set(range(1, 51))
                has_all_50 = has_all_50_zero_indexed or has_all_50_one_indexed

                # Only add task suffix if it doesn't have all 50 tasks
                if not has_all_50 and task_count > 0:
                    sorted_ids = sorted(task_ids)
                    task_ids_str = str(sorted_ids).replace(" ", "")
                    new_name += f"_tasks_{task_ids_str}"
                    rename_info["task_count"] = task_count
                    rename_info["task_ids"] = sorted_ids

            # Trial count renaming
            if rename_trials:
                unique_trial_counts, task_trials = get_trial_counts(data)

                if unique_trial_counts:
                    # Check if already has _num_trials_ in filename
                    if "_num_trials_" not in file_name:
                        trial_counts_str = str(unique_trial_counts).replace(" ", "")
                        new_name += f"_num_trials_{trial_counts_str}"
                        rename_info["unique_trial_counts"] = unique_trial_counts
                        rename_info["task_trials"] = task_trials

            # If the name changed, add to renames
            if new_name != base_name:
                new_name += ".json"
                rename_info["new"] = new_name
                renames.append(rename_info)

        except Exception as e:
            print(f"Error processing {file_name}: {e}")
            continue

    return renames


def print_summary(renames, rename_tasks, rename_trials):
    """Print summary of rename operations."""
    print("=" * 140)
    if rename_tasks and rename_trials:
        print(f"{'Original Filename':<70} {'Tasks':<15} {'Trials':<20} {'Action':<10}")
    elif rename_tasks:
        print(f"{'Original Filename':<80} {'Task Count':<12} {'Action':<28}")
    elif rename_trials:
        print(f"{'Original Filename':<70} {'Unique Trial Counts':<30} {'Action':<10}")
    print("=" * 140)

    for rename in renames:
        if rename_tasks and rename_trials:
            tasks = str(rename.get('task_count', 'N/A'))
            trials = str(rename.get('unique_trial_counts', 'N/A'))
            print(f"{rename['old']:<70} {tasks:<15} {trials:<20} RENAME")
        elif rename_tasks:
            tasks = str(rename.get('task_count', 'N/A'))
            print(f"{rename['old']:<80} {tasks:<12} RENAME")
        elif rename_trials:
            trials = str(rename.get('unique_trial_counts', 'N/A'))
            print(f"{rename['old']:<70} {trials:<30} RENAME")

    print("=" * 140)


def main():
    parser = argparse.ArgumentParser(
        description='Rename simulation files based on task presence and/or trial counts.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rename files with incomplete tasks
  python rename_incomplete_files.py --rename-tasks

  # Rename files with trial count information
  python rename_incomplete_files.py --rename-trials

  # Do both operations
  python rename_incomplete_files.py --rename-tasks --rename-trials

  # Dry run to preview changes
  python rename_incomplete_files.py --rename-trials --dry-run
        """
    )

    parser.add_argument(
        '--simulations-dir',
        type=Path,
        default=Path('data/simulations'),
        help='Directory containing simulation files (default: data/simulations)'
    )

    parser.add_argument(
        '--rename-tasks',
        action='store_true',
        help='Rename files based on which tasks are present (for incomplete files)'
    )

    parser.add_argument(
        '--rename-trials',
        action='store_true',
        help='Rename files based on unique trial counts across tasks'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without actually renaming files'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.rename_tasks and not args.rename_trials:
        parser.error("At least one of --rename-tasks or --rename-trials must be specified")

    if not args.simulations_dir.exists():
        print(f"Error: Directory {args.simulations_dir} does not exist")
        return

    # Analyze files
    renames = analyze_files(args.simulations_dir, args.rename_tasks, args.rename_trials)

    if not renames:
        print("No files to rename.")
        return

    # Print summary
    print_summary(renames, args.rename_tasks, args.rename_trials)

    print(f"\nTotal files to rename: {len(renames)}")
    print("\n" + "=" * 140)
    print("RENAME COMMANDS:")
    print("=" * 140)

    for rename in renames:
        old_path = args.simulations_dir / rename['old']
        new_path = args.simulations_dir / rename['new']
        print(f"\nOld: {rename['old']}")
        print(f"New: {rename['new']}")
        print(f"Command: mv \"{old_path}\" \"{new_path}\"")

    # Ask for confirmation
    if not args.dry_run:
        print("\n" + "=" * 140)
        response = input("Do you want to proceed with renaming these files? (yes/no): ")

        if response.lower() in ['yes', 'y']:
            print("\nRenaming files...")
            for rename in renames:
                old_path = args.simulations_dir / rename['old']
                new_path = args.simulations_dir / rename['new']
                os.rename(old_path, new_path)
                print(f"✓ Renamed: {rename['old']}")
            print(f"\n✓ Successfully renamed {len(renames)} files!")
        else:
            print("\nRename operation cancelled.")
    else:
        print("\n[DRY RUN] No files were renamed.")


if __name__ == "__main__":
    main()
