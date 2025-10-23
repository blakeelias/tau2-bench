#!/usr/bin/env python3
"""
Analyze simulation results and generate detailed narrative summaries (incremental version).
"""
import json
import sys
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
                    conversation_text.append(f"AGENT: [Tool Call] {func_name}({json.dumps(args, separators=(',', ':'))})")
            if content:
                conversation_text.append(f"AGENT: {content}")
        elif role == 'tool':
            tool_name = msg.get('name', 'unknown')
            # Truncate long tool responses
            tool_response = content[:300] + "..." if len(content) > 300 else content
            conversation_text.append(f"TOOL RESPONSE ({tool_name}): {tool_response}")

    return "\n".join(conversation_text)

def analyze_trial_with_llm(task_info, simulation, conversation_text):
    """Use LLM to analyze a trial and generate a narrative summary."""

    prompt = f"""You are analyzing a customer service conversation simulation between an airline agent and a customer.

**Task Purpose**: {task_info['purpose']}

**User Scenario**:
- Reason for call: {task_info['user_scenario']['reason_for_call']}
- Known info: {task_info['user_scenario']['known_info']}
- Task instructions: {task_info['user_scenario'].get('task_instructions', 'N/A')}

**Expected Agent Behavior**:
{json.dumps(task_info['evaluation_criteria']['nl_assertions'], indent=2)}

**Actual Conversation**:
{conversation_text}

**Trial Outcome**:
- Reward: {simulation['reward_info']['reward']}
- Success: {simulation['reward_info']['reward'] == 1.0}
- Termination: {simulation['termination_reason']}

Provide a detailed narrative summary in 3-5 paragraphs covering:

1. **User's Goal**: What did the user want to accomplish?
2. **Conversation Flow**: How did the interaction unfold chronologically? What were the key decision points?
3. **Agent's Actions**: What did the agent do (information gathering, tool calls, policy decisions)?
4. **Outcome Analysis**: Did the agent meet the evaluation criteria? Why did it succeed/fail?

Focus on SUBSTANCE over mechanics. Explain reasoning and decision-making, not just tool calls. Be specific about what information was gathered, what decisions were made, and why the outcome occurred."""

    try:
        response = completion(
            model="xai/grok-3-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error analyzing trial: {str(e)}"

def main():
    # Get task range from command line
    start_task = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end_task = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    # Load data
    filepath = '/workspaces/tau2-bench/data/simulations/2025-10-06T06:29:29.611973_airline_llm_agent_grok-3-mini_user_simulator_grok-3-mini.json'
    print(f"Loading data from {filepath}...")
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
    all_task_ids = sorted(task_simulations.keys(), key=lambda x: int(x))
    task_ids_to_process = [tid for tid in all_task_ids if start_task <= int(tid) < end_task]

    # Output file
    output_file = f'/workspaces/tau2-bench/simulation_analysis_tasks_{start_task}_to_{end_task-1}.md'

    with open(output_file, 'w') as outf:
        # Write header
        outf.write(f"# Simulation Analysis Report (Tasks {start_task}-{end_task-1})\n\n")
        outf.write(f"**Agent Model**: {data['info']['agent_info']['llm']}\n")
        outf.write(f"**User Simulator Model**: {data['info']['user_info']['llm']}\n")
        outf.write(f"**Timestamp**: {data['timestamp']}\n\n")
        outf.write("=" * 100 + "\n\n")

        # Process each task
        for task_id in task_ids_to_process:
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
            outf.write(f"## TASK {task_id}\n\n")
            outf.write(f"**Results**: {icon} **{successes}/{total}** trials successful\n\n")
            outf.write(f"**Purpose**: {task_info['purpose']}\n\n")

            # User scenario
            outf.write(f"**User Scenario**:\n")
            outf.write(f"- **Reason for call**: {task_info['user_scenario']['reason_for_call']}\n")
            outf.write(f"- **Known info**: {task_info['user_scenario']['known_info']}\n")
            if task_info['user_scenario'].get('task_instructions'):
                outf.write(f"- **Additional instructions**: {task_info['user_scenario']['task_instructions']}\n")

            # Expected behavior
            outf.write(f"\n**Expected Behavior**:\n")
            for assertion in task_info['evaluation_criteria'].get('nl_assertions', []):
                outf.write(f"- {assertion}\n")

            outf.write(f"\n---\n\n")

            # Analyze each trial
            for trial_idx, sim in enumerate(simulations):
                print(f"  Analyzing Trial {trial_idx}...")

                result = "✅ SUCCESS" if sim['reward_info']['reward'] == 1.0 else "❌ FAILURE"
                outf.write(f"### Trial {trial_idx}: {result}\n\n")
                outf.write(f"**Reward**: {sim['reward_info']['reward']:.2f} | ")
                outf.write(f"**Duration**: {sim['duration']:.1f}s | ")
                outf.write(f"**Steps**: {len(sim['messages'])}\n\n")

                # Generate narrative with LLM
                conversation_text = format_conversation_for_analysis(sim['messages'])
                narrative = analyze_trial_with_llm(task_info, sim, conversation_text)

                outf.write(narrative)
                outf.write("\n\n")

                # Flush after each trial
                outf.flush()

            outf.write("\n" + "=" * 100 + "\n\n")
            outf.flush()

    print(f"\nAnalysis complete! Written to {output_file}")

if __name__ == '__main__':
    main()
