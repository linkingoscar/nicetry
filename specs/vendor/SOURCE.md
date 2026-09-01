# External PROCESS 5.0 validation oracle — source and license boundary

- **Local optional file**: `process5.0.R` (ignored by Git and not distributed)
- **Upstream**: PROCESS for R, Andrew F. Hayes (2013–2025)
- **Known source**: official PROCESS for R distribution (user-provided copy path is
  configurable in `engine/R/tests/reference/generate-process-goldens.R` via
  `RESEARCHPATH_PROCESS_MACRO`)
- **SHA-256**: `3D02E6BBEC08A4A3EE9EDEB8E6300678D717A7A08E41E11C8149C04AB64B8648`
- **Copyright notice contained in the file**: “Copyright 2013-2025 by Andrew F.
  Hayes ALL RIGHTS RESERVED”
- **Purpose**: optional regeneration of frozen golden-standard evidence only.
  The product runner is an independent implementation and does not require,
  load, or execute this file.
- **License boundary**: no explicit redistribution license has been confirmed.
  ResearchPath therefore does not include the macro. A researcher who is
  authorized to use an official copy may point the generator at that local file
  with `RESEARCHPATH_PROCESS_MACRO` or the first command-line argument. Never
  add the upstream macro to Git or a release artifact without written
  redistribution permission from the copyright holder.
