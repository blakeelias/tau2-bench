# Copyright Sierra
"""
Airline tighter policy domain environment.
Uses the same database and tools as airline, but with a modified policy.
"""

import json
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.domains.airline.data_model import FlightDB
from tau2.domains.airline.tools import AirlineTools
from tau2.domains.airline_tighter_policy.utils import (
    AIRLINE_TIGHTER_POLICY_DB_PATH,
    AIRLINE_TIGHTER_POLICY_POLICY_PATH,
    AIRLINE_TIGHTER_POLICY_TASK_SET_PATH,
)
from tau2.environment.environment import Environment


def get_environment(
    db: Optional[FlightDB] = None,
    solo_mode: bool = False,
) -> Environment:
    """Get the airline-tighter-policy environment."""
    if solo_mode:
        raise ValueError("Airline tighter policy domain does not support solo mode")
    if db is None:
        db = FlightDB.load(AIRLINE_TIGHTER_POLICY_DB_PATH)
    tools = AirlineTools(db)
    with open(AIRLINE_TIGHTER_POLICY_POLICY_PATH, "r") as fp:
        policy = fp.read()
    return Environment(
        domain_name="airline_tighter_policy",
        policy=policy,
        tools=tools,
    )


def get_tasks() -> list[Task]:
    """Get the airline-tighter-policy tasks."""
    with open(AIRLINE_TIGHTER_POLICY_TASK_SET_PATH, "r") as fp:
        tasks = json.load(fp)
    return [Task.model_validate(task) for task in tasks]
