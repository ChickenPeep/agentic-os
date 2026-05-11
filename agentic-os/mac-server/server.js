require('dotenv').config();
const express = require('express');
const { exec } = require('child_process');
const app = express();
app.use(express.json());

const API_KEY  = process.env.AGENTIC_OS_API_KEY;
const VAULT    = process.env.VAULT_PATH || '/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault';
const PORT     = process.env.PORT || 4242;

app.get('/health', (_req, res) => res.json({ status: 'ok' }));

app.post('/run', (req, res) => {
  const auth = req.headers.authorization;
  if (!API_KEY || auth !== `Bearer ${API_KEY}`) {
    return res.status(401).json({ error: 'unauthorized' });
  }

  const { prompt, skill_id, triggered_by } = req.body;
  if (!prompt) return res.status(400).json({ error: 'prompt required' });

  // claude --print runs non-interactively and returns output to stdout
  const safe = prompt.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
  const cmd  = `cd "${VAULT}" && claude --print "${safe}"`;

  exec(cmd, { timeout: 120_000, maxBuffer: 10 * 1024 * 1024 }, (err, stdout, stderr) => {
    if (err) return res.status(500).json({ error: err.message, stderr });
    res.json({ output: stdout, stderr, skill_id, triggered_by });
  });
});

app.listen(PORT, '0.0.0.0', () =>
  console.log(`agentic-os server listening on :${PORT}`)
);
