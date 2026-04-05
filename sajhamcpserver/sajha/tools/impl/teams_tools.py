"""
Microsoft Teams connector tools (6 tools).
Reads team_id from worker connector_scope.teams_team_id if not provided in params.
"""
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.tools.impl.connector_base import get_ms_client, get_worker_context


class TeamsListChannelsTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'teams_list_channels',
            'description': 'List all channels in a Microsoft Teams team. Reads team_id from worker context.',
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
                'team_id': {'type': 'string', 'description': 'Teams team ID. Defaults to worker-mapped team.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        team_id = params.get('team_id') or worker_ctx.get('teams_team_id', '')
        if not team_id:
            return {'error': 'team_id required — provide as parameter or configure in worker connector_scope'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'teams/{team_id}/channels')
            return {'channels': result.get('value', []), 'count': len(result.get('value', []))}
        except Exception as e:
            return {'error': str(e)}


class TeamsGetMessagesTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'teams_get_messages',
            'description': 'Get recent messages from a Microsoft Teams channel.',
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
                'team_id': {'type': 'string', 'description': 'Teams team ID. Defaults to worker-mapped team.'},
                'channel_id': {'type': 'string', 'description': 'Channel ID to fetch messages from.'},
                'top': {'type': 'integer', 'description': 'Number of messages to return (default 20).', 'default': 20},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['channel_id']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        team_id = params.get('team_id') or worker_ctx.get('teams_team_id', '')
        channel_id = params.get('channel_id', '')
        if not team_id:
            return {'error': 'team_id required — provide as parameter or configure in worker connector_scope'}
        if not channel_id:
            return {'error': 'channel_id is required'}
        top = params.get('top', 20)
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'teams/{team_id}/channels/{channel_id}/messages?$top={top}')
            messages = result.get('value', [])
            return {'messages': messages, 'count': len(messages)}
        except Exception as e:
            return {'error': str(e)}


class TeamsGetMeetingsTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'teams_get_meetings',
            'description': 'Get online meetings or calendar events for a Teams user.',
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
                'user_id': {'type': 'string', 'description': 'User ID or UPN. Defaults to worker-mapped user.'},
                'start_datetime': {'type': 'string', 'description': 'ISO 8601 start datetime filter (optional).'},
                'end_datetime': {'type': 'string', 'description': 'ISO 8601 end datetime filter (optional).'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        user_id = params.get('user_id') or worker_ctx.get('teams_user_id', 'me')
        start_dt = params.get('start_datetime', '')
        end_dt = params.get('end_datetime', '')
        try:
            client = get_ms_client(worker_ctx)
            path = f'users/{user_id}/calendarView' if start_dt and end_dt else f'users/{user_id}/events'
            query = ''
            if start_dt and end_dt:
                query = f'?startDateTime={start_dt}&endDateTime={end_dt}'
            result = client.get(f'{path}{query}')
            events = result.get('value', [])
            return {'meetings': events, 'count': len(events)}
        except Exception as e:
            return {'error': str(e)}


class TeamsListMembersTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'teams_list_members',
            'description': 'List members of a Microsoft Teams team (group).',
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
                'team_id': {'type': 'string', 'description': 'Teams team ID. Defaults to worker-mapped team.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        team_id = params.get('team_id') or worker_ctx.get('teams_team_id', '')
        if not team_id:
            return {'error': 'team_id required — provide as parameter or configure in worker connector_scope'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'groups/{team_id}/members')
            members = result.get('value', [])
            return {'members': members, 'count': len(members)}
        except Exception as e:
            return {'error': str(e)}


class TeamsGetChannelFilesTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'teams_get_channel_files',
            'description': 'Get the files folder metadata for a Microsoft Teams channel.',
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
                'team_id': {'type': 'string', 'description': 'Teams team ID. Defaults to worker-mapped team.'},
                'channel_id': {'type': 'string', 'description': 'Channel ID to fetch files folder for.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['channel_id']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        team_id = params.get('team_id') or worker_ctx.get('teams_team_id', '')
        channel_id = params.get('channel_id', '')
        if not team_id:
            return {'error': 'team_id required — provide as parameter or configure in worker connector_scope'}
        if not channel_id:
            return {'error': 'channel_id is required'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'teams/{team_id}/channels/{channel_id}/filesFolder')
            return {'files_folder': result}
        except Exception as e:
            return {'error': str(e)}


class TeamsSendMessageTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'teams_send_message',
            'description': 'Send a message to a Microsoft Teams channel. Requires confirmation.',
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
                'team_id': {'type': 'string', 'description': 'Teams team ID. Defaults to worker-mapped team.'},
                'channel_id': {'type': 'string', 'description': 'Channel ID to send message to.'},
                'message': {'type': 'string', 'description': 'Message content (plain text or HTML).'},
                'content_type': {'type': 'string', 'enum': ['text', 'html'], 'default': 'text', 'description': 'Message content type.'},
                'confirmation_required': {'type': 'boolean', 'const': True, 'description': 'Must be true to confirm write operation.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['channel_id', 'message', 'confirmation_required']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        team_id = params.get('team_id') or worker_ctx.get('teams_team_id', '')
        channel_id = params.get('channel_id', '')
        message = params.get('message', '')
        content_type = params.get('content_type', 'text')
        if not team_id:
            return {'error': 'team_id required — provide as parameter or configure in worker connector_scope'}
        if not channel_id:
            return {'error': 'channel_id is required'}
        if not message:
            return {'error': 'message is required'}
        try:
            client = get_ms_client(worker_ctx)
            body = {
                'body': {
                    'contentType': content_type,
                    'content': message,
                }
            }
            # NOTE: ChannelMessage.Send does not exist as an Application permission in Microsoft Graph.
            # App-only channel posting requires a registered Teams Bot (via Bot Framework / Azure Bot Service).
            # This call will succeed only if the app is also registered as a Bot and added to the team.
            result = client.post(f'teams/{team_id}/channels/{channel_id}/messages', body)
            return {'ok': True, 'message_id': result.get('id'), 'created_at': result.get('createdDateTime')}
        except Exception as e:
            return {'error': str(e)}
