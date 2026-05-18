"""tavily_research_search — Tavily research search wrapper. Compliant with upstream BaseMCPTool."""
from tools_pack_impl._tavily_search_base import _TavilySearchBase


class TavilyResearchSearch(_TavilySearchBase):
    _TOPIC = "research"
