"""Tests for multi-outcome evaluation with scalar rewards."""

import pytest

from tau2.data_model.message import AssistantMessage, ToolCall
from tau2.data_model.simulation import SimulationRun, TerminationReason
from tau2.data_model.tasks import (
    AcceptableOutcome,
    Action,
    EvaluationCriteria,
    Task,
    UserScenario,
)
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation


@pytest.fixture
def multi_outcome_task():
    """Create a task with multiple acceptable outcomes."""
    outcome_a = AcceptableOutcome(
        outcome_id="test_outcome_A",
        description="Perfect match - highest reward",
        reward=1.0,
        actions=[
            Action(
                action_id="action_1",
                name="perfect_action",
                arguments={"arg1": "value1"},
            )
        ],
    )

    outcome_b = AcceptableOutcome(
        outcome_id="test_outcome_B",
        description="Good match - medium reward",
        reward=0.7,
        actions=[
            Action(
                action_id="action_2",
                name="good_action",
                arguments={"arg2": "value2"},
            )
        ],
    )

    outcome_c = AcceptableOutcome(
        outcome_id="test_outcome_C",
        description="Acceptable match - low reward",
        reward=0.5,
        actions=[
            Action(
                action_id="action_3",
                name="acceptable_action",
                arguments={"arg3": "value3"},
            )
        ],
    )

    criteria = EvaluationCriteria(acceptable_outcomes=[outcome_a, outcome_b, outcome_c])

    task = Task(
        id="multi_outcome_test",
        user_scenario=UserScenario(instructions="Test multi-outcome evaluation"),
        evaluation_criteria=criteria,
    )

    return task


@pytest.fixture
def legacy_task():
    """Create a legacy task without acceptable_outcomes (binary pass/fail)."""
    criteria = EvaluationCriteria(
        actions=[
            Action(
                action_id="legacy_action",
                name="legacy_action",
                arguments={"arg": "value"},
            )
        ],
    )

    task = Task(
        id="legacy_test",
        user_scenario=UserScenario(instructions="Test legacy evaluation"),
        evaluation_criteria=criteria,
    )

    return task


def create_simulation(tool_calls: list[ToolCall]) -> SimulationRun:
    """Helper to create a simulation with given tool calls."""
    return SimulationRun(
        id="sim_test",
        task_id="test_task",
        start_time="2025-01-01T00:00:00",
        end_time="2025-01-01T00:00:01",
        duration=1.0,
        messages=[
            AssistantMessage(
                role="assistant",
                content="test",
                tool_calls=tool_calls,
            )
        ],
        termination_reason=TerminationReason.USER_STOP,
    )


def test_multi_outcome_highest_reward(multi_outcome_task):
    """Test that evaluation returns highest reward when matched."""
    simulation = create_simulation(
        [ToolCall(name="perfect_action", arguments={"arg1": "value1"})]
    )

    result = evaluate_simulation(
        simulation=simulation,
        task=multi_outcome_task,
        evaluation_type=EvaluationType.ACTION,
        solo_mode=False,
        domain="airline",
    )

    assert result.reward == 1.0
    assert result.info["matched_outcome_id"] == "test_outcome_A"
    assert "Perfect match" in result.info["matched_outcome_description"]


def test_multi_outcome_medium_reward(multi_outcome_task):
    """Test that evaluation returns medium reward when matched."""
    simulation = create_simulation(
        [ToolCall(name="good_action", arguments={"arg2": "value2"})]
    )

    result = evaluate_simulation(
        simulation=simulation,
        task=multi_outcome_task,
        evaluation_type=EvaluationType.ACTION,
        solo_mode=False,
        domain="airline",
    )

    assert result.reward == 0.7
    assert result.info["matched_outcome_id"] == "test_outcome_B"
    assert "Good match" in result.info["matched_outcome_description"]


def test_multi_outcome_lowest_reward(multi_outcome_task):
    """Test that evaluation returns lowest reward when matched."""
    simulation = create_simulation(
        [ToolCall(name="acceptable_action", arguments={"arg3": "value3"})]
    )

    result = evaluate_simulation(
        simulation=simulation,
        task=multi_outcome_task,
        evaluation_type=EvaluationType.ACTION,
        solo_mode=False,
        domain="airline",
    )

    assert result.reward == 0.5
    assert result.info["matched_outcome_id"] == "test_outcome_C"
    assert "Acceptable match" in result.info["matched_outcome_description"]


def test_multi_outcome_no_match(multi_outcome_task):
    """Test that evaluation returns 0 when no outcome matches."""
    simulation = create_simulation(
        [ToolCall(name="unmatched_action", arguments={"arg": "wrong"})]
    )

    result = evaluate_simulation(
        simulation=simulation,
        task=multi_outcome_task,
        evaluation_type=EvaluationType.ACTION,
        solo_mode=False,
        domain="airline",
    )

    assert result.reward == 0.0
    assert result.info["note"] == "No acceptable outcome matched"


def test_multi_outcome_chooses_max_reward(multi_outcome_task):
    """Test that when multiple outcomes match, the max reward is returned."""
    # Modify task to have overlapping actions that both match
    multi_outcome_task.evaluation_criteria.acceptable_outcomes[0].actions = [
        Action(
            action_id="shared_action",
            name="shared_action",
            arguments={"shared": "value"},
        )
    ]
    multi_outcome_task.evaluation_criteria.acceptable_outcomes[2].actions = [
        Action(
            action_id="shared_action_2",
            name="shared_action",
            arguments={"shared": "value"},
        )
    ]

    simulation = create_simulation(
        [ToolCall(name="shared_action", arguments={"shared": "value"})]
    )

    result = evaluate_simulation(
        simulation=simulation,
        task=multi_outcome_task,
        evaluation_type=EvaluationType.ACTION,
        solo_mode=False,
        domain="airline",
    )

    # Should return the highest reward (1.0) even though both match
    assert result.reward == 1.0
    assert result.info["matched_outcome_id"] == "test_outcome_A"


def test_legacy_task_backward_compatibility(legacy_task):
    """Test that legacy tasks (without acceptable_outcomes) still work with binary rewards."""
    # Matching action - should get reward 1.0
    simulation = create_simulation(
        [ToolCall(name="legacy_action", arguments={"arg": "value"})]
    )

    result = evaluate_simulation(
        simulation=simulation,
        task=legacy_task,
        evaluation_type=EvaluationType.ACTION,
        solo_mode=False,
        domain="airline",
    )

    assert result.reward == 1.0
    # Legacy tasks don't have matched_outcome_id in info
    assert result.info is None or "matched_outcome_id" not in result.info

    # Non-matching action - should get reward 0.0
    simulation_fail = create_simulation(
        [ToolCall(name="wrong_action", arguments={"arg": "wrong"})]
    )

    result_fail = evaluate_simulation(
        simulation=simulation_fail,
        task=legacy_task,
        evaluation_type=EvaluationType.ACTION,
        solo_mode=False,
        domain="airline",
    )

    assert result_fail.reward == 0.0


def test_premature_termination_returns_zero(multi_outcome_task):
    """Test that prematurely terminated simulations return 0 reward."""
    simulation = SimulationRun(
        id="sim_test",
        task_id="test_task",
        start_time="2025-01-01T00:00:00",
        end_time="2025-01-01T00:00:01",
        duration=1.0,
        messages=[],
        termination_reason=TerminationReason.MAX_STEPS,  # Premature termination
    )

    result = evaluate_simulation(
        simulation=simulation,
        task=multi_outcome_task,
        evaluation_type=EvaluationType.ACTION,
        solo_mode=False,
        domain="airline",
    )

    assert result.reward == 0.0
    assert "terminated prematurely" in result.info["note"].lower()
