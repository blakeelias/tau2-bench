#!/usr/bin/env python3
"""
Create structured summaries for all simulations, ready for manual narrative filling.
"""
import json

def load_simulation_data(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def summarize_conversation(messages):
    """Create a bullet-point summary of conversation flow."""
    summary = []
    tool_calls_count = {}

    for msg in messages:
        role = msg.get('role', '')
        content = msg.get('content', '')
        tool_calls = msg.get('tool_calls', [])

        if role == 'assistant' and tool_calls:
            for tc in tool_calls:
                func_name = tc.get('name', 'unknown')
                tool_calls_count[func_name] = tool_calls_count.get(func_name, 0) + 1

        if role == 'user':
            if '###STOP###' in content:
                summary.append("User ended conversation (satisfied)")
            elif '###TRANSFER###' in content:
                summary.append("User requested transfer")
            elif '###OUT-OF-SCOPE###' in content:
                summary.append("User marked out-of-scope")

    if tool_calls_count:
        summary.append(f"Tool calls made: {dict(tool_calls_count)}")

    return summary

def main():
    filepath = '/workspaces/tau2-bench/data/simulations/2025-10-06T06:29:29.611973_airline_llm_agent_grok-3-mini_user_simulator_grok-3-mini.json'
    data = load_simulation_data(filepath)

    # Group simulations
    task_simulations = {}
    for sim in data['simulations']:
        task_id = sim['task_id']
        if task_id not in task_simulations:
            task_simulations[task_id] = []
        task_simulations[task_id].append(sim)

    tasks_by_id = {task['id']: task for task in data['tasks']}
    sorted_task_ids = sorted(task_simulations.keys(), key=lambda x: int(x))

    # Generate report
    output_file = '/workspaces/tau2-bench/simulation_summaries.md'

    with open(output_file, 'w') as f:
        f.write("# Simulation Results Summary\n\n")
        f.write(f"**Agent Model**: {data['info']['agent_info']['llm']}\n")
        f.write(f"**User Simulator Model**: {data['info']['user_info']['llm']}\n")
        f.write(f"**Timestamp**: {data['timestamp']}\n\n")
        f.write("=" * 100 + "\n\n")

        for task_id in sorted_task_ids:
            task = tasks_by_id[task_id]
            simulations = task_simulations[task_id]

            successes = sum(1 for s in simulations if s['reward_info']['reward'] == 1.0)
            total = len(simulations)

            if successes == total:
                icon = "✅"
            elif successes == 0:
                icon = "❌"
            else:
                icon = "⚠️"

            f.write(f"## TASK {task_id}\n\n")
            f.write(f"**Results**: {icon} **{successes}/{total}** trials successful\n\n")
            f.write(f"**Purpose**: {task['description']['purpose']}\n\n")

            # User scenario
            user_scenario = task['user_scenario']['instructions']
            f.write(f"**User Scenario**:\n")
            f.write(f"- **Reason for call**: {user_scenario['reason_for_call']}\n")
            f.write(f"- **Known info**: {user_scenario['known_info']}\n")
            if user_scenario.get('task_instructions'):
                f.write(f"- **Additional instructions**: {user_scenario['task_instructions']}\n")

            # Expected behavior
            f.write(f"\n**Expected Behavior**:\n")
            for assertion in task['evaluation_criteria'].get('nl_assertions', []):
                f.write(f"- {assertion}\n")

            f.write(f"\n---\n\n")

            # Trials
            for trial_idx, sim in enumerate(simulations):
                result = "✅ SUCCESS" if sim['reward_info']['reward'] == 1.0 else "❌ FAILURE"
                f.write(f"### Trial {trial_idx}: {result}\n\n")
                f.write(f"**Reward**: {sim['reward_info']['reward']:.2f} | ")
                f.write(f"**Duration**: {sim['duration']:.1f}s | ")
                f.write(f"**Messages**: {len(sim['messages'])} | ")
                f.write(f"**Termination**: {sim['termination_reason']}\n\n")

                # Quick summary
                summary_points = summarize_conversation(sim['messages'])
                if summary_points:
                    f.write("**Quick facts**:\n")
                    for point in summary_points:
                        f.write(f"- {point}\n")
                    f.write("\n")

                f.write("**What Happened**:\n")
                f.write("[Manual analysis needed - see formatted conversation in separate file]\n\n")

                f.write("**Why Success/Failure**:\n")
                f.write("[Analysis needed]\n\n")

            f.write("\n" + "=" * 100 + "\n\n")

    print(f"Summary template created: {output_file}")
    print(f"Total tasks: {len(sorted_task_ids)}")
    print(f"Total trials: {sum(len(task_simulations[tid]) for tid in sorted_task_ids)}")

if __name__ == '__main__':
    main()
