# -*- coding: utf-8 -*-
"""
plip_2d_diagram.py (v2 - correspondance atomique robuste)

Genere un diagramme 2D d'interactions ligand-recepteur a partir du
report.xml PLIP. La molecule est reconstruite DIRECTEMENT depuis les
coordonnees 3D reelles du complexe (ordre PDB), avec liaisons percues
par distance puis corrigees (ordres/aromaticite) via le SMILES PLIP,
en PRESERVANT l'ordre d'origine des atomes.

Usage :
    python3 plip_2d_diagram.py --xml REPORT.xml --complex COMPLEX.pdb --output OUT.png [--molecule NOM]
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem import rdDetermineBonds
from rdkit.Chem.Draw import rdMolDraw2D


def extract_ligand_atoms(complex_pdb: Path, reschain_lig: str, restype_lig: str, resnr_lig: str):
    atoms = []
    with complex_pdb.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.startswith(("ATOM", "HETATM")):
                continue
            chain = line[21].strip()
            resname = line[17:20].strip()
            resseq = line[22:26].strip()

            # PLIP peut indiquer une chaine pour le ligand (ex. A),
            # alors que le PDB conserve UNL sans chaine.
            chain_matches = (
                chain == reschain_lig
                or (
                    not chain
                    and resname == restype_lig
                    and restype_lig == "UNL"
                )
            )

            if not chain_matches:
                continue

            if resname != restype_lig:
                continue

            if resnr_lig and resseq != str(resnr_lig):
                continue
            name = line[12:16].strip()
            element = line[76:78].strip()
            if not element:
                element = "".join(c for c in name if c.isalpha())[:1]
            if element.upper() == "H":
                continue
            try:
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
            except ValueError:
                continue
            atoms.append({"name": name, "element": element, "x": x, "y": y, "z": z})
    if not atoms:
        raise RuntimeError(
            f"Aucun atome trouve pour le ligand (chain={reschain_lig}, "
            f"resname={restype_lig}, resnr={resnr_lig}) dans {complex_pdb}"
        )
    return atoms


def nearest_atom_index(atoms, x, y, z):
    best_index = -1
    best_dist = None
    for index, atom in enumerate(atoms):
        dist = ((atom["x"] - x) ** 2 + (atom["y"] - y) ** 2 + (atom["z"] - z) ** 2) ** 0.5
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_index = index
    if best_dist is None or best_dist > 1.0:
        raise RuntimeError(
            f"Aucun atome du ligand proche de ({x}, {y}, {z}) "
            f"(distance minimale trouvee : {best_dist})."
        )
    return best_index


def nearest_ring_atoms(mol, atoms, x, y, z, tol=2.0):
    """
    Pour pi-stacking/pi-cation, PLIP donne le centroide du cycle
    aromatique, pas un atome unique. On cherche le cycle aromatique
    le plus proche de ce centroide et on retourne tous ses atomes.
    """
    ring_info = mol.GetRingInfo()
    best_ring = None
    best_dist = None
    for ring in ring_info.AtomRings():
        if not all(mol.GetAtomWithIdx(i).GetIsAromatic() for i in ring):
            continue
        cx = sum(atoms[i]["x"] for i in ring) / len(ring)
        cy = sum(atoms[i]["y"] for i in ring) / len(ring)
        cz = sum(atoms[i]["z"] for i in ring) / len(ring)
        dist = ((cx - x) ** 2 + (cy - y) ** 2 + (cz - z) ** 2) ** 0.5
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_ring = ring
    if best_ring is None or best_dist > tol:
        raise RuntimeError(
            f"Aucun cycle aromatique du ligand proche de ({x}, {y}, {z}) "
            f"(distance minimale trouvee : {best_dist})."
        )
    return list(best_ring)


def build_ligand_mol_from_pdb_atoms(smiles: str, atoms) -> Chem.Mol:
    template = Chem.MolFromSmiles(smiles)
    if template is None:
        raise RuntimeError(f"SMILES PLIP illisible par RDKit : {smiles}")
    template_kek = Chem.Mol(template)
    Chem.Kekulize(template_kek, clearAromaticFlags=True)
    n_template_bonds = template_kek.GetNumBonds()

    # DetermineConnectivity devine les liaisons uniquement a partir des
    # distances 3D (covFactor = tolerance sur la somme des rayons
    # covalents). Deux echecs symetriques sont possibles :
    #  - tolerance trop stricte -> une liaison etiree est manquee
    #  - tolerance trop large   -> sur une pose repliee (rotations libres),
    #    deux atomes non lies peuvent se retrouver proches -> liaison
    #    fantome en plus
    # Dans les deux cas, AssignBondOrdersFromTemplate echoue avec
    # "No matching found", meme si c'est la bonne molecule/pose. On balaie
    # donc une plage de tolerances stricte -> large, et on ne tente
    # l'appariement au template QUE quand le nombre de liaisons obtenu
    # correspond exactement au nombre de liaisons du SMILES (test rapide,
    # necessaire avant toute correspondance de graphe).
    cov_factors = [round(1.00 + 0.05 * i, 2) for i in range(25)]  # 1.00 .. 2.20

    last_exc: Exception | None = None
    tried_matching = 0
    for cov_factor in cov_factors:
        rw = Chem.RWMol()
        for atom in atoms:
            rw.AddAtom(Chem.Atom(atom["element"].capitalize()))
        conf = Chem.Conformer(rw.GetNumAtoms())
        for i, atom in enumerate(atoms):
            conf.SetAtomPosition(i, (atom["x"], atom["y"], atom["z"]))
        rw.AddConformer(conf)
        mol_nobonds = rw.GetMol()
        try:
            rdDetermineBonds.DetermineConnectivity(mol_nobonds, covFactor=cov_factor)
        except Exception as exc:
            last_exc = RuntimeError(f"Perception des liaisons par distance echouee : {exc}")
            continue

        if mol_nobonds.GetNumBonds() != n_template_bonds:
            # Pas le bon nombre de liaisons a cette tolerance : inutile de
            # tenter l'appariement de graphe, ca ne peut pas matcher.
            continue

        tried_matching += 1
        Chem.SanitizeMol(
            mol_nobonds,
            sanitizeOps=(Chem.SANITIZE_ALL ^ Chem.SANITIZE_KEKULIZE ^ Chem.SANITIZE_SETAROMATICITY),
        )
        try:
            fixed = AllChem.AssignBondOrdersFromTemplate(template_kek, mol_nobonds)
        except ValueError as exc:
            last_exc = RuntimeError(
                f"Correspondance PDB <-> SMILES impossible ({exc}, covFactor={cov_factor}). "
                f"Le fichier complexe et le SMILES PLIP ne decrivent probablement pas "
                f"exactement la meme molecule/pose."
            )
            continue

        for atom in fixed.GetAtoms():
            atom.SetNoImplicit(False)
            atom.SetNumRadicalElectrons(0)
        fixed.UpdatePropertyCache(strict=False)
        Chem.SanitizeMol(fixed)
        AllChem.Compute2DCoords(fixed)
        return fixed

    if last_exc is None:
        last_exc = RuntimeError(
            f"Aucune tolerance de distance (covFactor 1.00 a 2.20) n'a produit "
            f"le bon nombre de liaisons ({n_template_bonds} attendues d'apres le SMILES)."
        )
    if tried_matching == 0:
        last_exc = RuntimeError(
            f"{last_exc} Aucun covFactor teste n'a meme produit le bon nombre de "
            f"liaisons ({n_template_bonds} attendues) -> probleme de geometrie "
            f"reelle de la pose (atomes en clash ou liaison anormalement longue), "
            f"pas juste de tolerance."
        )
    raise last_exc


INTERACTION_TAGS = {
    "hydrophobic_interaction": "Hydrophobic",
    "hydrogen_bond": "Hydrogen bond",
    "pi_stack": "π-stacking",
    "pi_cation_interaction": "π-cation",
    "salt_bridge": "Salt bridge",
    "halogen_bond": "Halogen bond",
    "water_bridge": "Water bridge",
}


def parse_plip_xml(xml_file: Path) -> dict:
    tree = ET.parse(xml_file)
    root = tree.getroot()
    smiles_el = root.find(".//smiles")
    if smiles_el is None or not smiles_el.text:
        raise RuntimeError("Balise <smiles> introuvable dans le XML PLIP.")
    smiles = smiles_el.text.strip()
    interactions = []
    interactions_root = root.find(".//interactions")
    if interactions_root is None:
        raise RuntimeError("Balise <interactions> introuvable dans le XML PLIP.")
    for group in interactions_root:
        for entry in group:
            label = INTERACTION_TAGS.get(entry.tag)
            if label is None:
                continue

            def get_text(name, default=""):
                el = entry.find(name)
                return el.text.strip() if el is not None and el.text else default

            def get_coord(parent_tag):
                el = entry.find(parent_tag)
                if el is None:
                    return None
                try:
                    return (float(el.find("x").text), float(el.find("y").text), float(el.find("z").text))
                except (AttributeError, TypeError, ValueError):
                    return None

            ligcoo = get_coord("ligcoo")
            if ligcoo is None:
                for alt in ("donorcoo", "acceptorcoo"):
                    ligcoo = get_coord(alt)
                    if ligcoo is not None:
                        break
            if ligcoo is None:
                continue
            distance = (
                get_text("dist")
                or get_text("centdist")
                or get_text("dist_h-a")
                or get_text("dist_d-a")
            )
            interactions.append({
                "type": label,
                "residue": get_text("restype") + " " + get_text("resnr"),
                "chain": get_text("reschain"),
                "distance": distance,
                "ligcoo": ligcoo,
            })
    return {"smiles": smiles, "interactions": interactions}


def render_diagram(mol, interactions, atoms, output_png: Path, molecule: str):
    highlight_atoms = []
    highlight_colors = {}
    highlight_radii = {}
    atom_notes = {}
    type_colors = {
        "Hydrogen bond": (0.85, 0.1, 0.1),
        "Hydrophobic": (0.2, 0.5, 0.2),
        "π-stacking": (0.5, 0.2, 0.7),
        "π-cation": (0.7, 0.4, 0.0),
        "Salt bridge": (0.0, 0.3, 0.7),
        "Halogen bond": (0.0, 0.6, 0.6),
        "Water bridge": (0.3, 0.3, 0.3),
    }
    legend_lines = []
    skipped = []
    ring_types = ("π-stacking", "π-cation")
    for item in interactions:
        x, y, z = item["ligcoo"]
        try:
            if item["type"] in ring_types:
                atom_indices = nearest_ring_atoms(mol, atoms, x, y, z)
            else:
                atom_indices = [nearest_atom_index(atoms, x, y, z)]
        except RuntimeError as exc:
            skipped.append(f"{item['type']} ({item['residue']}) : {exc}")
            continue
        color = type_colors.get(item["type"], (0.4, 0.4, 0.4))
        for idx in atom_indices:
            highlight_atoms.append(idx)
            highlight_colors[idx] = color
            highlight_radii[idx] = 0.3
        residue_label = item["residue"].replace(" ", "")
        note = f"{residue_label} {item['distance']}Å".strip()
        anchor = None
        for candidate in atom_indices:
            if candidate not in atom_notes:
                anchor = candidate
                break
        if anchor is None:
            anchor = atom_indices[0]
        if anchor in atom_notes:
            if note not in atom_notes[anchor]:
                atom_notes[anchor].append(note)
        else:
            atom_notes[anchor] = [note]
        atom_names = ", ".join(atoms[i]["name"] for i in atom_indices)
        legend_lines.append(
            f"{item['type']} — {item['residue']} ({item['chain']}) — {item['distance']} Å "
            f"[atome(s) {atom_names}]"
        )
    for idx, notes in atom_notes.items():
        mol.GetAtomWithIdx(idx).SetProp("atomNote", " / ".join(notes))
    canvas_w = max(1400, 60 * mol.GetNumAtoms())
    canvas_h = max(1100, 45 * mol.GetNumAtoms())
    drawer = rdMolDraw2D.MolDraw2DCairo(canvas_w, canvas_h)
    options = drawer.drawOptions()
    options.addAtomIndices = False
    options.bondLineWidth = 2
    options.annotationFontScale = 0.75
    rdMolDraw2D.PrepareAndDrawMolecule(
        drawer, mol, highlightAtoms=highlight_atoms,
        highlightAtomColors=highlight_colors,
        highlightAtomRadii=highlight_radii,
        legend=molecule,
    )
    drawer.FinishDrawing()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    output_png.write_bytes(drawer.GetDrawingText())
    legend_path = output_png.with_suffix(".legend.txt")
    legend_path.write_text("\n".join(legend_lines + (["", "IGNOREES :"] + skipped if skipped else [])), encoding="utf-8")
    return legend_lines, skipped


def generate(xml_file: Path, complex_pdb: Path, output_png: Path, molecule: str = ""):
    data = parse_plip_xml(xml_file)
    tree = ET.parse(xml_file)
    root = tree.getroot()
    reschain_lig = (root.find(".//chain").text or "A").strip()
    restype_lig = (root.find(".//hetid").text or "").strip()
    resnr_lig = (root.find(".//position").text or "").strip()
    atoms = extract_ligand_atoms(complex_pdb, reschain_lig, restype_lig, resnr_lig)
    mol = build_ligand_mol_from_pdb_atoms(data["smiles"], atoms)
    if not data["interactions"]:
        raise RuntimeError("Aucune interaction exploitable dans le XML PLIP.")
    legend, skipped = render_diagram(mol, data["interactions"], atoms, output_png, molecule or xml_file.stem)
    print(f"✓ Diagramme généré : {output_png}")
    print(f"✓ {len(legend)} interaction(s) annotée(s) :")
    for line in legend:
        print("   -", line)
    if skipped:
        print(f"⚠️  {len(skipped)} interaction(s) ignorée(s) :")
        for line in skipped:
            print("   -", line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", required=True, type=Path)
    parser.add_argument("--complex", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--molecule", default="")
    args = parser.parse_args()
    generate(args.xml, args.complex, args.output, args.molecule)
