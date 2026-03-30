// Build step: injects MCP_API_URL env var into public/index.html
const fs = require('fs');
const apiUrl = process.env.MCP_API_URL || 'http://localhost:8000/api/agent/run';

let html = fs.readFileSync('public/index.html', 'utf8');

// Inject a <script> tag before the closing </head> that sets window.MCP_API_URL
const injection = `<script>window.MCP_API_URL = '${apiUrl}';</script>`;
html = html.replace('</head>', injection + '\n</head>');

fs.writeFileSync('public/index.html', html);
console.log(`Injected MCP_API_URL = ${apiUrl}`);
