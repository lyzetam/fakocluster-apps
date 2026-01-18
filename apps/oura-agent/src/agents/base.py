"""Base agent class for specialist agents.

All specialist agents inherit from BaseAgent and implement their own
tools, system prompts, and domain expertise.
"""

import logging
from abc import ABC, abstractmethod
from typing import Annotated, Any, Literal, Sequence, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Base state shared by all agents.

    Attributes:
        messages: Conversation history with automatic appending
        user_id: Discord user identifier
        thread_id: Conversation thread identifier
        next_agent: For supervisor routing decisions
        agent_outputs: Collected outputs from specialist agents
        final_response: Synthesized final response
        tool_call_count: Track tool calls for loop detection
        correction_count: Track self-corrections for loop detection
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    thread_id: str
    next_agent: str
    agent_outputs: dict[str, str]
    final_response: str
    tool_call_count: int
    correction_count: int


class BaseAgent(ABC):
    """Abstract base class for all specialist agents.

    Each specialist agent:
    - Has a unique name and system prompt defining its expertise
    - Has access to specific tools for its domain
    - Builds its own LangGraph execution graph
    - Can reason, call tools, and self-correct

    Subclasses must implement:
        - name: Agent's unique identifier
        - system_prompt: Defines the agent's role and behavior
        - get_tools(): Returns the list of tools this agent can use
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0,
        max_tokens: int = 4096,
        api_key: str | None = None,
    ):
        """Initialize the agent.

        Args:
            model: Claude model to use
            temperature: Sampling temperature (0 for deterministic)
            max_tokens: Maximum tokens in response
            api_key: Anthropic API key (optional, uses env if not provided)
        """
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize LLM
        llm_kwargs = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if api_key:
            llm_kwargs["api_key"] = api_key

        self.llm = ChatAnthropic(**llm_kwargs)

        # Get tools and bind to LLM
        self.tools = self.get_tools()
        self.llm_with_tools = (
            self.llm.bind_tools(self.tools) if self.tools else self.llm
        )

        # Compile the graph
        self._graph = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent's unique name for routing and identification."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Agent's system prompt defining its role and expertise."""
        pass

    @abstractmethod
    def get_tools(self) -> list:
        """Return the list of tools this agent can use.

        Returns:
            List of LangChain tool functions
        """
        pass

    def build_graph(self) -> StateGraph:
        """Build this agent's LangGraph execution graph.

        The graph implements a ReAct pattern:
        1. Reason about the query
        2. Optionally call tools
        3. Return to reasoning with tool results
        4. Complete when no more tool calls needed

        Returns:
            Compiled StateGraph
        """
        graph = StateGraph(AgentState)

        # Agent reasoning node
        async def reason(state: AgentState) -> dict:
            """Main reasoning node - calls LLM with tools."""
            messages = [SystemMessage(content=self.system_prompt)] + list(
                state["messages"]
            )
            response = await self.llm_with_tools.ainvoke(messages)

            # Track tool calls for loop detection
            tool_count = state.get("tool_call_count", 0)
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_count += len(response.tool_calls)

            return {
                "messages": [response],
                "tool_call_count": tool_count,
            }

        # Add nodes
        graph.add_node("reason", reason)

        if self.tools:
            tool_node = ToolNode(self.tools)
            graph.add_node("tools", tool_node)

            # Entry point
            graph.add_edge(START, "reason")

            # Conditional routing after reasoning
            graph.add_conditional_edges(
                "reason",
                self._should_use_tools,
                {"tools": "tools", "end": END},
            )

            # Tools always return to reasoning
            graph.add_edge("tools", "reason")
        else:
            # No tools - simple flow
            graph.add_edge(START, "reason")
            graph.add_edge("reason", END)

        return graph.compile()

    def _should_use_tools(self, state: AgentState) -> Literal["tools", "end"]:
        """Determine if agent should call tools or finish.

        Args:
            state: Current agent state

        Returns:
            "tools" if tool calls pending, "end" otherwise
        """
        messages = state["messages"]
        last_message = messages[-1]

        # Check for tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            # Loop detection - prevent infinite tool calling
            if state.get("tool_call_count", 0) >= 10:
                logger.warning(
                    f"{self.name}: Max tool calls reached, forcing completion"
                )
                return "end"
            return "tools"

        return "end"

    @property
    def graph(self) -> StateGraph:
        """Get the compiled graph, building if necessary."""
        if self._graph is None:
            self._graph = self.build_graph()
        return self._graph

    async def invoke(
        self,
        messages: list[BaseMessage],
        user_id: str,
        thread_id: str | None = None,
        config: dict | None = None,
    ) -> dict:
        """Invoke this agent with a query.

        Args:
            messages: Input messages (usually just the user query)
            user_id: User identifier
            thread_id: Optional thread ID for conversation persistence
            config: Optional LangGraph config

        Returns:
            Final state dict with messages and response
        """
        initial_state = {
            "messages": messages,
            "user_id": user_id,
            "thread_id": thread_id or f"{self.name}:{user_id}",
            "next_agent": "",
            "agent_outputs": {},
            "final_response": "",
            "tool_call_count": 0,
            "correction_count": 0,
        }

        run_config = config or {}

        try:
            result = await self.graph.ainvoke(initial_state, run_config)
            return result
        except Exception as e:
            logger.error(f"{self.name}: Error during invocation: {e}", exc_info=True)
            raise

    def extract_response(self, result: dict) -> str:
        """Extract the final text response from agent result.

        Args:
            result: Result dict from invoke()

        Returns:
            Final response text
        """
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                if not (hasattr(msg, "tool_calls") and msg.tool_calls):
                    return msg.content

        return "I couldn't generate a response."

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, tools={len(self.tools)})"
