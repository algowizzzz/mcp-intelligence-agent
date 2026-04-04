from dotenv import load_dotenv
load_dotenv()

import os

from langchain.agents import create_agent
from langchain.agents.factory import AgentMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver
from .tools import AGENT_TOOLS
from .prompt import SYSTEM_PROMPT
from .llm_factory import create_llm
from .summariser import SummarisationMiddleware

_MAX_HISTORY_CHARS = 800_000  # Hard fallback only — SummarisationMiddleware fires first at 180k tokens

_DB_PATH = os.getenv('CHECKPOINT_DB_PATH', './sajhamcpserver/data/checkpoints.db')

class MessageTrimmer(AgentMiddleware):
    """Trims old messages before each model call to stay under Claude's 200k token limit."""

    @property
    def name(self) -> str:
        return "message_trimmer"

    def _has_tool_use(self, msg) -> bool:
        content = getattr(msg, 'content', '')
        if isinstance(content, list):
            return any(isinstance(b, dict) and b.get('type') == 'tool_use' for b in content)
        return False

    def _trim(self, messages):
        total = sum(len(str(getattr(m, 'content', ''))) for m in messages)
        while total > _MAX_HISTORY_CHARS and len(messages) > 2:
            cut_at = None
            for i, msg in enumerate(messages[:-2]):
                msg_type = getattr(msg, 'type', '')
                if msg_type == 'ai' and not self._has_tool_use(msg):
                    cut_at = i + 1
                    break
            if cut_at:
                removed = messages[:cut_at]
                del messages[:cut_at]
                total -= sum(len(str(getattr(m, 'content', ''))) for m in removed)
            else:
                removed = messages.pop(0)
                total -= len(str(getattr(removed, 'content', '')))
        return messages

    def wrap_model_call(self, request, handler):
        trimmed = self._trim(list(request.messages))
        return handler(request.override(messages=trimmed))

    async def awrap_model_call(self, request, handler):
        trimmed = self._trim(list(request.messages))
        return await handler(request.override(messages=trimmed))


# Shared across all per-request agent instances — preserves thread history
llm = create_llm()
checkpointer = SqliteSaver.from_conn_string(_DB_PATH)


def create_agent_for_worker(system_prompt: str, tools: list = None):
    """Create an agent instance with a specific system prompt and tool allowlist.

    Uses the shared checkpointer so all thread state is preserved across
    requests regardless of which per-request agent instance is created.
    Each request gets a fresh agent with the worker's current prompt + tools.
    """
    return create_agent(
        model=llm,
        tools=tools if tools is not None else AGENT_TOOLS,
        checkpointer=checkpointer,
        system_prompt=system_prompt,
        middleware=[SummarisationMiddleware(), MessageTrimmer()],
    )


# Default agent — used only for backward compatibility with direct imports.
# agent_server.py creates per-request instances via create_agent_for_worker().
agent = create_agent_for_worker(SYSTEM_PROMPT)
