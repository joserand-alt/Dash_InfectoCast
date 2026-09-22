
const fs = require('fs');
const html = fs.readFileSync('dashboard_gerado.html', 'utf-8');
const scriptMatch = html.match(/<script[^>]*>([\s\S]*?)<\/script>/gi);
const js = scriptMatch[1].replace(/<\/?script[^>]*>/gi, '');

// Let's write js to a temp file and run node --check
fs.writeFileSync('temp_check.js', js, 'utf-8');
