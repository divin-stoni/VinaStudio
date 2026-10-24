# -*- coding: utf-8 -*-
"""Echelle de couleurs du re-docking : separe echec reel et fluctuation des queues."""
from src import redocking as rd

MIN_CORE = 6   # atomes lourds minimum pour parler de noyau (fixe avant le calcul)
MIN_CORE_FRAC = 0.25  # ajoute apres observation de 6IIA (noyau 6/69) : sens le plus defavorable
LEVELS = {
    "vert":   ("#15803d", "●", "Reproduite"),
    "jaune":  ("#a16207", "◐", "Noyau reproduit, queues variables"),
    "orange": ("#c2410c", "◔", "Site retrouvé, noyau non reproduit"),
    "rouge":  ("#b91c1c", "○", "Site non retrouvé"),
}


def level_from_validation(v, ci):
    thr = rd.RMSD_THRESHOLD
    top = v.get("rmsd_top")
    s = (ci or {}).get("resume") or {}
    if top is not None and top < thr:
        return "vert"
    core = s.get("rmsd_core")
    if (core is not None and s.get("n_tail", 0) > 0
            and s.get("n_core", 0) >= MIN_CORE and core < thr
            and s.get("n_core", 0) / max(1, s.get("n_atoms", 1)) >= MIN_CORE_FRAC):
        return "jaune"
    nm, ns = v.get("n_modes") or 0, v.get("n_site") or 0
    if nm and ns / nm >= 0.5:
        return "orange"
    return "rouge"


def sentence(v):
    col, sym, label = LEVELS[v["niveau"]]
    n = v.get("noyau") or {}
    txt = (f"<span style='color:{col};font-weight:700'>{sym} {label}</span> : "
           f"pose n°1 à {v['rmsd_top']:.2f} Å")
    if n.get("n_tail", 0) > 0 and n.get("rmsd_core") is not None:
        txt += (f", noyau {n['rmsd_core']:.2f} Å ({n['n_core']}/{n['n_atoms']} atomes)")
        if n.get("rmsd_tail") is not None:
            txt += f", queues flexibles {n['rmsd_tail']:.2f} Å ({n['n_tail']} atomes)"
    return txt


def badge(v):
    import re
    col, sym, label = LEVELS[v["niveau"]]
    tip = re.sub(r"<[^>]+>", "", sentence(v))
    tip += (" Critère noyau/queues : descripteur secondaire. Seule la reproduction "
            "globale sous 2 Å valide la configuration.")
    return f"{sym} {label}", col, tip
