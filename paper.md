---
title: 'VinaStudio: An Integrated Desktop Workflow for Virtual Screening and Selectivity Analysis in MexAB/MexR Efflux Systems'
authors:
  - name: Divin Stoni MBANIMI
    affiliation: 1
  - name: Cyr Abraham YONDZA KOUMBA
    affiliation: 1
  - name: N'TOLLAUD Challenge Providence
    affiliation: 1
affiliations:
  - name: Master 2 Biotechnology and Health, UM6SS
    index: 1
date: 25 October 2026
---

# Summary

VinaStudio is an integrated Python/PySide6 desktop application designed to streamline virtual molecular docking and multi-target selectivity analysis, specifically tailored for the MexAB/MexR efflux pump system in *Pseudomonas aeruginosa*. Unlike conventional docking tools that focus solely on binding affinity, VinaStudio implements a "dual-target" filtering logic, simultaneously evaluating ligands against both efflux pump targets and regulatory sites. By integrating ligand preparation, AutoDock Vina-based docking, statistical analysis, and structural interaction visualization into a single reproducible workflow, VinaStudio reduces the friction between raw computational output and meaningful biological hypothesis generation.

# Statement of need

Virtual screening pipelines in pharmacology often require fragmented workflows involving separate tools for ligand preparation, docking execution, post-processing of results, and statistical analysis. This fragmentation complicates the analysis of selectivity, particularly in efflux systems where a therapeutic candidate must satisfy affinity constraints for both the efflux pump and its regulatory mechanism to be truly effective. Researchers currently lack a unified, user-friendly environment that links these steps while preserving data provenance. VinaStudio addresses this need by providing a compact, GUI-based research workflow that normalizes docking outputs, calculates selectivity indices, and supports comparative analysis, thereby enabling researchers to shift their focus from technical orchestration to biological interpretation.

# Key Features

- **Integrated Workflow:** Seamless transition from raw SDF/phytochemical input preparation to final scientific reports.
- **Dual-Target Selectivity Engine:** Built-in support for "pump+regulator" campaigns, calculating selectivity indices and facilitating multi-target hypothesis generation.
- **Robust Docking Engine:** Automation of AutoDock Vina configurations, grid-box management, and result parsing.
- **Advanced Post-Processing:** Automated statistical pipelines, including Pearson/Spearman correlations and bootstrap confidence intervals, to quantify the uncertainty of selectivity estimates.
- **Structural Interpretation:** Integrated 3D visualization using PLIP and pocket detection via `fpocket` to bridge the gap between quantitative docking scores and structural mechanisms.
- **Reproducibility:** Native session management to track all intermediate data and configuration parameters, ensuring experiment transparency.

# Validation

Re-docking validation was performed with the VinaStudio pipeline on 16 crystallographic complexes of RND transporters (AcrB n = 10, MexB n = 4, AdeB n = 1, CmeB n = 1), selected using criteria fixed before docking. The top-ranked pose reproduced the crystallographic ligand (RMSD < 2 Å) in 8/16 cases (50%; 95% Wilson CI 28-72%): 7/10 for AcrB and 0/4 for MexB. For 3W9J, the top-ranked pose was at 2.22 Å, with the pose core reproduced at 0.30 Å. This is a best-case test (search box centred on the co-crystallised ligand): re-docking tests the reproduction of a known pose, not the ranking of molecules by ΔG, so MexB docking scores should be read as relative rankings rather than pose predictions. Five further AcrB entries could not be evaluated because no PDB-format file was available from RCSB (mmCIF only).

# Availability

VinaStudio version 1.1.0 is released under the GPL-2.0-or-later licence. Source code, installers (Windows, Linux) and documentation are available at https://github.com/divin-stoni/VinaStudio.

# Acknowledgments

This work was developed by the lead author, Divin Stoni MBANIMI, with contributions from co-authors and testers Cyr Abraham YONDZA KOUMBA and N'TOLLAUD Challenge Providence, in the context of the M2 Biotechnology and Health program at UM6SS.

