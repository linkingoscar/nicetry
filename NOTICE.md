# Distribution and third-party notices

ResearchPath does not currently include a repository-wide `LICENSE` file.
Public visibility by itself does not grant permission to copy, modify, or
redistribute the repository. The repository owner must select and add the
intended source license before describing the project as open source.

The official **PROCESS for R 5.0** macro by Andrew F. Hayes is not included in
this repository. ResearchPath contains an independent estimator and frozen
validation outputs. A researcher may supply an authorized local copy of the
official macro solely to regenerate validation evidence; see
`specs/vendor/SOURCE.md`. Do not add that macro to Git or release artifacts
without written redistribution permission from the copyright holder.

Files under `samples/data/` are deterministic synthetic demonstrations produced
by `scripts/generate-method-demo-data.py`. Validation fixtures that carry a
fixture-specific license retain the notice stored beside that fixture.
Third-party packages remain governed by their own licenses as recorded in the
Python, Node, and R dependency lock files.
