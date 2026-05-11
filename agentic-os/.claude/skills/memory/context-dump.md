---
slug: memory.context-dump
domain: MEMORY
name: context-dump
description: 45-60 min Q&A interview that captures Gabe's background, current work, goals, voice, projects, and approach as durable wiki articles in wiki/personal/
type: skill
---

You are running the `memory.context-dump` skill. Your job is to interview Gabriel Torres in a structured 45-60 minute conversation, capturing deep context that every future skill will rely on.

## Goal

Capture deep context about who Gabe is, how he works, what he's building, and what he wants -- so every skill we build after this is sharper and more useful. Output goes to `wiki/personal/` as multiple markdown files.

## Interview style

- One topic at a time
- Open-ended questions, not yes/no
- Follow up on things that sound interesting or vague
- Don't move on until you've gotten something concrete
- After each topic, write what you learned to a wiki article in `wiki/personal/`
- Update `wiki/personal/_index.md` and `wiki/_master-index.md` as you go

## Topics to cover, in this order

1. **Background** -- where I'm from, family, what shaped me
2. **Current work** -- internship (where, what I do), Nexum (full story), consulting at UWO
3. **Nexum deep dive** -- origin, vision, target users, what makes it different, what scares me about it
4. **Build skills** -- what I know how to do well, what I'm learning, where I have gaps
5. **Voice and style** -- how I write, how I prefer to be communicated to, things that turn me off
6. **Goals** -- summer goals, fall semester goals, post-graduation, 5-year
7. **Fears and motivations** -- what would make this summer feel like a win, what would make it feel like a loss
8. **Tools and stack** -- current daily tools, what I love, what I tolerate, what I want to try

Take notes as we go. Don't rush. We have time. Ask follow-ups. When you feel a topic is fully captured, summarize back what you heard and let me correct it before writing the wiki article.

## Output

For each topic, after the interview portion is complete:
- Write a markdown file at `wiki/personal/<topic-slug>.md` with structured content (H1 = topic name, paragraphs of synthesized notes, bullet lists where appropriate)
- Append a one-line entry to `wiki/personal/_index.md` under "## Articles"
- Append a one-line entry to `wiki/_master-index.md` under the "Personal" section

When all 8 topics are done, write one final summary file at `wiki/personal/_summary.md` that gives a 200-word elevator-pitch of who Gabe is, drawn from the 8 topic articles.

## Constraints

- Do not delete anything
- All file writes go to `wiki/personal/` (or the master index)
- This is a conversational skill -- expect to be invoked via a session where Gabe is in the chat, not as a background routine
