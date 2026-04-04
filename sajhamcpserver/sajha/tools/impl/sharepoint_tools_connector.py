"""
SharePoint Online connector tools (6 tools).
Uses Microsoft Graph API for SharePoint operations.
Reads site_url from worker connector_scope.sharepoint_site_url if not provided.
NOTE: This file is separate from sharepoint_tool.py (existing file-based tool).
"""
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.tools.impl.connector_base import get_ms_client, get_worker_context


class SharePointListSitesTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'sharepoint_list_sites',
            'description': 'List SharePoint Online sites accessible to the connector.',
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
                'search': {'type': 'string', 'description': 'Optional search term to filter sites by name.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        search = params.get('search', '')
        try:
            client = get_ms_client(worker_ctx)
            path = f'sites?search={search}' if search else 'sites?search=*'
            result = client.get(path)
            sites = result.get('value', [])
            return {'sites': sites, 'count': len(sites)}
        except Exception as e:
            return {'error': str(e)}


class SharePointGetDocumentsTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'sharepoint_documents',
            'description': 'List documents in the root of a SharePoint site drive.',
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
                'site_id': {'type': 'string', 'description': 'SharePoint site ID. Defaults to worker-mapped site.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        site_id = params.get('site_id') or worker_ctx.get('sharepoint_site_id', '')
        if not site_id:
            return {'error': 'site_id required — provide as parameter or configure sharepoint_site_id in worker connector_scope'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'sites/{site_id}/drive/root/children')
            items = result.get('value', [])
            return {'documents': items, 'count': len(items)}
        except Exception as e:
            return {'error': str(e)}


class SharePointSearchDocumentsTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'sharepoint_search',
            'description': 'Search for documents or lists within a SharePoint site.',
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
                'site_id': {'type': 'string', 'description': 'SharePoint site ID. Defaults to worker-mapped site.'},
                'query': {'type': 'string', 'description': 'Search query string.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['query']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        site_id = params.get('site_id') or worker_ctx.get('sharepoint_site_id', '')
        query = params.get('query', '')
        if not site_id:
            return {'error': 'site_id required — provide as parameter or configure sharepoint_site_id in worker connector_scope'}
        if not query:
            return {'error': 'query is required'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'sites/{site_id}/lists?$filter=displayName ne \'\'&$top=50')
            lists = result.get('value', [])
            # Filter by query in name
            filtered = [l for l in lists if query.lower() in l.get('displayName', '').lower()]
            return {'lists': filtered, 'count': len(filtered), 'query': query}
        except Exception as e:
            return {'error': str(e)}


class SharePointGetListItemsTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'sharepoint_list_items',
            'description': 'Get items from a SharePoint list.',
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
                'site_id': {'type': 'string', 'description': 'SharePoint site ID. Defaults to worker-mapped site.'},
                'list_id': {'type': 'string', 'description': 'SharePoint list ID or name.'},
                'top': {'type': 'integer', 'description': 'Number of items to return (default 50).', 'default': 50},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['list_id']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        site_id = params.get('site_id') or worker_ctx.get('sharepoint_site_id', '')
        list_id = params.get('list_id', '')
        top = params.get('top', 50)
        if not site_id:
            return {'error': 'site_id required — provide as parameter or configure sharepoint_site_id in worker connector_scope'}
        if not list_id:
            return {'error': 'list_id is required'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'sites/{site_id}/lists/{list_id}/items?$top={top}&expand=fields')
            items = result.get('value', [])
            return {'items': items, 'count': len(items)}
        except Exception as e:
            return {'error': str(e)}


class SharePointDownloadFileTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'sharepoint_download_file',
            'description': 'Get download URL and metadata for a file in a SharePoint drive.',
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
                'site_id': {'type': 'string', 'description': 'SharePoint site ID. Defaults to worker-mapped site.'},
                'item_id': {'type': 'string', 'description': 'Drive item ID of the file.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['item_id']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        site_id = params.get('site_id') or worker_ctx.get('sharepoint_site_id', '')
        item_id = params.get('item_id', '')
        if not site_id:
            return {'error': 'site_id required — provide as parameter or configure sharepoint_site_id in worker connector_scope'}
        if not item_id:
            return {'error': 'item_id is required'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'sites/{site_id}/drive/items/{item_id}')
            return {
                'item_id': result.get('id'),
                'name': result.get('name'),
                'size': result.get('size'),
                'download_url': result.get('@microsoft.graph.downloadUrl'),
                'web_url': result.get('webUrl'),
                'last_modified': result.get('lastModifiedDateTime'),
            }
        except Exception as e:
            return {'error': str(e)}


class SharePointUploadFileTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'sharepoint_upload_file',
            'description': 'Upload a file to a SharePoint site drive root. Requires confirmation.',
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
                'site_id': {'type': 'string', 'description': 'SharePoint site ID. Defaults to worker-mapped site.'},
                'filename': {'type': 'string', 'description': 'Target filename (including extension).'},
                'content_base64': {'type': 'string', 'description': 'File content encoded as base64.'},
                'content_type': {'type': 'string', 'description': 'MIME type (e.g. application/pdf).', 'default': 'application/octet-stream'},
                'confirmation_required': {'type': 'boolean', 'const': True, 'description': 'Must be true to confirm write operation.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['filename', 'content_base64', 'confirmation_required']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        import base64
        worker_ctx = get_worker_context(params)
        site_id = params.get('site_id') or worker_ctx.get('sharepoint_site_id', '')
        filename = params.get('filename', '')
        content_b64 = params.get('content_base64', '')
        content_type = params.get('content_type', 'application/octet-stream')
        if not site_id:
            return {'error': 'site_id required — provide as parameter or configure sharepoint_site_id in worker connector_scope'}
        if not filename:
            return {'error': 'filename is required'}
        if not content_b64:
            return {'error': 'content_base64 is required'}
        try:
            client = get_ms_client(worker_ctx)
            file_data = base64.b64decode(content_b64)
            result = client.put(f'sites/{site_id}/drive/root:/{filename}:/content', file_data, content_type)
            return {
                'ok': True,
                'item_id': result.get('id'),
                'name': result.get('name'),
                'web_url': result.get('webUrl'),
                'size': result.get('size'),
            }
        except Exception as e:
            return {'error': str(e)}
