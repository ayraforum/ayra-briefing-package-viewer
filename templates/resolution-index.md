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
| 1 | Short decision name | [[02-resolution-title]] | Draft | CONFIDENTIAL:BOARD | Owner name |

## How to maintain this index

1. Create the next numbered resolution file, for example `03-new-resolution-title.md`.
2. Edit the new file's frontmatter at the top. At minimum, update `title`, `summary`, `confidentiality`, and `order`.
3. Add one row to the table above.
4. Keep the `order` value in the file aligned with the filename number so the left navigation stays predictable.

## Table row pattern

```markdown
| 2 | Short decision name | [[03-new-resolution-title]] | Draft | CONFIDENTIAL:BOARD | Owner name |
```

The `[[03-new-resolution-title]]` link should match the filename without `.md`.

