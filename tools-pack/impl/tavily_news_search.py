"""tavily_news_search — Tavily news search wrapper. Compliant with upstream BaseMCPTool."""
from tools_pack_impl._tavily_search_base import _TavilySearchBase


class TavilyNewsSearch(_TavilySearchBase):
    _TOPIC = "news"
