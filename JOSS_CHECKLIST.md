# JOSS submission checklist

This project is in a strong state for a scientific software submission, but some editorial metadata still needs to be finalized before a formal JOSS submission.

## Status overview

### Completed
- [x] The software has a clear scientific purpose.
- [x] The repository contains a real application, not just a toy prototype.
- [x] The README explains the actual functionality and scientific workflow.
- [x] The code includes a scientific analysis pipeline and export workflow.
- [x] The repository has automated tests.
- [x] The project has a proper open-source license.
- [x] Citation metadata exists in the repository.

### To finalize before submission
- [x] Add the final author list and affiliations.
- [x] Decide the canonical repository URL and ensure it is public.
- [ ] Finalize the software version tag.
- [x] Prepare the JOSS paper abstract and summary.
- [x] Add a final `paper.md` in the submission format required by JOSS.
- [ ] Check the runtime dependencies and installation procedure on a clean machine.

## Evidence of readiness

### Functionality
The project includes:
- ligand preparation
- receptor/profile management
- AutoDock Vina docking workflows
- scientific result fusion and selectivity calculations
- PLIP/interaction analysis and 3D visualization
- session export and data management

### Tests
The test suite is executed with:

```bash
cd /home/stoni/MexAB_MexR_Analyzer_BETA
./venv/bin/python -m pytest tests -q
```

Current verified status:
- 15 passed in 3.87s

### Documentation
The project includes:
- a functional project README,
- a license,
- citation metadata,
- a clear description of workflows and scientific intent.

## Recommended submission path

1. Confirm the final author metadata and affiliations.
2. Confirm the repository public URL: https://github.com/divin-stoni/VinaStudio
3. Finalize the software version tag.
4. Verify the installation steps on a fresh environment.
5. Submit the repository for review.

## Notes

This repository is publication-ready at the level of project structure, scientific functionality, and automated validation, but the final JOSS editorial metadata still requires the human authoring step.
