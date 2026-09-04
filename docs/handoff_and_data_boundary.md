# Handoff and data boundary

This repository is the download-friendly software layer, not a physical-design
archive.

Allowed: reusable Python, tests, synthetic provenance-tagged configurations and
generic documentation.

Keep only in approved company storage: PDK/manuals, Cadence/OA/netlists,
customer measurements, internal presentations/comments, calibrated process or
package parameters, server/user paths, credentials and complete result trees.

The internal design handoff should have a `START_HERE`, dependency manifest,
checksums, reproduction instructions and named successor in company-controlled
storage rather than only an intern's personal account.

Before each release inspect the complete Git history, run tests, scan for
credentials/absolute paths/project names/proprietary identifiers, and obtain
project-owner approval before choosing an open-source license.
