# Feature Requests

## Single Printable View

Status: Requested

Add an output mode that produces one continuous, print-friendly view of the package.

The current viewer is optimized for browsing: sections, cards, document panels, search, and classification indicators. That works well for interactive review, but Board and member package circulation also needs a simple printable view that can be saved to PDF or printed without requiring readers to expand, navigate, or search through the package.

Desired behavior:

- Generate a single continuous document view from the same package configuration.
- Preserve package order, section headings, document titles, summaries, labels, and source/display paths.
- Include all rendered Markdown content inline.
- Keep classification markings visible at the package, section, and document levels.
- Provide print CSS that avoids awkward page breaks where practical.
- Make the output usable through browser print-to-PDF without a separate PDF generation dependency.

Open questions:

- Should printable output be a separate HTML file, such as `package-print.html`, or a print mode within the existing viewer?
- Should confidential/package labels repeat in the header or footer on each printed page where browser support allows it?
- Should attachments and external PDFs be listed as references only, or should PDF text/images ever be embedded into the printable view?
- Should hidden/closed-session material be suppressible from a member-facing printable package through configuration?
