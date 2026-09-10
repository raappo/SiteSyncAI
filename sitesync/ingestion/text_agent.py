"""
SiteSync AI — Time Agent (LangChain LCEL Conversational Interface)

A guided conversational agent that helps field supervisors log activity progress.
Uses LangChain 0.3+ LCEL (no deprecated ConversationChain/ConversationBufferMemory).
Falls back to a simple rule-based mock if no LLM is configured.
"""
from __future__ import annotations

from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from rich.console import Console

from sitesync.config import settings

console = Console()

_TIME_AGENT_SYSTEM = """You are "SiteSync Time Agent" — an AI assistant deployed on an oil & gas infrastructure construction site.
Your ONLY job is to help field supervisors log their daily activity progress quickly and accurately.

Your conversation style:
- Be concise, professional, and friendly.
- Ask ONE clarifying question at a time if information is missing.
- Never ask for information already provided.
- Once you have: Discipline, Location, Activity Description, Progress %, and Date — say EXACTLY:
  "READY_TO_EXTRACT: <summary>" where <summary> is a single-line structured summary of the update.

Information you MUST collect before saying READY_TO_EXTRACT:
1. Engineering discipline (Civil / Piping / Electrical / Instrumentation / HSE)
2. Physical location on site
3. Activity description (what was done)
4. Progress percentage (what % complete)
5. Date (today or specific date)

If the supervisor has already given all 5, immediately output READY_TO_EXTRACT.

Example READY_TO_EXTRACT output:
READY_TO_EXTRACT: Piping | Tank Farm Area | Erect and weld spools on 6-inch hot oil line | 32% | 2026-09-10"""


class TimeAgent:
    """
    LCEL-based conversational Time Agent with in-memory message history.
    Falls back to a simple rule-based mock if no LLM is configured.
    """

    def __init__(self):
        self._history: list = []  # list of HumanMessage / AIMessage
        self._chain = self._build_chain()
        self._mock_mode = self._chain is None

    def _build_chain(self):
        """Build LangChain LCEL chain. Returns None if no LLM configured."""
        if not settings.active_models:
            console.print("[yellow]⚠ No LLM configured — Time Agent using mock mode.[/yellow]")
            return None

        base_url, api_key, model_id = settings.active_models[0]
        llm = ChatOpenAI(
            model=model_id,
            base_url=base_url,
            api_key=api_key,
            temperature=0.2,
            max_tokens=500,
            timeout=30,
            max_retries=2,
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", _TIME_AGENT_SYSTEM),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])

        return prompt | llm | StrOutputParser()

    def send(self, user_message: str) -> str:
        """Send a message and get the agent's response."""
        if self._mock_mode:
            return self._mock_response(user_message)

        try:
            response = self._chain.invoke({
                "input": user_message,
                "history": self._history,
            })
            # Update history
            self._history.append(HumanMessage(content=user_message))
            self._history.append(AIMessage(content=response))
            return response
        except Exception as e:
            console.print(f"[red]Time Agent LLM error: {e}[/red]")
            # Fall back to mock on error
            return self._mock_response(user_message)

    def _mock_response(self, user_message: str) -> str:
        """Simple mock response when no LLM is available."""
        import datetime
        today = datetime.date.today().isoformat()
        msg_lower = user_message.lower()

        # Check if the message already contains all key info
        has_discipline = any(d in msg_lower for d in ['civil', 'piping', 'electrical', 'instrumentation', 'hse'])
        has_percent = '%' in user_message or 'percent' in msg_lower or 'complete' in msg_lower
        has_location = any(w in msg_lower for w in ['zone', 'area', 'line', 'tank', 'section', 'grid', 'block', 'unit', 'bay'])

        if has_discipline and has_percent and has_location:
            # Extract discipline
            discipline = 'Civil'
            for d in ['Civil', 'Piping', 'Electrical', 'Instrumentation', 'HSE']:
                if d.lower() in msg_lower:
                    discipline = d
                    break
            return f"READY_TO_EXTRACT: {discipline} | Site Area | {user_message[:80]} | 50% | {today}"
        elif not has_discipline:
            return "Got it! Which engineering discipline is this for? (Civil / Piping / Electrical / Instrumentation / HSE)"
        elif not has_location:
            return "Understood. Which physical location or zone on site was this work done?"
        elif not has_percent:
            return "Thanks! What percentage complete is this activity?"
        else:
            return f"READY_TO_EXTRACT: Civil | Site Area | {user_message[:80]} | 50% | {today}"

    def reset(self):
        """Reset conversation history."""
        self._history = []


def parse_ready_signal(agent_response: str) -> Optional[str]:
    """Extract the summary from READY_TO_EXTRACT: <summary>."""
    if "READY_TO_EXTRACT:" in agent_response:
        return agent_response.split("READY_TO_EXTRACT:", 1)[1].strip()
    return None


# Keep backward compat: build_time_agent_chain returns a TimeAgent instance
def build_time_agent_chain(**kwargs) -> TimeAgent:
    """Create and return a TimeAgent instance (backward compatible)."""
    return TimeAgent()
