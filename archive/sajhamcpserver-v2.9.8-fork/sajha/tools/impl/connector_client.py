"""
Client classes for connector platform APIs.
MSGraphClient: Microsoft Graph API (Teams, SharePoint, Power BI, Outlook)
AtlassianClient: Confluence and Jira REST APIs
"""
import requests
import time
from typing import Optional


class MSGraphClient:
    """OAuth2 client_credentials flow for Microsoft Graph."""

    GRAPH_BASE = 'https://graph.microsoft.com/v1.0'
    POWERBI_BASE = 'https://api.powerbi.com/v1.0/myorg'
    TOKEN_URL = 'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'

    def __init__(self, tenant_id: str, client_id: str, client_secret: str, connector_id: str = 'microsoft'):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.connector_id = connector_id
        self._token: Optional[str] = None
        self._token_expires: float = 0.0

    def _get_token(self, scope: str = 'https://graph.microsoft.com/.default') -> str:
        """Fetch or return cached access token."""
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        url = self.TOKEN_URL.format(tenant_id=self.tenant_id)
        resp = requests.post(url, data={
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': scope,
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        self._token = data['access_token']
        self._token_expires = time.time() + data.get('expires_in', 3600)
        return self._token

    def get(self, path: str, base: str = 'graph', **kwargs) -> dict:
        """GET request to Microsoft API."""
        base_url = self.POWERBI_BASE if base == 'powerbi' else self.GRAPH_BASE
        scope = 'https://analysis.windows.net/powerbi/api/.default' if base == 'powerbi' else 'https://graph.microsoft.com/.default'
        token = self._get_token(scope)
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        resp = requests.get(f'{base_url}/{path.lstrip("/")}', headers=headers, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, body: dict, base: str = 'graph', **kwargs) -> dict:
        """POST request to Microsoft API."""
        base_url = self.POWERBI_BASE if base == 'powerbi' else self.GRAPH_BASE
        scope = 'https://analysis.windows.net/powerbi/api/.default' if base == 'powerbi' else 'https://graph.microsoft.com/.default'
        token = self._get_token(scope)
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        resp = requests.post(f'{base_url}/{path.lstrip("/")}', headers=headers, json=body, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def put(self, path: str, data: bytes, content_type: str = 'application/octet-stream', base: str = 'graph', **kwargs) -> dict:
        """PUT request to Microsoft API (used for file uploads)."""
        base_url = self.POWERBI_BASE if base == 'powerbi' else self.GRAPH_BASE
        scope = 'https://analysis.windows.net/powerbi/api/.default' if base == 'powerbi' else 'https://graph.microsoft.com/.default'
        token = self._get_token(scope)
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': content_type}
        resp = requests.put(f'{base_url}/{path.lstrip("/")}', headers=headers, data=data, timeout=60, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}


class AtlassianClient:
    """HTTP Basic Auth client for Confluence and Jira."""

    def __init__(self, email: str, api_token: str, base_url: str):
        self.auth = (email, api_token)
        self.base_url = base_url.rstrip('/')

    def get(self, path: str, **kwargs) -> dict:
        resp = requests.get(f'{self.base_url}/{path.lstrip("/")}',
                             auth=self.auth, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, body: dict, **kwargs) -> dict:
        resp = requests.post(f'{self.base_url}/{path.lstrip("/")}',
                              auth=self.auth, json=body, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def put(self, path: str, body: dict, **kwargs) -> dict:
        resp = requests.put(f'{self.base_url}/{path.lstrip("/")}',
                             auth=self.auth, json=body, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}
