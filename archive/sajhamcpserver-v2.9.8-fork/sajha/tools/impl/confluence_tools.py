"""
Confluence connector tools (5 tools).
Uses Atlassian Confluence REST API via AtlassianClient.
Reads space_key from worker connector_scope.confluence_space_key if not provided.
"""
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.tools.impl.connector_base import get_atlassian_client, get_worker_context


class ConfluenceListSpacesTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'confluence_list_spaces',
            'description': 'List all Confluence spaces accessible to the connector.',
            'version': '1.0.0',
            'enabled': True,
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self):
        return {
            'type': 'object',
            'properties': {
                'limit': {'type': 'integer', 'description': 'Maximum number of spaces to return (default 50).', 'default': 50},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        limit = params.get('limit', 50)
        confluence_url = worker_ctx.get('confluence_url', '')
        try:
            client = get_atlassian_client(base_url=confluence_url or None, worker_context=worker_ctx)
            result = client.get(f'wiki/rest/api/space?limit={limit}')
            spaces = result.get('results', [])
            return {'spaces': spaces, 'count': len(spaces)}
        except Exception as e:
            return {'error': str(e)}


class ConfluenceSearchPagesTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'confluence_search',
            'description': 'Search Confluence pages using CQL (Confluence Query Language).',
            'version': '1.0.0',
            'enabled': True,
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self):
        return {
            'type': 'object',
            'properties': {
                'query': {'type': 'string', 'description': 'CQL query or keyword to search pages. Example: "text ~ \'capital adequacy\'" or plain keywords.'},
                'space_key': {'type': 'string', 'description': 'Confluence space key to scope the search. Defaults to worker-mapped space.'},
                'limit': {'type': 'integer', 'description': 'Maximum number of results (default 25).', 'default': 25},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['query']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        query = params.get('query', '')
        space_key = params.get('space_key') or worker_ctx.get('confluence_space_key', '')
        limit = params.get('limit', 25)
        confluence_url = worker_ctx.get('confluence_url', '')
        if not query:
            return {'error': 'query is required'}
        try:
            client = get_atlassian_client(base_url=confluence_url or None, worker_context=worker_ctx)
            import urllib.parse
            cql = query if 'text ~' in query or 'space =' in query else f'text ~ "{query}"'
            if space_key and 'space =' not in cql:
                cql += f' AND space = "{space_key}"'
            encoded_cql = urllib.parse.quote(cql)
            result = client.get(f'wiki/rest/api/content/search?cql={encoded_cql}&limit={limit}')
            pages = result.get('results', [])
            return {'pages': pages, 'count': len(pages), 'query': query}
        except Exception as e:
            return {'error': str(e)}


class ConfluenceGetPageTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'confluence_get_page',
            'description': 'Get a specific Confluence page including its body content.',
            'version': '1.0.0',
            'enabled': True,
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self):
        return {
            'type': 'object',
            'properties': {
                'page_id': {'type': 'string', 'description': 'Confluence page ID.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['page_id']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        page_id = params.get('page_id', '')
        confluence_url = worker_ctx.get('confluence_url', '')
        if not page_id:
            return {'error': 'page_id is required'}
        try:
            client = get_atlassian_client(base_url=confluence_url or None, worker_context=worker_ctx)
            result = client.get(f'wiki/rest/api/content/{page_id}?expand=body.view,version,space')
            return {
                'page_id': result.get('id'),
                'title': result.get('title'),
                'space': result.get('space', {}).get('key'),
                'version': result.get('version', {}).get('number'),
                'body': result.get('body', {}).get('view', {}).get('value', ''),
                'web_url': result.get('_links', {}).get('webui', ''),
            }
        except Exception as e:
            return {'error': str(e)}


class ConfluenceListPagesTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'confluence_list_pages',
            'description': 'List pages in a Confluence space.',
            'version': '1.0.0',
            'enabled': True,
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self):
        return {
            'type': 'object',
            'properties': {
                'space_key': {'type': 'string', 'description': 'Confluence space key. Defaults to worker-mapped space.'},
                'limit': {'type': 'integer', 'description': 'Maximum pages to return (default 25).', 'default': 25},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        space_key = params.get('space_key') or worker_ctx.get('confluence_space_key', '')
        limit = params.get('limit', 25)
        confluence_url = worker_ctx.get('confluence_url', '')
        if not space_key:
            return {'error': 'space_key required — provide as parameter or configure confluence_space_key in worker connector_scope'}
        try:
            client = get_atlassian_client(base_url=confluence_url or None, worker_context=worker_ctx)
            result = client.get(f'wiki/rest/api/space/{space_key}/content/page?limit={limit}')
            pages = result.get('results', [])
            return {'pages': pages, 'count': len(pages), 'space_key': space_key}
        except Exception as e:
            return {'error': str(e)}


class ConfluenceCreatePageTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'confluence_create_page',
            'description': 'Create a new Confluence page in a space. Requires confirmation.',
            'version': '1.0.0',
            'enabled': True,
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

    def get_input_schema(self):
        return {
            'type': 'object',
            'properties': {
                'space_key': {'type': 'string', 'description': 'Confluence space key. Defaults to worker-mapped space.'},
                'title': {'type': 'string', 'description': 'Page title.'},
                'body': {'type': 'string', 'description': 'Page body content (HTML or plain text).'},
                'parent_id': {'type': 'string', 'description': 'Parent page ID (optional).'},
                'confirmation_required': {'type': 'boolean', 'const': True, 'description': 'Must be true to confirm write operation.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['title', 'body', 'confirmation_required']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        space_key = params.get('space_key') or worker_ctx.get('confluence_space_key', '')
        title = params.get('title', '')
        body = params.get('body', '')
        parent_id = params.get('parent_id', '')
        confluence_url = worker_ctx.get('confluence_url', '')
        if not space_key:
            return {'error': 'space_key required — provide as parameter or configure confluence_space_key in worker connector_scope'}
        if not title:
            return {'error': 'title is required'}
        if not body:
            return {'error': 'body is required'}
        try:
            client = get_atlassian_client(base_url=confluence_url or None, worker_context=worker_ctx)
            payload = {
                'type': 'page',
                'title': title,
                'space': {'key': space_key},
                'body': {
                    'storage': {
                        'value': body,
                        'representation': 'storage',
                    }
                },
            }
            if parent_id:
                payload['ancestors'] = [{'id': parent_id}]
            result = client.post('wiki/rest/api/content', payload)
            return {
                'ok': True,
                'page_id': result.get('id'),
                'title': result.get('title'),
                'web_url': result.get('_links', {}).get('webui', ''),
            }
        except Exception as e:
            return {'error': str(e)}
