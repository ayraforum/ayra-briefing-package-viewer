# Markdown Patterns

Use these patterns when assembling a package from loose Markdown files.

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

When a package should include canonical Markdown that lives outside the package folder, use configured document objects instead of copying the file:

```json
{
  "id": "resolutions",
  "title": "Resolutions",
  "description": "Decision items, draft resolution language, and supporting notes.",
  "path": "resolutions",
  "documents": [
    "01-resolution-index.md",
    {
      "source": "../../board-resolutions/drafts/2026-001-example.md",
      "display_path": "board-resolutions/drafts/2026-001-example.md",
      "order": 2
    }
  ]
}
```

Relative `source` paths are resolved from the package root first, then from the section folder. Optional fields include `display_path`, `title`, `summary`, `labels`, and `order`.

When a section needs internal hierarchy, use `groups` instead of a flat `documents` list:

```json
{
  "id": "key-material",
  "title": "Key Material",
  "description": "Supporting material grouped by agenda topic.",
  "path": "key-material",
  "groups": [
    {
      "id": "agenda-2",
      "title": "Agenda Topic 2 — Updates",
      "description": "Status context for the no-vote update segment.",
      "documents": [
        "01-executive-update.md",
        "02-calendar-status.md"
      ]
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

## Ordinary Document

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

## PDF Attachment

Use PDFs as package attachments, not embedded content. Put the PDF in the relevant folder, for example:

```text
financials/
  01-financials-index.md
  2026-q2-financial-statements.pdf
```

Create a Markdown index beside the PDF:

```markdown
---
title: Financials Index
summary: Board-facing index of the financial statements included in the package.
confidentiality: CONFIDENTIAL:BOARD
order: 1
---
# Financials Index

## Included statements

| Statement | File | Notes |
| --- | --- | --- |
| Q2 financial statements | [[2026-q2-financial-statements.pdf]] | Review before the budget resolution. |
```

The viewer can list PDF files and link to them. It does not embed PDF contents into the generated HTML.

## Classification Config

Classification levels are defined in `ayra_package_viewer/classification-levels.json`:

```json
{
  "label": "CONFIDENTIAL:BOARD",
  "visible_label": "CONFIDENTIAL:BOARD",
  "description": "Confidential to the Board. Use for material restricted to Board review, deliberation, or decision-making.",
  "value": 40
}
```

Higher `value` means more confidential.

## Resolution Index

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

## Reading path

1. Review this index first.
2. Open each resolution in order.
3. Read supporting sections where a resolution depends on context.
```

## Resolution Document

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
