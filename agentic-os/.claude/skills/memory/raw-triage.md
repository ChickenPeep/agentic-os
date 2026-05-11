---
slug: memory.raw-triage
domain: MEMORY
name: raw-triage
description: triages files in raw/ into wiki/<domain>/, archives sources, logs to Supabase
type: skill
---

You are running the `memory.raw-triage` skill. Your job is to triage every eligible file in `raw/` into the correct `wiki/<domain>/` location, archive the source files, update index files, and log each filing to Supabase. Your CWD is the vault root.

IMPORTANT: Use ONLY Bash tool calls for ALL file operations (reading, writing, moving, creating directories). Do NOT use the Write or Edit tools — use bash with heredocs and cat to write files. This ensures you work within the execution environment's permissions.

At the end you MUST output ONLY a single JSON object (no prose, no markdown fences) matching the schema at the bottom of this prompt.

---

## Step 1 — Read credentials and list files

Run all of this in a single bash call:

```bash
# Source secrets — prefer per-machine env (not in iCloud), fall back to vault env for non-sensitive vars
set -a
[ -f ~/.agentic-os.env ] && source ~/.agentic-os.env
[ -f credentials/.env ] && source credentials/.env  # for SUPABASE_URL etc.
set +a
TODAY=$(date +%Y-%m-%d)
echo "TODAY=$TODAY"
echo "SUPABASE_URL=$SUPABASE_URL"
find raw -maxdepth 1 -type f | sort
```

This tells you: (1) whether Supabase env vars loaded, and (2) which files are in raw/.

---

## Step 2 — Classify each eligible file

For each .md or .txt file found in raw/ (not in subdirs, not .gitkeep):

- Read the file with a bash cat command
- Read the relevant wiki domain _index.md for context (bash cat)
- Decide the domain based on content

The 9 domains and their wiki subfolders:
- NEXUM -> wiki/nexum/ : D3 football performance tracking platform, Supabase schema for Nexum, Hudl integration, play tracking, stat apps
- FOOTBALL -> wiki/football/ : gym sessions, lift notes, practice notes, on-field performance, physical training, game prep at UWO
- CONSULTING -> wiki/consulting/ : AI consulting at UW Oshkosh, Copilot/Gemini rollout, faculty workshops, DLP, M365, meetings with university staff
- SCHOOL -> wiki/school/ : coursework, classes, GPA, professors, academic deadlines at UW Oshkosh
- PERSONAL OPS -> wiki/personal-ops/ : personal productivity, time management, life organization, habits, routines
- BIBLE STUDY -> wiki/bible-study/ : Bible study leadership, spiritual reflection, small group content
- SIDE PROJECTS -> wiki/side-projects/ : projects other than Nexum and agentic-os
- MEMORY -> wiki/memory/ : meta-level notes about how Gabriel organizes information, the agentic-os system itself
- PRODUCTIVITY -> wiki/productivity/ : tools, workflows, or techniques for being more productive in general

High confidence = file clearly belongs to ONE domain. Low confidence = could plausibly belong to 2+ domains, or matches none well.

For .pdf files: skip with reason "pdf not yet supported".
For files with no extension or other extensions: skip with reason "unsupported extension".

---

## Step 3 — For each HIGH CONFIDENCE file, do all of this in sequence:

### 3a. Determine article metadata
- Title: a clean descriptive title (not just the filename) in Title Case
- Slug: kebab-case of the title, lowercase, hyphens only, no special chars
- Domain folder: the wiki subfolder name from the table above
- Summary: one sentence describing what the article covers

### 3b. Check if destination already exists
```bash
test -f "wiki/<domain-folder>/<slug>.md" && echo "EXISTS" || echo "NEW"
```

### 3c. Write the wiki article using bash heredoc

If NEW, write the full article:
```bash
mkdir -p "wiki/<domain-folder>"
cat > "wiki/<domain-folder>/<slug>.md" << ARTICLE_EOF
---
source: raw/<original-filename>
triaged_at: ${TODAY}
domain: <DOMAIN LABEL>
---

# <Title>

<One paragraph summary of the content>

<Normalized markdown body preserving the key facts and structure from the source>
ARTICLE_EOF
```

If EXISTS, append to it:
```bash
cat >> "wiki/<domain-folder>/<slug>.md" << ARTICLE_EOF

## Update ${TODAY}

<The new content from the source file, normalized>
ARTICLE_EOF
```

### 3d. Update the domain _index.md

Check if it has an "## Articles" section and append a bullet:
```bash
grep -q "## Articles" "wiki/<domain-folder>/_index.md" || echo "## Articles" >> "wiki/<domain-folder>/_index.md"
echo "- [<Title>](<slug>.md) — <one-sentence summary>" >> "wiki/<domain-folder>/_index.md"
```

### 3e. Archive the source file
```bash
mkdir -p "raw/_archived/${TODAY}"
mv "raw/<filename>" "raw/_archived/${TODAY}/<filename>"
```

### 3f. Insert to Supabase wiki_articles table
```bash
set -a
[ -f ~/.agentic-os.env ] && source ~/.agentic-os.env
[ -f credentials/.env ] && source credentials/.env
set +a
curl -s -X POST "$SUPABASE_URL/rest/v1/wiki_articles?on_conflict=path" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=minimal,resolution=merge-duplicates" \
  -d "{\"domain\":\"<DOMAIN>\",\"path\":\"wiki/<domain-folder>/<slug>.md\",\"title\":\"<Title>\",\"summary\":\"<one-sentence summary>\",\"source_raw_files\":[\"raw/<filename>\"]}"
```

If curl returns an error JSON, note it but continue.

---

## Step 4 — For each LOW CONFIDENCE file:

```bash
mkdir -p raw/_uncertain
mv "raw/<filename>" "raw/_uncertain/<filename>"
```

Do NOT write a wiki article. Add to uncertain array in the output.

---

## Step 5 — Update wiki/_master-index.md

For each domain that got new articles, update the article count in the master index table. The table row format is:
`| [Domain](domain-folder/_index.md) | domain-folder/ | N |`

Read the file first, then use bash to update the count:
```bash
cat wiki/_master-index.md
```

Then rewrite just the affected lines using sed or a python one-liner:
```bash
python3 -c "
import re
with open('wiki/_master-index.md') as f:
    content = f.read()
# Increment count for domain
content = re.sub(r'(\| \[Nexum\].*\| )(\d+)( \|)', lambda m: m.group(1)+str(int(m.group(2))+1)+m.group(3), content)
with open('wiki/_master-index.md', 'w') as f:
    f.write(content)
"
```

(Adapt the regex for whichever domains actually got articles.)

---

## Step 6 — Output ONLY this JSON

No prose, no markdown fences, just the raw JSON object:

{
  "files_seen": <integer: count of all files found at raw/ maxdepth 1>,
  "filed": [
    {"src": "raw/<filename>", "dest": "wiki/<domain-folder>/<slug>.md", "domain": "<DOMAIN>", "action": "created or appended"}
  ],
  "uncertain": ["raw/_uncertain/<filename>"],
  "skipped": [{"src": "raw/<filename>", "reason": "<reason>"}],
  "errors": ["<error message if anything failed>"]
}

---

## Constraints

- Never delete any file. Always mv, never rm.
- Do not process files inside raw/_archived/ or raw/_uncertain/.
- Only process .md and .txt files today. Skip .pdf, .gitkeep, and other extensions.
- On any error for a single file, log it and continue with the next.
- Source ~/.agentic-os.env (then credentials/.env) before every curl call to ensure SUPABASE_SERVICE_ROLE_KEY is loaded.
- path in wiki_articles rows is relative to vault root e.g. "wiki/nexum/my-article.md".
- Use ${TODAY} (captured in Step 1) for all triaged_at values and archive folder names.
- Return ONLY the raw JSON object as your final output — no other text.
