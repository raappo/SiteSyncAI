"""
SiteSync AI — Time Agent (LangChain Conversational Interface)

A guided LangChain ConversationChain that acts as a "field Time Agent."
Site supervisors describe their work in natural language; the agent
probes for missing details (discipline, location, progress%, date)
before triggering the extraction pipeline.
"""
from __future__ import annotations

from typing import Optional

from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
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
READY_TO_EXTRACT: Piping | Tank Farm Area | Erect and weld spools on 6-inch hot oil line | 32% | 2024-02-14

Current conversation context:"""


def build_time_agent_chain(
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> ConversationChain:
    """Build a LangChain ConversationChain for the Time Agent."""

    # Use settings.active_models priority order if not explicitly specified
    if model is None and settings.active_models:
        _base_url, _api_key, _model = settings.active_models[0]
    else:
        _model = model or settings.nvidia_default_model
        _base_url = base_url or settings.nvidia_base_url
        _api_key = api_key or settings.nvidia_api_key

    llm = ChatOpenAI(
        model=_model,
        base_url=base_url or _base_url,
        api_key=api_key or _api_key,
        temperature=0.2,
        max_tokens=500,
        timeout=30,
    )

    memory = ConversationBufferMemory(return_messages=True, memory_key="history")

    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(_TIME_AGENT_SYSTEM),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{input}"),
    ])

    chain = ConversationChain(
        llm=llm,
        memory=memory,
        prompt=prompt,
        verbose=False,
    )
    return chain


def parse_ready_signal(agent_response: str) -> Optional[str]:
    """Extract the summary from READY_TO_EXTRACT: <summary>."""
    if "READY_TO_EXTRACT:" in agent_response:
        return agent_response.split("READY_TO_EXTRACT:", 1)[1].strip()
    return None
