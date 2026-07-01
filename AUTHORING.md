# Authoring Guide

This guide shows the Markdown patterns used by the Ayra Briefing Package Viewer. Copy these blocks into a package folder and edit the placeholders.

## Package Folder

Create one folder for the package:

```text
board-briefing/
  package-viewer.json
  00-start-here.md
  resolutions/
    01-resolution-index.md
    02-first-resolution.md
  updates/
    01-executive-update.md
  references/
    01-background-note.md
```

Top-level folders become package areas. If `package-viewer.json` lists sections, those sections appear first; other folders with Markdown are discovered automatically unless `"auto_discover_sections": false` is set.

## Package Config

Create `package-viewer.json` in the package folder:

```json
{
  "title": "Board Briefing Package",
  "subtitle": "A compact package for resolutions, updates, and supporting material.",
  "audience": "Prepared for Board review.",
  "labels": ["CONFIDENTIAL:BOARD"],
  "output": "board-briefing-viewer.html",
  "landing": {
    "file": "00-start-here.md",
    "intro": "Start here for the shape of the package. Use the package areas to find decision items, updates, and supporting material."
  },
  "sections": [
    {
      "id": "resolutions",
      "title": "Resolutions",
      "description": "Decision items, draft resolution language, and supporting notes.",
      "path": "resolutions"
    },
    {
      "id": "updates",
      "title": "Updates",
      "description": "Operating updates and current context.",
      "path": "updates"
    }
  ]
}
```

## Start Page

Create `00-start-here.md`:

```markdown
# Board Briefing Package

This package collects the materials needed for Board review.

## Package shape

- **Resolutions** holds decision items.
- **Updates** holds current context.
- **References** holds supporting material.

## Reading path

1. Start with the resolution index.
2. Read supporting updates where a resolution depends on current context.
3. Use references for background material.
```

## Standard Document

Use this for ordinary updates, references, notes, and supporting material:

```markdown
---
title: Executive Update
summary: One sentence explaining what this document contains.
confidentiality: CONFIDENTIAL:BOARD
order: 1
---
# Executive Update

## Current position

Write the short update here.

## What changed

- First change.
- Second change.

## Open items

- First open item.
- Second open item.
```

## Resolution Index

For governance packages, start from [templates/resolution-index.md](templates/resolution-index.md).

Use an index file when a section contains a maintained list of items. For resolutions, create `resolutions/01-resolution-index.md`:

```markdown
---
title: Resolution Index
summary: A maintained table of contents for the resolutions included in the package.
confidentiality: CONFIDENTIAL:BOARD
order: 1
---
# Resolution Index

Use this file as the maintained list of resolutions in the package. Each row in the table should point to one resolution document in this folder.

## Current resolutions

| # | Resolution | File | Status | Classification | Owner |
| --- | --- | --- | --- | --- | --- |
| 1 | Approve annual budget | [[02-approve-annual-budget]] | Draft | CONFIDENTIAL:BOARD | Treasurer |
| 2 | Confirm public supporting item | [[03-confirm-public-supporting-item]] | Draft | PUBLIC | Governance |

## Maintenance note

When adding a resolution, create the next numbered file and add a matching row to the table above.
```

## Resolution Document

For governance packages, start from [templates/resolution.md](templates/resolution.md).

Create one numbered file per resolution, for example `resolutions/02-approve-annual-budget.md`:

```markdown
---
title: Approve Annual Budget
summary: One sentence explaining what the Board is being asked to decide.
confidentiality: CONFIDENTIAL:BOARD
order: 2
---
# Approve Annual Budget

## Document control

| Field | Value |
| --- | --- |
| Resolution ID | BR-002 |
| Status | Draft |
| Owner | Treasurer |
| Decision date | [meeting date] |
| Classification | CONFIDENTIAL:BOARD |

## Proposed action

That the Board approve the annual budget for [period].

## Rationale

Explain why the decision is needed now.

## Draft resolution text

Resolved, that [formal resolution language].

## Supporting materials

- [[../financials/01-budget-summary]]
- [[../updates/01-executive-update]]

## Notes

Add drafting notes, dependencies, or open questions.
```

## Classification Values

Use one of these values in `labels`, `label`, `classification`, or `confidentiality` frontmatter:

| Value | Use when |
| --- | --- |
| PUBLIC | The item can be shared outside Ayra. |
| CONFIDENTIAL:BOARD | The item is Board-only. |
| CONFIDENTIAL:MEMBER | The item relates to a specific member or members. |
| CONFIDENTIAL:AYRA | The item is for Ayra staff and members. |
| CONFIDENTIAL:STAFF | The item is for Ayra staff only. |

## Build

Run the builder from the viewer repo:

```bash
python3 -B -m ayra_package_viewer path/to/package-folder
```

## Agent Instructions for Governance Repositories

When a governance repository will regularly produce briefing packages, add an agent-facing instruction file that points agents to this viewer and its skill.

For Codex, add or update `AGENTS.md` in the governance repo:

````markdown
# AGENTS.md

When assembling Board, member, election, nomination, nominee, governance, or update briefing packages, use the Ayra Briefing Package Viewer.

Viewer repo:

`/Users/darrellodonnell/projects/ayra-briefing-package-viewer`

Agent skill:

`/Users/darrellodonnell/projects/ayra-briefing-package-viewer/skills/build-briefing-package/SKILL.md`

Before building a package:

1. Read the skill file.
2. If copy-paste Markdown patterns are needed, read `skills/build-briefing-package/references/markdown-patterns.md`.
3. Use the viewer repo templates for governance resolutions:
   - `templates/resolution-index.md`
   - `templates/resolution.md`
4. Keep package authoring instructions out of delivered package content.
5. Build with:

```bash
python3 -B -m ayra_package_viewer path/to/package-folder
```
````

For Claude, add or update `CLAUDE.md` in the governance repo with the same operational instruction:

````markdown
# CLAUDE.md

When assembling Board, member, election, nomination, nominee, governance, or update briefing packages, use the Ayra Briefing Package Viewer.

Read this workflow before building a package:

`/Users/darrellodonnell/projects/ayra-briefing-package-viewer/skills/build-briefing-package/SKILL.md`

Use copy-paste Markdown patterns from:

`/Users/darrellodonnell/projects/ayra-briefing-package-viewer/skills/build-briefing-package/references/markdown-patterns.md`

Use resolution templates from:

- `/Users/darrellodonnell/projects/ayra-briefing-package-viewer/templates/resolution-index.md`
- `/Users/darrellodonnell/projects/ayra-briefing-package-viewer/templates/resolution.md`

Build with:

```bash
python3 -B -m ayra_package_viewer path/to/package-folder
```
````

If the governance repo should be portable across machines, vendor the skill into the repo instead of relying on an absolute path:

```text
governance-repo/
  .agents/
    skills/
      build-briefing-package/
        SKILL.md
        references/
          markdown-patterns.md
```

Then point `AGENTS.md` and `CLAUDE.md` to `.agents/skills/build-briefing-package/SKILL.md`.
