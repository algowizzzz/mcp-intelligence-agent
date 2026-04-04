"""
Outlook / Exchange connector tools (6 tools).
Uses Microsoft Graph API for mailbox operations.
Reads user_email from worker connector_scope.outlook_user_email if not provided.
"""
from sajha.tools.base_mcp_tool import BaseMCPTool
from sajha.tools.impl.connector_base import get_ms_client, get_worker_context


class OutlookReadEmailsTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'outlook_read_email',
            'description': 'Read recent emails from an Outlook mailbox.',
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
                'user_email': {'type': 'string', 'description': 'Mailbox UPN/email. Defaults to worker-mapped mailbox.'},
                'folder': {'type': 'string', 'description': 'Mail folder name (default: Inbox).', 'default': 'Inbox'},
                'top': {'type': 'integer', 'description': 'Number of messages to return (default 20).', 'default': 20},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        user_email = params.get('user_email') or worker_ctx.get('outlook_user_email', '')
        folder = params.get('folder', 'Inbox')
        top = params.get('top', 20)
        if not user_email:
            return {'error': 'user_email required — provide as parameter or configure outlook_user_email in worker connector_scope'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'users/{user_email}/mailFolders/{folder}/messages?$top={top}&$orderby=receivedDateTime desc')
            messages = result.get('value', [])
            return {'messages': messages, 'count': len(messages), 'folder': folder}
        except Exception as e:
            return {'error': str(e)}


class OutlookSearchEmailsTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'outlook_search_email',
            'description': 'Search emails in an Outlook mailbox using a keyword query.',
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
                'user_email': {'type': 'string', 'description': 'Mailbox UPN/email. Defaults to worker-mapped mailbox.'},
                'query': {'type': 'string', 'description': 'Search query (keywords, subject, sender, etc.).'},
                'top': {'type': 'integer', 'description': 'Number of results to return (default 20).', 'default': 20},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['query']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        user_email = params.get('user_email') or worker_ctx.get('outlook_user_email', '')
        query = params.get('query', '')
        top = params.get('top', 20)
        if not user_email:
            return {'error': 'user_email required — provide as parameter or configure outlook_user_email in worker connector_scope'}
        if not query:
            return {'error': 'query is required'}
        try:
            client = get_ms_client(worker_ctx)
            import urllib.parse
            encoded = urllib.parse.quote(f'"{query}"')
            result = client.get(f'users/{user_email}/messages?$search={encoded}&$top={top}')
            messages = result.get('value', [])
            return {'messages': messages, 'count': len(messages), 'query': query}
        except Exception as e:
            return {'error': str(e)}


class OutlookGetEmailTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'outlook_get_email',
            'description': 'Get a specific email message by ID from an Outlook mailbox.',
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
                'user_email': {'type': 'string', 'description': 'Mailbox UPN/email. Defaults to worker-mapped mailbox.'},
                'message_id': {'type': 'string', 'description': 'Message ID to retrieve.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['message_id']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        user_email = params.get('user_email') or worker_ctx.get('outlook_user_email', '')
        message_id = params.get('message_id', '')
        if not user_email:
            return {'error': 'user_email required — provide as parameter or configure outlook_user_email in worker connector_scope'}
        if not message_id:
            return {'error': 'message_id is required'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'users/{user_email}/messages/{message_id}')
            return {'message': result}
        except Exception as e:
            return {'error': str(e)}


class OutlookListFoldersTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'outlook_list_folders',
            'description': 'List mail folders in an Outlook mailbox.',
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
                'user_email': {'type': 'string', 'description': 'Mailbox UPN/email. Defaults to worker-mapped mailbox.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            }
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        user_email = params.get('user_email') or worker_ctx.get('outlook_user_email', '')
        if not user_email:
            return {'error': 'user_email required — provide as parameter or configure outlook_user_email in worker connector_scope'}
        try:
            client = get_ms_client(worker_ctx)
            result = client.get(f'users/{user_email}/mailFolders')
            folders = result.get('value', [])
            return {'folders': folders, 'count': len(folders)}
        except Exception as e:
            return {'error': str(e)}


class OutlookSendEmailTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'outlook_send_email',
            'description': 'Send an email from an Outlook mailbox. Requires confirmation.',
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
                'user_email': {'type': 'string', 'description': 'Sender mailbox UPN/email. Defaults to worker-mapped mailbox.'},
                'to': {'type': 'array', 'items': {'type': 'string'}, 'description': 'List of recipient email addresses.'},
                'subject': {'type': 'string', 'description': 'Email subject.'},
                'body': {'type': 'string', 'description': 'Email body content.'},
                'body_type': {'type': 'string', 'enum': ['Text', 'HTML'], 'default': 'Text'},
                'cc': {'type': 'array', 'items': {'type': 'string'}, 'description': 'CC recipients (optional).'},
                'confirmation_required': {'type': 'boolean', 'const': True, 'description': 'Must be true to confirm write operation.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['to', 'subject', 'body', 'confirmation_required']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        user_email = params.get('user_email') or worker_ctx.get('outlook_user_email', '')
        to_list = params.get('to', [])
        subject = params.get('subject', '')
        body = params.get('body', '')
        body_type = params.get('body_type', 'Text')
        cc_list = params.get('cc', [])
        if not user_email:
            return {'error': 'user_email required — provide as parameter or configure outlook_user_email in worker connector_scope'}
        if not to_list:
            return {'error': 'to (recipients list) is required'}
        if not subject:
            return {'error': 'subject is required'}
        try:
            client = get_ms_client(worker_ctx)
            to_recipients = [{'emailAddress': {'address': addr}} for addr in to_list]
            cc_recipients = [{'emailAddress': {'address': addr}} for addr in cc_list]
            payload = {
                'message': {
                    'subject': subject,
                    'body': {'contentType': body_type, 'content': body},
                    'toRecipients': to_recipients,
                },
                'saveToSentItems': True,
            }
            if cc_recipients:
                payload['message']['ccRecipients'] = cc_recipients
            client.post(f'users/{user_email}/sendMail', payload)
            return {'ok': True, 'subject': subject, 'to': to_list}
        except Exception as e:
            return {'error': str(e)}


class OutlookReplyEmailTool(BaseMCPTool):
    def __init__(self, config=None):
        default_config = {
            'name': 'outlook_reply_email',
            'description': 'Reply to an email in an Outlook mailbox. Requires confirmation.',
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
                'user_email': {'type': 'string', 'description': 'Mailbox UPN/email. Defaults to worker-mapped mailbox.'},
                'message_id': {'type': 'string', 'description': 'ID of the message to reply to.'},
                'comment': {'type': 'string', 'description': 'Reply comment/body text.'},
                'reply_all': {'type': 'boolean', 'description': 'If true, reply all. Default false.', 'default': False},
                'confirmation_required': {'type': 'boolean', 'const': True, 'description': 'Must be true to confirm write operation.'},
                '_worker_context': {'type': 'object', 'description': 'Injected by agent server.'},
            },
            'required': ['message_id', 'comment', 'confirmation_required']
        }

    def get_output_schema(self):
        return {'type': 'object'}

    def execute(self, params):
        worker_ctx = get_worker_context(params)
        user_email = params.get('user_email') or worker_ctx.get('outlook_user_email', '')
        message_id = params.get('message_id', '')
        comment = params.get('comment', '')
        reply_all = params.get('reply_all', False)
        if not user_email:
            return {'error': 'user_email required — provide as parameter or configure outlook_user_email in worker connector_scope'}
        if not message_id:
            return {'error': 'message_id is required'}
        if not comment:
            return {'error': 'comment is required'}
        try:
            client = get_ms_client(worker_ctx)
            endpoint = 'replyAll' if reply_all else 'reply'
            client.post(f'users/{user_email}/messages/{message_id}/{endpoint}', {'comment': comment})
            return {'ok': True, 'message_id': message_id, 'reply_all': reply_all}
        except Exception as e:
            return {'error': str(e)}
