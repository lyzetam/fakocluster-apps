"""Supervisor Agent - Orchestrator for multi-agent health system.

The Supervisor routes queries to specialist agents based on intent:
- sleep_analyst: Sleep questions (stages, quality, trends)
- fitness_coach: Activity, readiness, workouts, recovery
- memory_keeper: Goals, recall, baselines, insights
- data_auditor: Data quality, sync status, freshness

For complex queries spanning multiple domains, it can call multiple
specialists and synthesize their responses.
"""

import asyncio
import logging
from typing import Any, Literal, Optional, Sequence, TypedDict, Annotated

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from memory.embeddings import EmbeddingService
from src.agents.data_auditor import DataAuditorAgent
from src.agents.fitness_coach import FitnessCoachAgent
from src.agents.memory_keeper import MemoryKeeperAgent
from src.agents.sleep_analyst import SleepAnalystAgent

logger = logging.getLogger(__name__)


class SupervisorState(TypedDict):
    """State for supervisor orchestration.

    Attributes:
        messages: Conversation history
        user_id: Discord user identifier
        thread_id: Conversation thread identifier
        next_agents: List of agents to call (for multi-agent queries)
        agent_outputs: Collected outputs from specialist agents
        final_response: Synthesized final response
        routing_decision: The routing decision made by the supervisor
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    thread_id: str
    next_agents: list[str]
    agent_outputs: dict[str, str]
    final_response: str
    routing_decision: str


# Routing prompt for the supervisor
ROUTING_PROMPT = """You are a Health Assistant Supervisor. Your job is to route user queries to the right specialist agent(s).

## Available Specialists

1. **sleep_analyst** - Sleep questions
   - How did I sleep? Sleep quality, duration, stages
   - Sleep trends, patterns, efficiency
   - Deep sleep, REM, light sleep analysis
   - Optimal bedtime recommendations

2. **fitness_coach** - Activity and fitness questions
   - Steps, calories, movement, activity
   - Exercise readiness, recovery status
   - Workouts, training, exercise
   - HRV, resting heart rate

3. **memory_keeper** - Goals and memory questions
   - Setting health goals ("I want to sleep 8 hours")
   - Recalling past advice ("What did you tell me about...")
   - Tracking progress toward goals
   - User baselines and history

4. **data_auditor** - Data quality questions
   - Is my ring syncing?
   - Why is my data old?
   - Data freshness, collection status
   - Troubleshooting sync issues

## Routing Rules

1. **Single Domain**: Route to one specialist
   - "How did I sleep?" → sleep_analyst
   - "Should I work out?" → fitness_coach
   - "Set a goal for 8 hours sleep" → memory_keeper
   - "Is my data syncing?" → data_auditor

2. **Multi-Domain**: Route to multiple specialists (comma-separated)
   - "How did I sleep and am I ready to exercise?" → sleep_analyst,fitness_coach
   - "What's my sleep goal progress?" → memory_keeper,sleep_analyst

3. **Greetings/General**: Handle directly
   - "Hello", "Hi", "Thanks" → supervisor

## Your Response

Respond with ONLY the agent name(s) to route to, separated by commas.
If it's a greeting or unclear question, respond with "supervisor".

Examples:
- "How was my sleep?" → sleep_analyst
- "Steps today?" → fitness_coach
- "Remember my HRV advice" → memory_keeper
- "Is my ring working?" → data_auditor
- "Sleep and activity trends" → sleep_analyst,fitness_coach
- "Hello!" → supervisor
"""

# Synthesis prompt for combining specialist outputs
SYNTHESIS_PROMPT = """You are a Health Assistant synthesizing responses from specialist agents.

Given the specialist responses below, create a unified, helpful response for the user.

## Guidelines
- Don't repeat information across specialists
- Highlight the most actionable insights
- If there are data quality warnings, mention them prominently
- Be conversational and supportive
- Keep the response concise but complete
- Use markdown formatting for readability

## Specialist Responses
{agent_outputs}

## Your Task
Create a cohesive response that combines these specialist insights into a helpful, unified answer."""


class SupervisorAgent:
    """Orchestrator agent that routes queries to specialists.

    The supervisor:
    1. Analyzes the user's query to determine intent
    2. Routes to one or more specialist agents
    3. Synthesizes responses from specialists
    4. Returns a unified response

    Attributes:
        llm: Claude model for routing and synthesis
        agents: Dict of specialist agent instances
        agent_graphs: Dict of compiled specialist graphs
        checkpointer: PostgreSQL checkpointer for conversation state
    """

    def __init__(
        self,
        connection_string: str,
        embedding_service: EmbeddingService,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        checkpointer: Optional[AsyncPostgresSaver] = None,
    ):
        """Initialize the supervisor.

        Args:
            connection_string: PostgreSQL connection string
            embedding_service: Service for generating embeddings
            api_key: Anthropic API key
            model: Claude model name
            checkpointer: Optional checkpointer for conversation persistence
        """
        self.connection_string = connection_string
        self.api_key = api_key
        self.model = model
        self.checkpointer = checkpointer

        # Initialize LLM for routing and synthesis
        self.llm = ChatAnthropic(
            api_key=api_key,
            model=model,
            temperature=0,
            max_tokens=4096,
        )

        # Initialize specialist agents
        self.agents = {
            "sleep_analyst": SleepAnalystAgent(
                connection_string=connection_string,
                api_key=api_key,
                model=model,
            ),
            "fitness_coach": FitnessCoachAgent(
                connection_string=connection_string,
                api_key=api_key,
                model=model,
            ),
            "memory_keeper": MemoryKeeperAgent(
                connection_string=connection_string,
                embedding_service=embedding_service,
                api_key=api_key,
                model=model,
            ),
            "data_auditor": DataAuditorAgent(
                connection_string=connection_string,
                api_key=api_key,
                model=model,
            ),
        }

        # Build the orchestration graph
        self._graph = None

    @property
    def graph(self) -> StateGraph:
        """Get the compiled orchestration graph."""
        if self._graph is None:
            self._graph = self._build_graph()
        return self._graph

    def _build_graph(self) -> StateGraph:
        """Build the supervisor orchestration graph."""
        graph = StateGraph(SupervisorState)

        # Node: Route the query
        async def route_query(state: SupervisorState) -> dict:
            """Determine which agent(s) should handle the query."""
            messages = [
                SystemMessage(content=ROUTING_PROMPT),
                state["messages"][-1],  # User's message
            ]

            response = await self.llm.ainvoke(messages)
            routing = response.content.strip().lower()

            # Parse routing decision
            if "," in routing:
                agents = [a.strip() for a in routing.split(",")]
            else:
                agents = [routing]

            # Validate agent names
            valid_agents = []
            for agent in agents:
                if agent in self.agents:
                    valid_agents.append(agent)
                elif agent == "supervisor":
                    valid_agents.append("supervisor")

            # Fallback to supervisor if no valid agents
            if not valid_agents:
                valid_agents = ["supervisor"]

            logger.info(f"Routing decision: {valid_agents}")

            return {
                "next_agents": valid_agents,
                "routing_decision": routing,
            }

        # Node: Call specialist agent(s)
        async def call_specialists(state: SupervisorState) -> dict:
            """Execute the specialist agent(s)."""
            agents_to_call = state.get("next_agents", [])
            outputs = {}

            if "supervisor" in agents_to_call and len(agents_to_call) == 1:
                # Handle directly with a friendly response
                response = await self.llm.ainvoke([
                    SystemMessage(
                        content="You are a friendly health assistant. Respond helpfully and warmly to greetings and general questions. Keep it brief."
                    ),
                    *state["messages"],
                ])
                outputs["supervisor"] = response.content
            else:
                # Call specialist agents
                # Remove 'supervisor' if present with other agents
                specialists = [a for a in agents_to_call if a != "supervisor"]

                # Run specialists in parallel
                async def call_agent(agent_name: str) -> tuple[str, str]:
                    """Call a single agent and return (name, response)."""
                    agent = self.agents[agent_name]
                    try:
                        result = await agent.invoke(
                            messages=list(state["messages"]),
                            user_id=state["user_id"],
                            thread_id=f"{state['thread_id']}:{agent_name}",
                        )
                        response = agent.extract_response(result)
                        return agent_name, response
                    except Exception as e:
                        logger.error(f"Error calling {agent_name}: {e}")
                        return agent_name, f"Error: {str(e)}"

                # Run all specialists in parallel
                tasks = [call_agent(name) for name in specialists]
                results = await asyncio.gather(*tasks)

                for name, response in results:
                    outputs[name] = response

            return {"agent_outputs": outputs}

        # Node: Synthesize responses
        async def synthesize_response(state: SupervisorState) -> dict:
            """Synthesize responses from specialists into a unified answer."""
            outputs = state.get("agent_outputs", {})

            if len(outputs) == 1:
                # Single agent - use directly
                final = list(outputs.values())[0]
            else:
                # Multiple agents - synthesize
                outputs_text = "\n\n".join(
                    f"### {name.replace('_', ' ').title()}\n{output}"
                    for name, output in outputs.items()
                )

                prompt = SYNTHESIS_PROMPT.format(agent_outputs=outputs_text)

                response = await self.llm.ainvoke([
                    SystemMessage(content=prompt),
                ])
                final = response.content

            return {
                "final_response": final,
                "messages": [AIMessage(content=final)],
            }

        # Add nodes to graph
        graph.add_node("route", route_query)
        graph.add_node("specialists", call_specialists)
        graph.add_node("synthesize", synthesize_response)

        # Add edges
        graph.add_edge(START, "route")
        graph.add_edge("route", "specialists")
        graph.add_edge("specialists", "synthesize")
        graph.add_edge("synthesize", END)

        # Compile with checkpointer if provided
        if self.checkpointer:
            return graph.compile(checkpointer=self.checkpointer)
        return graph.compile()

    async def process_message(
        self,
        message: str,
        user_id: str,
        channel_id: str,
        session_id: str,
    ) -> str:
        """Process a user message through the multi-agent system.

        Args:
            message: User's message
            user_id: Discord user ID
            channel_id: Discord channel ID
            session_id: Conversation session ID

        Returns:
            Final response text
        """
        thread_id = f"oura-health-{user_id}-{channel_id}"

        initial_state = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "thread_id": thread_id,
            "next_agents": [],
            "agent_outputs": {},
            "final_response": "",
            "routing_decision": "",
        }

        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = await self.graph.ainvoke(initial_state, config)
            return result["final_response"]

        except Exception as e:
            logger.error(f"Error in supervisor: {e}", exc_info=True)
            return (
                "I encountered an error processing your question. "
                "Please try again or rephrase your question."
            )

    def get_thread_config(self, user_id: str, channel_id: str) -> dict:
        """Get LangGraph config for a conversation thread.

        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID

        Returns:
            Config dict with thread_id
        """
        thread_id = f"oura-health-{user_id}-{channel_id}"
        return {"configurable": {"thread_id": thread_id}}

    async def invoke(
        self,
        messages: list[BaseMessage],
        user_id: str,
        thread_id: str,
        config: Optional[dict] = None,
    ) -> dict:
        """Direct invoke method for compatibility.

        Args:
            messages: Input messages
            user_id: User identifier
            thread_id: Thread identifier
            config: Optional config

        Returns:
            Result dict with final_response
        """
        initial_state = {
            "messages": messages,
            "user_id": user_id,
            "thread_id": thread_id,
            "next_agents": [],
            "agent_outputs": {},
            "final_response": "",
            "routing_decision": "",
        }

        run_config = config or {"configurable": {"thread_id": thread_id}}

        result = await self.graph.ainvoke(initial_state, run_config)
        return result
