"""Multi-agent architecture for Oura Health Agent.

This module implements a hierarchical multi-agent system where specialist agents
handle domain-specific queries and a supervisor agent orchestrates routing.

Agent Hierarchy:
    SupervisorAgent (Orchestrator)
        ├── SleepAnalystAgent - Sleep questions (stages, quality, trends)
        ├── FitnessCoachAgent - Activity, readiness, workouts, recovery
        ├── MemoryKeeperAgent - Goals, recall, baselines, insights
        └── DataAuditorAgent - Data quality, sync status, freshness
"""

from src.agents.base import AgentState, BaseAgent
from src.agents.data_auditor import DataAuditorAgent
from src.agents.fitness_coach import FitnessCoachAgent
from src.agents.memory_keeper import MemoryKeeperAgent
from src.agents.sleep_analyst import SleepAnalystAgent
from src.agents.supervisor import SupervisorAgent

__all__ = [
    "AgentState",
    "BaseAgent",
    "DataAuditorAgent",
    "FitnessCoachAgent",
    "MemoryKeeperAgent",
    "SleepAnalystAgent",
    "SupervisorAgent",
]
