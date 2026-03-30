"""
SummarisationMiddleware — compresses conversation history when token budget is exceeded.
Fires in before_agent hook (once per user turn) using LangChain AgentMiddleware.
"""
import os
from langchain.agents.factory import AgentMiddleware
from langchain_core.messages import SystemMessage
from .prompt import SUMMARISE_PROMPT


_WARN_TOKENS = int(os.getenv('CONTEXT_WARN_TOKENS', '120000'))
_HARD_TOKENS = int(os.getenv('CONTEXT_HARD_TOKENS', '160000'))
_TAIL_KEEP = 10  # always keep the last N messages verbatim


def _estimate_tokens(messages) -> int:
    return sum(len(str(getattr(m, 'content', ''))) // 4 for m in messages)


class SummarisationMiddleware(AgentMiddleware):
    """
    When total conversation history exceeds CONTEXT_WARN_TOKENS, summarises
    older messages into a single SystemMessage and replaces them in state.
    The last _TAIL_KEEP messages are always kept verbatim so tool_call /
    tool_result pairs are never split.
    """

    def __init__(self):
        from .llm_factory import create_llm
        self._llm = create_llm()

    @property
    def name(self) -> str:
        return "summariser"

    def _should_summarise(self, messages) -> bool:
        return _estimate_tokens(messages) >= _WARN_TOKENS

    def _summarise(self, head):
        from langchain_core.messages import HumanMessage
        prompt_msgs = [
            SystemMessage(content=SUMMARISE_PROMPT),
            HumanMessage(content="\n\n".join(
                f"[{getattr(m, 'type', 'message').upper()}]: {getattr(m, 'content', '')}"
                for m in head
            ))
        ]
        response = self._llm.invoke(prompt_msgs)
        return getattr(response, 'content', str(response))

    def _do_summarise(self, state):
        messages = list(state.get('messages', []))
        if not self._should_summarise(messages):
            return None

        tail = messages[-_TAIL_KEEP:]
        head = messages[:-_TAIL_KEEP]
        if not head:
            return None

        summary_text = self._summarise(head)
        summary_msg = SystemMessage(content=f"## Prior Conversation Summary\n{summary_text}")
        return {'messages': [summary_msg] + tail}

    def before_agent(self, state, runtime):
        return self._do_summarise(state)

    async def abefore_agent(self, state, runtime):
        return self._do_summarise(state)
