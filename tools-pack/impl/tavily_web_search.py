"""tavily_web_search — Tavily general search wrapper. Compliant with upstream BaseMCPTool."""
from tools_pack_impl._tavily_search_base import _TavilySearchBase


class TavilyWebSearch(_TavilySearchBase):
    _TOPIC = "general"
