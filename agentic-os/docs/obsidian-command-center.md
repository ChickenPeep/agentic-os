# Obsidian Command Center — setup

The vault IS the command center. Skills + the Discord bot write markdown notes;
`command-center/Command Center.md` renders them as live tables. Claude runs in a docked
terminal; an embedded web pane sits on the right. No web app, no database.

## 1. Plugins (Settings → Community plugins → Browse)

| Plugin | ID | Role |
|---|---|---|
| **Dataview** | `dataview` | Renders the command center tables. **Required.** Enable "Enable JavaScript Queries" in its settings (the Activity/Ideas tables use DataviewJS). |
| **Terminal** (polyipseity) | `terminal` | Claude docked in a bottom pane. |
| **Custom Frames** (Ellpeck) | `obsidian-custom-frames` | The embedded web-search pane. |

Enable the **Snippets** toggle: Settings → Appearance → CSS snippets → refresh → turn on
`command-center`.

## 2. Layout
1. Open `command-center/Command Center.md` in the main pane.
2. Terminal: Command palette → *Terminal: Open integrated terminal* → drag the tab to the
   bottom split → `cd` to the vault root → run `claude`.
3. Custom Frames: add a frame (URL `https://www.perplexity.ai` or your search engine) →
   open it in the right split. This is the embedded web search.
4. Save the layout: Workspaces core plugin → Save (e.g. "Command Center").

## 3. Phone
Install Obsidian mobile + the Dataview plugin and open `Command Center.md`. The vault
syncs via iCloud, so activity/ideas/projects show on your phone. Use the Discord bot to
actually run things remotely.

## 4. How results show up
- **Skills / Pokemon hunter / bot** → write notes into `command-center/activity/` and
  `command-center/ideas/` (via `agentic-os/lib/notes.py`).
- **Research:** ask Claude (terminal or bot) to research; it runs the `deep-research`
  skill and saves the cited report into `command-center/research/` (`notes.write_research`).
- **Skills registry:** run `python3 -c "import sys;sys.path.insert(0,'agentic-os/lib');import notes;notes.sync_skills('.')"` after adding/editing a skill to refresh `command-center/skills/`.
