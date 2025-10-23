#!/usr/bin/env python3
"""
Format conversations from simulation results for manual analysis.
"""
import json
import sys

def load_simulation_data(filepath):
    """Load simulation JSON data."""
    with open(filepath, 'r') as f:
        return json.load(f)

def format_conversation(messages):
    """Format conversation messages in a readable way."""
    lines = []

    for i, msg in enumerate(messages):
        role = msg.get('role', '')
        content = msg.get('content', '')
        tool_calls = msg.get('tool_calls', [])

        if role == 'user':
            # Check for special tokens
            if '###STOP###' in content:
                lines.append(f"👤 USER: {content.replace('###STOP###', '[STOP - Task Complete]')}")
            elif '###TRANSFER###' in content:
                lines.append(f"👤 USER: {content.replace('###TRANSFER###', '[TRANSFER - Requesting Human]')}")
            elif '###OUT-OF-SCOPE###' in content:
                lines.append(f"👤 USER: {content.replace('###OUT-OF-SCOPE###', '[OUT-OF-SCOPE]')}")
            else:
                lines.append(f"👤 USER: {content}")

        elif role == 'assistant':
            if tool_calls:
                for tc in tool_calls:
                    func_name = tc.get('name', 'unknown')
                    args = tc.get('arguments', {})
                    # Format key arguments nicely
                    if isinstance(args, dict):
                        key_args = []
                        for k, v in list(args.items())[:3]:  # Show first 3 args
                            if isinstance(v, str) and len(v) > 50:
                                v = v[:50] + "..."
                            key_args.append(f"{k}={repr(v)}")
                        args_str = ", ".join(key_args)
                        if len(args) > 3:
                            args_str += ", ..."
                    else:
                        args_str = str(args)
                    lines.append(f"🤖 AGENT [TOOL CALL]: {func_name}({args_str})")
            if content:
                lines.append(f"🤖 AGENT: {content}")

        elif role == 'tool':
            tool_name = msg.get('name', 'unknown')
            # Summarize tool response
            if len(content) > 200:
                content_preview = content[:200] + f"... [+{len(content)-200} chars]"
            else:
                content_preview = content
            lines.append(f"⚙️  TOOL ({tool_name}): {content_preview}")

        lines.append("")  # Empty line between messages

    return "\n".join(lines)

def main():
    task_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    # Load data
    filepath = '/workspaces/tau2-bench/data/simulations/2025-10-06T06:29:29.611973_airline_llm_agent_grok-3-mini_user_simulator_grok-3-mini.json'
    data = load_simulation_data(filepath)

    # Group simulations by task_id
    task_simulations = {}
    for sim in data['simulations']:
        tid = sim['task_id']
        if tid not in task_simulations:
            task_simulations[tid] = []
        task_simulations[tid].append(sim)

    # Create task lookup
    tasks_by_id = {task['id']: task for task in data['tasks']}

    # Get the specified task
    task_id_str = str(task_id)
    if task_id_str not in tasks_by_id:
        print(f"Task {task_id} not found!")
        return

    task = tasks_by_id[task_id_str]
    simulations = task_simulations[task_id_str]

    # Print task info
    print("=" * 100)
    print(f"TASK {task_id}")
    print("=" * 100)
    print(f"\nPURPOSE: {task['description']['purpose']}\n")

    print("USER SCENARIO:")
    print(f"  - Reason: {task['user_scenario']['instructions']['reason_for_call']}")
    print(f"  - Known: {task['user_scenario']['instructions']['known_info']}")
    if task['user_scenario']['instructions'].get('task_instructions'):
        print(f"  - Instructions: {task['user_scenario']['instructions']['task_instructions']}")

    print(f"\nEXPECTED BEHAVIOR:")
    for assertion in task['evaluation_criteria'].get('nl_assertions', []):
        print(f"  - {assertion}")

    # Count successes
    successes = sum(1 for s in simulations if s['reward_info']['reward'] == 1.0)
    print(f"\nRESULTS: {successes}/{len(simulations)} successful")
    print("\n" + "=" * 100)

    # Print each trial
    for trial_idx, sim in enumerate(simulations):
        result = "SUCCESS" if sim['reward_info']['reward'] == 1.0 else "FAILURE"
        print(f"\n\n{'='*100}")
        print(f"TRIAL {trial_idx}: {result} (Reward: {sim['reward_info']['reward']:.2f})")
        print(f"Duration: {sim['duration']:.1f}s | Messages: {len(sim['messages'])} | Termination: {sim['termination_reason']}")
        print('='*100)
        print()

        conversation = format_conversation(sim['messages'])
        print(conversation)

if __name__ == '__main__':
    main()
