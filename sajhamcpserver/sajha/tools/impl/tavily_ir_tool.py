"""
Tavily-native Investor Relations tools — universal coverage for any public company.
Replaces scraper-based IR tools (hardcoded ~10 companies) with Tavily search/extract.
Three tools: IRFindPageTool, IRFindDocumentsTool, IRExtractContentTool
"""
import json
import re
from typing import Dict, Any, List, Optional
from sajha.tools.base_mcp_tool import BaseMCPTool
from .edgar_tavily_client import tavily_search, tavily_extract


DOCUMENT_TYPE_QUERIES = {
    'annual_report':           'annual report 10-K investor relations',
    'quarterly_report':        'quarterly report 10-Q earnings investor relations',
    'earnings_presentation':   'earnings presentation slides deck quarterly results',
    'investor_presentation':   'investor presentation day slides deck',
    'proxy_statement':         'proxy statement DEF14A annual meeting',
    'press_release':           'press release earnings results announcement',
    'esg_report':              'ESG sustainability report',
    'supplemental':            'financial supplement supplemental data package',
    'all':                     'investor relations annual quarterly earnings presentations',
}

IR_DOMAINS = [
    'sec.gov', 'ir.', 'investors.', 'investor.', 'annualreports.com',
    'prnewswire.com', 'businesswire.com', 'globe newswire.com',
]


class IRFindPageTool(BaseMCPTool):
    """Find the investor relations page URL for any public company via Tavily search."""

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'ir_find_page',
            'description': 'Find the investor relations (IR) page URL for any publicly traded company. Works for any ticker — not limited to pre-configured companies. Returns the IR page URL and company name.',
            'version': '2.0.0',
            'enabled': True
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {
                    'type': 'string',
                    'description': 'Stock ticker symbol (e.g., AAPL, BMO, JPM, TSLA)'
                },
                'company_name': {
                    'type': 'string',
                    'description': 'Optional company name to improve search accuracy'
                }
            },
            'required': ['ticker']
        }

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'},
                'company_name': {'type': 'string'},
                'ir_page_url': {'type': 'string'},
                'success': {'type': 'boolean'},
                'sources': {'type': 'array'}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments['ticker'].upper()
        company_name = arguments.get('company_name', '')

        name_part = company_name if company_name else ticker
        # Quoted ticker avoids ambiguity; "investor relations" anchors to IR pages
        query = f'"{name_part}" investor relations official IR page'

        result = tavily_search(
            query=query,
            include_domains=[],
            max_results=7,
            include_answer=False,
            search_depth='basic'
        )

        results = result.get('results', [])
        ir_url = ''
        found_company = company_name or ticker

        # Score results: prefer known IR URL patterns over generic SEC index pages
        best_score = -1
        for r in results:
            url = r.get('url', '')
            title = r.get('title', '')
            score = r.get('score', 0) * 10  # Tavily relevance score as base
            lower_url = url.lower()
            lower_title = title.lower()

            # IR subdomain/path patterns
            if re.search(r'https?://(ir|investors?)\.',  lower_url):
                score += 20
            # /ir at end or /ir/ in path, /investors/, /investor-relations
            if re.search(r'/ir(/|$)', lower_url) or '/investors/' in lower_url or '/investor-relations' in lower_url:
                score += 15
            # Ticker in the domain (e.g., apple.com/investor-relations)
            url_domain = lower_url.split('/')[2] if lower_url.count('/') >= 2 else ''
            if ticker.lower() in url_domain:
                score += 10
            # Prefer company website over news/aggregators/third-party
            if any(x in lower_url for x in ['sec.gov/cgi', 'finance.yahoo', 'bloomberg', 'reuters',
                                              'alphaspread.com', 'quartr.com', 'seekingalpha.com',
                                              'macrotrends.', 'wisesheets.']):
                score -= 15
            # Raw SEC Archives text index files are not IR pages
            if 'sec.gov/Archives' in url and url.endswith('.txt'):
                score -= 30
            # Specific document files (PDFs, exhibits) are NOT the IR home page
            if url.lower().endswith('.pdf') or '/dam/' in lower_url or '/documents/' in lower_url:
                score -= 20
            if 'investor' in lower_title or 'relations' in lower_title:
                score += 5

            if score > best_score:
                best_score = score
                ir_url = url
                if not company_name:
                    # Extract company name from title: prefer the part AFTER the separator
                    # (e.g. "Investor Relations | Apple Inc" → "Apple Inc")
                    for sep in [' | ', ' – ', ' - ']:
                        if sep in title:
                            parts = title.split(sep)
                            # Take last part as company name if it looks like a company
                            found_company = parts[-1].strip() if len(parts[-1]) > 3 else parts[0].strip()
                            break
                    else:
                        found_company = title.strip()

        return {
            'ticker': ticker,
            'company_name': found_company,
            'ir_page_url': ir_url,
            'success': bool(ir_url),
            'sources': [{'url': r.get('url', ''), 'title': r.get('title', '')} for r in results[:3]],
            '_source': ir_url or query
        }


class IRFindDocumentsTool(BaseMCPTool):
    """Find investor relations documents for any public company via Tavily search."""

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'ir_find_documents',
            'description': 'Find investor relations documents (annual reports, earnings presentations, proxy statements, ESG reports, supplementals) for any publicly traded company. Works universally — not limited to pre-configured companies.',
            'version': '2.0.0',
            'enabled': True
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {
                    'type': 'string',
                    'description': 'Stock ticker symbol (e.g., AAPL, BMO, JPM)'
                },
                'company_name': {
                    'type': 'string',
                    'description': 'Optional company name to improve search accuracy'
                },
                'document_type': {
                    'type': 'string',
                    'description': 'Type of document',
                    'enum': ['annual_report', 'quarterly_report', 'earnings_presentation',
                             'investor_presentation', 'proxy_statement', 'press_release',
                             'esg_report', 'supplemental', 'all'],
                    'default': 'all'
                },
                'year': {
                    'type': 'integer',
                    'description': 'Year for documents (e.g., 2024)',
                    'minimum': 2000,
                    'maximum': 2030
                },
                'limit': {
                    'type': 'integer',
                    'description': 'Maximum documents to return',
                    'default': 8,
                    'minimum': 1,
                    'maximum': 20
                }
            },
            'required': ['ticker']
        }

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'ticker': {'type': 'string'},
                'document_type': {'type': 'string'},
                'year': {'type': ['integer', 'null']},
                'count': {'type': 'integer'},
                'documents': {'type': 'array'},
                'success': {'type': 'boolean'}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        ticker = arguments['ticker'].upper()
        company_name = arguments.get('company_name', '')
        document_type = arguments.get('document_type', 'all')
        year = arguments.get('year')
        limit = arguments.get('limit', 8)

        name_part = company_name if company_name else ticker
        doc_query = DOCUMENT_TYPE_QUERIES.get(document_type, DOCUMENT_TYPE_QUERIES['all'])

        query_parts = [name_part, ticker, doc_query]
        if year:
            query_parts.append(str(year))
        query = ' '.join(query_parts)

        # Prefer IR/investor domains and PDF file types
        include_domains = ['ir.', 'investors.', 'investor.', 'sec.gov',
                           'prnewswire.com', 'businesswire.com', 'globenewswire.com']

        result = tavily_search(
            query=query,
            include_domains=include_domains,
            max_results=min(limit + 3, 15),
            include_answer=False,
            search_depth='advanced'
        )

        raw_results = result.get('results', [])
        documents = []
        for r in raw_results:
            url = r.get('url', '')
            title = r.get('title', '')
            published = r.get('published_date', '')
            # Determine document type from URL/title
            detected_type = _detect_doc_type(url, title, document_type)
            documents.append({
                'title': title,
                'url': url,
                'date': published,
                'type': detected_type,
                'score': r.get('score', 0)
            })

        # Sort by score descending
        documents.sort(key=lambda x: x.get('score', 0), reverse=True)
        documents = documents[:limit]
        # Remove internal score field
        for d in documents:
            d.pop('score', None)

        return {
            'ticker': ticker,
            'document_type': document_type,
            'year': year,
            'count': len(documents),
            'documents': documents,
            'success': len(documents) > 0,
            '_source': query
        }


class IRExtractContentTool(BaseMCPTool):
    """Extract content from an investor relations document URL using Tavily /extract."""

    def __init__(self, config: Dict = None):
        default_config = {
            'name': 'ir_extract_content',
            'description': 'Extract and return readable content from an investor relations document URL (annual report, earnings presentation, press release, etc.). Accepts any URL returned by ir_find_documents or ir_find_page. For large SEC Archives HTML filings (sec.gov/Archives), automatically uses direct streaming to handle files up to 15 MB.',
            'version': '2.0.0',
            'enabled': True
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'url': {
                    'type': 'string',
                    'description': 'URL of the IR document to extract content from'
                },
                'query': {
                    'type': 'string',
                    'description': 'Optional: focus the extracted content on this topic (e.g., "revenue guidance", "capital allocation", "risk factors")'
                },
                'section': {
                    'type': 'string',
                    'description': 'For SEC 10-K/10-Q filings: specific section to extract',
                    'enum': ['item 1', 'item 1a', 'item 7', 'item 7a', 'item 8', 'item 9a'],
                }
            },
            'required': ['url']
        }

    def get_output_schema(self) -> Dict:
        return {
            'type': 'object',
            'properties': {
                'url': {'type': 'string'},
                'content': {'type': 'string'},
                'content_length': {'type': 'integer'},
                'extraction_method': {'type': 'string'},
                'success': {'type': 'boolean'}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict:
        url = arguments['url']
        query = arguments.get('query', '')
        section = arguments.get('section', '')

        content = ''
        method = ''

        # For large SEC Archives HTML, use direct streaming
        if 'sec.gov/Archives' in url and url.lower().endswith(('.htm', '.html', '')):
            section_marker = section if section else 'item 7'
            try:
                from .edgar_tavily_client import stream_sec_section
                content = stream_sec_section(url, section_marker, content_kb=120)
                if content and len(content.strip()) > 200:
                    method = 'stream_sec_section'
            except Exception:
                content = ''

        # Tavily /extract for all other URLs (and as fallback)
        if not content:
            try:
                results = tavily_extract([url], query=query if query else None)
                if results:
                    raw = results[0].get('raw_content', '')
                    if raw and len(raw.strip()) > 200:
                        content = raw
                        method = 'tavily_extract'
            except Exception:
                pass

        return {
            'url': url,
            'content': content[:50000] if content else '',
            'content_length': len(content),
            'extraction_method': method,
            'success': bool(content and len(content.strip()) > 200),
            '_source': url
        }


def _detect_doc_type(url: str, title: str, requested_type: str) -> str:
    """Detect document type from URL and title."""
    if requested_type != 'all':
        return requested_type
    lower = (url + ' ' + title).lower()
    if any(x in lower for x in ['annual report', '10-k', 'annual-report']):
        return 'annual_report'
    if any(x in lower for x in ['10-q', 'quarterly report', 'q1', 'q2', 'q3', 'q4']):
        return 'quarterly_report'
    if any(x in lower for x in ['earnings presentation', 'earnings deck', 'earnings slides']):
        return 'earnings_presentation'
    if any(x in lower for x in ['investor presentation', 'investor day', 'investor-day']):
        return 'investor_presentation'
    if any(x in lower for x in ['proxy', 'def14a']):
        return 'proxy_statement'
    if any(x in lower for x in ['press release', 'news release']):
        return 'press_release'
    if any(x in lower for x in ['esg', 'sustainability', 'corporate responsibility']):
        return 'esg_report'
    if any(x in lower for x in ['supplement', 'financial data']):
        return 'supplemental'
    return 'document'


TAVILY_IR_TOOLS = {
    'ir_find_page': IRFindPageTool,
    'ir_find_documents': IRFindDocumentsTool,
    'ir_extract_content': IRExtractContentTool,
}
