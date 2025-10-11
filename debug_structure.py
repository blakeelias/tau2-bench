#!/usr/bin/env python3
"""Debug script to understand the JSON structure."""

import json
from pathlib import Path

# Load one file and examine its structure
path = Path('data/simulations/2025-10-08T09:35:50.985724_FIX_CANCELATION_EVAL_airline_tighter_policy_llm_agent_grok-3_user_simulator_grok-3.json')

with open(path, 'r') as f:
    data = json.load(f)

# Look at the first simulation
sim = data['simulations'][0]
print(f"Simulation ID: {sim['id']}")
print(f"Task ID: {sim['task_id']}")
print(f"Reward: {sim['reward_info']['reward']}")
print(f"Termination: {sim['termination_reason']}")
print(f"\nSimulation top-level keys: {sim.keys()}")

# Check if there's an interactions or messages field
for key in sim.keys():
    if 'inter' in key.lower() or 'conv' in key.lower() or 'mess' in key.lower():
        print(f"\nFound key '{key}' with {len(sim[key])} items")
        if sim[key]:
            print(f"First item keys: {sim[key][0].keys() if isinstance(sim[key], list) else 'not a list'}")

# Look at reward_info structure
print(f"\nReward info keys: {sim['reward_info'].keys()}")

# Check interactions
interactions = sim.get('interactions', [])
print(f"\nInteractions: {len(interactions)} items")
if interactions:
    print(f"First interaction keys: {interactions[0].keys()}")
    print(f"First interaction: {json.dumps(interactions[0], indent=2)[:500]}")
