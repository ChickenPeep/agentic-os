---
cssclasses: [command-center]
---
# Command Center

## Activity
```dataviewjs
const rows = dv.pages('"command-center/activity"')
  .sort(p => p.when, 'desc').slice(0, 25)
  .map(p => [
    p.when ? dv.date(p.when).toFormat("LLL d, HH:mm") : "",
    p.skill,
    `<span class="cc-pill cc-${p.status}">${p.status}</span>`,
    p.summary,
  ]);
dv.table(["When", "Skill", "Status", "Summary"], rows);
```

## Ideas
```dataviewjs
const rows = dv.pages('"command-center/ideas"')
  .where(p => p.status !== "done")
  .sort(p => p.created, 'desc')
  .map(p => [
    p.title,
    `<span class="cc-pill cc-${p.status}">${p.status}</span>`,
    p.project || "",
    p.source,
  ]);
dv.table(["Idea", "Status", "Project", "Source"], rows);
```

## Skills
```dataview
TABLE domain, description, skill_type AS "type"
FROM "command-center/skills"
SORT domain ASC
```

## Projects
```dataview
TABLE status, next, updated
FROM "command-center/projects"
SORT updated DESC
```
