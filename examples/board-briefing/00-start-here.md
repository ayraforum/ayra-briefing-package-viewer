# Board Briefing Package

This example shows the package structure we can use when Ayra needs to send a compact briefing as a single HTML file or web link.

## Package shape

- **Resolutions** holds the decision material.
- **Updates** holds current context and status material.
- **Financial Documents** holds current and referenced financial documents.
- **References** holds information that may be relevant for the Board, typically external to Ayra.
- The generated landing page explains the browser and builds the "where to find things" cards from the package structure.

## Authoring note

When assembling a real package, keep the source markdown in the owning knowledge-base folder and run the viewer builder against that folder. The output HTML can sit beside the package or be published as a single web link.

