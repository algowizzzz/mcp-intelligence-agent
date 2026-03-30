// Build step: injects runtime config env vars into public/index.html
const fs = require('fs');
const apiUrl = process.env.MCP_API_URL || 'http://localhost:8000/api/agent/run';
const frontendApiKey = process.env.FRONTEND_API_KEY || '';

let html = fs.readFileSync('public/index.html', 'utf8');

// Inject a <script> tag before the closing </head> that sets runtime config globals
const injection = `<script>window.MCP_API_URL = '${apiUrl}'; window.FRONTEND_API_KEY = '${frontendApiKey}';</script>`;
html = html.replace('</head>', injection + '\n</head>');

fs.writeFileSync('public/index.html', html);
console.log(`Injected MCP_API_URL = ${apiUrl}`);
console.log(`Injected FRONTEND_API_KEY = ${frontendApiKey ? '(set)' : '(empty)'}`);
