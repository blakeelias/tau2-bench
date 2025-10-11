#!/usr/bin/env python3
"""
Analyze simulation files for cases where the agent transferred to human
but failed evaluation because other tasks weren't completed.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

def load_simulation(path: Path) -> Dict[str, Any]:
    """Load a simulation JSON file."""
    with open(path, 'r') as f:
        return json.load(f)

def analyze_simulation(sim: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a single simulation for transfer + failure cases."""
    task_id = sim.get('task_id')
    reward = sim.get('reward_info', {}).get('reward', None)

    # Check if there was a transfer to human
    transferred = False
    messages = sim.get('messages', [])

    for msg in messages:
        if msg.get('role') == 'assistant':
            tool_calls = msg.get('tool_calls') or []
            for call in tool_calls:
                # Check both formats
                name = call.get('name') or call.get('function', {}).get('name')
                if name == 'transfer_to_human_agents':
                    transferred = True
                    break
        if transferred:
            break

    # Also check termination reason
    termination = sim.get('termination_reason', '')
    if 'transfer' in termination.lower():
        transferred = True

    return {
        'task_id': task_id,
        'transferred': transferred,
        'reward': reward,
        'termination_reason': termination,
        'num_messages': len(messages)
    }

def main():
    sim_dir = Path('data/simulations')

    # Get all JSON files
    json_files = list(sim_dir.glob('*.json'))

    print(f"Analyzing {len(json_files)} simulation files...\n")

    # Focus on files with transfers
    transfer_files = []
    for path in json_files:
        with open(path, 'r') as f:
            content = f.read()
            if 'transfer_to_human' in content:
                transfer_files.append(path)

    print(f"Found {len(transfer_files)} files with human transfers\n")

    # Analyze each file
    transfer_cases = []
    failure_cases = []

    for path in transfer_files:
        data = load_simulation(path)
        simulations = data.get('simulations', [])
        tasks = data.get('tasks', [])

        # Create a task lookup
        task_lookup = {t['id']: t for t in tasks}

        for sim in simulations:
            analysis = analyze_simulation(sim)

            # If transferred, investigate
            if analysis['transferred']:
                task_id = analysis['task_id']
                task = task_lookup.get(task_id, {})
                eval_criteria = task.get('evaluation_criteria', {})

                # Check if there are actions that could have been completed
                required_actions = eval_criteria.get('actions', [])
                communicate_info = eval_criteria.get('communicate_info', [])

                case_info = {
                    'file': path.name,
                    'task_id': task_id,
                    'task_description': task.get('description', {}),
                    'user_scenario': task.get('user_scenario', {}),
                    'required_actions': required_actions,
                    'communicate_info': communicate_info,
                    'nl_assertions': eval_criteria.get('nl_assertions', []),
                    'reward': analysis['reward'],
                    'reward_info': sim.get('reward_info', {}),
                    'termination_reason': analysis['termination_reason'],
                    'num_messages': analysis['num_messages']
                }

                transfer_cases.append(case_info)

                # Check if there were required actions/info AND low reward
                if (required_actions or communicate_info) and analysis['reward'] < 1.0:
                    failure_cases.append(case_info)

    print(f"Total transfer cases: {len(transfer_cases)}")
    print(f"Transfer cases with required actions/info and reward < 1.0: {len(failure_cases)}\n")

    # Show reward distribution for transfer cases
    reward_dist = {}
    for case in transfer_cases:
        reward = case['reward']
        reward_dist[reward] = reward_dist.get(reward, 0) + 1

    print("Reward distribution for all transfer cases:")
    for reward in sorted(reward_dist.keys()):
        print(f"  Reward {reward}: {reward_dist[reward]} cases")

    print("\n" + "=" * 80)

    # Print detailed analysis of failure cases
    for i, case in enumerate(failure_cases, 1):
        print(f"\n### FAILURE CASE {i} ###")
        print(f"File: {case['file']}")
        print(f"Task ID: {case['task_id']}")
        print(f"\nTask Purpose: {case['task_description'].get('purpose', 'N/A')}")
        print(f"\nUser Scenario:")
        print(f"  Reason for call: {case['user_scenario'].get('instructions', {}).get('reason_for_call', 'N/A')}")
        print(f"  Task instructions: {case['user_scenario'].get('instructions', {}).get('task_instructions', 'N/A')}")
        print(f"\nRequired Actions ({len(case['required_actions'])}):")
        for action in case['required_actions']:
            print(f"  - {action.get('name')}: {action.get('arguments', {})}")
        print(f"\nCommunicate Info ({len(case['communicate_info'])}):")
        for info in case['communicate_info']:
            print(f"  - {info}")
        print(f"\nNL Assertions ({len(case['nl_assertions'])}):")
        for assertion in case['nl_assertions']:
            print(f"  - {assertion}")
        print(f"\nReward Info: {case['reward_info']}")
        print(f"Termination: {case['termination_reason']}")
        print(f"Messages: {case['num_messages']}")
        print(f"Reward: {case['reward']}")
        print("=" * 80)

    # Save detailed results to file
    output_path = Path('transfer_failure_analysis.json')
    with open(output_path, 'w') as f:
        json.dump(failure_cases, f, indent=2)

    print(f"\nDetailed results saved to: {output_path}")

if __name__ == '__main__':
    main()
