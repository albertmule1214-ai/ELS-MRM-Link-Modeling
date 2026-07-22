# Data and intellectual-property boundary

This repository follows an allowlist model.

## Allowed in Git

- Reusable source code and tests.
- Synthetic configurations with provenance labels.
- Original generic modeling documentation.
- Small synthetic examples when they contain no project-specific parameters.

## Keep local or in approved internal storage

- Papers and specification PDFs.
- Internal project documents and presentation files.
- Extracted page images and personal reading notes based on restricted material.
- Raw measurements and vendor exports.
- Project-specific device parameters, masks, PDK data and calibrated models.
- Absolute local paths, account identifiers and credentials.

The ignored directories `configs/local/` and `data/raw/` are the intended local interfaces. Before publishing any new file, review both its content and its Git history; deleting a sensitive file in a later commit does not remove it from earlier history.

