"""
Base helpers for all connector tools.
Provides credential resolution and client factory methods.
"""
from sajha.core.connectors_registry import ConnectorsRegistry

_registry = ConnectorsRegistry()


def get_ms_client(worker_context: dict = None):
    """Build an MSGraphClient from connector credentials + worker context."""
    from sajha.tools.impl.connector_client import MSGraphClient
    creds = _registry.get_credentials('microsoft_azure')
    if not creds:
        # Try worker context credentials
        if worker_context:
            creds = {
                'tenant_id': worker_context.get('azure_tenant_id', ''),
                'client_id': worker_context.get('azure_client_id', ''),
                'client_secret': worker_context.get('azure_client_secret', ''),
            }
    return MSGraphClient(
        tenant_id=creds.get('tenant_id', ''),
        client_id=creds.get('client_id', ''),
        client_secret=creds.get('client_secret', ''),
    )


def get_atlassian_client(base_url: str = None, worker_context: dict = None):
    """Build an AtlassianClient from connector credentials + worker context."""
    from sajha.tools.impl.connector_client import AtlassianClient
    creds = _registry.get_credentials('atlassian')
    if not creds and worker_context:
        creds = {
            'email': worker_context.get('atlassian_email', ''),
            'api_token': worker_context.get('atlassian_api_token', ''),
            'base_url': worker_context.get('atlassian_base_url', ''),
        }
    url = base_url or creds.get('confluence_url') or creds.get('base_url', '')
    return AtlassianClient(
        email=creds.get('email', ''),
        api_token=creds.get('api_token', ''),
        base_url=url,
    )


def get_worker_context(params: dict) -> dict:
    """Extract _worker_context from tool params."""
    return params.get('_worker_context', {})
