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
from src.docking.receptor_profile import resolve_target_profile, TARGET_ALIASES

DEFAULT_TARGET = "MexB"

# Nombre de hits traités automatiquement en batch (aucune sélection
# utilisateur) — mettre une valeur haute revient à "tous les hits".
AUTO_TOP_N = 500

# Noms de cibles historiques utilisés comme noms de dossiers de résultats
# (docking/results/batch_vina_engine/<target>/). Le récepteur lui-même
# n'est plus jamais stocké ici — il est résolu via receptor_profile
# (voir _receptor() ci-dessous), source unique de vérité. Étendre cette
# liste manuellement quand un nouveau couple pompe/dérépresseur est ajouté
# (Section 7 du protocole multi-récepteurs), en plus de l'alias
# correspondant dans receptor_profile.TARGET_ALIASES.
# Cibles historiques, conservées comme socle minimal.
KNOWN_TARGET_LABELS = ["MexB", "MexR"]


def known_target_labels() -> list:
    """
    Toutes les cibles connues du logiciel, découvertes dynamiquement.

    Trois sources cumulées :
        1. les cibles historiques MexB / MexR ;
        2. tous les profils déclarés dans receptor_profiles/*.json ;
        3. tous les dossiers de résultats réellement présents sous
           docking/results/batch_vina_engine/.

    La source 3 est indispensable : un récepteur importé puis son
    profil supprimé laisse malgré tout des fichiers à nettoyer, et un
    récepteur docké doit voir ses hits chargés même si son profil a
    changé de nom entre-temps.

    Remplace la liste écrite en dur, qui faisait que le nettoyage de
    fin de session et le traitement PLIP en lot ignoraient purement et
    simplement tous les récepteurs ajoutés après MexB/MexR.
    """

    labels = list(KNOWN_TARGET_LABELS)

    try:
        from src.docking.receptor_profile import list_profile_ids

        for profile_id in list_profile_ids():
            if profile_id not in labels:
                labels.append(profile_id)
    except Exception:
        pass

    try:
        if BATCH_ROOT.is_dir():
            for child in sorted(BATCH_ROOT.iterdir()):
                if child.is_dir() and child.name not in labels:
                    labels.append(child.name)
    except Exception:
        pass

    return labels

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
    return resolve_target_profile(target).pdbqt_path


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


def hit_result_key(target: str, molecule: str) -> str:
    """Clé unique pour hit_results : deux cibles différentes (MexB, MexR,
    ou tout autre couple pompe/dérépresseur) peuvent doquer un ligand du
    même nom — sans le suffixe cible, la seconde cible traitée écrasait
    purement et simplement les résultats de la première dans le
    dictionnaire (c'était toujours la dernière de known_target_labels()
    qui survivait, en général le dérépresseur)."""
    return f"{molecule} — {target}"


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
            self.progress.emit(f"{hit.molecule} ({hit.target})", index, total)

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

                key = hit_result_key(hit.target, hit.molecule)
                results[key] = {
                    "interactions": interactions,
                    "diagram": str(output_png),
                    "complex": str(_plip_complex_pdb(hit.target, hit.molecule)),
                    "target": hit.target,
                    "molecule": hit.molecule,
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

def export_visualization_results(batch_payload: dict, destination_dir: Path) -> Path:
    """Exporte TOUTES les cibles présentes dans batch_payload (MexB, MexR,
    ou tout autre couple), pas une seule : avant, l'appelant ne passait
    qu'une cible et le dossier d'une autre cible dockée dans la même
    campagne n'était jamais copié."""
    destination_dir = Path(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)

    results = batch_payload.get("results", {})

    targets = sorted({
        data.get("target", DEFAULT_TARGET) for data in results.values()
    }) or [DEFAULT_TARGET]

    # Une seule cible : structure plate, inchangée pour les campagnes
    # mono-récepteur existantes. Plusieurs cibles : un sous-dossier par
    # cible pour ne jamais mélanger leurs diagrammes/complexes.
    single_target = len(targets) == 1

    for target in targets:
        target_dest = destination_dir if single_target else destination_dir / target

        diagrams_src = _diagrams_dir(target)
        if diagrams_src.exists():
            shutil.copytree(diagrams_src, target_dest / "diagrammes_2d", dirs_exist_ok=True)

        plip_src = _plip_workdir(target)
        if plip_src.exists():
            shutil.copytree(plip_src, target_dest / "plip_xml_complex", dirs_exist_ok=True)

    summary_csv = destination_dir / "residus_interactions.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["target", "molecule", "residue", "residue_id", "chain", "distance", "interaction_types"],
        )
        writer.writeheader()
        for key, data in results.items():
            molecule = data.get("molecule", key)
            target = data.get("target", DEFAULT_TARGET)
            for row in data["interactions"]["summary"]:
                writer.writerow({"target": target, "molecule": molecule, **row})

    return destination_dir


# ============================================================================
# NETTOYAGE — appelé à la fermeture du logiciel
# Ne touche jamais aux résultats bruts de docking (individual/*.pdbqt,
# docking_results.csv) : uniquement les fichiers dérivés de la visualisation.
# ============================================================================

def cleanup_visualization_outputs(targets=None) -> None:
    # Toutes les cibles, pas seulement MexB/MexR : sinon les sorties
    # des récepteurs ajoutés après coup ne sont jamais nettoyées.
    targets = targets or known_target_labels()

    for target in targets:
        for folder in (_plip_workdir(target), _diagrams_dir(target), _selected_poses_dir(target)):
            if folder.exists():
                shutil.rmtree(folder, ignore_errors=True)
