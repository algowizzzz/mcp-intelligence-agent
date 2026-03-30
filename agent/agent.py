from dotenv import load_dotenv
load_dotenv()

from langchain.agents import create_agent
from langchain.agents.factory import AgentMiddleware
from langgraph.checkpoint.memory import MemorySaver
from .tools import AGENT_TOOLS
from .prompt import SYSTEM_PROMPT
from .llm_factory import create_llm
from .summariser import SummarisationMiddleware

_MAX_HISTORY_CHARS = 200_000  # ~50k tokens — leaves room for tools + response within 200k context

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
            # Find the first safe cut point: an AI message with no tool_use blocks.
            # Cutting after such a message avoids orphaned tool_result blocks.
            cut_at = None
            for i, msg in enumerate(messages[:-2]):  # leave at least 2 messages
                msg_type = getattr(msg, 'type', '')
                if msg_type == 'ai' and not self._has_tool_use(msg):
                    cut_at = i + 1  # safe to discard everything before this index
                    break
            if cut_at:
                removed = messages[:cut_at]
                del messages[:cut_at]
                total -= sum(len(str(getattr(m, 'content', ''))) for m in removed)
            else:
                # No safe boundary found — remove oldest single message as fallback
                removed = messages.pop(0)
                total -= len(str(getattr(removed, 'content', '')))
        return messages

    def wrap_model_call(self, request, handler):
        trimmed = self._trim(list(request.messages))
        return handler(request.override(messages=trimmed))

    async def awrap_model_call(self, request, handler):
        trimmed = self._trim(list(request.messages))
        return await handler(request.override(messages=trimmed))


llm = create_llm()
checkpointer = MemorySaver()

agent = create_agent(
    model=llm,
    tools=AGENT_TOOLS,
    checkpointer=checkpointer,
    system_prompt=SYSTEM_PROMPT,
    middleware=[SummarisationMiddleware(), MessageTrimmer()],
)
