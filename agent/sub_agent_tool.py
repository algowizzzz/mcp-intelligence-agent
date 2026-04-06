"""sub_agent_tool.py — `task()` LangChain tool for multi-agent workers (REQ-13).

Injects a `task` tool into the lead agent that spawns focused sub-agents,
polls their progress, and streams task lifecycle events back to the SSE
response via an asyncio.Queue held in a ContextVar.

SSE Writer contract
-------------------
agent_server.py must set the _sse_writer_ctx ContextVar before calling
agent.astream_events().  The value must be a callable that accepts a dict
and puts it into the SSE stream.  A convenience function `get_stream_writer()`
is provided here for agent_server to import and use.

Example setup in agent_server.py stream() function:

    from agent.sub_agent_tool import set_stream_writer
    # inside the stream() async generator, before astream_events:
    queue = asyncio.Queue()
    token = set_stream_writer(queue.put_nowait)
    try:
        async for event in agent_instance.astream_events(...):
            # drain queue before yielding each event
            while not queue.empty():
                sse_evt = queue.get_nowait()
                yield f"data: {json.dumps(sse_evt)}\\n\\n"
            ...
    finally:
        _sse_writer_ctx.reset(token)
"""

from __future__ import annotations

import asyncio
import json
import uuid
from contextvars import ContextVar
from fnmatch import fnmatch
from typing import Annotated, Callable, Optional

from langchain_core.tools import tool
try:
    from langgraph.prebuilt import InjectedToolCallId
except ImportError:
    from langchain_core.tools import InjectedToolCallId

from agent.sub_agent_executor import SubAgentExecutor

# ── SSE writer ContextVar ──────────────────────────────────────────────────────
# Holds a callable(dict) → None that forwards task lifecycle events to the
# parent request's SSE stream.  Defaults to a no-op so sub-agent tools remain
# safe even if the writer was never set (e.g. in unit tests).

_sse_writer_ctx: ContextVar[Callable[[dict], None]] = ContextVar(
    "sse_writer_ctx", default=lambda evt: None
)


def set_stream_writer(writer: Callable[[dict], None]):
    """Set the SSE writer for the current async task context.

    Returns the ContextVar token so the caller can reset it in a finally block.

    Parameters
    ----------
    writer : callable(dict) -> None
        Typically ``queue.put_nowait`` where queue is an asyncio.Queue drained
        by the SSE generator in agent_server.py.
    """
    return _sse_writer_ctx.set(writer)


def get_stream_writer() -> Callable[[dict], None]:
    """Return the SSE writer callable bound to the current async task context."""
    return _sse_writer_ctx.get()


# ── task() tool factory ────────────────────────────────────────────────────────

def create_task_tool(
    parent_tools: list,
    parent_worker_ctx: dict,
    llm,
    create_agent_fn,
):
    """Return a configured `task` LangChain tool for use in a lead agent.

    Parameters
    ----------
    parent_tools : list
        Full tool list available to the lead agent — sub-agents receive a
        filtered subset.
    parent_worker_ctx : dict
        Worker context dict from _worker_ctx (worker_id, paths, etc.).
    llm :
        LLM instance shared with the lead agent.
    create_agent_fn : callable
        Typically ``create_agent_for_worker`` from agent.agent.
    """

    # Build a name → tool mapping once at factory time.
    _tool_index: dict = {t.name: t for t in parent_tools}

    @tool
    async def task(
        description: str,
        prompt: str,
        tool_call_id: Annotated[str, InjectedToolCallId],
        tools: Optional[list[str]] = None,
        max_turns: int = 20,
        timeout_seconds: int = 120,
        max_result_chars: int = 8000,
    ) -> str:
        """Spawn a specialised sub-agent to handle a focused sub-task in parallel.

        Use this tool to delegate well-scoped work to a sub-agent while the
        lead agent continues orchestrating.  Results are returned as a text
        summary once the sub-agent completes.

        Parameters
        ----------
        description : str
            3-5 word label shown in the UI progress card (e.g. "Fetch VaR data").
        prompt : str
            Detailed instruction for the sub-agent.  Be specific — the sub-agent
            has no conversation history beyond this prompt.
        tools : list[str] | None
            Optional glob patterns to filter tools available to the sub-agent
            (e.g. ["iris_*", "edgar_*"]).  None means all parent tools.
        max_turns : int
            Maximum reasoning turns for the sub-agent (default 20).
        timeout_seconds : int
            Wall-clock timeout before the sub-agent is aborted (default 120s).
        max_result_chars : int
            Maximum characters of sub-agent output returned to the lead agent
            (default 8000 ≈ 2k tokens).
        """
        # 1. Filter tools by glob patterns if provided.
        if tools:
            filtered_names = {
                name
                for name in _tool_index
                if any(fnmatch(name, pat) for pat in tools)
            }
            sub_tools = [t for t in parent_tools if t.name in filtered_names]
        else:
            sub_tools = list(parent_tools)

        # 2. Remove task() itself to prevent infinite recursion.
        sub_tools = [t for t in sub_tools if t.name != "task"]

        # 3. Generate a short unique task ID.
        task_id = "task-" + uuid.uuid4().hex[:8]

        # 4. Create the executor.
        executor = SubAgentExecutor(
            prompt=prompt,
            tools=sub_tools,
            parent_worker_ctx=parent_worker_ctx,
            llm=llm,
            create_agent_fn=create_agent_fn,
            max_result_chars=max_result_chars,
            timeout_seconds=timeout_seconds,
        )

        # 5. Fire off the sub-agent (non-blocking).
        executor.execute_async(task_id)

        # 6. Get the SSE writer for this request context.
        writer = get_stream_writer()

        # 7. Emit task_started.
        writer({"type": "task_started", "task_id": task_id, "description": description})

        # 8. Poll loop — check every 5 seconds for new messages or terminal status.
        _POLL_INTERVAL = 5.0

        while True:
            await asyncio.sleep(_POLL_INTERVAL)

            # Drain any new messages and emit task_running events.
            new_messages = SubAgentExecutor.poll_messages(task_id)
            for msg in new_messages:
                writer(
                    {
                        "type": "task_running",
                        "task_id": task_id,
                        "name": description,
                        "message": msg,
                    }
                )

            status_info = SubAgentExecutor.get_status(task_id)
            status = status_info.get("status", "not_found")

            if status == "completed":
                writer(
                    {
                        "type": "task_completed",
                        "task_id": task_id,
                        "name": description,
                    }
                )
                return status_info.get("result") or ""

            elif status == "failed":
                error_msg = status_info.get("error", "Sub-agent failed with unknown error")
                writer(
                    {
                        "type": "task_failed",
                        "task_id": task_id,
                        "error": error_msg,
                    }
                )
                return f"[Sub-agent task '{description}' failed: {error_msg}]"

            elif status == "timed_out":
                writer(
                    {
                        "type": "task_timed_out",
                        "task_id": task_id,
                        "error": "timeout",
                    }
                )
                return (
                    f"[Sub-agent task '{description}' timed out after "
                    f"{timeout_seconds}s — no result available]"
                )

            elif status == "not_found":
                # Registry entry disappeared — treat as failure.
                writer(
                    {
                        "type": "task_failed",
                        "task_id": task_id,
                        "error": "Task registry entry not found",
                    }
                )
                return f"[Sub-agent task '{description}' registry entry not found]"

            # status == "running" — keep polling.

    return task
