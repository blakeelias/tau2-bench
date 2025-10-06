#!/usr/bin/env python3
"""
Aggregate failure analysis for tau2 simulation results.

This script analyzes simulation trajectories to characterize:
- Which types of tasks succeed/fail
- Which types of actions the agent struggles with
- Failure patterns by component (communication, environment, database)
"""
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger
from rich.console import Console
from rich.table import Table

from tau2.data_model.simulation import Results
from tau2.metrics.agent_metrics import is_successful
from tau2.metrics.break_down_metrics import (
    result_reward_actions_analysis,
    result_reward_analysis,
)
from tau2.utils.display import ConsoleDisplay
from tau2.utils.io_utils import expand_paths


def analyze_failure_patterns(results: Results, console: Optional[Console] = None):
    """Analyze and display failure patterns across simulations."""
    if console is None:
        console = ConsoleDisplay.console

    console.print(f"\n[bold blue]Analyzing {len(results.simulations)} simulations...[/]")

    if len(results.simulations) == 0:
        console.print("[yellow]No simulations found in this file.[/]")
        return

    # Get reward breakdown
    df_rewards = result_reward_analysis(results)

    if len(df_rewards) == 0:
        console.print("[yellow]No reward data available for analysis.[/]")
        return

    # Overall success rate
    total_sims = len(df_rewards)
    successful_sims = df_rewards["success"].sum()
    failed_sims = total_sims - successful_sims

    console.print(f"\n[bold]Overall Statistics:[/]")
    console.print(f"  Total simulations: {total_sims}")
    console.print(f"  ✅ Successful: {successful_sims} ({successful_sims/total_sims*100:.1f}%)")
    console.print(f"  ❌ Failed: {failed_sims} ({failed_sims/total_sims*100:.1f}%)")

    # Task-level success rate
    console.print(f"\n[bold]Task-level Analysis:[/]")
    task_success = df_rewards.groupby("task_id")["success"].agg(["sum", "count"])
    task_success["rate"] = task_success["sum"] / task_success["count"]
    task_success = task_success.sort_values("rate")

    # Tasks that always fail
    always_fail = task_success[task_success["sum"] == 0]
    if len(always_fail) > 0:
        console.print(f"  🔴 Always fail ({len(always_fail)} tasks):")
        for task_id in always_fail.index[:10]:  # Show first 10
            console.print(f"    • {task_id}")
        if len(always_fail) > 10:
            console.print(f"    ... and {len(always_fail) - 10} more")

    # Tasks that always succeed
    always_succeed = task_success[task_success["rate"] == 1.0]
    if len(always_succeed) > 0:
        console.print(f"  🟢 Always succeed ({len(always_succeed)} tasks):")
        for task_id in always_succeed.index[:10]:
            console.print(f"    • {task_id}")
        if len(always_succeed) > 10:
            console.print(f"    ... and {len(always_succeed) - 10} more")

    # Intermittent failures
    intermittent = task_success[(task_success["rate"] > 0) & (task_success["rate"] < 1)]
    if len(intermittent) > 0:
        console.print(f"  🟡 Intermittent failures ({len(intermittent)} tasks):")
        for task_id in intermittent.index[:10]:
            rate = intermittent.loc[task_id, "rate"]
            console.print(f"    • {task_id}: {rate*100:.0f}% success")
        if len(intermittent) > 10:
            console.print(f"    ... and {len(intermittent) - 10} more")

    # Analyze failures by component
    failed_df = df_rewards[~df_rewards["success"]]
    if len(failed_df) > 0:
        console.print(f"\n[bold]Failure Breakdown by Component:[/]")

        # Create a table for component failures
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan")
        table.add_column("Failures", justify="right")
        table.add_column("% of Failures", justify="right")

        # Communication failures
        if "communication" in failed_df.columns:
            comm_fail = failed_df["communication"].notna() & (failed_df["communication"] == 0)
            comm_fail_count = comm_fail.sum()
            if comm_fail_count > 0:
                table.add_row(
                    "Communication",
                    str(comm_fail_count),
                    f"{comm_fail_count/failed_sims*100:.1f}%",
                )

        # Environment failures
        if "environment" in failed_df.columns:
            env_fail = failed_df["environment"].notna() & (failed_df["environment"] == 0)
            env_fail_count = env_fail.sum()
            if env_fail_count > 0:
                table.add_row(
                    "Environment",
                    str(env_fail_count),
                    f"{env_fail_count/failed_sims*100:.1f}%",
                )

        # Database failures
        if "database" in failed_df.columns:
            db_fail = failed_df["database"].notna() & (failed_df["database"] == 0)
            db_fail_count = db_fail.sum()
            if db_fail_count > 0:
                table.add_row(
                    "Database", str(db_fail_count), f"{db_fail_count/failed_sims*100:.1f}%"
                )

        console.print(table)

        # Write action analysis
        console.print(f"\n[bold]Write Action Analysis:[/]")
        write_actions = failed_df[failed_df["num_write_action"] > 0]
        if len(write_actions) > 0:
            total_write_actions = write_actions["num_write_action"].sum()
            correct_write_actions = write_actions["num_correct_write_action"].sum()
            console.print(
                f"  Failed simulations with write actions: {len(write_actions)}"
            )
            console.print(f"  Total write actions attempted: {int(total_write_actions)}")
            console.print(
                f"  Correct write actions: {int(correct_write_actions)} ({correct_write_actions/total_write_actions*100:.1f}%)"
            )
        else:
            console.print("  No write actions in failed simulations")


def analyze_action_patterns(results: Results, console: Optional[Console] = None):
    """Analyze which specific actions the agent struggles with."""
    if console is None:
        console = ConsoleDisplay.console

    try:
        df_actions = result_reward_actions_analysis(results)
    except Exception:
        console.print(
            "\n[yellow]⚠️  Could not analyze action patterns (no action checks available)[/]"
        )
        return

    console.print(f"\n[bold]Action Performance Analysis:[/]")

    # Group by action name and requestor
    action_stats = (
        df_actions.groupby(["requestor", "action_name"])["action_match"]
        .agg(["sum", "count"])
        .reset_index()
    )
    action_stats["success_rate"] = action_stats["sum"] / action_stats["count"]
    action_stats = action_stats.sort_values("success_rate")

    # Agent actions
    agent_actions = action_stats[action_stats["requestor"] == "assistant"]
    if len(agent_actions) > 0:
        console.print(f"\n[cyan]Agent Actions (worst performing):[/]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Action", style="cyan")
        table.add_column("Success", justify="right")
        table.add_column("Total", justify="right")
        table.add_column("Rate", justify="right")

        for _, row in agent_actions.head(10).iterrows():
            rate_color = "green" if row["success_rate"] > 0.8 else "yellow" if row["success_rate"] > 0.5 else "red"
            table.add_row(
                row["action_name"],
                str(int(row["sum"])),
                str(int(row["count"])),
                f"[{rate_color}]{row['success_rate']*100:.1f}%[/{rate_color}]",
            )
        console.print(table)

    # User actions
    user_actions = action_stats[action_stats["requestor"] == "user"]
    if len(user_actions) > 0:
        console.print(f"\n[cyan]User Actions (worst performing):[/]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Action", style="cyan")
        table.add_column("Success", justify="right")
        table.add_column("Total", justify="right")
        table.add_column("Rate", justify="right")

        for _, row in user_actions.head(10).iterrows():
            rate_color = "green" if row["success_rate"] > 0.8 else "yellow" if row["success_rate"] > 0.5 else "red"
            table.add_row(
                row["action_name"],
                str(int(row["sum"])),
                str(int(row["count"])),
                f"[{rate_color}]{row['success_rate']*100:.1f}%[/{rate_color}]",
            )
        console.print(table)


def analyze_failures(input_paths: list[str]) -> None:
    """
    Analyze simulation failures across multiple trajectory files.

    Args:
        input_paths: List of paths to trajectory files, directories, or glob patterns
    """
    files = expand_paths(input_paths, extension=".json")
    console = ConsoleDisplay.console

    if not files:
        console.print("❌ No trajectory files found", style="red")
        sys.exit(1)

    console.print(
        f"\n🔍 Analyzing failures in {len(files)} trajectory file(s)", style="bold blue"
    )

    all_results = []
    for file_path in files:
        console.print(f"\n[dim]Loading {file_path}...[/]")
        try:
            results = Results.load(file_path)
            all_results.append(results)
        except Exception as e:
            console.print(f"  ❌ Error loading file: {e}", style="red")
            continue

    if not all_results:
        console.print("❌ No valid trajectory files loaded", style="red")
        sys.exit(1)

    # Analyze each file separately
    for i, (file_path, results) in enumerate(zip(files, all_results), 1):
        console.print("\n" + "=" * 80)
        console.print(f"[bold]File {i}/{len(files)}: {Path(file_path).name}[/]")
        console.print("=" * 80)

        analyze_failure_patterns(results, console)
        analyze_action_patterns(results, console)

    # If multiple files, show combined summary
    if len(all_results) > 1:
        console.print("\n" + "=" * 80)
        console.print("[bold]Combined Summary Across All Files[/]")
        console.print("=" * 80)

        total_sims = sum(len(r.simulations) for r in all_results)
        total_success = sum(
            sum(1 for sim in r.simulations if is_successful(sim.reward_info.reward))
            for r in all_results
        )
        console.print(f"\n  Total simulations: {total_sims}")
        console.print(
            f"  Overall success rate: {total_success/total_sims*100:.1f}% ({total_success}/{total_sims})"
        )


def make_parser():
    """Make parser for analyze_failures command."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze simulation failures and action patterns"
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Paths to trajectory files, directories, or glob patterns",
    )
    return parser


def main():
    """Analyze failures from command line."""
    logger.configure(handlers=[{"sink": sys.stderr, "level": "ERROR"}])
    parser = make_parser()
    args = parser.parse_args()
    analyze_failures(args.paths)


if __name__ == "__main__":
    main()
