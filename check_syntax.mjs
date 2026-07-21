// Extract the script from ChatWidget.astro and run `node --check` on it
import { readFileSync, writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';

const astro = readFileSync('D:/project/astro/src/components/ChatWidget.astro', 'utf8');
const startMarker = '<script is:inline define:vars={{ apiUrl, hidePaths }}>';
const endMarker = '</script>';
const i1 = astro.indexOf(startMarker) + startMarker.length;
const i2 = astro.indexOf(endMarker, i1);
let body = astro.substring(i1, i2).trim();

// Mimic define:vars injection (Astro prepends `const apiUrl = JSON.stringify(val);` etc.)
body = `const apiUrl = "/api/chat";\nconst hidePaths = ["/music","/video-gen","/interactive-showcase"];\n` + body;

writeFileSync('D:/project/chat-bot/_widget_test.mjs', body);
try {
  execSync('node --check D:/project/chat-bot/_widget_test.mjs', { stdio: 'inherit' });
  console.log('SYNTAX OK');
} catch (e) {
  console.log('SYNTAX FAIL');
  process.exit(1);
}
