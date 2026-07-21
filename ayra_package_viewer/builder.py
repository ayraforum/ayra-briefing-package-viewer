#!/usr/bin/env python3
"""Build a self-contained Ayra briefing package viewer from markdown.

The package folder is intentionally markdown-first. A small optional
`package-viewer.json` file can set title, labels, output path, section order,
and hand-authored landing copy. The builder has no third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Any

CONFIG_NAME = "package-viewer.json"
CLASSIFICATION_CONFIG = Path(__file__).with_name("classification-levels.json")
REPO_ROOT = Path(__file__).resolve().parent.parent
AUTHORING_SOURCE = REPO_ROOT / "AUTHORING.md"
MARKDOWN_PATTERNS_SOURCE = REPO_ROOT / "skills/build-briefing-package/references/markdown-patterns.md"
BUILD_INSTRUCTIONS_NAME = "build-instructions.html"
LANDING_CANDIDATES = (
    "00-start-here.md",
    "start-here.md",
    "Start Here.md",
    "index.md",
    "README.md",
)

LABEL_ALIASES = {
    "AYRA INTERNAL": "CONFIDENTIAL:STAFF",
    "AYRA STAFF ONLY": "CONFIDENTIAL:STAFF",
    "STAFF CONFIDENTIAL": "CONFIDENTIAL:STAFF",
    "AYRA CONFIDENTIAL": "CONFIDENTIAL:AYRA",
    "MEMBER CONFIDENTIAL": "CONFIDENTIAL:MEMBER",
    "BOARD CONFIDENTIAL": "CONFIDENTIAL:BOARD",
}


def load_classification_levels() -> dict[str, dict[str, Any]]:
    raw = json.loads(CLASSIFICATION_CONFIG.read_text(encoding="utf-8"))
    levels: dict[str, dict[str, Any]] = {}
    for item in raw:
        label = str(item["label"]).strip().upper()
        levels[label] = {
            "visible_label": str(item.get("visible_label") or label),
            "description": str(item["description"]),
            "value": float(item["value"]),
        }
    if "PUBLIC" not in levels:
        raise ValueError("classification-levels.json must define PUBLIC")
    return dict(sorted(levels.items(), key=lambda pair: pair[1]["value"]))


CLASSIFICATION_LEVELS = load_classification_levels()

PLACEHOLDER_WORDS = re.compile(
    r"name|link|date|phase|deadline|status|bracket|sender|owner|class|council|member",
    re.I,
)
LIST_LINE = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
HEADING_LINE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_LINE = re.compile(r"^(`{3,})(.*)$")
PACKAGE_FILE_SUFFIXES = {".md", ".pdf"}


@dataclass
class Document:
    id: str
    title: str
    rel_path: str
    body_md: str
    summary: str
    labels: list[str]
    order: int
    kind: str = "markdown"


@dataclass
class DocumentSource:
    path: Path
    rel_path: str
    title: str | None = None
    summary: str | None = None
    labels: list[str] | None = None
    order: int | None = None


@dataclass
class DocumentGroup:
    id: str
    title: str
    description: str
    documents: list[Document]


@dataclass
class Section:
    id: str
    title: str
    description: str
    documents: list[Document]
    groups: list[DocumentGroup] | None = None


@dataclass
class Package:
    root: Path
    title: str
    subtitle: str
    labels: list[str]
    audience: str
    output: Path
    instructions_output: Path
    landing_md: str
    landing_intro: str
    sections: list[Section]


def esc(text: Any) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def slug(text: str, fallback: str = "item") -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value or fallback


WIKILINK_INDEX: dict[str, str] = {}


def register_wikilinks(package: "Package") -> None:
    """Map document paths (and bare filenames) to in-viewer anchors so wikilinks resolve."""
    WIKILINK_INDEX.clear()
    ambiguous: set[str] = set()
    for section in package.sections:
        for doc in section.documents:
            href = f"#{section.id}/{doc.id}"
            stem = re.sub(r"\.(md|pdf)$", "", doc.rel_path, flags=re.IGNORECASE).lower()
            WIKILINK_INDEX.setdefault(stem, href)
            base = stem.split("/")[-1]
            if base in WIKILINK_INDEX and WIKILINK_INDEX[base] != href:
                ambiguous.add(base)
            else:
                WIKILINK_INDEX.setdefault(base, href)
    for base in ambiguous:
        WIKILINK_INDEX.pop(base, None)


def resolve_wikilink(target: str) -> str | None:
    cleaned = target.strip().split("#", 1)[0]
    cleaned = re.sub(r"\.md$", "", cleaned, flags=re.IGNORECASE)
    while cleaned.startswith("../"):
        cleaned = cleaned[3:]
    cleaned = cleaned.lstrip("./").lower()
    if not cleaned:
        return None
    return WIKILINK_INDEX.get(cleaned) or WIKILINK_INDEX.get(cleaned.split("/")[-1])


def inline(text: str, highlight: bool = True) -> str:
    out = esc(text)
    stash: list[str] = []

    def keep(html: str) -> str:
        stash.append(html)
        return f"\x00{len(stash) - 1}\x00"

    out = re.sub(r"`([^`]+)`", lambda m: keep("<code>" + esc(m.group(1)) + "</code>"), out)
    out = re.sub(
        r"\{\{[^}]+\}\}",
        lambda m: keep(
            f'<span class="merge">{esc(m.group(0))}</span>' if highlight else esc(m.group(0))
        ),
        out,
    )
    out = re.sub(r"!\[\[([^\]]+)\]\]", r"<em>See: \1</em>", out)

    def wikilink(match: re.Match) -> str:
        target = match.group(1)
        label = match.group(2) if match.lastindex and match.lastindex >= 2 and match.group(2) else target.split("/")[-1]
        href = resolve_wikilink(target)
        if href:
            return keep(f'<a href="{href}">{label}</a>')
        return label

    out = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", wikilink, out)
    out = re.sub(r"\[\[([^\]]+)\]\]", wikilink, out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    if highlight:
        out = re.sub(
            r"\[([^\]\[]{1,44})\](?!\()",
            lambda m: (
                f'<span class="merge">[{esc(m.group(1))}]</span>'
                if PLACEHOLDER_WORDS.search(m.group(1))
                else m.group(0)
            ),
            out,
        )
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<em>\1</em>", out)
    out = re.sub(r"(?<![\w_])_([^_]+)_(?![\w_])", r"<em>\1</em>", out)
    out = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", out)
    for index, html in enumerate(stash):
        out = out.replace(f"\x00{index}\x00", html)
    return out


def render_list(lines: list[str], highlight: bool) -> str:
    parsed = []
    for line in lines:
        match = LIST_LINE.match(line)
        if not match:
            continue
        indent = len(match.group(1).replace("\t", "    "))
        parsed.append((indent, match.group(2)[0].isdigit(), match.group(3)))

    out: list[str] = []
    stack: list[tuple[int, str]] = []
    for indent, ordered, text in parsed:
        tag = "ol" if ordered else "ul"
        if not stack:
            out.append(f"<{tag}>")
            stack.append((indent, tag))
        elif indent > stack[-1][0]:
            out.append(f"<{tag}>")
            stack.append((indent, tag))
        else:
            out.append("</li>")
            while len(stack) > 1 and indent < stack[-1][0]:
                _, closing = stack.pop()
                out.append(f"</{closing}></li>")
        out.append("<li>" + inline(text, highlight))
    if parsed:
        out.append("</li>")
    while stack:
        _, closing = stack.pop()
        out.append(f"</{closing}>")
        if stack:
            out.append("</li>")
    return "".join(out)


def is_table_separator(line: str) -> bool:
    return bool(re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]+\|?\s*$", line))


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def heading_anchor(text: str, prefix: str = "") -> str:
    base = "h-" + slug(re.sub(r"\*+", "", text), "heading")
    return f"{slug(prefix, 'doc')}-{base}" if prefix else base


def render_markdown(markdown: str, highlight: bool = True, anchor_prefix: str = "") -> str:
    lines = markdown.replace("\r\n", "\n").split("\n")
    html: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        fence = FENCE_LINE.match(line)
        if fence:
            fence_len = len(fence.group(1))
            closing_fence = re.compile(rf"^`{{{fence_len},}}\s*$")
            code: list[str] = []
            i += 1
            while i < len(lines) and not closing_fence.match(lines[i]):
                code.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            html.append("<pre><code>" + esc("\n".join(code)) + "</code></pre>")
            continue

        heading = HEADING_LINE.match(line)
        if heading:
            level = min(6, len(heading.group(1)) + 1)
            text = heading.group(2)
            html.append(
                f'<h{level} id="{heading_anchor(text, anchor_prefix)}">{inline(text, highlight)}</h{level}>'
            )
            i += 1
            continue

        if "|" in line and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            headers = split_table_row(line)
            i += 2
            rows = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append(split_table_row(lines[i]))
                i += 1
            head = "".join(f"<th>{inline(c, highlight)}</th>" for c in headers)
            body = "".join(
                "<tr>" + "".join(f"<td>{inline(c, highlight)}</td>" for c in row) + "</tr>"
                for row in rows
            )
            html.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
            continue

        if re.match(r"^\s*>\s?", line):
            quote: list[str] = []
            while i < len(lines) and re.match(r"^\s*>\s?", lines[i]):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            kind = ""
            callout = re.match(r"^\[!(\w+)\]\s*(.*)$", quote[0] if quote else "", re.I)
            if callout:
                kind = f" callout callout-{callout.group(1).lower()}"
                quote[0] = "**" + (callout.group(2) or callout.group(1).title()) + "**"
            html.append(
                f'<blockquote class="{kind.strip()}">'
                + render_markdown("\n".join(quote), highlight)
                + "</blockquote>"
            )
            continue

        if LIST_LINE.match(line):
            block: list[str] = []
            while i < len(lines) and LIST_LINE.match(lines[i]):
                block.append(lines[i])
                i += 1
            html.append(render_list(block, highlight))
            continue

        paragraph = [line.strip()]
        i += 1
        while (
            i < len(lines)
            and lines[i].strip()
            and not HEADING_LINE.match(lines[i])
            and not FENCE_LINE.match(lines[i])
            and not LIST_LINE.match(lines[i])
            and not re.match(r"^\s*>\s?", lines[i])
            and not ("|" in lines[i] and i + 1 < len(lines) and is_table_separator(lines[i + 1]))
        ):
            paragraph.append(lines[i].strip())
            i += 1
        html.append("<p>" + inline(" ".join(paragraph), highlight) + "</p>")
    return "\n".join(html)


def md_to_text(markdown: str) -> str:
    text = re.sub(r"```[^\n]*\n?", "", markdown)
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"^\s*>\s?", "", line)
        line = re.sub(r"^#{1,6}\s+", "", line)
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    lines = markdown.replace("\r\n", "\n").split("\n")
    if not lines or lines[0] != "---":
        return {}, markdown
    data: dict[str, Any] = {}
    body_start = 0
    for index in range(1, len(lines)):
        if lines[index] == "---":
            body_start = index + 1
            break
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[index])
        if match:
            key, value = match.group(1), match.group(2).strip()
            if value.startswith("[") and value.endswith("]"):
                data[key] = [part.strip().strip('"') for part in value[1:-1].split(",") if part.strip()]
            else:
                data[key] = value.strip('"')
    if not body_start:
        return {}, markdown
    return data, "\n".join(lines[body_start:]).lstrip("\n")


def doc_title(frontmatter: dict[str, Any], body: str, path: Path) -> str:
    if frontmatter.get("title"):
        return str(frontmatter["title"])
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip().strip("*")
    stem = re.sub(r"^\d+[-_\s]*", "", path.stem)
    return stem.replace("-", " ").replace("_", " ").title()


def doc_order(frontmatter: dict[str, Any], path: Path) -> int:
    if frontmatter.get("order"):
        try:
            return int(str(frontmatter["order"]))
        except ValueError:
            pass
    match = re.match(r"^(\d+)", path.name)
    return int(match.group(1)) if match else 999


def first_paragraph(body: str) -> str:
    stripped = re.sub(r"^#\s+.+\n", "", body.strip(), count=1)
    for block in re.split(r"\n\s*\n", stripped):
        clean = block.strip()
        if clean and not clean.startswith("#") and not clean.startswith("|"):
            return md_to_text(clean).split("\n")[0][:220]
    return ""


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_label(label: str) -> str:
    normalized = re.sub(r"\s+", " ", label.strip()).upper()
    normalized = LABEL_ALIASES.get(normalized, normalized)
    if normalized not in CLASSIFICATION_LEVELS:
        allowed = ", ".join(CLASSIFICATION_LEVELS)
        raise ValueError(f"Unknown label '{label}'. Use one of: {allowed}")
    return normalized


def frontmatter_labels(frontmatter: dict[str, Any]) -> list[str]:
    raw = (
        frontmatter.get("labels")
        or frontmatter.get("label")
        or frontmatter.get("confidentiality")
        or frontmatter.get("classification")
        or []
    )
    if isinstance(raw, str):
        raw = [raw]
    return [normalize_label(str(label)) for label in raw]


def is_hidden(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def path_rel_or_display(root: Path, path: Path) -> str:
    try:
        return rel(root, path)
    except ValueError:
        return path.as_posix()


def config_labels(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = [raw]
    return [normalize_label(str(label)) for label in raw]


def load_document(root: Path, source: DocumentSource | Path) -> Document:
    if isinstance(source, Path):
        source = DocumentSource(path=source, rel_path=path_rel_or_display(root, source))

    path = source.path
    if path.suffix.lower() == ".pdf":
        title = source.title or re.sub(r"^\d+[-_\s]*", "", path.stem).replace("-", " ").replace("_", " ").title()
        return Document(
            id="doc-" + slug(source.rel_path, "doc"),
            title=title,
            rel_path=source.rel_path,
            body_md="",
            summary=source.summary or "PDF attachment. Open the file separately; it is referenced by this package but not embedded into the HTML.",
            labels=source.labels or [],
            order=source.order if source.order is not None else doc_order({}, path),
            kind="pdf",
        )

    frontmatter, body = strip_frontmatter(path.read_text(encoding="utf-8"))
    title = source.title or doc_title(frontmatter, body, path)
    body_without_h1 = re.sub(r"^#\s+.+\n", "", body, count=1)
    return Document(
        id="doc-" + slug(source.rel_path, "doc"),
        title=title,
        rel_path=source.rel_path,
        body_md=body_without_h1,
        summary=str(source.summary or frontmatter.get("summary") or first_paragraph(body)),
        labels=source.labels if source.labels is not None else frontmatter_labels(frontmatter),
        order=source.order if source.order is not None else doc_order(frontmatter, path),
    )


def discover_landing(root: Path, config: dict[str, Any]) -> tuple[Path | None, str]:
    landing_config = config.get("landing", {})
    if isinstance(landing_config, str):
        configured = root / landing_config
        return (configured, configured.read_text(encoding="utf-8")) if configured.exists() else (None, "")
    if isinstance(landing_config, dict) and landing_config.get("file"):
        configured = root / str(landing_config["file"])
        return (configured, configured.read_text(encoding="utf-8")) if configured.exists() else (None, "")
    for name in LANDING_CANDIDATES:
        candidate = root / name
        if candidate.exists():
            return candidate, candidate.read_text(encoding="utf-8")
    return None, ""


def resolve_configured_document(root: Path, section_path: Path, item: Any) -> DocumentSource | None:
    if isinstance(item, str):
        path = root / item
        if not path.exists():
            path = section_path / item
        if path.exists() and path.suffix.lower() in PACKAGE_FILE_SUFFIXES:
            return DocumentSource(path=path, rel_path=path_rel_or_display(root, path))
        return None

    if not isinstance(item, dict):
        return None

    raw_source = item.get("source") or item.get("file") or item.get("path")
    if not raw_source:
        return None

    source_path = Path(str(raw_source))
    candidates = [source_path] if source_path.is_absolute() else [root / source_path, section_path / source_path]
    path = next((candidate.resolve() for candidate in candidates if candidate.exists()), None)
    if not path or path.suffix.lower() not in PACKAGE_FILE_SUFFIXES:
        return None

    rel_path = str(
        item.get("display_path")
        or item.get("package_path")
        or item.get("rel_path")
        or raw_source
    )
    return DocumentSource(
        path=path,
        rel_path=rel_path,
        title=str(item["title"]) if item.get("title") is not None else None,
        summary=str(item["summary"]) if item.get("summary") is not None else None,
        labels=config_labels(item.get("labels") or item.get("label") or item.get("confidentiality") or item.get("classification")),
        order=int(item["order"]) if item.get("order") is not None else None,
    )


def configured_documents(root: Path, section_path: Path, docs: list[Any] | None) -> list[DocumentSource]:
    if not docs:
        return sorted(
            (
                DocumentSource(path=path, rel_path=rel(root, path))
                for path in section_path.rglob("*")
                if path.is_file()
                and path.suffix.lower() in PACKAGE_FILE_SUFFIXES
                and not is_hidden(path.relative_to(root))
            ),
            key=lambda source: source.path.as_posix().lower(),
        )
    sources = []
    for item in docs:
        source = resolve_configured_document(root, section_path, item)
        if source:
            sources.append(source)
    return sources


def load_configured_documents(root: Path, sources: list[DocumentSource], excluded: set[str]) -> list[Document]:
    documents = [load_document(root, source) for source in sources if source.rel_path not in excluded]
    documents.sort(key=lambda doc: (doc.order, doc.title.lower()))
    return documents


def assign_section_document_ids(section: Section) -> None:
    seen: dict[str, int] = {}
    for doc in section.documents:
        base = slug(f"{section.id}-{doc.rel_path}", "doc")
        seen[base] = seen.get(base, 0) + 1
        suffix = f"-{seen[base]}" if seen[base] > 1 else ""
        doc.id = f"doc-{base}{suffix}"


def load_configured_groups(root: Path, section_path: Path, raw_groups: Any, excluded: set[str]) -> tuple[list[Document], list[DocumentGroup]]:
    documents: list[Document] = []
    groups: list[DocumentGroup] = []
    if not isinstance(raw_groups, list):
        return documents, groups

    for raw in raw_groups:
        if not isinstance(raw, dict):
            continue
        group_id = slug(str(raw.get("id") or raw.get("title") or "group"), "group")
        group_path = root / str(raw.get("path")) if raw.get("path") else section_path
        sources = configured_documents(root, group_path, raw.get("documents"))
        group_docs = load_configured_documents(root, sources, excluded)
        if not group_docs:
            continue
        documents.extend(group_docs)
        groups.append(
            DocumentGroup(
                id=group_id,
                title=str(raw.get("title") or group_id.replace("-", " ").title()),
                description=str(raw.get("description") or ""),
                documents=group_docs,
            )
        )
    return documents, groups


def load_sections(root: Path, config: dict[str, Any], landing_path: Path | None) -> list[Section]:
    excluded = {CONFIG_NAME}
    if landing_path:
        excluded.add(rel(root, landing_path))
    excluded.update(str(item) for item in config.get("exclude", []))

    sections: list[Section] = []
    section_config = config.get("sections")
    configured_paths: set[str] = set()
    if section_config:
        for raw in section_config:
            section_id = slug(str(raw.get("id") or raw.get("path") or raw.get("title")), "section")
            section_path = root / str(raw.get("path") or section_id)
            if section_path.exists():
                configured_paths.add(rel(root, section_path))
            if raw.get("groups"):
                documents, groups = load_configured_groups(root, section_path, raw.get("groups"), excluded)
            else:
                doc_paths = configured_documents(root, section_path, raw.get("documents"))
                documents = load_configured_documents(root, doc_paths, excluded)
                groups = []
            if documents:
                section = Section(
                    id=section_id,
                    title=str(raw.get("title") or section_id.replace("-", " ").title()),
                    description=str(raw.get("description") or ""),
                    documents=documents,
                    groups=groups or None,
                )
                assign_section_document_ids(section)
                sections.append(section)
        if config.get("auto_discover_sections") is False:
            return sections

    for directory in sorted((path for path in root.iterdir() if path.is_dir() and not path.name.startswith(".")), key=lambda p: p.name.lower()):
        if rel(root, directory) in configured_paths:
            continue
        doc_paths = configured_documents(root, directory, None)
        documents = [load_document(root, source) for source in doc_paths if source.rel_path not in excluded]
        documents.sort(key=lambda doc: (doc.order, doc.title.lower()))
        if documents:
            section = Section(
                id=slug(directory.name, "section"),
                title=directory.name.replace("-", " ").replace("_", " ").title(),
                description="",
                documents=documents,
            )
            assign_section_document_ids(section)
            sections.append(section)

    root_docs = [
        load_document(root, path)
        for path in sorted((path for path in root.iterdir() if path.is_file() and path.suffix.lower() in PACKAGE_FILE_SUFFIXES), key=lambda p: p.name.lower())
        if rel(root, path) not in excluded
    ]
    root_docs.sort(key=lambda doc: (doc.order, doc.title.lower()))
    if root_docs:
        section = Section(id="documents", title="Documents", description="", documents=root_docs)
        assign_section_document_ids(section)
        sections.insert(0, section)
    return sections


def load_package(root: Path, output_override: str | None = None) -> Package:
    root = root.resolve()
    config = read_json(root / CONFIG_NAME)
    landing_path, landing_raw = discover_landing(root, config)
    landing_frontmatter, landing_md = strip_frontmatter(landing_raw)
    labels = [normalize_label(label) for label in config.get("labels", ["CONFIDENTIAL:AYRA"])]
    output_name = output_override or config.get("output") or f"{slug(config.get('title') or root.name)}-viewer.html"
    landing_config = config.get("landing") if isinstance(config.get("landing"), dict) else {}
    return Package(
        root=root,
        title=str(config.get("title") or landing_frontmatter.get("title") or root.name.replace("-", " ").title()),
        subtitle=str(config.get("subtitle") or landing_frontmatter.get("summary") or ""),
        labels=labels,
        audience=str(config.get("audience") or ""),
        output=(root / output_name).resolve(),
        instructions_output=(root / BUILD_INSTRUCTIONS_NAME).resolve(),
        landing_md=re.sub(r"^#\s+.+\n", "", landing_md, count=1),
        landing_intro=str(landing_config.get("intro") or config.get("intro") or ""),
        sections=load_sections(root, config, landing_path),
    )


def label_badges(labels: list[str]) -> str:
    return "".join(classification_badge(label, "label") for label in labels)


def compact_label_badges(labels: list[str]) -> str:
    return "".join(classification_badge(label, "doc-label") for label in labels)


def classification_badge(label: str, class_name: str = "label") -> str:
    level = CLASSIFICATION_LEVELS[label]
    description = level["description"]
    visible_label = level["visible_label"]
    return (
        f'<span class="classification-badge {class_name} label-{slug(label)}" '
        f'tabindex="0" role="button" title="{esc(description)}" aria-label="Show classification reference for {esc(label)}" '
        f'data-tooltip="{esc(description)}">{esc(visible_label)}</span>'
    )


def primary_label(labels: list[str]) -> str | None:
    if not labels:
        return None
    return max(labels, key=lambda label: CLASSIFICATION_LEVELS.get(label, {}).get("value", -1))


def classification_strip(labels: list[str]) -> str:
    label = primary_label(labels)
    if not label:
        return ""
    descriptions = " ".join(CLASSIFICATION_LEVELS[item]["description"] for item in labels)
    return (
        f'<div class="classification-strip strip-{slug(label)}">'
        f'<div class="classification-strip-label">{compact_label_badges(labels)}</div>'
        f'<p>{esc(descriptions)}</p>'
        f"</div>"
    )


def section_label_summary(section: Section) -> str:
    labels: list[str] = []
    for doc in section.documents:
        for label in doc.labels:
            if label not in labels:
                labels.append(label)
    if not labels:
        return ""
    return "Includes " + ", ".join(CLASSIFICATION_LEVELS[label]["visible_label"] for label in labels)


def build_landing(package: Package) -> str:
    total_docs = sum(len(section.documents) for section in package.sections)
    cards = []
    for section in package.sections:
        first_doc = section.documents[0].id if section.documents else ""
        section_meta = section_label_summary(section)
        cards.append(
            f'<button class="tile" data-go="{esc(section.id)}" data-panel="{esc(first_doc)}">'
            f'<strong>{esc(section.title)}</strong>'
            f'<span>{esc(section.description or f"{len(section.documents)} document" + ("" if len(section.documents) == 1 else "s"))}</span>'
            f'<small>{len(section.documents)} item{"" if len(section.documents) == 1 else "s"}'
            f'{(" · " + esc(section_meta)) if section_meta else ""}</small>'
            f"</button>"
        )
    intro = package.landing_intro or (
        "This browser collects the package materials into one self-contained view. "
        "Use the tabs across the top for package areas, the left navigation for individual documents, and search when you need a specific phrase."
    )
    custom = f'<section class="ov-block doc-body landing-copy">{render_markdown(package.landing_md)}</section>' if package.landing_md.strip() else ""
    audience = f'<p class="audience">{esc(package.audience)}</p>' if package.audience else ""
    return f"""
<section class="hero">
  <div class="hero-kicker">Ayra briefing package</div>
  <h1>{esc(package.title)}</h1>
  {f'<p>{esc(package.subtitle)}</p>' if package.subtitle else ''}
  {audience}
  <div class="label-row">{label_badges(package.labels)}</div>
  <div class="stats">
    <div class="stat"><strong>{len(package.sections)}</strong><span>package areas</span></div>
    <div class="stat"><strong>{total_docs}</strong><span>source documents</span></div>
    <div class="stat"><strong>{date.today().isoformat()}</strong><span>generated</span></div>
  </div>
</section>
<section class="ov-block">
  <h2>How to use this browser</h2>
  <p>{esc(intro)}</p>
  <p class="muted">The header label is the handling rule for the whole package. Individual documents may carry their own labels where an item is less restricted or has a different audience. Click any classification indicator for the full reference.</p>
</section>
<section class="ov-block">
  <h2>Where to find things</h2>
  <div class="tiles">{''.join(cards)}</div>
</section>
{custom}"""


def build_classification_reference() -> str:
    rows = []
    for label, level in CLASSIFICATION_LEVELS.items():
        rows.append(
            f"""
<article class="classification-card">
  <div>{classification_badge(label)}</div>
  <p>{esc(level["description"])}</p>
  <small>Sensitivity value: {level["value"]}</small>
</article>"""
        )
    return f"""
<section>
  <h2>Classification Levels</h2>
  <p>Use these labels to distinguish the handling rule for the overall package from the classification of individual documents inside it.</p>
</section>
<section>
  <h2>How to read the labels</h2>
  <p>The package label is the outer envelope: it tells the recipient how the delivered package should be handled. A document label describes the specific item and may be less restricted, including public material inside a Board-confidential package.</p>
</section>
<section class="classification-grid">
  {''.join(rows)}
</section>"""


def build_nav_button(doc: Document) -> str:
    return (
        f'<button class="nav-btn" data-panel="{esc(doc.id)}">'
        f'<span class="nav-title">{esc(doc.title)}</span>'
        f'<span class="nav-source">{esc(doc.rel_path)}</span></button>'
    )


def build_section_nav(section: Section) -> str:
    if section.groups:
        return "".join(
            f'<div class="nav-group">'
            f'<div class="nav-group-head"><strong>{esc(group.title)}</strong>'
            f'{f"<span>{esc(group.description)}</span>" if group.description else ""}</div>'
            f'{"".join(build_nav_button(doc) for doc in group.documents)}</div>'
            for group in section.groups
        )
    return "".join(build_nav_button(doc) for doc in section.documents)


def build_section_panels(section: Section) -> str:
    panels = []
    for doc in section.documents:
        label_text = " ".join(doc.labels)
        search_blob = esc(" ".join([doc.title, doc.rel_path, doc.summary, label_text, md_to_text(doc.body_md), doc.kind]).lower())
        summary = f'<p class="doc-summary">{esc(doc.summary)}</p>' if doc.summary else ""
        labels = classification_strip(doc.labels)
        if doc.kind == "pdf":
            panels.append(
                f"""
<section class="panel" id="{esc(doc.id)}" hidden data-search="{search_blob}">
  <div class="panel-head">
    <h2>{esc(doc.title)}</h2>
    <p class="source-path"><span>Source</span> {esc(doc.rel_path)}</p>
  </div>
  {labels}
  {summary}
  <div class="attachment-card">
    <strong>PDF attachment</strong>
    <p>This file is part of the package, but it is not embedded in the generated HTML. Keep the PDF beside the HTML output or publish it at the same relative path.</p>
    <a class="btn-link" href="{esc(doc.rel_path)}" target="_blank" rel="noopener">Open PDF</a>
  </div>
</section>"""
            )
            continue

        headings = re.findall(r"^##\s+(.+?)\s*$", doc.body_md, re.M)
        toc = ""
        if len(headings) >= 4:
            links = "".join(
                f'<a href="#{esc(section.id)}/{esc(doc.id)}/{heading_anchor(h, doc.id)}">{esc(re.sub(r"[*]+", "", h))}</a>' for h in headings
            )
            toc = f'<nav class="toc">{links}</nav>'
        panels.append(
            f"""
<section class="panel" id="{esc(doc.id)}" hidden data-search="{search_blob}">
  <div class="panel-head">
    <h2>{esc(doc.title)}</h2>
    <p class="source-path"><span>Source</span> {esc(doc.rel_path)}</p>
  </div>
  {labels}
  {summary}
  {toc}
  <div class="doc-body">{render_markdown(doc.body_md, anchor_prefix=doc.id)}</div>
</section>"""
        )
    return "".join(panels)


CSS = """
:root {
  --magenta: #ea1572;
  --sapphire: #2e55d1;
  --tangerine: #f3ab58;
  --sand: #e9e5dd;
  --slate: #073642;
  --ink: #16323c;
  --muted: #5d6f76;
  --bg: #f6f3ec;
  --panel: #ffffff;
  --line: #ddd6c8;
  --soft: #f3eee4;
  --public: #2f8f5b;
  --board-red: #e0001b;
  --sticky-offset: 72px;
  --radius: 8px;
  --shadow: 0 8px 24px rgba(7, 54, 66, 0.08);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: Poppins, "Segoe UI", system-ui, -apple-system, sans-serif;
  font-size: 15px;
  line-height: 1.6;
}
h1, h2, h3, h4 { color: var(--slate); line-height: 1.25; margin: 1.2em 0 0.5em; }
h1 { font-size: 30px; margin-top: 0; }
h2 { font-size: 20px; }
h3 { font-size: 17px; }
h4 { font-size: 15px; }
a { color: var(--sapphire); }
code {
  background: var(--soft); border: 1px solid var(--line); border-radius: 4px;
  padding: 0.05em 0.35em; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 0.9em;
}
pre { background: var(--soft); border: 1px solid var(--line); border-radius: var(--radius); padding: 12px; overflow: auto; }
pre code { background: none; border: 0; padding: 0; }
table { width: 100%; border-collapse: collapse; margin: 14px 0; background: #fff; font-size: 14px; }
th, td { border: 1px solid var(--line); padding: 7px 10px; text-align: left; vertical-align: top; }
th { background: var(--sand); color: var(--slate); }
blockquote {
  margin: 14px 0; padding: 10px 16px; border-left: 4px solid var(--sapphire);
  background: #eef1fb; border-radius: 0 var(--radius) var(--radius) 0;
}
blockquote.callout-warning, blockquote.callout-caution { border-left-color: var(--tangerine); background: #fdf3e3; }
blockquote.callout-info { border-left-color: var(--sapphire); background: #eef1fb; }
blockquote.callout-resolution {
  border: 1px solid #cfd4dc;
  border-left: 5px solid var(--slate);
  background: #f7f6f1;
  font-family: Georgia, "Times New Roman", serif;
  padding: 14px 18px;
}
blockquote.callout-resolution > p:first-child {
  font-family: inherit;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: 0.82em;
  color: var(--slate);
}
.merge {
  background: #fdeef5; border: 1px dashed var(--magenta); border-radius: 4px;
  padding: 0 4px; color: #b00f57; font-size: 0.92em; white-space: nowrap;
}
.top {
  position: sticky; top: 0; z-index: 10;
  background: var(--slate); color: #fff;
  display: flex; align-items: center; gap: 18px; flex-wrap: nowrap;
  padding: 12px 22px;
}
.brand { display: flex; align-items: baseline; gap: 10px; min-width: 130px; }
.brand .word { font-weight: 700; font-size: 20px; letter-spacing: 0.5px; }
.brand .word b { color: var(--magenta); }
.menu-toggle {
  display: none; align-items: center; justify-content: center; gap: 4px;
  width: 42px; height: 42px; border: 0; border-radius: 8px;
  background: rgba(255, 255, 255, 0.12); cursor: pointer;
}
.menu-toggle .bars span {
  display: block; width: 20px; height: 2px; border-radius: 999px;
  background: #fff;
}
.menu-toggle .bars { display: grid; gap: 4px; }
.tabs { display: flex; gap: 2px; flex-wrap: wrap; }
.tab {
  background: none; border: 0; color: #cfd9d6; font: inherit; font-weight: 500; font-size: 14px;
  padding: 8px 13px; cursor: pointer; border-radius: 8px;
}
.tab:hover { color: #fff; }
.tab.active { color: #fff; background: rgba(255, 255, 255, 0.12); box-shadow: inset 0 -3px 0 var(--magenta); }
.classification-badge {
  position: relative; display: inline-flex; align-items: center; width: fit-content;
  color: var(--slate); background: var(--tangerine); border-radius: 999px;
  font-weight: 800; letter-spacing: 0.7px; text-transform: uppercase;
  box-shadow: 0 1px 0 rgba(7, 54, 66, 0.12);
  cursor: help; outline: none;
}
.classification-badge::after {
  content: attr(data-tooltip);
  position: absolute; left: 0; top: calc(100% + 9px); z-index: 30;
  width: min(300px, 72vw); padding: 10px 12px; border-radius: 8px;
  background: var(--slate); color: #fff; text-transform: none; letter-spacing: 0;
  font-size: 12px; font-weight: 500; line-height: 1.45;
  box-shadow: 0 10px 26px rgba(7, 54, 66, 0.2);
  opacity: 0; pointer-events: none; transform: translateY(-3px);
  transition: opacity 120ms ease, transform 120ms ease;
}
.classification-badge:hover::after, .classification-badge:focus-visible::after {
  opacity: 1; transform: translateY(0);
}
.classification-badge:focus-visible { box-shadow: 0 0 0 3px rgba(46, 85, 209, 0.22); }
.label { font-size: 12px; padding: 5px 11px; }
.doc-label { margin-left: 8px; padding: 3px 9px; font-size: 10.5px; vertical-align: middle; }
.label-public { background: var(--public); color: #fff; }
.label-confidential-staff { background: var(--tangerine); color: var(--slate); }
.label-confidential-ayra { background: var(--magenta); color: #fff; }
.label-confidential-member { background: var(--sapphire); color: #fff; }
.label-confidential-board { background: var(--board-red); color: #fff; }
.doc-label.label-public { background: var(--public); color: #fff; }
.doc-label.label-confidential-staff { background: var(--tangerine); color: var(--slate); }
.doc-label.label-confidential-ayra { background: var(--magenta); color: #fff; }
.doc-label.label-confidential-member { background: var(--sapphire); color: #fff; }
.doc-label.label-confidential-board { background: var(--board-red); color: #fff; }
.searchbar {
  position: sticky; top: var(--top-height, 58px); z-index: 9;
  background: #fbf9f4; border-bottom: 1px solid var(--line);
  padding: 10px 22px; display: flex; justify-content: center;
}
.layout.no-search .searchbar { display: none; }
.searchwrap { display: flex; align-items: center; gap: 10px; width: min(440px, 100%); }
#search {
  border: 0; border-radius: 8px; padding: 8px 12px; font: inherit; font-size: 13px;
  width: 100%; background: #fff; border: 1px solid var(--line);
}
#search-count { font-size: 12px; color: var(--muted); white-space: nowrap; }
.layout { display: grid; grid-template-columns: 310px minmax(0, 1fr); min-height: calc(100vh - 58px); }
.layout.no-aside { grid-template-columns: 1fr; }
.layout.no-aside aside { display: none; }
aside {
  background: #fbf9f4; border-right: 1px solid var(--line);
  padding: 18px 14px; position: sticky; top: 58px; height: calc(100vh - 58px); overflow: auto;
}
main { padding: 26px 30px 60px; min-width: 0; }
.shell { max-width: 1000px; margin: 0 auto; }
.nav-group {
  margin-bottom: 14px; padding: 11px 10px 10px 12px;
  background: #f0e8dc; border: 1px solid #d9cdbb; border-left: 4px solid var(--tangerine);
  border-radius: 8px;
}
.nav-group + .nav-group { margin-top: 14px; }
.nav-group-head {
  display: grid; gap: 6px; padding: 0 2px 10px; color: var(--slate);
}
.nav-group-head strong {
  width: fit-content; max-width: 100%; padding: 3px 7px;
  background: rgba(7, 54, 66, 0.09); border-radius: 4px;
  color: var(--slate); font-size: 10.5px; line-height: 1.25;
  letter-spacing: 0.8px; text-transform: uppercase;
}
.nav-group-head span {
  color: var(--muted); font-size: 12px; line-height: 1.35; font-style: italic;
}
.nav-btn {
  display: grid; gap: 3px; width: 100%;
  background: none; border: 1px solid transparent; border-radius: 8px;
  padding: 8px 10px; font: inherit; color: var(--ink);
  cursor: pointer; text-align: left;
}
.nav-group .nav-btn { padding-left: 9px; padding-right: 8px; }
.nav-btn:hover { background: rgba(255, 255, 255, 0.58); }
.nav-btn.active { background: #fff; border-color: var(--line); box-shadow: inset 3px 0 0 var(--magenta); }
.nav-title {
  font-size: 13.5px; line-height: 1.35; font-weight: 500;
}
.nav-btn.active .nav-title { font-weight: 700; }
.nav-source {
  display: block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  color: var(--muted); font-size: 10.5px; line-height: 1.25; opacity: 0.62;
}
.hero {
  background: var(--slate); color: #e8eeec; border-radius: 8px;
  padding: 30px 34px; box-shadow: var(--shadow);
}
.hero-kicker {
  color: var(--tangerine); text-transform: uppercase; letter-spacing: 1px;
  font-size: 11px; font-weight: 700; margin-bottom: 8px;
}
.hero h1 { color: #fff; }
.hero p { max-width: 76ch; color: #cfd9d6; }
.hero .audience { color: #fff; font-weight: 500; }
.label-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }
.muted { color: var(--muted); }
.stats { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 20px; }
.stat {
  background: rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 10px 16px;
  display: grid; gap: 2px; min-width: 120px;
}
.stat strong { color: var(--tangerine); font-size: 19px; }
.stat span { font-size: 12px; color: #cfd9d6; }
.ov-block { margin-top: 30px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin-top: 14px; }
.tile {
  background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 14px 16px; text-align: left; cursor: pointer; font: inherit;
  display: grid; gap: 4px; box-shadow: var(--shadow);
}
.tile:hover { border-color: var(--magenta); }
.tile strong { color: var(--slate); }
.tile span { font-size: 13px; color: var(--muted); }
.tile small { color: var(--magenta); font-weight: 600; }
.classification-hero { background: linear-gradient(135deg, var(--slate) 68%, #4a1031); }
.classification-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px; margin-top: 24px;
}
.classification-card {
  background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
  box-shadow: var(--shadow); padding: 16px;
}
.classification-card p { margin: 12px 0 0; color: var(--muted); }
.classification-card small { display: block; margin-top: 10px; color: var(--muted); font-weight: 700; }
.attachment-card {
  background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
  box-shadow: var(--shadow); padding: 18px 20px; margin-top: 14px;
}
.attachment-card strong { color: var(--slate); font-size: 16px; }
.attachment-card p { color: var(--muted); margin: 8px 0 14px; }
.btn-link {
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 8px; background: var(--sapphire); color: #fff; text-decoration: none;
  font-weight: 700; padding: 8px 13px;
}
.btn-link:hover { background: #2547ad; }
.classification-modal {
  position: fixed; inset: 0; z-index: 40; display: grid; place-items: center;
  background: rgba(7, 54, 66, 0.58); padding: 24px;
}
.classification-modal[hidden] { display: none; }
.classification-modal-panel {
  width: min(940px, 100%); max-height: min(760px, 88vh); overflow: auto;
  background: var(--bg); color: var(--ink); border-radius: 8px;
  box-shadow: 0 22px 60px rgba(7, 54, 66, 0.34); padding: 22px 24px 26px;
}
.classification-modal-head {
  display: flex; justify-content: space-between; align-items: start; gap: 18px;
  border-bottom: 1px solid var(--line); padding-bottom: 12px; margin-bottom: 16px;
}
.classification-modal-head h2 { margin: 0; }
.modal-close {
  border: 1px solid var(--line); background: #fff; color: var(--slate);
  border-radius: 8px; font: inherit; font-weight: 700; cursor: pointer;
  padding: 6px 10px;
}
.modal-close:hover { border-color: var(--slate); }
.classification-strip {
  position: sticky; top: var(--sticky-offset); z-index: 6;
  display: grid; grid-template-columns: max-content minmax(0, 1fr); align-items: center;
  gap: 14px; margin: 12px 0 14px; padding: 12px 16px;
  border-radius: 8px; border: 1px solid rgba(7, 54, 66, 0.12);
  color: #fff; box-shadow: var(--shadow);
}
.classification-strip .doc-label { margin-left: 0; border: 1px solid rgba(255, 255, 255, 0.55); }
.classification-strip p { margin: 0; font-size: 13px; font-weight: 500; color: inherit; }
.classification-strip-label { display: flex; gap: 8px; flex-wrap: wrap; }
.strip-public { background: var(--public); }
.strip-confidential-staff { background: var(--tangerine); color: var(--slate); }
.strip-confidential-ayra { background: var(--magenta); }
.strip-confidential-member { background: var(--sapphire); }
.strip-confidential-board { background: var(--board-red); }
.panel-head { display: grid; gap: 5px; margin-bottom: 6px; }
.panel-head h2 { margin: 0; }
.source-path {
  margin: 0; color: var(--muted); font-size: 11.5px; line-height: 1.35;
  overflow-wrap: anywhere; opacity: 0.66;
}
.source-path span {
  margin-right: 5px; color: var(--slate); font-size: 10px; font-weight: 700;
  letter-spacing: 0.6px; text-transform: uppercase; opacity: 0.68;
}
.doc-summary { color: var(--muted); max-width: 78ch; }
.doc-body {
  background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
  box-shadow: var(--shadow); padding: 8px 28px 22px; margin-top: 12px;
}
.landing-copy { padding-top: 14px; }
.toc {
  display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 10px;
  background: var(--soft); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 10px 14px; font-size: 13px;
}
.toc a { text-decoration: none; }
.toc a:hover { text-decoration: underline; }
.footer-note { margin-top: 40px; color: var(--muted); font-size: 12px; text-align: center; }
.instructions-shell { padding: 26px 30px 60px; }
.instructions-body { margin-top: 22px; }
.instructions-body h2 { margin-top: 1.8em; }
.instructions-body h3 { margin-top: 1.5em; }
@media (max-width: 980px) {
  .layout, .layout.no-aside { grid-template-columns: 1fr; }
  aside { position: static; height: auto; max-height: 42vh; border-right: 0; border-bottom: 1px solid var(--line); }
  .searchwrap { width: 100%; }
  .searchbar { padding: 9px 14px; }
  .classification-strip { grid-template-columns: 1fr; gap: 8px; }
}
@media (max-width: 1120px) {
  .top { gap: 12px; padding: 10px 14px; }
  .brand { min-width: auto; }
  .menu-toggle { display: inline-flex; }
  .tabs {
    display: none; position: absolute; left: 14px; right: 14px; top: calc(100% + 8px);
    background: var(--slate); border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 8px; box-shadow: 0 14px 32px rgba(7, 54, 66, 0.26);
    padding: 8px; grid-template-columns: 1fr; gap: 4px;
  }
  .top.menu-open .tabs { display: grid; }
  .tab { text-align: left; padding: 11px 12px; }
}
@media print {
  .top, aside { display: none; }
  .layout { display: block; }
  .doc-body { box-shadow: none; }
}
"""


JS = """
const state = { view: "start", panel: {} };
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

function closeMenu() {
  const top = document.querySelector(".top");
  if (top) top.classList.remove("menu-open");
  const toggle = document.querySelector(".menu-toggle");
  if (toggle) toggle.setAttribute("aria-expanded", "false");
}

function setView(view, skipHash) {
  closeMenu();
  state.view = view;
  $$(".tab").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  $$(".viewpane").forEach((p) => { p.hidden = p.id !== "view-" + view; });
  $$(".navpane").forEach((p) => { p.hidden = p.id !== "nav-" + view; });
  const hasNav = !!document.getElementById("nav-" + view);
  $("#layout").classList.toggle("no-aside", !hasNav);
  $("#layout").classList.toggle("no-search", !hasNav);
  $("#search").value = "";
  applySearch();
  updateStickyOffset();
  if (hasNav) {
    const first = $("#view-" + view + " .panel");
    const stored = state.panel[view];
    if (stored && document.getElementById(stored)) setPanel(stored, true);
    else if (first) setPanel(first.id, true);
  }
  if (!skipHash) syncHash();
  window.scrollTo(0, 0);
}

function setPanel(id, skipHash) {
  state.panel[state.view] = id;
  $$("#view-" + state.view + " .panel").forEach((p) => { p.hidden = p.id !== id; });
  $$("#nav-" + state.view + " .nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.panel === id));
  if (!skipHash) syncHash();
  updateStickyOffset();
}

function syncHash() {
  const panel = state.panel[state.view];
  const hasNav = !!document.getElementById("nav-" + state.view);
  history.replaceState(null, "", "#" + state.view + (hasNav && panel ? "/" + panel : ""));
}

function scrollToAnchor(anchor) {
  if (!anchor) return;
  requestAnimationFrame(() => {
    const target = document.getElementById(anchor);
    if (target) target.scrollIntoView({ block: "start" });
  });
}

function openRoute(view, panel, anchor, replaceHash) {
  if (!view || !document.getElementById("view-" + view)) return false;
  state.panel[view] = panel || state.panel[view];
  setView(view, true);
  if (panel && document.getElementById(panel)) setPanel(panel, true);
  if (replaceHash) {
    history.replaceState(null, "", "#" + view + (panel ? "/" + panel : "") + (anchor ? "/" + anchor : ""));
  }
  scrollToAnchor(anchor);
  return true;
}

function applySearch() {
  const q = $("#search").value.trim().toLowerCase();
  $("#search-count").textContent = "";
  if (state.view === "start") return;
  let hits = 0;
  $$("#view-" + state.view + " .panel").forEach((panel) => {
    const hit = !q || panel.dataset.search.includes(q);
    panel.hidden = q ? !hit : panel.id !== state.panel[state.view];
    if (q && hit) hits += 1;
  });
  $$("#nav-" + state.view + " .nav-btn").forEach((button) => {
    const panel = document.getElementById(button.dataset.panel);
    const hit = !q || (panel && panel.dataset.search.includes(q));
    button.hidden = !hit;
  });
  if (q) $("#search-count").textContent = hits + " match" + (hits === 1 ? "" : "es");
}

document.addEventListener("click", (event) => {
  const closeClassification = event.target.closest("[data-close-classification]");
  if (closeClassification || event.target.id === "classification-modal") {
    closeClassificationReference();
    return;
  }
  const classificationBadge = event.target.closest(".classification-badge");
  if (classificationBadge) {
    openClassificationReference();
    return;
  }
  const menuToggle = event.target.closest(".menu-toggle");
  if (menuToggle) {
    const top = document.querySelector(".top");
    const open = !top.classList.contains("menu-open");
    top.classList.toggle("menu-open", open);
    menuToggle.setAttribute("aria-expanded", open ? "true" : "false");
    return;
  }
  const tab = event.target.closest(".tab");
  if (tab) return setView(tab.dataset.view);
  const tocLink = event.target.closest(".toc a");
  if (tocLink) {
    const hash = tocLink.getAttribute("href") || "";
    const [view, panel, anchor] = hash.replace(/^#/, "").split("/");
    if (openRoute(view, panel, anchor, true)) {
      event.preventDefault();
      return;
    }
  }
  const navButton = event.target.closest(".nav-btn");
  if (navButton) { setPanel(navButton.dataset.panel); window.scrollTo(0, 0); return; }
  const tile = event.target.closest("[data-go]");
  if (tile) {
    setView(tile.dataset.go);
    if (tile.dataset.panel) setPanel(tile.dataset.panel);
  }
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".top")) closeMenu();
});

$("#search").addEventListener("input", applySearch);
window.addEventListener("resize", () => {
  closeMenu();
  updateStickyOffset();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeClassificationReference();
  if ((event.key === "Enter" || event.key === " ") && event.target.closest(".classification-badge")) {
    event.preventDefault();
    openClassificationReference();
  }
});

function openClassificationReference() {
  const modal = document.getElementById("classification-modal");
  if (!modal) return;
  modal.hidden = false;
  const close = modal.querySelector("[data-close-classification]");
  if (close) close.focus();
}

function closeClassificationReference() {
  const modal = document.getElementById("classification-modal");
  if (modal) modal.hidden = true;
}

function updateStickyOffset() {
  const top = document.querySelector(".top");
  const searchbar = document.querySelector(".searchbar");
  const topHeight = top ? Math.ceil(top.getBoundingClientRect().height) : 0;
  const searchHeight = searchbar && !searchbar.hidden && getComputedStyle(searchbar).display !== "none"
    ? Math.ceil(searchbar.getBoundingClientRect().height)
    : 0;
  document.documentElement.style.setProperty("--top-height", topHeight + "px");
  document.documentElement.style.setProperty("--sticky-offset", (topHeight + searchHeight + 10) + "px");
}

function navigateFromHash(skipHash) {
  const hash = location.hash.replace(/^#/, "");
  const [view, panel, anchor] = hash.split("/");
  if (openRoute(view, panel, anchor, false)) {
    return;
  }
  setView("start", skipHash);
}

window.addEventListener("hashchange", () => navigateFromHash(false));

(function init() {
  navigateFromHash(true);
})();
"""


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>__CSS__</style>
</head>
<body>
<header class="top">
  <div class="brand"><span class="word">ayra<b>.</b></span></div>
  <button class="menu-toggle" type="button" aria-label="Open package menu" aria-expanded="false">
    <span class="bars" aria-hidden="true"><span></span><span></span><span></span></span>
  </button>
  <nav class="tabs">__TABS__</nav>
</header>
<div class="searchbar">
  <div class="searchwrap">
    <span id="search-count"></span>
    <input id="search" type="search" placeholder="Search package...">
  </div>
</div>
<div class="layout no-search" id="layout">
  <aside>__NAV__</aside>
  <main>
    <div class="shell">
      __VIEWS__
      <p class="footer-note">Generated __STAMP__ from markdown sources in this package using Ayra Briefing Package Viewer · <a href="__BUILD_INSTRUCTIONS_HREF__">Build instructions</a></p>
    </div>
  </main>
</div>
<div class="classification-modal" id="classification-modal" hidden>
  <div class="classification-modal-panel" role="dialog" aria-modal="true" aria-labelledby="classification-modal-title">
    <div class="classification-modal-head">
      <h2 id="classification-modal-title">Classification Reference</h2>
      <button class="modal-close" type="button" data-close-classification>Close</button>
    </div>
    __CLASSIFICATION_REFERENCE__
  </div>
</div>
<script>__JS__</script>
</body>
</html>
"""


BUILD_INSTRUCTIONS_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Build Instructions</title>
<style>__CSS__</style>
</head>
<body>
<header class="top">
  <div class="brand"><span class="word">ayra<b>.</b></span></div>
  <nav class="tabs"><a class="tab active" href="__PACKAGE_HREF__">Back to package</a></nav>
</header>
<main>
  <div class="shell instructions-shell">
    <section class="hero">
      <div class="hero-kicker">Ayra Briefing Package Viewer</div>
      <h1>Build Instructions</h1>
      <p>Use these instructions to assemble a package from Markdown files and rebuild the HTML viewer.</p>
    </section>
    <div class="doc-body instructions-body">__BODY__</div>
    <p class="footer-note">Generated __STAMP__ from the viewer authoring instructions.</p>
  </div>
</main>
</body>
</html>
"""


def read_instruction_source(path: Path, title: str, resource_name: str) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    try:
        return (
            resources.files("ayra_package_viewer.instructions")
            .joinpath(resource_name)
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, ModuleNotFoundError):
        pass
    return f"# {title}\n\nInstruction source not found at `{path}`."


def build_instructions_html(package: Package) -> str:
    authoring = read_instruction_source(AUTHORING_SOURCE, "Authoring Guide", "authoring.md")
    patterns = read_instruction_source(MARKDOWN_PATTERNS_SOURCE, "Markdown Patterns", "markdown-patterns.md")
    body_md = (
        "# Authoring Overview\n\n"
        + re.sub(r"^#\s+.+\n", "", authoring, count=1)
        + "\n\n# Copy-Paste Markdown Patterns\n\n"
        + re.sub(r"^#\s+.+\n", "", patterns, count=1)
    )
    package_href = package.output.name
    return (
        BUILD_INSTRUCTIONS_TEMPLATE
        .replace("__CSS__", CSS)
        .replace("__BODY__", render_markdown(body_md, highlight=False))
        .replace("__PACKAGE_HREF__", esc(package_href))
        .replace("__STAMP__", date.today().isoformat())
    )


def build_html(package: Package) -> str:
    register_wikilinks(package)
    tabs = [
        '<button class="tab" data-view="start">Start</button>',
    ]
    nav = []
    views = [
        f'<section class="viewpane" id="view-start" data-type="overview" hidden>{build_landing(package)}</section>',
    ]
    for section in package.sections:
        tabs.append(f'<button class="tab" data-view="{esc(section.id)}">{esc(section.title)}</button>')
        nav.append(f'<div class="navpane" id="nav-{esc(section.id)}" hidden>{build_section_nav(section)}</div>')
        views.append(
            f'<section class="viewpane" id="view-{esc(section.id)}" data-type="docs" hidden>'
            f'{build_section_panels(section)}</section>'
        )
    return (
        HTML_TEMPLATE
        .replace("__TITLE__", esc(package.title))
        .replace("__CSS__", CSS)
        .replace("__JS__", JS)
        .replace("__TABS__", "".join(tabs))
        .replace("__LABELS__", label_badges(package.labels))
        .replace("__NAV__", "".join(nav))
        .replace("__VIEWS__", "".join(views))
        .replace("__CLASSIFICATION_REFERENCE__", build_classification_reference())
        .replace("__BUILD_INSTRUCTIONS_HREF__", esc(package.instructions_output.name))
        .replace("__STAMP__", date.today().isoformat())
    )


def build(package_dir: Path, output_override: str | None = None) -> Package:
    package = load_package(package_dir, output_override)
    if not package.sections:
        raise ValueError(f"No markdown documents found in {package.root}")
    html = build_html(package)
    package.output.parent.mkdir(parents=True, exist_ok=True)
    package.output.write_text(html, encoding="utf-8")
    package.instructions_output.write_text(build_instructions_html(package), encoding="utf-8")
    return package


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build an Ayra briefing package viewer.")
    parser.add_argument("package_dir", nargs="?", default=".", help="Folder containing markdown package materials.")
    parser.add_argument("-o", "--output", help="Output HTML filename or path, relative to the package folder unless absolute.")
    args = parser.parse_args(argv)

    output_override = args.output
    if output_override and not Path(output_override).is_absolute():
        output_override = str(Path(output_override))
    package = build(Path(args.package_dir), output_override)
    print(f"Wrote {package.output}")
    print(f"Wrote {package.instructions_output}")
    print(f"  Package : {package.title}")
    print(f"  Labels  : {', '.join(package.labels)}")
    print(f"  Sections: {len(package.sections)}")
    print(f"  Docs    : {sum(len(section.documents) for section in package.sections)}")


if __name__ == "__main__":
    main()
