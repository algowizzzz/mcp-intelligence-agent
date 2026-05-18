"""
Jira connector tools (7 tools).
Uses Atlassian Jira REST API v3 via AtlassianClient.
Reads project_key from worker connector_scope.jira_project_key if not provided.
"""
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.tools.impl.connector_base import get_atlassian_client, get_worker_context


class JiraListProjectsTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'jira_list_projects',
            'description': 'List all Jira projects accessible to the connector.',
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
                'max_results': {'type': 'integer', 'description': 'Max projects to return (default 50).', 'default': 50},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        max_results = params.get('max_results', 50)
        jira_url = worker_ctx.get('jira_url', '')
        try:
            client = get_atlassian_client(base_url=jira_url or None, worker_context=worker_ctx)
            result = client.get(f'rest/api/3/project?maxResults={max_results}')
            if isinstance(result, list):
                return {'projects': result, 'count': len(result)}
            projects = result.get('values', result) if isinstance(result, dict) else result
            return {'projects': projects, 'count': len(projects)}
        except Exception as e:
            return {'error': str(e)}


class JiraSearchIssuesTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'jira_search_issues',
            'description': 'Search Jira issues using JQL (Jira Query Language).',
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
                'jql': {'type': 'string', 'description': 'JQL query string. Example: "project = RISK AND status = Open".'},
                'project_key': {'type': 'string', 'description': 'Jira project key to scope the search. Defaults to worker-mapped project.'},
                'max_results': {'type': 'integer', 'description': 'Max issues to return (default 50).', 'default': 50},
                'fields': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Specific fields to include (optional).'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['jql']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        jql = params.get('jql', '')
        project_key = params.get('project_key') or worker_ctx.get('jira_project_key', '')
        max_results = params.get('max_results', 50)
        fields = params.get('fields', ['summary', 'status', 'assignee', 'priority', 'created', 'updated', 'description'])
        jira_url = worker_ctx.get('jira_url', '')
        if not jql:
            return {'error': 'jql is required'}
        # Auto-scope to project if available and not already in JQL
        if project_key and 'project' not in jql.lower():
            jql = f'project = {project_key} AND ({jql})'
        try:
            client = get_atlassian_client(base_url=jira_url or None, worker_context=worker_ctx)
            payload = {
                'jql': jql,
                'maxResults': max_results,
                'fields': fields,
            }
            result = client.post('rest/api/3/search', payload)
            issues = result.get('issues', [])
            return {
                'issues': issues,
                'count': len(issues),
                'total': result.get('total', len(issues)),
                'jql': jql,
            }
        except Exception as e:
            return {'error': str(e)}


class JiraGetIssueTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'jira_get_issue',
            'description': 'Get a specific Jira issue by key (e.g. PROJ-123).',
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
                'issue_key': {'type': 'string', 'description': 'Jira issue key (e.g. RISK-42).'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['issue_key']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        issue_key = params.get('issue_key', '')
        jira_url = worker_ctx.get('jira_url', '')
        if not issue_key:
            return {'error': 'issue_key is required'}
        try:
            client = get_atlassian_client(base_url=jira_url or None, worker_context=worker_ctx)
            result = client.get(f'rest/api/3/issue/{issue_key}')
            fields = result.get('fields', {})
            return {
                'issue_key': result.get('key'),
                'summary': fields.get('summary'),
                'status': fields.get('status', {}).get('name'),
                'assignee': fields.get('assignee', {}).get('displayName') if fields.get('assignee') else None,
                'priority': fields.get('priority', {}).get('name') if fields.get('priority') else None,
                'created': fields.get('created'),
                'updated': fields.get('updated'),
                'description': fields.get('description'),
                'labels': fields.get('labels', []),
                'full': result,
            }
        except Exception as e:
            return {'error': str(e)}


class JiraListSprintsTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'jira_list_sprints',
            'description': 'List sprints for a Jira board.',
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
                'board_id': {'type': 'string', 'description': 'Jira board ID. Defaults to worker-mapped board.'},
                'state': {'type': 'string', 'enum': ['active', 'closed', 'future'], 'description': 'Sprint state filter (optional).'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        board_id = params.get('board_id') or worker_ctx.get('jira_board_id', '')
        state = params.get('state', '')
        jira_url = worker_ctx.get('jira_url', '')
        if not board_id:
            return {'error': 'board_id required — provide as parameter or configure jira_board_id in worker connector_scope'}
        try:
            client = get_atlassian_client(base_url=jira_url or None, worker_context=worker_ctx)
            path = f'rest/agile/1.0/board/{board_id}/sprint'
            if state:
                path += f'?state={state}'
            result = client.get(path)
            sprints = result.get('values', [])
            return {'sprints': sprints, 'count': len(sprints)}
        except Exception as e:
            return {'error': str(e)}


class JiraCreateIssueTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'jira_create_issue',
            'description': 'Create a new Jira issue. Requires confirmation.',
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
                'project_key': {'type': 'string', 'description': 'Jira project key. Defaults to worker-mapped project.'},
                'summary': {'type': 'string', 'description': 'Issue summary/title.'},
                'issue_type': {'type': 'string', 'description': 'Issue type (e.g. Bug, Story, Task).', 'default': 'Task'},
                'description': {'type': 'string', 'description': 'Issue description (optional).'},
                'priority': {'type': 'string', 'description': 'Priority (e.g. High, Medium, Low). Optional.'},
                'labels': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Labels to attach (optional).'},
                'confirmation_required': {'type': 'boolean', 'const': True, 'description': 'Must be true to confirm write operation.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['summary', 'confirmation_required']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        project_key = params.get('project_key') or worker_ctx.get('jira_project_key', '')
        summary = params.get('summary', '')
        issue_type = params.get('issue_type', 'Task')
        description = params.get('description', '')
        priority = params.get('priority', '')
        labels = params.get('labels', [])
        jira_url = worker_ctx.get('jira_url', '')
        if not project_key:
            return {'error': 'project_key required — provide as parameter or configure jira_project_key in worker connector_scope'}
        if not summary:
            return {'error': 'summary is required'}
        try:
            client = get_atlassian_client(base_url=jira_url or None, worker_context=worker_ctx)
            fields = {
                'project': {'key': project_key},
                'summary': summary,
                'issuetype': {'name': issue_type},
            }
            if description:
                fields['description'] = {
                    'type': 'doc', 'version': 1,
                    'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': description}]}]
                }
            if priority:
                fields['priority'] = {'name': priority}
            if labels:
                fields['labels'] = labels
            result = client.post('rest/api/3/issue', {'fields': fields})
            return {
                'ok': True,
                'issue_key': result.get('key'),
                'issue_id': result.get('id'),
                'self': result.get('self'),
            }
        except Exception as e:
            return {'error': str(e)}


class JiraUpdateIssueTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'jira_update_issue',
            'description': 'Update fields on an existing Jira issue. Requires confirmation.',
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
                'issue_key': {'type': 'string', 'description': 'Jira issue key to update (e.g. RISK-42).'},
                'summary': {'type': 'string', 'description': 'New summary/title (optional).'},
                'description': {'type': 'string', 'description': 'New description (optional).'},
                'priority': {'type': 'string', 'description': 'New priority (optional).'},
                'labels': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Updated labels (optional).'},
                'confirmation_required': {'type': 'boolean', 'const': True, 'description': 'Must be true to confirm write operation.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['issue_key', 'confirmation_required']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        issue_key = params.get('issue_key', '')
        jira_url = worker_ctx.get('jira_url', '')
        if not issue_key:
            return {'error': 'issue_key is required'}
        fields = {}
        if params.get('summary'):
            fields['summary'] = params['summary']
        if params.get('description'):
            fields['description'] = {
                'type': 'doc', 'version': 1,
                'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': params['description']}]}]
            }
        if params.get('priority'):
            fields['priority'] = {'name': params['priority']}
        if params.get('labels') is not None:
            fields['labels'] = params['labels']
        if not fields:
            return {'error': 'At least one field to update is required (summary, description, priority, or labels)'}
        try:
            client = get_atlassian_client(base_url=jira_url or None, worker_context=worker_ctx)
            client.put(f'rest/api/3/issue/{issue_key}', {'fields': fields})
            return {'ok': True, 'issue_key': issue_key, 'updated_fields': list(fields.keys())}
        except Exception as e:
            return {'error': str(e)}


class JiraAddCommentTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'jira_add_comment',
            'description': 'Add a comment to a Jira issue. Requires confirmation.',
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
                'issue_key': {'type': 'string', 'description': 'Jira issue key (e.g. RISK-42).'},
                'comment': {'type': 'string', 'description': 'Comment body text.'},
                'confirmation_required': {'type': 'boolean', 'const': True, 'description': 'Must be true to confirm write operation.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['issue_key', 'comment', 'confirmation_required']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        issue_key = params.get('issue_key', '')
        comment = params.get('comment', '')
        jira_url = worker_ctx.get('jira_url', '')
        if not issue_key:
            return {'error': 'issue_key is required'}
        if not comment:
            return {'error': 'comment is required'}
        try:
            client = get_atlassian_client(base_url=jira_url or None, worker_context=worker_ctx)
            body = {
                'body': {
                    'type': 'doc', 'version': 1,
                    'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': comment}]}]
                }
            }
            result = client.post(f'rest/api/3/issue/{issue_key}/comment', body)
            return {
                'ok': True,
                'comment_id': result.get('id'),
                'issue_key': issue_key,
                'created': result.get('created'),
            }
        except Exception as e:
            return {'error': str(e)}
