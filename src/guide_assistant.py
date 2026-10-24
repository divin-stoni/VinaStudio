# -*- coding: utf-8 -*-
"""
guide_assistant.py

Assistant de choix pour l'import et la validation d'un recepteur (sans Qt).
Transforme les mesures techniques en conseils simples : feu tricolore,
phrase claire, action proposee.

Seuils PROVISOIRES, calibres sur un banc de 6 complexes AcrB (re-docking) :
- facteur B du ligand / facteur B moyen de la chaine : <= 1.9 correct,
  > 2.5 peu fiable (1T9X : 3.97 -> echec du re-docking).
- contacts proteine-ligand (< 4.5 A) : < 10 site tres superficiel.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

B_RATIO_OK = 1.9
B_RATIO_BAD = 2.5
CONTACTS_BAD = 10
CONTACTS_WARN = 25
BOX_BIG = 30.0
MARGIN_MIN = 4.0
MARGIN_MAX = 15.0
RMSD_OK = 2.0

LIKELY_NOT_LIGANDS = {
    "DDM", "LMT", "LMU", "BOG", "BNG", "LDA", "PLM", "OLC", "PEG", "GOL",
    "SO4", "EDO", "PGE", "P6G", "1PE", "D10", "C8E", "OLA", "MYR", "HTO",
    "LHG", "PC1",
}
METAL_IONS = {"ZN", "FE", "FE2", "CU", "CU1", "MN", "CO", "NI", "MG", "CA"}

LIPID_NAME_KEYWORDS = (
    "decanoate", "decyl", "decane", "dodecan", "hexadecan", "octadecan",
    "phosphatidyl", "glycerol", "maltoside", "palmitoyl", "oleoyl",
    "stearoyl", "myristoyl", "polyethylene",
)


def short_name(name, n=40):
    """Nom de ligand lisible : retire le balisage ~{N}, tronque."""
    name = re.sub(r"~\{([^}]*)\}", r"\1", name or "")
    name = re.sub(r"\s+", " ", name).strip()
    return name if len(name) <= n else name[: n - 1].rstrip() + "…"


def _is_acyclic(xyz, cutoff=1.85):
    """True si le graphe des liaisons (atomes lourds a < 1,85 A) n'a aucun cycle."""
    pts = []
    for q in np.asarray(xyz, dtype=float):
        # ecarte les conformations alternatives (atomes quasi superposes)
        if all(np.linalg.norm(q - k) > 0.7 for k in pts):
            pts.append(q)
    n = len(pts)
    if n < 2:
        return True
    arr = np.asarray(pts)
    d = np.linalg.norm(arr[:, None, :] - arr[None, :, :], axis=2)
    adj = (d < cutoff) & ~np.eye(n, dtype=bool)
    edges = int(adj.sum() // 2)
    seen = np.zeros(n, dtype=bool)
    comps = 0
    for i in range(n):
        if seen[i]:
            continue
        comps += 1
        seen[i] = True
        stack = [i]
        while stack:
            u = stack.pop()
            for v in np.nonzero(adj[u] & ~seen)[0]:
                seen[v] = True
                stack.append(int(v))
    return edges - n + comps == 0


def is_lipid_like(lig) -> bool:
    """Lipide ou detergent probable : nom typique, ou longue molecule sans aucun cycle."""
    nm = (lig.name or "").lower()
    if any(k in nm for k in LIPID_NAME_KEYWORDS):
        return True
    return lig.n_atoms >= 14 and _is_acyclic(lig.xyz)


LEVEL_ORDER = {"ok": 0, "info": 1, "warn": 2, "bad": 3}
LEVEL_COLOR = {"ok": "#15803d", "info": "#475569", "warn": "#b45309", "bad": "#b91c1c"}
LEVEL_ICON = {"ok": "✔", "info": "ℹ", "warn": "⚠", "bad": "✖"}

VALIDATION_DIR = Path(__file__).resolve().parent.parent / "receptor_profiles" / "validation"


@dataclass
class Advice:
    level: str
    title: str
    text: str
    fix: str = ""


# ------------------------------------------------------------------ mesures
def ligand_bfactors(pdb_path, lig):
    """(B moyen du ligand, B moyen de sa chaine liante) ou (None, None)."""
    try:
        _res, ch_l, numicode = lig.key.split(":")
    except ValueError:
        return None, None
    chain = lig.best_chain or ch_l
    b_lig, b_prot = [], []
    try:
        with open(pdb_path, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.startswith("ENDMDL"):
                    break
                rec = line[:6]
                if rec not in ("ATOM  ", "HETATM"):
                    continue
                try:
                    b = float(line[60:66])
                except ValueError:
                    continue
                ch = line[21:22].strip() or "_"
                if (rec == "HETATM" and line[17:20].strip().upper() == lig.resname.upper()
                        and ch == ch_l and (line[22:26].strip() + line[26:27].strip()) == numicode):
                    b_lig.append(b)
                elif rec == "ATOM  " and ch == chain:
                    b_prot.append(b)
    except OSError:
        return None, None
    if not b_lig or not b_prot:
        return None, None
    bl, bp = float(np.mean(b_lig)), float(np.mean(b_prot))
    if bl <= 0 or bp <= 0:
        return None, None
    return bl, bp


def best_ligand_key(report) -> str:
    """Ligand de reference le plus fiable (et pas seulement le plus gros)."""
    cands = []
    for lig in report.ligands:
        if lig.resname in LIKELY_NOT_LIGANDS or lig.best_contacts < CONTACTS_BAD:
            continue
        bl, bp = ligand_bfactors(report.path, lig)
        ratio = (bl / bp) if (bl and bp) else None
        if is_lipid_like(lig):
            pen = 3
        elif ratio is None or ratio <= B_RATIO_OK:
            pen = 0 if ratio is not None else 1
        elif ratio <= B_RATIO_BAD:
            pen = 1
        else:
            pen = 2
        cands.append((pen, -lig.best_contacts, lig.key))
    if cands:
        return sorted(cands)[0][2]
    return report.suggested_ligand or ""


# ----------------------------------------------------------------- conseils
def advise_structure(report) -> list:
    out = []
    r = report.resolution
    if r is None:
        out.append(Advice("info", "Résolution inconnue",
                          "Le fichier n'indique pas de résolution (RMN, cryo-EM ou modèle prédit)."))
    elif r <= 2.5:
        out.append(Advice("ok", f"Bonne résolution ({r:.2f} Å)",
                          "Les positions des atomes sont précises."))
    elif r <= 3.0:
        out.append(Advice("info", f"Résolution correcte ({r:.2f} Å)",
                          "Utilisable, mais les chaînes latérales sont moins précises."))
    elif r <= 3.5:
        out.append(Advice("warn", f"Résolution moyenne ({r:.2f} Å)",
                          "Les chaînes latérales et le ligand peuvent être mal placés.",
                          "Si une meilleure structure existe pour la même protéine, préfère-la."))
    else:
        out.append(Advice("bad", f"Résolution faible ({r:.2f} Å)",
                          "Les positions des atomes sont peu fiables.",
                          "Cherche une structure de la même protéine à 3 Å ou mieux."))
    if report.n_models > 1:
        out.append(Advice("info", "Plusieurs modèles (RMN)",
                          f"Le fichier contient {report.n_models} modèles ; seul le premier sera utilisé."))
    if report.mutation:
        out.append(Advice("warn", "Protéine mutée",
                          "Cette structure porte des mutations par rapport à la séquence normale.",
                          "Vérifie que la mutation n'est pas dans le site étudié."))
    miss = sum(c.missing for c in report.chains.values())
    if miss:
        out.append(Advice("info", f"{miss} résidu(s) non résolus",
                          "Des boucles manquent dans la structure ; elles ne seront pas reconstruites."))
    metals = [k for k in report.ions if k in METAL_IONS]
    if metals:
        out.append(Advice("info", "Ions métalliques présents",
                          f"{', '.join(metals)} sera retiré. Si l'ion est structural pour ta protéine, "
                          "le docking peut être faussé."))
    if not report.ligands:
        out.append(Advice("warn", "Aucun ligand dans la structure",
                          "Sans ligand de référence, la grid box ne peut pas être placée automatiquement "
                          "ni le docking contrôlé par re-docking.",
                          "Place la boîte avec « Ajustement précis » sur le site à étudier."))
    return out


def advise_ligand(report, lig) -> list:
    out = []
    if lig is None:
        return out
    name = f"{lig.resname}" + (f" ({short_name(lig.name)})" if lig.name else "")
    if lig.resname in LIKELY_NOT_LIGANDS or is_lipid_like(lig):
        out.append(Advice("warn", f"{name} ressemble à un détergent ou un lipide",
                          "Ce n'est probablement pas une vraie molécule de référence pour le site.",
                          "Choisis plutôt un autre ligand, s'il y en a un."))
    c = lig.best_contacts
    if c < CONTACTS_BAD:
        out.append(Advice("bad", "Ligand très peu en contact avec la protéine",
                          f"Seulement {c} atomes de protéine à moins de 4,5 Å : le site est superficiel "
                          "ou le ligand est mal défini.",
                          "Un re-docking sur ce ligand ne prouvera pas grand-chose."))
    elif c < CONTACTS_WARN:
        out.append(Advice("warn", "Ligand peu enfoui",
                          f"{c} atomes de protéine à moins de 4,5 Å : le site est ouvert, "
                          "Vina a beaucoup de place pour se tromper."))
    else:
        out.append(Advice("ok", "Ligand bien enfoui",
                          f"{c} atomes de protéine à moins de 4,5 Å."))
    bl, bp = ligand_bfactors(report.path, lig)
    if bl and bp:
        ratio = bl / bp
        if ratio <= B_RATIO_OK:
            out.append(Advice("ok", "Position du ligand bien définie",
                              f"Son agitation (facteur B) est proche de celle de la protéine (×{ratio:.1f})."))
        elif ratio <= B_RATIO_BAD:
            out.append(Advice("warn", "Position du ligand moyennement définie",
                              f"Son facteur B est ×{ratio:.1f} celui de la protéine : la densité "
                              "électronique est faible à cet endroit."))
        else:
            out.append(Advice("bad", "Position du ligand peu fiable",
                              f"Son facteur B est ×{ratio:.1f} celui de la protéine : le ligand est mal "
                              "défini dans le cristal.",
                              "Ne l'utilise pas comme référence de validation ; prends une structure mieux résolue."))
    total = sum(ch.contacts.get(lig.key, 0) for ch in report.chains.values()) or 1
    frac = c / total
    if frac < 0.8:
        out.append(Advice("info", "Ligand partagé entre plusieurs chaînes",
                          f"Seulement {frac*100:.0f} % de ses contacts sont sur la chaîne {lig.best_chain}.",
                          "Garde aussi les chaînes voisines si le site est à leur interface."))
    ch = report.chains.get(lig.best_chain)
    if ch is not None and sum(1 for o in report.chains.values() if o.group == ch.group) > 1:
        out.append(Advice("info", "Plusieurs copies identiques de la protéine",
                          f"Le ligand n'est lié qu'à la chaîne {lig.best_chain}. Pour une pompe asymétrique "
                          "(accès, liaison, sortie), les autres copies n'ont pas la même forme.",
                          f"Garde la chaîne {lig.best_chain} seule : docking plus rapide et plus pertinent."))
    return out


def advise_selection(report, choices) -> list:
    out = []
    chains = choices.get("chains") or []
    lig = report.ligand_by_key(choices.get("ligand", "")) if choices.get("ligand") else None
    if not chains:
        out.append(Advice("bad", "Aucune chaîne gardée", "Il faut garder au moins une chaîne."))
    elif lig is not None and lig.best_chain and lig.best_chain not in chains:
        out.append(Advice("bad", "La chaîne du ligand n'est pas gardée",
                          f"Le ligand {lig.resname} est lié à la chaîne {lig.best_chain} : la boîte "
                          "serait placée dans le vide.",
                          "Coche cette chaîne ou clique sur « Appliquer les réglages recommandés »."))
    elif len(chains) > 1:
        groups = {report.chains[c].group for c in chains if c in report.chains}
        if len(groups) < len(chains):
            out.append(Advice("info", f"{len(chains)} chaînes gardées dont des copies identiques",
                              "Le docking sera plus lent sans forcément être plus pertinent."))
    if not choices.get("protonate") and not report.has_h:
        out.append(Advice("warn", "Hydrogènes non ajoutés",
                          "Sans hydrogènes polaires, Vina ne voit pas les liaisons hydrogène. "
                          "Le banc d'essai de validation a été fait avec les hydrogènes ajoutés (pH 7,4).",
                          "Coche « Ajouter les hydrogènes » sauf si ton fichier en contient déjà."))
    return out


def advise_box(report, choices) -> list:
    out = []
    lig = report.ligand_by_key(choices.get("ligand", "")) if choices.get("ligand") else None
    if lig is None:
        if report.ligands:
            out.append(Advice("warn", "Pas de ligand choisi pour la boîte",
                              "La boîte sera centrée sur toute la protéine, sans signification biologique.",
                              "Choisis un ligand de référence dans la liste."))
        return out
    margin = float(choices.get("margin", 8.0))
    from src import grid_fit
    _c, size, _cl = grid_fit.box_from_coords(lig.xyz, margin)
    size = [float(v) for v in size]
    dims = " × ".join(f"{v:.0f}" for v in size)
    if margin < MARGIN_MIN:
        out.append(Advice("warn", "Marge trop petite",
                          f"Avec {margin:.1f} Å, un ligand plus gros que celui du cristal ne tiendra pas.",
                          "Garde 6 à 10 Å."))
    elif margin > MARGIN_MAX:
        out.append(Advice("warn", "Marge très grande",
                          f"Boîte de {dims} Å : Vina explorera trop d'espace.",
                          "Réduis la marge (8 Å est un bon point de départ)."))
    elif max(size) > BOX_BIG:
        out.append(Advice("warn", "Boîte grande",
                          f"{dims} Å : un côté dépasse {BOX_BIG:.0f} Å, la recherche devient moins reproductible.",
                          "Réduis la marge ou garde une exhaustiveness d'au moins 32."))
    else:
        out.append(Advice("ok", "Taille de boîte raisonnable",
                          f"{dims} Å autour de {lig.label}."))
    return out


def advise_all(report, choices) -> list:
    lig = report.ligand_by_key(choices.get("ligand", "")) if choices.get("ligand") else None
    adv = []
    adv += advise_selection(report, choices)
    adv += advise_ligand(report, lig)
    adv += advise_box(report, choices)
    adv += advise_structure(report)
    return adv


def advise_validation(v) -> list:
    if not v:
        return [Advice("warn", "Configuration non validée",
                       "Ce récepteur n'a pas encore été contrôlé : on ne sait pas si la grid box et les "
                       "paramètres retrouvent une pose connue.",
                       "Lance le re-docking de contrôle avant d'interpréter des scores.")]
    ref = v.get("reference", "?")
    if v.get("passed"):
        return [Advice("ok", "Configuration validée",
                       f"Re-docking de {ref} : RMSD {v['rmsd_top']:.2f} Å (seuil {RMSD_OK:.0f} Å).")]
    if v.get("rmsd_best") is not None and v["rmsd_best"] < RMSD_OK:
        return [Advice("warn", "Validation partielle",
                       f"Re-docking de {ref} : la bonne pose existe (RMSD {v['rmsd_best']:.2f} Å) mais "
                       f"n'est pas classée première (pose n°1 : {v['rmsd_top']:.2f} Å).",
                       "Interprète les scores avec prudence et regarde plusieurs poses.")]
    nm, ns = v.get("n_modes") or 0, v.get("n_site") or 0
    if nm and ns / nm >= 0.5 and v.get("center_dist_top") is not None:
        fr = v.get("frac_2a_top")
        part = (f" ; {fr*100:.0f} % des atomes de la pose n°1 sont à moins de 2 Å du cristal"
                if fr is not None else "")
        return [Advice("warn", "Site retrouvé, pose non reproduite",
                       f"Re-docking de {ref} : {ns} pose(s) sur {nm} sont dans le bon site "
                       f"(écart des centres, pose n°1 : {v['center_dist_top']:.1f} Å), mais la pose "
                       f"n°1 s'écarte de {v['rmsd_top']:.2f} Å du cristal{part}.",
                       "Le site est repéré, mais pas la conformation fine : regarde les poses. "
                       "Les groupes chargés ou flexibles sont les plus difficiles à placer.")]
    return [Advice("bad", "Validation échouée",
                   f"Re-docking de {ref} : RMSD {v['rmsd_top']:.2f} Å, aucune pose sous {RMSD_OK:.0f} Å.",
                   "Vérifie la grid box, la qualité du ligand de référence, ou essaie un autre complexe.")]


# ---------------------------------------------------------------- synthese
def overall(advices):
    worst = max((LEVEL_ORDER[a.level] for a in advices), default=0)
    level = [k for k, v in LEVEL_ORDER.items() if v == worst][0]
    phrase = {
        "ok": "Tout est en ordre pour importer.",
        "info": "Import possible ; quelques points à connaître.",
        "warn": "Import possible, mais lis les avertissements : ils peuvent affecter la fiabilité du docking.",
        "bad": "Je déconseille ces réglages : regarde les points rouges.",
    }[level]
    return level, phrase


def to_html(advices, phrase="", level="info", max_items=9) -> str:
    esc = html.escape
    items = sorted(advices, key=lambda a: -LEVEL_ORDER[a.level])
    shown, hidden = items[:max_items], max(0, len(items) - max_items)
    rows = []
    if phrase:
        rows.append(f'<span style="color:{LEVEL_COLOR[level]}"><b>{LEVEL_ICON[level]} {esc(phrase)}</b></span>')
    for a in shown:
        line = (f'<span style="color:{LEVEL_COLOR[a.level]}">{LEVEL_ICON[a.level]} <b>{esc(a.title)}</b></span>'
                f" : {esc(a.text)}")
        if a.fix:
            line += f' <i>→ {esc(a.fix)}</i>'
        rows.append(line)
    if hidden:
        rows.append(f"<i>… et {hidden} autre(s) remarque(s) sans gravité.</i>")
    return "<br>".join(rows)


# -------------------------------------------------------------- validation
def save_validation(profile_id, data: dict) -> Path:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    p = VALIDATION_DIR / f"{profile_id}.json"
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def load_validation(profile_id):
    p = VALIDATION_DIR / f"{profile_id}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def validation_from_result(res, reference: str) -> dict:
    return {
        "reference": reference,
        "passed": bool(res.passed),
        "rmsd_top": res.rmsd_top,
        "rmsd_best": res.rmsd_best,
        "score_top": res.affinity_top,
        "n_heavy": res.n_heavy,
        "threshold": RMSD_OK,
        "n_modes": res.n_modes,
        "center_dist_top": getattr(res, "center_dist_top", None),
        "n_site": getattr(res, "n_site", 0),
        "frac_2a_top": getattr(res, "frac_2a_top", None),
    }


def validation_badge(v) -> str:
    if not v:
        return "⚠ non validé"
    if v.get("passed"):
        return f"✔ validé (RMSD {v['rmsd_top']:.2f} Å)"
    if v.get("rmsd_best") is not None and v["rmsd_best"] < RMSD_OK:
        return "⚠ validation partielle"
    nm, ns = v.get("n_modes") or 0, v.get("n_site") or 0
    if nm and ns / nm >= 0.5 and v.get("center_dist_top") is not None:
        return "⚠ site retrouvé, pose non reproduite"
    return "✖ validation échouée"
