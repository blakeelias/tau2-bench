#!/usr/bin/env python3
"""Examine a specific case in detail."""

import json
from pathlib import Path

# Look at Task 11 from the second failure case
path = Path('data/simulations/2025-10-06T16:23:30.695138_airline_llm_agent_grok-4-fast-reasoning_user_simulator_grok-4-fast-reasoning.json')

with open(path, 'r') as f:
    data = json.load(f)

# Find the simulation for task 11
for sim in data['simulations']:
    if sim['task_id'] == '11':
        print(f"Task ID: {sim['task_id']}")
        print(f"Reward: {sim['reward_info']['reward']}")
        print(f"Termination: {sim['termination_reason']}")
        print(f"\n{'='*80}\n")

        # Print the conversation
        messages = sim['messages']
        print(f"Conversation ({len(messages)} messages):\n")

        for i, msg in enumerate(messages):
            role = msg['role']
            content = msg.get('content', '')
            tool_calls = msg.get('tool_calls') or []

            print(f"\n--- Message {i+1}: {role.upper()} ---")
            if content:
                print(content[:500])
            if tool_calls:
                print(f"\nTool calls:")
                for call in tool_calls:
                    name = call.get('name') or call.get('function', {}).get('name')
                    print(f"  - {name}")

        print(f"\n\n{'='*80}\n")
        print(f"Evaluation Summary:")
        print(f"  Reward: {sim['reward_info']['reward']}")
        print(f"  DB Match: {sim['reward_info']['db_check'].get('db_match')}")
        print(f"\nAction Checks:")
        for check in sim['reward_info']['action_checks']:
            action_name = check['action']['name']
            action_match = check['action_match']
            print(f"  - {action_name}: {'✓' if action_match else '✗'}")

        break
