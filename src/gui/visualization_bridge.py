# -*- coding: utf-8 -*-
"""
src/gui/visualization_bridge.py

Pont entre l'interface (main_window.py -> VisualizationPage) et les
moteurs backend :
    - plip_runner.py      -> calcul PLIP (extraction pose + XML + complex.pdb)
    - plip_2d_diagram.py  -> génération du diagramme 2D (structure réelle
                              de la molécule, RDKit) à partir du XML PLIP

Le projet a deux cibles (MexB, MexR), chacune avec son récepteur et
son propre dossier docking/results/batch_vina_engine/<cible>/.
Toutes les fonctions publiques prennent un paramètre `target`
(défaut "MexB", la cible principale du PFE).

Le circuit intermédiaire CSV (interaction_2d.py) a été retiré :
tout part désormais directement du XML + complex.pdb produits par
PLIPRunner, sans fichier CSV intermédiaire.

API attendue par main_window.py (NE PAS renommer) :
    load_top_hits(top_n)               -> list[Hit]
    compute_interactions_for_hit(hit)  -> {"summary": [...], "total": int, "xml": str}
    PlipWorker(hit)                    -> QObject (signals finished/failed)
    generate_2d_for_molecule(molecule) -> {"output": str}
"""

from __future__ import annotations

import csv
import re
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal

# ============================================================================
# CONFIG
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from src.visualization.plip_runner import PLIPRunner
from src.plip_2d_diagram import generate as render_2d_diagram

DEFAULT_TARGET = "MexB"

# Nombre de hits traités automatiquement en batch (aucune sélection
# utilisateur) — mettre une valeur haute revient à "tous les hits".
AUTO_TOP_N = 500

RECEPTORS = {
    "MexB": PROJECT_ROOT / "docking" / "receptor" / "3W9J.pdbqt",
    "MexR": PROJECT_ROOT / "docking" / "receptor" / "MexR" / "MEXR_1LNW.pdbqt",
}

BATCH_ROOT = PROJECT_ROOT / "docking" / "results" / "batch_vina_engine"

PLIP_WORKDIR_ROOT = PROJECT_ROOT / "visualization_results" / "plip"


def _target_root(target: str) -> Path:
    return BATCH_ROOT / target


def _ligands_dir(target: str) -> Path:
    return _target_root(target) / "individual"


def _results_csv(target: str) -> Path:
    return _target_root(target) / "docking_results.csv"


def _diagrams_dir(target: str) -> Path:
    return _target_root(target) / "2d_diagrams"


def _selected_poses_dir(target: str) -> Path:
    return _target_root(target) / "selected_poses"


def _plip_workdir(target: str) -> Path:
    return PLIP_WORKDIR_ROOT / target


def _plip_complex_pdb(target: str, molecule: str) -> Path:
    return _plip_workdir(target) / f"{molecule}_complex.pdb"


def _plip_report_xml(target: str, molecule: str) -> Path:
    # PLIPRunner crée un sous-dossier par molécule :
    # visualization_results/plip/<target>/<molecule>/
    # et écrit le rapport XML à l'intérieur.
    molecule_dir = _plip_workdir(target) / molecule

    expected = molecule_dir / f"{molecule}_complex_report.xml"
    if expected.exists():
        return expected

    # Fallback robuste : PLIP peut modifier le nom du complexe.
    reports = sorted(
        molecule_dir.glob("*_report.xml"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if reports:
        return reports[0]

    # Retourne le chemin attendu même s'il n'existe pas encore.
    # Cela permet au code appelant de produire son propre message d'erreur.
    return expected


def _receptor(target: str) -> Path:
    if target not in RECEPTORS:
        raise ValueError(f"Cible inconnue : {target}. Attendu : {list(RECEPTORS)}")
    return RECEPTORS[target]


# ============================================================================
# HIT — un ligand docké candidat pour la visualisation
# ============================================================================

@dataclass
class Hit:
    molecule: str
    score: float
    ligand_pdbqt: Path
    receptor: Path
    target: str


_VINA_SCORE_RE = re.compile(
    r"VINA RESULT:\s*(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

_MODEL_RE = re.compile(r"^MODEL\s+(\d+)", re.IGNORECASE)

_SCORE_COLUMN_CANDIDATES = ["score", "affinity", "binding_energy", "vina_score", "best_score", "energy"]
_MOLECULE_COLUMN_CANDIDATES = ["molecule", "ligand", "ligand_id", "name", "id", "cid"]


def _load_scores_from_csv(csv_path: Path) -> dict[str, float] | None:
    if not csv_path.exists():
        return None

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)

        if not reader.fieldnames:
            return None

        lower_fields = {name.lower(): name for name in reader.fieldnames}

        molecule_col = next(
            (lower_fields[c] for c in _MOLECULE_COLUMN_CANDIDATES if c in lower_fields),
            None,
        )
        score_col = next(
            (lower_fields[c] for c in _SCORE_COLUMN_CANDIDATES if c in lower_fields),
            None,
        )

        if not molecule_col or not score_col:
            return None

        scores = {}
        for row in reader:
            try:
                scores[str(row[molecule_col]).strip()] = float(row[score_col])
            except (ValueError, TypeError, KeyError):
                continue

    return scores or None


def _best_score_in_pdbqt(pdbqt_path: Path) -> float | None:
    best = None

    with pdbqt_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            match = _VINA_SCORE_RE.search(line)
            if match:
                value = float(match.group(1))
                if best is None or value < best:
                    best = value

    return best


def load_top_hits(top_n: int, target: str = DEFAULT_TARGET) -> list["Hit"]:
    ligands_dir = _ligands_dir(target)
    receptor = _receptor(target)

    if not ligands_dir.exists():
        raise FileNotFoundError(f"Dossier des ligands dockés introuvable : {ligands_dir}")

    pdbqt_by_molecule = {}
    for pdbqt_file in ligands_dir.glob("*_out.pdbqt"):
        molecule = pdbqt_file.stem
        if molecule.endswith("_out"):
            molecule = molecule[: -len("_out")]
        pdbqt_by_molecule[molecule] = pdbqt_file

    scores = _load_scores_from_csv(_results_csv(target))

    candidates = []

    if scores:
        for molecule, score in scores.items():
            pdbqt_file = pdbqt_by_molecule.get(molecule)
            if pdbqt_file is None:
                continue
            candidates.append(
                Hit(
                    molecule=molecule,
                    score=score,
                    ligand_pdbqt=pdbqt_file,
                    receptor=receptor,
                    target=target,
                )
            )
    else:
        for molecule, pdbqt_file in pdbqt_by_molecule.items():
            score = _best_score_in_pdbqt(pdbqt_file)
            if score is None:
                continue
            candidates.append(
                Hit(
                    molecule=molecule,
                    score=score,
                    ligand_pdbqt=pdbqt_file,
                    receptor=receptor,
                    target=target,
                )
            )

    candidates.sort(key=lambda hit: hit.score)

    return candidates[: max(0, int(top_n))]


# ============================================================================
# RESIDUS / INTERACTIONS — onglet "Résidus de référence"
# (lecture directe du XML PLIP, plus de CSV intermédiaire)
# ============================================================================

_CATEGORY_LABELS = {
    "hydrophobic_interactions": "Hydrophobic",
    "hydrogen_bonds": "Polar/H-bond",
    "pi_stacks": "pi-Stacking",
    "pi_cation_interactions": "pi-Cation",
    "salt_bridges": "Salt bridge",
    "halogen_bonds": "Halogen bond",
    "water_bridges": "Water bridge",
    "metal_complexes": "Metal complex",
}


def _category_label(tag: str) -> str:
    return _CATEGORY_LABELS.get(tag, tag.replace("_", " ").capitalize())


def _extract_distance(fields: dict) -> float | None:
    values = []
    for key, value in fields.items():
        if "dist" not in key.lower() or value is None:
            continue
        try:
            values.append(float(value))
        except ValueError:
            continue
    return min(values) if values else None


def _parse_plip_interactions(xml_path: Path) -> list[dict]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    rows = []

    for category in root.findall(".//interactions/*"):
        label = _category_label(category.tag)

        for interaction_elem in category:
            fields = {child.tag: (child.text or "").strip() for child in interaction_elem}

            residue = fields.get("restype", "").strip()
            residue_id = fields.get("resnr", "").strip()
            chain = fields.get("reschain", "").strip()
            distance = _extract_distance(fields)

            if not residue or not residue_id or distance is None:
                continue

            rows.append(
                {
                    "residue": residue,
                    "residue_id": residue_id,
                    "chain": chain,
                    "distance": distance,
                    "interaction_types": label,
                }
            )

    if not rows:
        raise RuntimeError(f"Aucune interaction exploitable dans {xml_path}")

    return rows


def _deduplicate_interactions(rows: list[dict]) -> list[dict]:
    grouped = {}

    for row in rows:
        key = (row["residue"], row["residue_id"], row["chain"])
        current = grouped.get(key)

        if current is None or row["distance"] < current["distance"]:
            grouped[key] = row

    return sorted(grouped.values(), key=lambda item: item["distance"])


def compute_interactions_for_hit(hit: Hit) -> dict:
    xml_path = _plip_report_xml(hit.target, hit.molecule)

    if not xml_path.exists():
        raise FileNotFoundError(
            f"Aucune interaction PLIP calculée pour {hit.molecule}. "
            f"Lance d'abord le calcul PLIP pour cette molécule."
        )

    rows = _parse_plip_interactions(xml_path)
    deduped = _deduplicate_interactions(rows)

    return {
        "summary": deduped,
        "total": len(deduped),
        "xml": str(xml_path),
    }


# ============================================================================
# EXTRACTION DE POSE (pose unique pour PLIP)
# ============================================================================

def _extract_best_pose(ligand_pdbqt: Path, output_path: Path) -> Path:
    best_pose_number = None
    best_score = None
    current_pose_number = None

    with ligand_pdbqt.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            stripped = line.strip()

            model_match = _MODEL_RE.match(stripped)
            if model_match:
                current_pose_number = int(model_match.group(1))
                continue

            score_match = _VINA_SCORE_RE.search(stripped)
            if score_match and current_pose_number is not None:
                current_score = float(score_match.group(1))
                if best_score is None or current_score < best_score:
                    best_score = current_score
                    best_pose_number = current_pose_number

    if best_pose_number is None:
        best_pose_number = 1

    inside = False
    lines = []

    model_pattern = re.compile(rf"^MODEL\s+{best_pose_number}\s*$", re.IGNORECASE)
    next_model_pattern = re.compile(r"^MODEL\s+\d+", re.IGNORECASE)

    with ligand_pdbqt.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            stripped = line.strip()

            if model_pattern.match(stripped):
                inside = True
                lines.append(line)
                continue

            if inside and next_model_pattern.match(stripped):
                break

            if inside:
                lines.append(line)
                if stripped.upper() == "ENDMDL":
                    break

    if not lines:
        raise RuntimeError(f"Impossible d'extraire une pose depuis {ligand_pdbqt}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(lines), encoding="utf-8")

    return output_path


# ============================================================================
# PLIP WORKER — onglet "Calcul PLIP" (thread dédié, ne bloque pas l'UI)
# ============================================================================

class PlipWorker(QObject):

    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, hit: Hit):
        super().__init__()
        self.hit = hit

    def run(self):
        try:
            pose_file = _selected_poses_dir(self.hit.target) / f"{self.hit.molecule}_pose_best.pdbqt"
            _extract_best_pose(self.hit.ligand_pdbqt, pose_file)

            runner = PLIPRunner(workdir=str(_plip_workdir(self.hit.target)))
            plip_result = runner.run(
                receptor=self.hit.receptor,
                pose=pose_file,
                ligand_id=self.hit.molecule,
            )

            self.finished.emit(
                {
                    "xml": plip_result["xml"],
                    "complex": plip_result["complex"],
                }
            )

        except Exception as exc:
            self.failed.emit(str(exc))


# ============================================================================
# BATCH — PLIP + diagramme 2D pour TOUS les hits, sans sélection manuelle
# ============================================================================

class BatchWorker(QObject):

    progress = Signal(str, int, int)
    finished = Signal(dict)

    def __init__(self, hits):
        super().__init__()
        self.hits = hits

    def run(self):
        results = {}
        errors = []
        total = len(self.hits)

        for index, hit in enumerate(self.hits, start=1):
            self.progress.emit(hit.molecule, index, total)

            try:
                pose_file = _selected_poses_dir(hit.target) / f"{hit.molecule}_pose_best.pdbqt"
                _extract_best_pose(hit.ligand_pdbqt, pose_file)

                runner = PLIPRunner(workdir=str(_plip_workdir(hit.target)))
                runner.run(receptor=hit.receptor, pose=pose_file, ligand_id=hit.molecule)

                interactions = compute_interactions_for_hit(hit)

                output_png = _diagrams_dir(hit.target) / hit.molecule / f"{hit.molecule}_interaction_2d.png"
                output_png.parent.mkdir(parents=True, exist_ok=True)

                render_2d_diagram(
                    _plip_report_xml(hit.target, hit.molecule),
                    _plip_complex_pdb(hit.target, hit.molecule),
                    output_png,
                    hit.molecule,
                )

                results[hit.molecule] = {
                    "interactions": interactions,
                    "diagram": str(output_png),
                }

            except Exception as exc:
                errors.append(f"{hit.molecule} : {exc}")

        self.finished.emit({"results": results, "errors": errors})


# ============================================================================
# DIAGRAMME 2D — onglet "Interaction 2D"
# (vrai diagramme moléculaire RDKit, via plip_2d_diagram.py)
# ============================================================================

def generate_2d_for_molecule(molecule: str, target: str = DEFAULT_TARGET) -> dict:
    xml_file = _plip_report_xml(target, molecule)
    complex_file = _plip_complex_pdb(target, molecule)

    if not xml_file.exists() or not complex_file.exists():
        raise FileNotFoundError(
            f"Résultats PLIP introuvables pour {molecule} ({target}). "
            f"Lance d'abord le calcul PLIP pour cette molécule."
        )

    output_png = _diagrams_dir(target) / molecule / f"{molecule}_interaction_2d.png"
    output_png.parent.mkdir(parents=True, exist_ok=True)

    render_2d_diagram(xml_file, complex_file, output_png, molecule)

    return {"output": str(output_png)}


# ============================================================================
# EXPORT — bouton "Exporter tout"
# ============================================================================

def export_visualization_results(target: str, batch_payload: dict, destination_dir: Path) -> Path:
    destination_dir = Path(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)

    diagrams_src = _diagrams_dir(target)
    if diagrams_src.exists():
        shutil.copytree(diagrams_src, destination_dir / "diagrammes_2d", dirs_exist_ok=True)

    plip_src = _plip_workdir(target)
    if plip_src.exists():
        shutil.copytree(plip_src, destination_dir / "plip_xml_complex", dirs_exist_ok=True)

    summary_csv = destination_dir / "residus_interactions.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["molecule", "residue", "residue_id", "chain", "distance", "interaction_types"],
        )
        writer.writeheader()
        for molecule, data in batch_payload.get("results", {}).items():
            for row in data["interactions"]["summary"]:
                writer.writerow({"molecule": molecule, **row})

    return destination_dir


# ============================================================================
# NETTOYAGE — appelé à la fermeture du logiciel
# Ne touche jamais aux résultats bruts de docking (individual/*.pdbqt,
# docking_results.csv) : uniquement les fichiers dérivés de la visualisation.
# ============================================================================

def cleanup_visualization_outputs(targets=None) -> None:
    targets = targets or list(RECEPTORS.keys())

    for target in targets:
        for folder in (_plip_workdir(target), _diagrams_dir(target), _selected_poses_dir(target)):
            if folder.exists():
                shutil.rmtree(folder, ignore_errors=True)
