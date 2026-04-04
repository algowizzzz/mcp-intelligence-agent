"""
Power BI / Microsoft Fabric connector tools (6 tools).
Uses Power BI REST API via MSGraphClient with powerbi base.
Reads workspace_id from worker connector_scope.powerbi_workspace_id if not provided.
"""
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.tools.impl.connector_base import get_ms_client, get_worker_context


class PowerBIListWorkspacesTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'powerbi_list_workspaces',
            'description': 'List all Power BI workspaces (groups) accessible to the connector.',
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
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        try:
            client = get_ms_client(worker_ctx)
            result = client.get('groups', base='powerbi')
            workspaces = result.get('value', [])
            return {'workspaces': workspaces, 'count': len(workspaces)}
        except Exception as e:
            return {'error': str(e)}


class PowerBIGetReportTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'powerbi_get_report',
            'description': 'Get metadata for a specific Power BI report.',
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
                'workspace_id': {'type': 'string', 'description': 'Power BI workspace ID. Defaults to worker-mapped workspace.'},
                'report_id': {'type': 'string', 'description': 'Power BI report ID.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['report_id']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        workspace_id = params.get('workspace_id') or worker_ctx.get('powerbi_workspace_id', '')
        report_id = params.get('report_id', '')
        if not workspace_id:
            return {'error': 'workspace_id required — provide as parameter or configure powerbi_workspace_id in worker connector_scope'}
        if not report_id:
            return {'error': 'report_id is required'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'groups/{workspace_id}/reports/{report_id}', base='powerbi')
            return {'report': result}
        except Exception as e:
            return {'error': str(e)}


class PowerBIListReportsTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'powerbi_list_reports',
            'description': 'List all Power BI reports in a workspace.',
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
                'workspace_id': {'type': 'string', 'description': 'Power BI workspace ID. Defaults to worker-mapped workspace.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        workspace_id = params.get('workspace_id') or worker_ctx.get('powerbi_workspace_id', '')
        if not workspace_id:
            return {'error': 'workspace_id required — provide as parameter or configure powerbi_workspace_id in worker connector_scope'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'groups/{workspace_id}/reports', base='powerbi')
            reports = result.get('value', [])
            return {'reports': reports, 'count': len(reports)}
        except Exception as e:
            return {'error': str(e)}


class PowerBIListDatasetsTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'powerbi_list_datasets',
            'description': 'List all Power BI datasets in a workspace.',
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
                'workspace_id': {'type': 'string', 'description': 'Power BI workspace ID. Defaults to worker-mapped workspace.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        workspace_id = params.get('workspace_id') or worker_ctx.get('powerbi_workspace_id', '')
        if not workspace_id:
            return {'error': 'workspace_id required — provide as parameter or configure powerbi_workspace_id in worker connector_scope'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'groups/{workspace_id}/datasets', base='powerbi')
            datasets = result.get('value', [])
            return {'datasets': datasets, 'count': len(datasets)}
        except Exception as e:
            return {'error': str(e)}


class PowerBIGetDatasetTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'powerbi_get_dataset',
            'description': 'Get metadata for a specific Power BI dataset.',
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
                'workspace_id': {'type': 'string', 'description': 'Power BI workspace ID. Defaults to worker-mapped workspace.'},
                'dataset_id': {'type': 'string', 'description': 'Power BI dataset ID.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['dataset_id']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        workspace_id = params.get('workspace_id') or worker_ctx.get('powerbi_workspace_id', '')
        dataset_id = params.get('dataset_id', '')
        if not workspace_id:
            return {'error': 'workspace_id required — provide as parameter or configure powerbi_workspace_id in worker connector_scope'}
        if not dataset_id:
            return {'error': 'dataset_id is required'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'groups/{workspace_id}/datasets/{dataset_id}', base='powerbi')
            return {'dataset': result}
        except Exception as e:
            return {'error': str(e)}


class PowerBIRefreshDatasetTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'powerbi_refresh_dataset',
            'description': 'Trigger a refresh for a Power BI dataset. Requires confirmation.',
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
                'workspace_id': {'type': 'string', 'description': 'Power BI workspace ID. Defaults to worker-mapped workspace.'},
                'dataset_id': {'type': 'string', 'description': 'Power BI dataset ID to refresh.'},
                'notify_option': {'type': 'string', 'enum': ['MailOnFailure', 'MailOnCompletion', 'NoNotification'], 'default': 'MailOnFailure'},
                'confirmation_required': {'type': 'boolean', 'const': True, 'description': 'Must be true to confirm write operation.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['dataset_id', 'confirmation_required']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        workspace_id = params.get('workspace_id') or worker_ctx.get('powerbi_workspace_id', '')
        dataset_id = params.get('dataset_id', '')
        notify = params.get('notify_option', 'MailOnFailure')
        if not workspace_id:
            return {'error': 'workspace_id required — provide as parameter or configure powerbi_workspace_id in worker connector_scope'}
        if not dataset_id:
            return {'error': 'dataset_id is required'}
        try:
            client = get_ms_client(worker_ctx)
            client.post(f'groups/{workspace_id}/datasets/{dataset_id}/refreshes',
                        {'notifyOption': notify}, base='powerbi')
            return {'ok': True, 'dataset_id': dataset_id, 'status': 'refresh_triggered'}
        except Exception as e:
            return {'error': str(e)}
