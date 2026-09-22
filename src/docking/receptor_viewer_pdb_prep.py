# -*- coding: utf-8 -*-
"""
receptor_viewer_pdb_prep.py

Prépare le fichier .pdb utilisé par le visualiseur 3D à partir d'un PDB
brut (potentiellement multi-chaînes/multi-copies) et du .pdbqt déjà
utilisé par Vina pour ce récepteur.

Détecte automatiquement, par comparaison des résidus et de leur
numérotation, quelle chaîne du PDB brut correspond au .pdbqt, et
n'extrait que celle-ci (+ ses hétéroatomes/eaux) pour le visualiseur.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ChainMatch:
    chain_id: str
    overlap: int
    pdbqt_residue_count: int
    chain_residue_count: int

    @property
    def coverage_ratio(self) -> float:
        if self.pdbqt_residue_count == 0:
            return 0.0
        return self.overlap / self.pdbqt_residue_count


def _extract_residue_signature_from_pdbqt(pdbqt_path: Path) -> set[tuple[str, int]]:
    signature = set()

    with pdbqt_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not (line.startswith("ATOM") or line.startswith("HETATM")):
                continue

            resname = line[17:20].strip()
            resnum_str = line[22:26].strip()

            try:
                resnum = int(resnum_str)
            except ValueError:
                continue

            if resname:
                signature.add((resname, resnum))

    return signature


def _extract_chains_from_pdb(pdb_path: Path) -> dict[str, set[tuple[str, int]]]:
    chains: dict[str, set[tuple[str, int]]] = {}

    with pdb_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line.startswith("ATOM"):
                continue

            chain_id = line[21:22].strip() or "_"
            resname = line[17:20].strip()
            resnum_str = line[22:26].strip()

            try:
                resnum = int(resnum_str)
            except ValueError:
                continue

            if not resname:
                continue

            chains.setdefault(chain_id, set()).add((resname, resnum))

    return chains


def detect_matching_chain(
    raw_pdb_path: Path,
    pdbqt_path: Path,
) -> tuple[Optional[ChainMatch], list[ChainMatch]]:
    pdbqt_signature = _extract_residue_signature_from_pdbqt(pdbqt_path)

    if not pdbqt_signature:
        raise ValueError(
            f"Aucun résidu exploitable trouvé dans {pdbqt_path}."
        )

    pdb_chains = _extract_chains_from_pdb(raw_pdb_path)

    if not pdb_chains:
        raise ValueError(
            f"Aucune chaîne exploitable trouvée dans {raw_pdb_path}."
        )

    matches = []

    for chain_id, chain_signature in pdb_chains.items():
        overlap = len(pdbqt_signature & chain_signature)

        matches.append(
            ChainMatch(
                chain_id=chain_id,
                overlap=overlap,
                pdbqt_residue_count=len(pdbqt_signature),
                chain_residue_count=len(chain_signature),
            )
        )

    matches.sort(key=lambda m: m.overlap, reverse=True)

    best = matches[0] if matches else None

    if best is not None and best.coverage_ratio < 0.5:
        best = None

    return best, matches


def extract_chain_for_viewer(
    raw_pdb_path: Path,
    chain_id: str,
    output_path: Path,
    keep_hetero: bool = True,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    kept_lines = []

    with raw_pdb_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            record = line[:6].strip()

            if record in ("ATOM", "HETATM"):
                line_chain = line[21:22].strip() or "_"

                if line_chain != chain_id:
                    continue

                if record == "HETATM" and not keep_hetero:
                    continue

                kept_lines.append(line)

            elif record in ("HEADER", "TITLE", "CRYST1", "REMARK", "SEQRES", "END", "TER"):
                kept_lines.append(line)

    output_path.write_text("".join(kept_lines), encoding="utf-8")

    return output_path


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Prépare un .pdb pour le visualiseur 3D à partir d'un PDB brut multi-chaînes."
    )
    parser.add_argument("raw_pdb", type=Path)
    parser.add_argument("pdbqt", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--no-hetero", action="store_true")

    args = parser.parse_args()

    print("=" * 70)
    print(f"Détection de la chaîne correspondante — {args.raw_pdb.name} <-> {args.pdbqt.name}")
    print("=" * 70)

    best, all_matches = detect_matching_chain(args.raw_pdb, args.pdbqt)

    print()
    print("Recouvrement par chaîne :")
    for match in all_matches:
        marker = " <-- MEILLEURE CORRESPONDANCE" if match is best else ""
        print(
            f"  Chaîne {match.chain_id} : {match.overlap}/{match.pdbqt_residue_count} "
            f"résidus communs ({match.coverage_ratio:.0%}){marker}"
        )

    print()

    if best is None:
        print("[ERREUR] Aucune chaîne ne correspond avec une confiance suffisante (>=50%).")
        return 1

    output = extract_chain_for_viewer(
        args.raw_pdb,
        best.chain_id,
        args.output,
        keep_hetero=not args.no_hetero,
    )

    print(f"[OK] Chaîne {best.chain_id} extraite -> {output}")
    print(f"[OK] Hétéroatomes/eaux : {'conservés' if not args.no_hetero else 'retirés'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
