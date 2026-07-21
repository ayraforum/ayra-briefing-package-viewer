---
name: build-briefing-package
description: Use when taking loose Markdown files and assembling them into an Ayra briefing package for the Ayra Briefing Package Viewer. Covers organizing files into package sections, adding package-viewer.json, creating landing/start pages, applying PUBLIC or CONFIDENTIAL:CAVEAT classifications, using governance resolution templates, building the HTML viewer, and verifying the result.
---

# Build Briefing Package

Use this skill when the user asks to turn loose Markdown files into a self-contained Ayra briefing package viewer, or asks for help creating Board, member, election, nomination, nominee, governance, or update packages.

## Core Workflow

1. Locate the source Markdown files and confirm the package audience, purpose, and highest package classification.
2. Create or choose a package folder in the owning repo. Do not move confidential material across repo or audience boundaries without explicit approval.
3. Organize source files into top-level section folders such as `resolutions/`, `updates/`, `financials/`, `references/`, `nominees/`, or `process/`. If one section has internal hierarchy, such as Key Material following agenda topics, configure that section with `groups` so the generated navigation preserves the context. If the source of truth already lives elsewhere in the same repo, such as formal resolution drafts, configure the section's `documents` list with external `source` paths instead of copying the files into the package.
4. Add frontmatter to each document:
   - `title`
   - `summary`
   - `confidentiality` or `labels`
   - `order`
5. Create `package-viewer.json` with package title, audience, package-level labels, output filename, landing settings, and any curated section order.
6. Create `00-start-here.md` as the package landing/start page.
7. For governance packages with resolutions, use the bundled resolution templates.
8. Build the package:

```bash
ayra-package-viewer path/to/package-folder
```

9. Verify the generated HTML includes the expected sections, document count, classification strips, and start page.

## Classification Values

Use only these canonical values:

- `PUBLIC`
- `CONFIDENTIAL:BOARD`
- `CONFIDENTIAL:MEMBER`
- `CONFIDENTIAL:AYRA`
- `CONFIDENTIAL:STAFF`

The package label is the handling rule for the delivered package. Individual documents may be less restricted or differently restricted. Example: a `CONFIDENTIAL:BOARD` package may contain a `PUBLIC` reference document.

Classification levels are configured in `ayra_package_viewer/classification-levels.json`. Higher numeric values mean more confidential and control priority when an item carries multiple labels.

## When To Read References

Read [references/markdown-patterns.md](references/markdown-patterns.md) when you need copy-paste Markdown patterns for `package-viewer.json`, start pages, ordinary documents, resolution indexes, or resolution documents.

Use the root viewer repo templates when creating real resolution files:

- `templates/resolution-index.md`
- `templates/resolution.md`

## Guardrails

- Keep authoring instructions out of delivered package content unless the package itself is instructional.
- Use package examples to demonstrate outputs, not as the only place instructions live.
- Treat financial statements and other PDFs as linked attachments; do not embed PDF contents in the generated HTML.
- Do not duplicate canonical governance records solely for package display. Use configured external `source` documents when the package should render the canonical file.
- Do not expose one member's confidential information in another member's context.
- For Ayra packages, preserve the distinction between package-level classification and document-level classification.
- After editing source Markdown or config, always rebuild the HTML and report the generated file.
