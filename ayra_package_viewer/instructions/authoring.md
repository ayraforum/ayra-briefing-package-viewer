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

Use external configured documents when the package should include a canonical source file that lives elsewhere, such as a formal resolution in a `board-resolutions/` folder. This avoids copying resolution text into the package and creating drift. In `package-viewer.json`, add a `documents` list to the section:

```json
{
  "id": "resolutions",
  "title": "Resolutions",
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

Relative `source` paths are resolved from the package root first, then from the section folder. Use `display_path` to show a stable package-friendly path in the generated viewer.

Use grouped sections when a package area needs hierarchy inside the left navigation. For example, Key Material can follow agenda topics instead of listing every document as a peer:

```json
{
  "id": "key-material",
  "title": "Key Material",
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
    },
    {
      "id": "agenda-5",
      "title": "Agenda Topic 5 — GFC Advice",
      "description": "Entity-boundary advice received or pending.",
      "documents": [
        "03-gfc-advice-status.md"
      ]
    }
  ]
}
```

## Markdown Patterns

Copy-paste patterns live in one place to avoid drift:

- [Markdown patterns](https://github.com/ayraforum/ayra-briefing-package-viewer/blob/main/skills/build-briefing-package/references/markdown-patterns.md)

For governance packages, use the reusable resolution templates:

- [Resolution index template](https://github.com/ayraforum/ayra-briefing-package-viewer/blob/main/templates/resolution-index.md)
- [Resolution template](https://github.com/ayraforum/ayra-briefing-package-viewer/blob/main/templates/resolution.md)

Financial statements and other PDFs should be referenced as attachments, not embedded. Put the PDF in the relevant package folder, such as `financials/`, and include a Markdown index that describes what the PDF is and how it should be read.

## Classification Values

Use one of these values in `labels`, `label`, `classification`, or `confidentiality` frontmatter:

| Value | Use when |
| --- | --- |
| PUBLIC | The item can be shared outside Ayra. |
| CONFIDENTIAL:BOARD | The item is Board-only. |
| CONFIDENTIAL:MEMBER | The item relates to a specific member or members. |
| CONFIDENTIAL:AYRA | The item is for Ayra staff and members. |
| CONFIDENTIAL:STAFF | The item is for Ayra staff only. |

The classification levels are configured in [classification-levels.json](https://github.com/ayraforum/ayra-briefing-package-viewer/blob/main/ayra_package_viewer/classification-levels.json). Higher numeric values mean more confidential and control sorting/priority.

## Build

Install the builder once:

```bash
pipx install git+https://github.com/ayraforum/ayra-briefing-package-viewer.git
```

Then build packages from anywhere:

```bash
ayra-package-viewer path/to/package-folder
```

## Agent Instructions for Governance Repositories

When a governance repository will regularly produce briefing packages, add an agent-facing instruction file that points agents to this viewer and its skill.

For Codex, add or update `AGENTS.md` in the governance repo:

````markdown
# AGENTS.md

When assembling Board, member, election, nomination, nominee, governance, or update briefing packages, use the Ayra Briefing Package Viewer.

Viewer repo:

`https://github.com/ayraforum/ayra-briefing-package-viewer`

Agent skill:

`https://github.com/ayraforum/ayra-briefing-package-viewer/blob/main/skills/build-briefing-package/SKILL.md`

Before building a package:

1. Read the skill file.
2. If copy-paste Markdown patterns are needed, read `https://github.com/ayraforum/ayra-briefing-package-viewer/blob/main/skills/build-briefing-package/references/markdown-patterns.md`.
3. Use the viewer repo templates for governance resolutions:
   - `https://github.com/ayraforum/ayra-briefing-package-viewer/blob/main/templates/resolution-index.md`
   - `https://github.com/ayraforum/ayra-briefing-package-viewer/blob/main/templates/resolution.md`
4. Keep package authoring instructions out of delivered package content.
5. Build with:

```bash
ayra-package-viewer path/to/package-folder
```
````

For Claude, add or update `CLAUDE.md` in the governance repo with the same operational instruction:

````markdown
# CLAUDE.md

When assembling Board, member, election, nomination, nominee, governance, or update briefing packages, use the Ayra Briefing Package Viewer.

Read this workflow before building a package:

`https://github.com/ayraforum/ayra-briefing-package-viewer/blob/main/skills/build-briefing-package/SKILL.md`

Use copy-paste Markdown patterns from:

`https://github.com/ayraforum/ayra-briefing-package-viewer/blob/main/skills/build-briefing-package/references/markdown-patterns.md`

Use resolution templates from:

- `https://github.com/ayraforum/ayra-briefing-package-viewer/blob/main/templates/resolution-index.md`
- `https://github.com/ayraforum/ayra-briefing-package-viewer/blob/main/templates/resolution.md`

Build with:

`ayra-package-viewer path/to/package-folder`
````

If the governance repo should carry its own copy of the agent instructions, copy the skill files into that repo. This makes the governance repo usable on another machine even if the viewer repo is checked out somewhere else, or not checked out at all:

```text
governance-repo/
  .agents/
    skills/
      build-briefing-package/
        SKILL.md
        references/
          markdown-patterns.md
```

Then point `AGENTS.md` and `CLAUDE.md` to `.agents/skills/build-briefing-package/SKILL.md` inside that governance repo.
