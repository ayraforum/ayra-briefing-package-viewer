# Ayra Briefing Package Viewer

Build a self-contained HTML browser for an Ayra briefing package from a folder of Markdown files.

The tool is meant for governance and business packages that need to be delivered as a single HTML file or a single web link: Board briefings, election process materials, nominations packages, nominee information, member updates, and similar packages.

## Basic use

```bash
python3 -m ayra_package_viewer path/to/package-folder
```

The package folder can be mostly Markdown. Add `package-viewer.json` only for values that should not be inferred cleanly from the files.

For copy-paste Markdown patterns, see [AUTHORING.md](AUTHORING.md).

For agent-facing workflow instructions, see [skills/build-briefing-package/SKILL.md](skills/build-briefing-package/SKILL.md).

For adding the skill to a governance repo for Codex or Claude, see the "Agent Instructions for Governance Repositories" section in [AUTHORING.md](AUTHORING.md).

## Package structure

```text
package-folder/
  package-viewer.json
  00-start-here.md
  resolutions/
    01-resolution-index.md
    02-sample-resolution.md
  updates/
    01-executive-update.md
```

The builder discovers Markdown documents in configured sections, creates a generated landing page, renders Markdown into panels, adds search, and writes one standalone HTML file.

The package-level label is the handling rule for the whole delivered package. Individual Markdown files can carry their own labels in frontmatter when a specific item has a different classification, including material that is public inside a Board-confidential package.

Readers can click any classification indicator to open the classification reference. The same descriptions also appear when a reader hovers over, or keyboard-focuses, a classification badge.

When `sections` is present, those sections appear first and use their configured titles/descriptions. Other top-level folders containing Markdown are still discovered automatically and added as additional cards. Set `"auto_discover_sections": false` to make the config list exclusive.

## Config values

```json
{
  "title": "Board Briefing Package",
  "subtitle": "A compact package for resolutions and updates.",
  "audience": "Prepared for Board review.",
  "labels": ["CONFIDENTIAL:BOARD"],
  "output": "board-briefing-viewer.html",
  "landing": {
    "file": "00-start-here.md",
    "intro": "Start here for the shape of the package."
  },
  "sections": [
    {
      "id": "resolutions",
      "title": "Resolutions",
      "description": "Decision items and supporting notes.",
      "path": "resolutions"
    }
  ]
}
```

Supported labels:

- `PUBLIC` - public
- `CONFIDENTIAL:BOARD` - Board-only material
- `CONFIDENTIAL:MEMBER` - material related to a specific member or members
- `CONFIDENTIAL:AYRA` - for Ayra staff and members
- `CONFIDENTIAL:STAFF` - Ayra staff only

## Document labels

Set document-level labels in Markdown frontmatter:

```markdown
---
title: Executive Update
confidentiality: PUBLIC
---
```

You can also use `labels`, `label`, or `classification`:

```markdown
---
title: Resolution Index
labels: ["CONFIDENTIAL:BOARD"]
---
```

## Example

```bash
python3 -m ayra_package_viewer examples/board-briefing
```

This writes `examples/board-briefing/board-briefing-viewer.html`.
