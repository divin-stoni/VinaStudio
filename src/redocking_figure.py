# -*- coding: utf-8 -*-
"""Figure de validation par re-docking : cristal vs poses Vina (PNG)."""
import sys
from pathlib import Path
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from src import redocking as rd

C_REF, C_P1, C_BEST = "#2e9e5b", "#e8833a", "#2f6fb5"


def _aligned(ref, types, poses):
    """Pour chaque pose, la permutation d'atomes equivalents qui minimise le RMSD."""
    perms = rd._automorphisms(types, rd._bond_matrix(ref, types))
    out, rmsds = [], []
    for xyz in poses:
        d = np.sqrt(((xyz[perms] - ref[None]) ** 2).sum(axis=2).mean(axis=1))
        k = int(d.argmin())
        out.append(xyz[perms[k]])
        rmsds.append(float(d[k]))
    return out, rmsds


def _draw(ax, xyz, bonds, i, j, color, lw, alpha=1.0, zorder=2):
    for a, b in bonds:
        ax.plot([xyz[a, i], xyz[b, i]], [xyz[a, j], xyz[b, j]],
                color=color, lw=lw, alpha=alpha, zorder=zorder, solid_capstyle="round")
    ax.scatter(xyz[:, i], xyz[:, j], s=14, color=color, alpha=alpha, zorder=zorder + 1)


def make_figure(work, tag, out_png, title="", threshold=2.0):
    work = Path(work)
    cris = work / f"{tag}_cristal.pdbqt"
    dock = work / f"{tag}_redock_out.pdbqt"
    ref = np.asarray(rd.read_pdbqt_models(cris)[0][1], float)
    types = rd.read_pdbqt_heavy_types(cris)
    models = rd.read_pdbqt_models(dock)
    energies = [float(m[0]) for m in models]
    poses, rmsds = _aligned(ref, types, [np.asarray(m[1], float) for m in models])
    best = int(np.argmin(rmsds))
    bonds = np.argwhere(np.triu(rd._bond_matrix(ref, types)))

    shown = [ref, poses[0]] + ([poses[best]] if best != 0 else [])
    allxyz = np.vstack(shown)
    lo, hi = allxyz.min(axis=0) - 1.5, allxyz.max(axis=0) + 1.5

    fig = Figure(figsize=(12, 7.6), dpi=150, facecolor="white")
    FigureCanvasAgg(fig)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.6, 1], hspace=0.35, wspace=0.22, top=0.80)
    for n, (i, j, lab) in enumerate(((0, 1, "X-Y"), (0, 2, "X-Z"), (1, 2, "Y-Z"))):
        ax = fig.add_subplot(gs[0, n])
        _draw(ax, ref, bonds, i, j, C_REF, 3.2, 0.95, 2)
        if best != 0:
            _draw(ax, poses[best], bonds, i, j, C_BEST, 1.8, 0.9, 4)
        _draw(ax, poses[0], bonds, i, j, C_P1, 1.8, 0.9, 6)
        ax.set_xlim(lo[i], hi[i])
        ax.set_ylim(lo[j], hi[j])
        ax.set_aspect("equal")
        ax.set_title(f"Projection {lab}", fontsize=10)
        ax.set_xlabel("XYZ"[i] + " (Å)", fontsize=8)
        ax.set_ylabel("XYZ"[j] + " (Å)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.2)
        if n == 0:
            ax.plot([], [], color=C_REF, lw=3.2, label="Cristal (référence)")
            ax.plot([], [], color=C_P1, lw=1.8, label=f"Pose n°1 : {rmsds[0]:.2f} Å")
            if best != 0:
                ax.plot([], [], color=C_BEST, lw=1.8,
                        label=f"Meilleure (pose {best + 1}) : {rmsds[best]:.2f} Å")
            fig.legend(*ax.get_legend_handles_labels(), loc="upper center",
                       bbox_to_anchor=(0.5, 0.92), ncol=3, fontsize=8.5, frameon=False)

    axb = fig.add_subplot(gs[1, :])
    x = np.arange(1, len(rmsds) + 1)
    cols = [C_REF if r < threshold else "#b9bec5" for r in rmsds]
    axb.bar(x, rmsds, color=cols, edgecolor=["black" if k == 0 else "none" for k in range(len(x))],
            linewidth=1.4)
    axb.axhline(threshold, color="#b91c1c", ls="--", lw=1)
    axb.text(len(x) + 0.45, threshold, f"seuil {threshold:.1f} Å", color="#b91c1c",
             fontsize=8, va="bottom", ha="right",
             bbox=dict(facecolor="white", edgecolor="none", pad=1.5), zorder=5)
    axb.set_xticks(x)
    axb.set_xticklabels([f"{k}\n{e:.1f}" for k, e in zip(x, energies)], fontsize=8)
    axb.set_xlabel("Rang de la pose (ligne du bas : énergie, kcal/mol)", fontsize=9)
    axb.set_ylabel("RMSD (Å)", fontsize=9)
    axb.set_xlim(0.4, len(x) + 0.6)
    axb.grid(axis="y", alpha=0.2)

    verdict = "VALIDÉ" if rmsds[0] < threshold else "NON VALIDÉ (pose n°1)"
    fig.suptitle(f"{title}   |   {verdict}   |   pose n°1 : {rmsds[0]:.2f} Å"
                 f"   |   meilleure : pose {best + 1}, {rmsds[best]:.2f} Å",
                 fontsize=11, y=0.97)
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150, bbox_inches="tight", facecolor="white")
    return {"rmsds": rmsds, "energies": energies, "best": best + 1, "passed": rmsds[0] < threshold}


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit("usage : python -m src.redocking_figure DOSSIER TAG SORTIE.png [TITRE]")
    res = make_figure(sys.argv[1], sys.argv[2], sys.argv[3],
                      sys.argv[4] if len(sys.argv) > 4 else "")
    print(f"OK : {sys.argv[3]} | pose n°1 {res['rmsds'][0]:.2f} Å | meilleure pose {res['best']}")
