# VinaStudio

[![Tests](https://github.com/divin-stoni/VinaStudio/actions/workflows/tests.yml/badge.svg)](https://github.com/divin-stoni/VinaStudio/actions/workflows/tests.yml)
[![License: GPL v2+](https://img.shields.io/badge/license-GPL--2.0--or--later-blue.svg)](LICENSE)

VinaStudio is an advanced desktop application designed for streamlined virtual molecular docking and multi-target selectivity analysis, specifically tailored for the **MexAB/MexR efflux system** in *Pseudomonas aeruginosa*.

## Key Features
- **Dual-Target Selectivity Engine:** Simultaneous evaluation of ligands against pump (MexB) and regulatory (MexR) targets.
- **Integrated Pipeline:** Seamless transition from raw SDF inputs to scientifically interpretable results.
- **Automated Docking:** Powered by AutoDock Vina, with automated grid generation and log parsing.
- **Advanced Statistical Analysis:** Automated fusion of docking results with Pearson/Spearman correlations and bootstrap confidence intervals.
- **Structural Visualization:** Integrated 3D viewer with PLIP interaction analysis and pocket detection (via `fpocket`).
- **Reproducibility:** Native session management to track all experiment parameters and intermediate data.

## Installation
VinaStudio is a cross-platform application. Detailed installation instructions and binary releases for Windows and Linux are available in the [Releases](https://github.com/divin-stoni/VinaStudio/releases) section.

## Usage
1.  **Prepare:** Import SDF/phytochemical libraries and prepare for docking.
2.  **Dock:** Configure targets and run AutoDock Vina directly from the GUI.
3.  **Analyze:** Use the statistical engine to calculate selectivity indices and analyze hits.
4.  **Visualize:** Explore binding poses, pockets, and interactions in the 3D viewer.
5.  **Export:** Generate reproducible scientific reports and session files.

## Documentation
For a detailed description of the scientific methodology and features, please refer to the [VinaStudio Article](ARTICLE_VinaStudio.md).

## Citation
If you use VinaStudio in your research, please cite:
Divin Stoni MBANIMI, et al. (2026). VinaStudio: An Integrated Desktop Workflow for Virtual Screening and Selectivity Analysis.

## License
VinaStudio is distributed under the GNU General Public License, version 2 or (at your option) any later version (GPL-2.0-or-later). See `LICENSE` and `THIRD_PARTY_NOTICES.md`.
