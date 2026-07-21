# Ayra Briefing Package Viewer

Build a self-contained HTML browser for an Ayra briefing package from a folder of Markdown files.

The tool is meant for governance and business packages that need to be delivered as a single HTML file or a single web link: Board briefings, election process materials, nominations packages, nominee information, member updates, and similar packages.

## Basic use

Install the builder once:

```bash
pipx install git+https://github.com/ayraforum/ayra-briefing-package-viewer.git
```

Then build packages from anywhere:

```bash
ayra-package-viewer path/to/package-folder
```

The package folder can be mostly Markdown. Add `package-viewer.json` only for values that should not be inferred cleanly from the files.

For copy-paste Markdown patterns, see [AUTHORING.md](AUTHORING.md).

For requested improvements, see [FEATURE_REQUESTS.md](FEATURE_REQUESTS.md).

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

Configured sections may also point to Markdown or PDF sources outside the package folder. Use this when a package should include a canonical governance record, such as a resolution draft, without copying it into the package and creating drift.

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
  ]
}
```

When `documents` is omitted, the viewer discovers Markdown and PDF files under the section `path`. When `documents` is present, each item may be a string path inside the package folder or an object with a `source` path. Relative `source` paths are resolved from the package root first, then from the section folder. Optional object keys include `display_path`, `title`, `summary`, `labels`, and `order`.

Sections may also use `groups` instead of a single flat `documents` list. Use groups when one package area needs internal hierarchy, such as agenda-topic support material:

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

Classification levels are configured in [classification-levels.json](ayra_package_viewer/classification-levels.json). Each level has a canonical `label`, `visible_label`, `description`, and numeric `value`. Higher `value` means more confidential and controls which classification dominates when multiple labels appear on one item.

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
ayra-package-viewer examples/board-briefing
```

This writes `examples/board-briefing/board-briefing-viewer.html`.
