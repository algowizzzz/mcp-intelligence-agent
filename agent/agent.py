from dotenv import load_dotenv
load_dotenv()

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from .tools import AGENT_TOOLS
from .prompt import SYSTEM_PROMPT

llm = ChatAnthropic(
    model='claude-sonnet-4-20250514',
    temperature=0,
    streaming=True,
)

checkpointer = MemorySaver()

agent = create_agent(
    model=llm,
    tools=AGENT_TOOLS,
    checkpointer=checkpointer,
    system_prompt=SYSTEM_PROMPT,
)
