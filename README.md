# VinaStudio

[![Tests](https://github.com/divin-stoni/VinaStudio/actions/workflows/tests.yml/badge.svg)](https://github.com/divin-stoni/VinaStudio/actions/workflows/tests.yml)
[![License: GPL v2+](https://img.shields.io/badge/license-GPL--2.0--or--later-blue.svg)](LICENSE)

VinaStudio is a desktop application (Python / PySide6) for virtual molecular docking and multi-target selectivity analysis, developed for the **MexAB/MexR efflux system** of *Pseudomonas aeruginosa*. Current version: **1.1.0**.

## What it adds
Automated docking already exists in other tools. VinaStudio's specific contribution is a **dual-criterion filter**: a candidate must have a favourable ΔG for the pump (MexB, efficacy) and a ΔG for the regulator (MexR) that stays above a risk threshold, so that it is unlikely to derepress the pump it is meant to inhibit. The threshold comes from a reference derepressor molecule supplied by the user (for example pyocyanine), not from a hard-coded value.

## Key Features
- **Dual-target docking and selectivity analysis:** MexB and MexR docking with AutoDock Vina, selectivity index, dual-criterion filter, and a predictive mode that estimates MexR-related risk from the MexB score alone.
- **Reference molecules:** inhibitors, substrates, derepressors and co-crystal ligands can be declared as references; only the references can be re-docked and merged with existing results.
- **Receptors:** MexB (PDB 3W9J) and MexR are built in; user receptors can be imported (PDB/PDBQT) with validation checks and an adjustable grid box.
- **Ligands:** SDF libraries, plus a Phytomolecules tab (plant search, SDF extraction named by PubChem CID, free molecule search through PubChem).
- **Statistics:** Pearson/Spearman correlations with FDR correction, bootstrap confidence intervals, leave-one-out, ANCOVA.
- **Structure:** PLIP interaction analysis, 2D interaction diagrams, interactive 3D viewer, pocket detection (`fpocket`).
- **Sessions and export:** results of a session are temporary until exported with the single "Export results" button.
- **Interface:** French / English, customisable theme and background.

## Validation
- **Unit tests:** 32 automated tests, run on Python 3.11 and 3.14 by GitHub Actions.
- **Re-docking benchmark** (VinaStudio pipeline, 16 crystallographic RND-transporter complexes, selection criteria fixed before docking): the top-ranked pose reproduced the crystallographic ligand (RMSD < 2 Å) in 8/16 cases (50%, 95% Wilson CI 28-72%): AcrB 7/10, MexB 0/4, AdeB 1/1, CmeB 0/1. For 3W9J (MexB), the top pose is at 2.22 Å with the pose core reproduced at 0.30 Å. This is a best-case test (box centred on the crystal ligand) of pose reproduction, not of ligand ranking. Details and raw results: [`docs/validation_bench/`](docs/validation_bench/).

## Installation
Download from the [Releases](https://github.com/divin-stoni/VinaStudio/releases) page:

| Platform | File |
|---|---|
| Windows | `VinaStudio-Setup-1.1.0.exe` |
| Linux (Ubuntu/Debian) | `vinastudio_1.1.0_amd64.deb` |
| Linux (portable) | `VinaStudio-Linux-x86_64-1.1.0.tar.gz` |

Linux (.deb): `sudo apt install ./vinastudio_1.1.0_amd64.deb`

Linux (portable): `tar -xzf VinaStudio-Linux-x86_64-1.1.0.tar.gz`, then run `VinaStudio` from the extracted folder.

Windows: run the installer. SmartScreen may show a warning at first launch if the installer is not code-signed.

## Usage
1. **Prepare:** import SDF or phytochemical libraries and prepare the ligands.
2. **Dock:** choose targets, set the grid box, run AutoDock Vina from the GUI.
3. **Analyze:** compute selectivity indices, apply the dual-criterion filter, review the hits.
4. **Visualize:** explore poses, pockets and interactions in 3D and 2D.
5. **Export:** export results and session files in one folder.

## Limitations
VinaStudio produces computational predictions only; no experimental validation of the selected compounds is included. Docking scores are best read as relative rankings: in the re-docking benchmark above, MexB poses were not reproduced as top-ranked poses. The software depends on external tools (AutoDock Vina, Open Babel, PLIP, fpocket).

## Documentation
Scientific methodology and features: [VinaStudio article](ARTICLE_VinaStudio.md), [paper.md](paper.md), [CHANGELOG.md](CHANGELOG.md).

## Citation
If you use VinaStudio in your research, please cite the metadata in [`CITATION.cff`](CITATION.cff):
Divin Stoni MBANIMI, et al. (2026). VinaStudio: An Integrated Desktop Workflow for Virtual Screening and Selectivity Analysis.

## License
VinaStudio is distributed under the GNU General Public License, version 2 or (at your option) any later version (GPL-2.0-or-later). See `LICENSE` and `THIRD_PARTY_NOTICES.md`.
