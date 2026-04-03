#!/usr/bin/env python3
"""Run SAJHA MCP Server with WSGI prefix middleware for single-port Docker deployment.

When nginx proxies /mcp-studio/ to SAJHA (with path stripping), this middleware
reads the X-Script-Name header set by nginx and sets Flask's SCRIPT_NAME so that
url_for(), url_for('static'), and redirect() all generate /mcp-studio/-prefixed URLs.
"""
import os
import sys
import logging
from pathlib import Path

# SAJHA must run from its own directory — it uses relative paths for config/data
SAJHA_DIR = Path(__file__).parent / 'sajhamcpserver'
os.chdir(SAJHA_DIR)
sys.path.insert(0, str(SAJHA_DIR))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


class ScriptNameMiddleware:
    """Set WSGI SCRIPT_NAME from X-Script-Name header so Flask generates prefixed URLs.

    nginx's proxy_pass strips the location prefix before forwarding, so PATH_INFO
    is already correct. This middleware only sets SCRIPT_NAME so Flask URL generation
    includes the prefix in generated hrefs, redirects, and static asset URLs.
    """
    def __init__(self, wsgi_app):
        self.app = wsgi_app

    def __call__(self, environ, start_response):
        prefix = environ.get('HTTP_X_SCRIPT_NAME', '').rstrip('/')
        if prefix:
            environ['SCRIPT_NAME'] = prefix
        return self.app(environ, start_response)


def main():
    from sajha.core.properties_configurator import PropertiesConfigurator
    from sajha.web.sajhamcpserver_web import SajhaMCPServerWebApp

    props = PropertiesConfigurator(['config/server.properties', 'config/application.properties'])

    host = os.getenv('SAJHA_HOST', props.get('server.host', '127.0.0.1'))
    port = int(os.getenv('SAJHA_PORT', props.get('server.port', '3002')))

    web_app = SajhaMCPServerWebApp()
    web_app.prepare()

    app = web_app.get_app()
    socketio = web_app.get_socketio()

    # Wrap WSGI app so nginx proxy knows to set SCRIPT_NAME
    app.wsgi_app = ScriptNameMiddleware(app.wsgi_app)

    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
