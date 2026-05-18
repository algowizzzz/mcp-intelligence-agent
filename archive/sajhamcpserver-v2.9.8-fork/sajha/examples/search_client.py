#!/usr/bin/env python3
"""
SAJHA MCP Server - Search Tools Client v2.3.0

Copyright © 2025-2030, All Rights Reserved
Ashutosh Sinha
Email: ajsinha@gmail.com

Example client for Tavily Search tools:
- tavily_web_search: Tavily web search
- tavily_news_search: Tavily news search
- tavily_research_search: Tavily research search
- tavily_domain_search: Tavily domain-specific search

Usage:
    export SAJHA_API_KEY="sja_your_key_here"
    python -m sajha.examples.search_client
"""

from base_client import SajhaClient, SajhaAPIError, pretty_print, run_example


class SearchClient(SajhaClient):
    """Client for Tavily Search tools."""

    # ============= Tavily Search =============
    def tavily_web_search(self,
                          query: str,
                          max_results: int = 10,
                          include_answer: bool = True) -> dict:
        """
        Perform Tavily web search with AI-powered results.

        Args:
            query: Search query
            max_results: Maximum results
            include_answer: Include AI-generated answer
        """
        return self.execute_tool('tavily_web_search', {
            'query': query,
            'max_results': max_results,
            'include_answer': include_answer
        })

    def tavily_news_search(self,
                           query: str,
                           max_results: int = 10,
                           days: int = 7) -> dict:
        """
        Search recent news with Tavily.

        Args:
            query: Search query
            max_results: Maximum results
            days: News from last N days
        """
        return self.execute_tool('tavily_news_search', {
            'query': query,
            'max_results': max_results,
            'days': days
        })

    def tavily_research_search(self,
                               query: str,
                               max_results: int = 10,
                               search_depth: str = 'advanced') -> dict:
        """
        Deep research search with Tavily.

        Args:
            query: Research query
            max_results: Maximum results
            search_depth: 'basic' or 'advanced'
        """
        return self.execute_tool('tavily_research_search', {
            'query': query,
            'max_results': max_results,
            'search_depth': search_depth
        })

    def tavily_domain_search(self,
                             query: str,
                             domains: list,
                             max_results: int = 10) -> dict:
        """
        Search within specific domains.

        Args:
            query: Search query
            domains: List of domains to search
            max_results: Maximum results
        """
        return self.execute_tool('tavily_domain_search', {
            'query': query,
            'domains': domains,
            'max_results': max_results
        })


@run_example
def example_tavily_web_search():
    """Example: Tavily web search"""
    client = SearchClient()

    print("\n Tavily Web Search: 'latest AI developments'")
    results = client.tavily_web_search(
        query="latest AI developments 2024",
        max_results=5,
        include_answer=True
    )
    pretty_print(results, "Tavily Search Results")


@run_example
def example_tavily_news():
    """Example: Tavily news search"""
    client = SearchClient()

    print("\n Tavily News Search: 'Federal Reserve interest rates'")
    results = client.tavily_news_search(
        query="Federal Reserve interest rates",
        max_results=5,
        days=7
    )
    pretty_print(results, "Recent News")


@run_example
def example_tavily_research():
    """Example: Tavily research search"""
    client = SearchClient()

    print("\n Tavily Research: 'quantum computing applications'")
    results = client.tavily_research_search(
        query="quantum computing real-world applications",
        max_results=5,
        search_depth='advanced'
    )
    pretty_print(results, "Research Results")


@run_example
def example_tavily_domain():
    """Example: Tavily domain-specific search"""
    client = SearchClient()

    print("\n Tavily Domain Search: 'GPT-4' on tech sites")
    results = client.tavily_domain_search(
        query="GPT-4 capabilities",
        domains=["techcrunch.com", "wired.com", "theverge.com"],
        max_results=5
    )
    pretty_print(results, "Tech News on GPT-4")


@run_example
def example_research_workflow():
    """Example: Complete research workflow"""
    client = SearchClient()

    topic = "Electric vehicles market trends"
    print(f"\n Research Workflow: {topic}")
    print("=" * 60)

    # Step 1: Web search
    print("\n1. General web search:")
    web = client.tavily_web_search(topic, max_results=3)
    if web.get('results'):
        for r in web['results'][:3]:
            print(f"   - {r.get('title', 'N/A')[:50]}")

    # Step 2: Recent news
    print("\n2. Recent news (7 days):")
    news = client.tavily_news_search(topic, max_results=3, days=7)
    if news.get('results'):
        for r in news['results'][:3]:
            print(f"   - {r.get('title', 'N/A')[:50]}")

    # Step 3: Deep research
    print("\n3. In-depth research:")
    research = client.tavily_research_search(topic, max_results=3)
    if research.get('answer'):
        print(f"   Summary: {research['answer'][:200]}...")


if __name__ == '__main__':
    print("=" * 60)
    print(" SAJHA MCP Server - Search Tools Examples v2.3.0")
    print("=" * 60)

    example_tavily_web_search()
    example_tavily_news()
    example_tavily_research()
    example_tavily_domain()
    example_research_workflow()
