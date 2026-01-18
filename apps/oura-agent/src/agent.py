"""LangGraph ReAct agent for Oura Health Agent.

Implements a planning, tool-using, reflecting agent that answers
health questions using Oura Ring data.
"""

import logging
from datetime import datetime
from typing import Annotated, Any, Literal, Optional, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)

# System prompt with guardrails
SYSTEM_PROMPT = """You are the Oura Health Agent, a friendly and knowledgeable health assistant that helps users understand their health data from their Oura Ring.

## Your Capabilities
You have access to comprehensive health data including:
- Sleep data (duration, quality, stages, efficiency)
- Activity data (steps, calories, workouts)
- Readiness and recovery metrics
- Heart rate and HRV data
- Stress and resilience metrics
- Advanced metrics (VO2 max, SpO2, respiratory rate)
- Meditation and breathing sessions

## Guidelines

### Be Helpful and Personalized
- Answer questions about the user's health data with specific numbers and insights
- Provide context (e.g., "Your sleep score of 85 is excellent")
- Offer actionable recommendations based on data
- Remember past conversations and user goals

### Be Clear and Concise
- Start with the most important information
- Use bullet points for readability
- Explain metrics in plain language
- Don't overwhelm with too much data at once

### Use Tools Appropriately
- Always use tools to get actual data - never make up numbers
- Choose the most specific tool for the question
- Use multiple tools if needed for comprehensive answers
- If data isn't available, say so clearly

### SAFETY GUARDRAILS - IMPORTANT

1. **No Medical Diagnoses**: Never diagnose medical conditions. If the user asks "Do I have sleep apnea?" say "I can show you breathing-related metrics, but diagnosing sleep apnea requires a clinical sleep study. Please consult your doctor."

2. **Healthcare Escalation**: For serious concerns, always recommend consulting a healthcare provider:
   - Persistent low SpO2 (<90%)
   - Significant heart rate abnormalities
   - Severe sleep disturbances
   - Signs of illness lasting multiple days

3. **Acknowledge Limitations**:
   - Oura Ring is a wellness device, not a medical device
   - Data shows trends and indicators, not definitive diagnoses
   - Personal baselines matter more than general standards

4. **Mental Health Sensitivity**: Be supportive if users express stress or health anxiety. Suggest professional support when appropriate.

5. **Data Privacy**: Only discuss the user's own health data.

### Response Format
- Use markdown formatting for better readability
- Include relevant emoji sparingly (📊 for data, 💤 for sleep, 🏃 for activity, ❤️ for heart, 🧘 for mindfulness)
- Structure longer responses with headers
- End actionable responses with clear next steps

### Example Interactions

**User**: "How did I sleep?"
**You**: [Use get_last_night_sleep tool, then respond with formatted summary]

**User**: "Am I ready to work out?"
**You**: [Use check_exercise_readiness tool, provide recommendation based on score]

**User**: "What's wrong with my sleep?"
**You**: [Use multiple sleep tools, identify patterns, provide recommendations - but don't diagnose]

Remember: You're a helpful health companion, not a doctor. Always ground responses in actual data from the tools."""


class AgentState(TypedDict):
    """State for the health agent graph."""

    messages: Annotated[list, add_messages]
    user_id: str
    channel_id: str
    session_id: str
    tool_results: Optional[list[dict]]
    needs_reflection: bool
    reflection_done: bool


def create_health_agent(
    model: ChatAnthropic,
    tools: list,
    checkpointer: Optional[Any] = None,
) -> StateGraph:
    """Create the LangGraph health agent.

    Args:
        model: Claude model instance
        tools: List of tool functions
        checkpointer: Optional checkpointer for state persistence

    Returns:
        Compiled StateGraph
    """
    # Bind tools to the model
    model_with_tools = model.bind_tools(tools)

    def should_continue(state: AgentState) -> Literal["tools", "reflect", "end"]:
        """Determine the next step in the graph."""
        messages = state["messages"]
        last_message = messages[-1]

        # If the LLM made tool calls, execute them
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        # If we haven't reflected yet, do so
        if not state.get("reflection_done", False) and state.get("needs_reflection", True):
            return "reflect"

        return "end"

    def call_model(state: AgentState) -> dict:
        """Call the LLM with the current state."""
        messages = state["messages"]

        # Add system message if not present
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

        response = model_with_tools.invoke(messages)

        return {
            "messages": [response],
            "needs_reflection": True,
            "reflection_done": False,
        }

    def reflect_on_response(state: AgentState) -> dict:
        """Evaluate response quality before delivery."""
        messages = state["messages"]
        last_message = messages[-1]

        # Only reflect on AI messages that aren't tool calls
        if not isinstance(last_message, AIMessage):
            return {"reflection_done": True}

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return {"reflection_done": True}

        response = last_message.content

        # Quality checks
        checks = {
            "has_content": bool(response and len(response) > 20),
            "not_too_long": len(response) < 4000,
            "has_data_reference": any(
                keyword in response.lower()
                for keyword in ["score", "hours", "minutes", "bpm", "ms", "steps", "%"]
            ),
        }

        all_passed = all(checks.values())

        if not all_passed:
            logger.warning(f"Response quality checks: {checks}")
            # In a more advanced implementation, we could ask the model to revise
            # For now, we just log and continue

        return {"reflection_done": True}

    # Create the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("reflect", reflect_on_response)

    # Set entry point
    graph.set_entry_point("agent")

    # Add conditional edges
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "reflect": "reflect",
            "end": END,
        },
    )

    # Tools always go back to agent
    graph.add_edge("tools", "agent")

    # Reflection goes to end
    graph.add_edge("reflect", END)

    # Compile with checkpointer if provided
    if checkpointer:
        return graph.compile(checkpointer=checkpointer)
    return graph.compile()


class HealthAgent:
    """High-level interface for the health agent."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        tools: list = None,
        checkpointer: Optional[Any] = None,
    ):
        """Initialize the health agent.

        Args:
            api_key: Anthropic API key
            model: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            tools: List of tools to use
            checkpointer: Optional checkpointer for state persistence
        """
        self.llm = ChatAnthropic(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.tools = tools or []
        self.checkpointer = checkpointer
        self.graph = create_health_agent(
            model=self.llm,
            tools=self.tools,
            checkpointer=self.checkpointer,
        )

    async def process_message(
        self,
        message: str,
        user_id: str,
        channel_id: str,
        session_id: str,
        config: Optional[dict] = None,
    ) -> str:
        """Process a user message and return the response.

        Args:
            message: User's message
            user_id: Discord user ID
            channel_id: Discord channel ID
            session_id: Conversation session ID
            config: Optional LangGraph config (includes thread_id)

        Returns:
            Agent's response text
        """
        # Build initial state
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "channel_id": channel_id,
            "session_id": session_id,
            "tool_results": None,
            "needs_reflection": True,
            "reflection_done": False,
        }

        # Use provided config or default
        run_config = config or {}

        try:
            # Run the graph
            result = await self.graph.ainvoke(initial_state, run_config)

            # Extract the final response
            messages = result.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    if not (hasattr(msg, "tool_calls") and msg.tool_calls):
                        return msg.content

            return "I apologize, but I couldn't generate a response. Please try again."

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return (
                "I encountered an error while processing your question. "
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
