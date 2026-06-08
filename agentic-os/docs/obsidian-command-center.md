# Obsidian Command Center — setup guide

Turn the vault into a "command center" where Claude runs in a terminal docked to the
bottom, a localhost/HTML preview sits on the right (same flow as the NEXUM app), a
design-critique panel sits beside it, and the "brain" is just the vault itself
(markdown + `[[wikilinks]]`, no embeddings — matching CLAUDE.md and Chase Hannegan's
actual setup: **skills > memory > dashboard, Claude reads the vault directly**).

Do this on the Mac mini (canonical host); the same plugins work on the Windows desktop
since the vault is iCloud-synced.

## 1. Plugins to install

Settings -> Community plugins -> Browse, install + enable:

| Pane | Plugin | ID | Role |
|---|---|---|---|
| Terminal (bottom) | **Terminal** (polyipseity) | `terminal` | Integrated shell inside an Obsidian pane. |
| Localhost preview (right) | **Custom Frames** (Ellpeck) | `obsidian-custom-frames` | Renders any `localhost:PORT` in a sidebar iframe. |
| HTML file preview (optional) | **Live Preview** (HxGuang) | `live-preview` | Serves vault `.html` on 127.0.0.1:5500 w/ auto-reload. |

Alternative terminal: **Claude Code Terminal** (dternyak) gives a real PTY + auto-launches
Claude, but only as a sidebar/floating window — not a bottom dock. Use Terminal
(polyipseity) since the goal is "pulls up from the bottom."

## 2. Terminal that pulls up from the bottom

1. Terminal plugin settings -> add an **integrated** profile (default shell is fine;
   on the Mac it's zsh, on Windows PowerShell).
2. Command palette -> **Terminal: Open integrated terminal**.
3. Drag that pane's tab to the **bottom** of the window until the bottom split
   highlights, then drop. It now lives as a pull-up panel; collapse/expand from the tab.
4. In it: `cd` to the vault root and run `claude`. Claude now reads/writes the vault
   directly — this is the memory layer, no RAG needed.

Save this as a workspace (Workspaces core plugin -> Save) so the layout restores.

## 3. Localhost preview on the right (the NEXUM flow)

1. Start your dev server in the bottom terminal, e.g. NEXUM: `cd <nexum> && npm run dev`
   (Vite on `localhost:5173`), or the agentic-os dashboard (`npm run dev`).
2. Custom Frames settings -> add a frame: URL `http://localhost:5173`, name "Preview",
   open as **right sidebar**.
3. Command palette -> **Custom Frames: Open Preview**, then drag it to the right split.
   Reload the frame after the server is up.

Build a feature in the terminal -> watch it live on the right, exactly like NEXUM.

## 4. Design-critique panel (uses the `impeccable` skill)

There is no off-the-shelf critique plugin, so wire the existing **`impeccable`** skill
(in the NEXUM repo) to a third pane:

1. In the bottom terminal: run `impeccable critique` (or `audit`/`shape`/`polish`) on the
   HTML/component you're previewing.
2. Have it write critique output to a markdown note, e.g. `output/critique-<feature>.md`.
3. Open that note in a pane next to the preview (or point a second Custom Frames pane at a
   small local critique app). The critique now sits beside the live preview — the
   "sliders/tweaks" review feel without a custom plugin.

## 5. The brain = markdown only (no new infra)

Per CLAUDE.md ("No vector DB. Markdown only") and Hannegan's approach, skip embeddings.
Claude in the bottom terminal reads `wiki/_master-index.md`, each domain `_index.md`, and
folder structure directly (grep + `[[wikilinks]]`). The `memory.raw-triage` skill already
keeps those indexes current. Borrow conventions from `kepano/obsidian-skills` so Claude
always writes Obsidian-flavored markdown.

If grep ever proves insufficient, the RAG add-on path is **Smart Connections** (semantic
"related notes") + **Copilot for Obsidian** with a local **Ollama/LM Studio** model — a
clean later addition, not part of this setup, and it would require revisiting the
"markdown only" rule in CLAUDE.md.

## Final layout

```
+------------------+---------------------------+
|                  |                           |
|   vault notes    |   Custom Frames preview   |
|   (main editor)  |   (localhost:PORT)        |
|                  |---------------------------|
|                  |   critique note pane      |
+------------------+---------------------------+
|        Terminal (bottom split): `claude`     |
+----------------------------------------------+
```
Save as a Workspace so it restores every session.
