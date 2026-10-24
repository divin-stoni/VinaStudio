# -*- coding: utf-8 -*-
"""RMSD du noyau rigide et des queues flexibles d'un re-docking."""
from pathlib import Path
import numpy as np
from src import redocking as rd


def _heavy_map(pdbqt):
    m, k, started = {}, 0, False
    for line in open(pdbqt, errors="ignore"):
        if line.startswith(("ATOM", "HETATM")):
            parts = line.split()
            if not parts or parts[-1] in rd._H_TYPES:
                continue
            try:
                m[int(line[6:11])] = k
            except ValueError:
                continue
            k += 1
            started = True
        elif started and line.startswith("ENDMDL"):
            break
    return m


def _torsion_bonds(pdbqt, hmap):
    out = []
    for line in open(pdbqt, errors="ignore"):
        if line.startswith("ENDMDL"):
            break
        if line.startswith("BRANCH"):
            p = line.split()
            try:
                a, b = int(p[1]), int(p[2])
            except (IndexError, ValueError):
                continue
            if a in hmap and b in hmap:
                out.append((hmap[a], hmap[b]))
    return out


def _bridges(adj):
    out = []
    for a, b in np.argwhere(np.triu(adj)):
        a, b = int(a), int(b)
        seen, stack = {a}, [a]
        while stack:
            u = stack.pop()
            for v in np.nonzero(adj[u])[0]:
                v = int(v)
                if (u, v) in ((a, b), (b, a)):
                    continue
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        if b not in seen and adj[a].sum() >= 2 and adj[b].sum() >= 2:
            out.append((a, b))
    return out


def _components(adj, cuts):
    cut = {frozenset(c) for c in cuts}
    n = len(adj)
    comp = [-1] * n
    c = 0
    for s in range(n):
        if comp[s] >= 0:
            continue
        comp[s] = c
        stack = [s]
        while stack:
            u = stack.pop()
            for v in np.nonzero(adj[u])[0]:
                v = int(v)
                if comp[v] < 0 and frozenset((u, v)) not in cut:
                    comp[v] = c
                    stack.append(v)
        c += 1
    return np.array(comp)


def analyse(work, tag):
    work = Path(work)
    cris = work / f"{tag}_cristal.pdbqt"
    ref = np.asarray(rd.read_pdbqt_models(cris)[0][1], float)
    types = rd.read_pdbqt_heavy_types(cris)
    models = rd.read_pdbqt_models(work / f"{tag}_redock_out.pdbqt")
    adj = rd._bond_matrix(ref, types)
    cuts = _torsion_bonds(cris, _heavy_map(cris))
    mode = "torsions Vina"
    if not cuts:
        cuts = _bridges(adj)
        mode = "liaisons hors cycle"
    comp = _components(adj, cuts)
    core = comp == int(np.bincount(comp).argmax())
    tail = ~core
    perms = rd._automorphisms(types, adj)
    poses = []
    for _aff, xyz in models:
        xyz = np.asarray(xyz, float)
        d = np.sqrt(((xyz[perms] - ref[None]) ** 2).sum(axis=2))
        d = d[int(np.sqrt((d ** 2).mean(axis=1)).argmin())]
        poses.append({
            "rmsd_global": float(np.sqrt((d ** 2).mean())),
            "rmsd_core": float(np.sqrt((d[core] ** 2).mean())),
            "rmsd_tail": float(np.sqrt((d[tail] ** 2).mean())) if tail.any() else None})
    first = poses[0]
    return {"poses": poses, "resume": {
        "mode": mode, "n_atoms": int(len(core)), "n_core": int(core.sum()),
        "n_tail": int(tail.sum()), "rmsd_core": first["rmsd_core"],
        "rmsd_tail": first["rmsd_tail"]}}
