# Copyright Sierra
"""
Airline relaxed domain environment.
Uses the same database and policy as airline, but with relaxed task evaluation criteria.
"""

import json
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.domains.airline.data_model import FlightDB
from tau2.domains.airline.tools import AirlineTools
from tau2.domains.airline.utils import AIRLINE_DB_PATH, AIRLINE_POLICY_PATH
from tau2.domains.airline_relaxed.utils import AIRLINE_RELAXED_TASK_SET_PATH
from tau2.environment.environment import Environment


def get_environment(
    db: Optional[FlightDB] = None,
    solo_mode: bool = False,
) -> Environment:
    """Get the airline-relaxed environment (same as airline)."""
    if solo_mode:
        raise ValueError("Airline relaxed domain does not support solo mode")
    if db is None:
        db = FlightDB.load(AIRLINE_DB_PATH)
    tools = AirlineTools(db)
    with open(AIRLINE_POLICY_PATH, "r") as fp:
        policy = fp.read()
    return Environment(
        domain_name="airline-relaxed",
        policy=policy,
        tools=tools,
    )


def get_tasks() -> list[Task]:
    """Get the airline-relaxed tasks with multi-outcome evaluation."""
    with open(AIRLINE_RELAXED_TASK_SET_PATH, "r") as fp:
        tasks = json.load(fp)
    return [Task.model_validate(task) for task in tasks]
