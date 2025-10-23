#!/usr/bin/env python3
"""
Analyze simulation results and generate detailed narrative summaries.
"""
import json
import os
from litellm import completion

def load_simulation_data(filepath):
    """Load simulation JSON data."""
    with open(filepath, 'r') as f:
        return json.load(f)

def get_task_info(task):
    """Extract key information from a task."""
    return {
        'id': task['id'],
        'purpose': task['description']['purpose'],
        'user_scenario': task['user_scenario']['instructions'],
        'evaluation_criteria': task['evaluation_criteria']
    }

def format_conversation_for_analysis(messages):
    """Format conversation messages for LLM analysis."""
    conversation_text = []

    for msg in messages:
        role = msg.get('role', '')
        content = msg.get('content', '')
        tool_calls = msg.get('tool_calls', [])

        if role == 'user':
            conversation_text.append(f"USER: {content}")
        elif role == 'assistant':
            if tool_calls:
                for tc in tool_calls:
                    func_name = tc.get('name', tc.get('function', {}).get('name', 'unknown'))
                    args = tc.get('arguments', {})
                    if isinstance(args, str):
                        args = json.loads(args)
                    conversation_text.append(f"AGENT: [Tool Call] {func_name}({json.dumps(args)})")
            if content:
                conversation_text.append(f"AGENT: {content}")
        elif role == 'tool':
            tool_name = msg.get('name', 'unknown')
            # Truncate long tool responses
            tool_response = content[:500] + "..." if len(content) > 500 else content
            conversation_text.append(f"TOOL RESPONSE ({tool_name}): {tool_response}")

    return "\n".join(conversation_text)

def analyze_trial_with_llm(task_info, simulation, conversation_text):
    """Use LLM to analyze a trial and generate a narrative summary."""

    prompt = f"""You are analyzing a customer service conversation simulation.

**Task Purpose**: {task_info['purpose']}

**User Scenario**:
- Reason for call: {task_info['user_scenario']['reason_for_call']}
- Known info: {task_info['user_scenario']['known_info']}
- Task instructions: {task_info['user_scenario'].get('task_instructions', 'N/A')}

**Expected Behavior**:
{json.dumps(task_info['evaluation_criteria']['nl_assertions'], indent=2)}

**Actual Conversation**:
{conversation_text}

**Trial Outcome**:
- Reward: {simulation['reward_info']['reward']}
- Success: {simulation['reward_info']['reward'] == 1.0}
- Termination reason: {simulation['termination_reason']}

Please provide a detailed narrative summary that covers:

1. **What the user wanted**: Summarize the user's initial request and any fallback preferences
2. **How the conversation unfolded**: Describe the key interactions step-by-step, focusing on decision points and critical exchanges
3. **What the agent did**: Describe the agent's actions, including tool calls and responses
4. **Why it succeeded/failed**: Explain whether the agent met the evaluation criteria and why

Write this as a clear, chronological narrative in 3-5 paragraphs. Focus on the SUBSTANCE of what happened, not just mechanical listing of tool calls. Explain the agent's reasoning and decision-making.

Be specific about:
- What information the agent gathered
- What decisions the agent made and why
- Whether the agent followed policy correctly
- What the user's reactions were
- The final outcome

Keep it concise but informative."""

    try:
        response = completion(
            model="grok-3-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error analyzing trial: {str(e)}"

def main():
    # Load data
    filepath = '/workspaces/tau2-bench/data/simulations/2025-10-06T06:29:29.611973_airline_llm_agent_grok-3-mini_user_simulator_grok-3-mini.json'
    data = load_simulation_data(filepath)

    # Group simulations by task_id
    task_simulations = {}
    for sim in data['simulations']:
        task_id = sim['task_id']
        if task_id not in task_simulations:
            task_simulations[task_id] = []
        task_simulations[task_id].append(sim)

    # Create task lookup
    tasks_by_id = {task['id']: task for task in data['tasks']}

    # Sort task_ids numerically
    sorted_task_ids = sorted(task_simulations.keys(), key=lambda x: int(x))

    # Analyze each task
    output_lines = []
    output_lines.append(f"# Simulation Analysis Report")
    output_lines.append(f"\n**Agent Model**: {data['info']['agent_info']['llm']}")
    output_lines.append(f"**User Simulator Model**: {data['info']['user_info']['llm']}")
    output_lines.append(f"**Timestamp**: {data['timestamp']}\n")
    output_lines.append("=" * 100 + "\n")

    for task_id in sorted_task_ids:
        print(f"Analyzing Task {task_id}...")

        task = tasks_by_id[task_id]
        task_info = get_task_info(task)
        simulations = task_simulations[task_id]

        # Count successes
        successes = sum(1 for s in simulations if s['reward_info']['reward'] == 1.0)
        total = len(simulations)

        # Determine icon
        if successes == total:
            icon = "✅"
        elif successes == 0:
            icon = "❌"
        else:
            icon = "⚠️"

        # Task header
        output_lines.append(f"## TASK {task_id}")
        output_lines.append(f"\n**Results**: {icon} {successes}/{total} trials successful")
        output_lines.append(f"\n**Purpose**: {task_info['purpose']}")

        # User scenario
        output_lines.append(f"\n**User Scenario**:")
        output_lines.append(f"- **Reason for call**: {task_info['user_scenario']['reason_for_call']}")
        output_lines.append(f"- **Known info**: {task_info['user_scenario']['known_info']}")
        if task_info['user_scenario'].get('task_instructions'):
            output_lines.append(f"- **Additional instructions**: {task_info['user_scenario']['task_instructions']}")

        # Expected behavior
        output_lines.append(f"\n**Expected Behavior**:")
        for assertion in task_info['evaluation_criteria'].get('nl_assertions', []):
            output_lines.append(f"- {assertion}")

        output_lines.append(f"\n---\n")

        # Analyze each trial
        for trial_idx, sim in enumerate(simulations):
            print(f"  Analyzing Trial {trial_idx}...")

            result = "✅ SUCCESS" if sim['reward_info']['reward'] == 1.0 else "❌ FAILURE"
            output_lines.append(f"\n### Trial {trial_idx}: {result}")
            output_lines.append(f"**Reward**: {sim['reward_info']['reward']:.2f}")
            output_lines.append(f"**Duration**: {sim['duration']:.1f}s")
            output_lines.append(f"**Steps**: {len(sim['messages'])}\n")

            # Generate narrative with LLM
            conversation_text = format_conversation_for_analysis(sim['messages'])
            narrative = analyze_trial_with_llm(task_info, sim, conversation_text)

            output_lines.append(narrative)
            output_lines.append("\n")

        output_lines.append("\n" + "=" * 100 + "\n")

    # Write output
    output_file = '/workspaces/tau2-bench/simulation_analysis.md'
    with open(output_file, 'w') as f:
        f.write('\n'.join(output_lines))

    print(f"\nAnalysis complete! Written to {output_file}")

if __name__ == '__main__':
    main()
