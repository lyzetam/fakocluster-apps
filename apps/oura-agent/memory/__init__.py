"""Memory systems for Oura Health Agent.

Provides three types of memory:
1. Working Memory - Conversation state within a session (LangGraph checkpointer)
2. Episodic Memory - Past conversations searchable by semantic similarity (pgvector)
3. Long-Term Memory - User goals, baselines, and preferences (PostgreSQL)
"""

from memory.embeddings import EmbeddingService, get_embedding_service
from memory.episodic import EpisodicMemory, EpisodicMemoryEntry
from memory.long_term import HealthBaseline, HealthGoal, LongTermMemory
from memory.working import WorkingMemory, create_thread_id, get_working_memory

__all__ = [
    # Embeddings
    "EmbeddingService",
    "get_embedding_service",
    # Episodic memory
    "EpisodicMemory",
    "EpisodicMemoryEntry",
    # Long-term memory
    "LongTermMemory",
    "HealthGoal",
    "HealthBaseline",
    # Working memory
    "WorkingMemory",
    "create_thread_id",
    "get_working_memory",
]
