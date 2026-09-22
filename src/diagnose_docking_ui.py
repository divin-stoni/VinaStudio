#!/usr/bin/env python3
"""
diagnose_docking_ui.py
=======================

Diagnostic ergonomique STATIQUE de la section "docking" d'une interface
PySide6/Qt (VinaStudio, main_window.py).

Ce script n'exécute PAS l'application (pas de rendu réel, pas de mesure
de pixels à l'écran) — il n'a pas accès à un environnement graphique.
Il analyse le CODE SOURCE (via l'AST Python) pour repérer des schémas
structurels connus pour produire des problèmes ergonomiques :

  1. Chaînes de texte "brutes" (make_label / QLabel avec littéral) qui
     court-circuitent le système de traduction (_t_label / _t_button)
     utilisé partout ailleurs dans le même panneau — source d'incohérence
     (et souvent d'anglicismes oubliés, ex: "Exhaustiveness").
  2. Colonnes de QGridLayout marquées "extensibles" (setColumnStretch(col,1))
     mais dont TOUS les widgets qu'elles contiennent ont une largeur
     plafonnée (setMaximumWidth) — la colonne réclame de l'espace au
     layout mais ne l'utilise jamais : c'est l'espace mort / "surface qui
     ne sert à rien" que tu décris.
  3. Incohérence des marges/espacements entre panneaux frères
     (setContentsMargins différents d'un ContentPanel à l'autre sans
     raison apparente).
  4. Champs numériques sans texte par défaut ni placeholder — boîte vide
     qui n'apporte aucune information tant qu'on n'a pas cliqué dedans.

Le rapport final donne des numéros de ligne exacts et des suggestions
concrètes, mais reste un GUIDE — pas un verdict pixel-parfait. À utiliser
comme point de départ pour prioriser les retouches, pas comme certitude
absolue sur chaque point.

Usage:
    python3 diagnose_docking_ui.py chemin/vers/main_window.py
"""

import ast
import re
import sys
from collections import defaultdict

TARGET_FUNCTIONS = {"create_docking_page", "_build_generic_grid_panel"}

WIDTH_HEIGHT_SETTERS = {
    "setMaximumWidth", "setMinimumWidth", "setFixedWidth",
    "setMaximumHeight", "setMinimumHeight", "setFixedHeight",
}

# Domaine : sigles/noms propres à ne jamais considérer comme anglicismes
DOMAIN_WHITELIST = {
    "mexb", "mexr", "mexy", "mexz", "acrb", "acrr", "adeabc", "cmeb",
    "pdb", "pdbqt", "vina", "fpocket", "csv", "gui", "sdf", "chimerax",
    "rdkit", "biopython", "opengl", "pyside6", "qwebengineview",
    "dmso", "cid", "3dmol",
}

FRENCH_ACCENTS = "éèêëàâäôöûüçîïÉÈÊËÀÂÄÔÖÛÜÇÎÏ"

# Mots français courants qui s'écrivent comme (ou presque comme) leur
# équivalent anglais -> faux positifs fréquents à exclure explicitement.
FRENCH_FALSE_FRIENDS = {
    "mode", "modes", "double", "simple", "style", "page", "pages",
    "image", "images", "table", "tables", "date", "dates", "groupe",
    "liste", "ligne", "lignes", "colonne", "colonnes", "valeur",
    "valeurs", "champ", "champs", "cible", "cibles", "poche", "poches",
    "statut", "config", "export", "import", "fichier", "fichiers",
    "dossier", "dossiers", "module", "modules", "système", "resultat",
    "resultats", "aucun", "aucune", "calcul", "calculs", "cours",
    "actif", "active", "panel", "panels", "score", "scores", "test",
    "tests", "type", "types", "zone", "zones", "point", "points",
    "centre", "taille", "grille", "profil", "profils", "seuil",
    "seuils", "erreur", "erreurs", "log", "logs",
}


# ---------------------------------------------------------------------
# Extraction du texte source des fonctions cibles
# ---------------------------------------------------------------------

def extract_function_sources(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    lines = source.splitlines()
    tree = ast.parse(source, filename=filepath)

    funcs = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in TARGET_FUNCTIONS:
            start = node.lineno
            end = getattr(node, "end_lineno", None)
            if end is None:
                end = start + 1
            funcs[node.name] = {
                "node": node,
                "start": start,
                "end": end,
                "text": "\n".join(lines[start - 1:end]),
            }
    return funcs, lines


# ---------------------------------------------------------------------
# 1. Chaînes brutes vs. système de traduction
# ---------------------------------------------------------------------

def find_raw_labels(func_node):
    """Retourne les appels make_label(...)/QLabel(...) avec un littéral
    en premier argument, distincts de self._t_label(...)/self._t_button(...)."""
    raw = []
    translated_texts = []

    for node in ast.walk(func_node):
        if not isinstance(node, ast.Call):
            continue

        func = node.func
        name = None
        if isinstance(func, ast.Name):
            name = func.attr if isinstance(func, ast.Attribute) else func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr

        if name in ("make_label", "QLabel"):
            if node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                raw.append((node.lineno, node.args[0].value))

        elif name in ("_t_label", "_t_button"):
            # signature (self, key, default_text, style=None) ou (key, text)
            text_arg = None
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                text_arg = node.args[1].value
            elif len(node.args) >= 1 and isinstance(node.args[0], ast.Constant):
                text_arg = node.args[0].value
            if isinstance(text_arg, str):
                translated_texts.append(text_arg)

    return raw, translated_texts


def looks_english(word, french_vocab):
    w = word.strip(",.():;!?\"'").lower()
    if len(w) < 4:
        return False
    if w in DOMAIN_WHITELIST:
        return False
    if w in FRENCH_FALSE_FRIENDS:
        return False
    if any(c in FRENCH_ACCENTS for c in word):
        return False
    if w in french_vocab:
        return False
    if not w.isalpha():
        return False
    # Suffixes anglais fréquents et absents du français standard
    english_suffixes = ("ness", "tion" , "ing", "ity", "ment")
    # "tion"/"ment" existent aussi en français -> on ne les garde pas seuls
    if w.endswith("ness") or w.endswith("ing"):
        return True
    # Mot 100% ASCII, pas dans le vocabulaire français du fichier,
    # pas un sigle connu -> candidat
    return True


# ---------------------------------------------------------------------
# 2. Colonnes extensibles vs contenu plafonné (espace mort)
# ---------------------------------------------------------------------

def find_dead_stretch_columns(func_text, func_start_line):
    """
    Heuristique par blocs : on découpe le texte de la fonction en blocs
    séparés par des lignes 'grid = QGridLayout(...)' / 'xxx_grid = QGridLayout()'
    puis on regarde, pour chaque bloc, si setColumnStretch(col, 1) est posé
    ET si des setMaximumWidth(...) apparaissent dans le même bloc (signe que
    les widgets placés dans les colonnes extensibles sont en réalité
    plafonnés en largeur).
    """
    findings = []
    grid_var_pattern = re.compile(r'^\s*(\w+)\s*=\s*QGridLayout\(')
    stretch_pattern = re.compile(r'(\w+)\.setColumnStretch\((\d+),\s*(\d+)\)')
    maxwidth_pattern = re.compile(r'\.setMaximumWidth\((\d+)\)')

    lines = func_text.splitlines()
    current_grid_var = None
    block_start_idx = 0
    blocks = []  # (grid_var, start_idx, end_idx)

    for i, line in enumerate(lines):
        m = grid_var_pattern.match(line)
        if m:
            if current_grid_var is not None:
                blocks.append((current_grid_var, block_start_idx, i))
            current_grid_var = m.group(1)
            block_start_idx = i
    if current_grid_var is not None:
        blocks.append((current_grid_var, block_start_idx, len(lines)))

    for grid_var, start_idx, end_idx in blocks:
        block_lines = lines[start_idx:end_idx]
        block_text = "\n".join(block_lines)

        stretches = {}
        for sm in stretch_pattern.finditer(block_text):
            var, col, val = sm.group(1), int(sm.group(2)), int(sm.group(3))
            if var == grid_var:
                stretches[col] = val

        maxwidths = [int(x) for x in maxwidth_pattern.findall(block_text)]

        elastic_cols = [c for c, v in stretches.items() if v == 1]
        if elastic_cols and maxwidths:
            real_line = func_start_line + start_idx
            findings.append({
                "grid_var": grid_var,
                "line": real_line,
                "elastic_columns": elastic_cols,
                "capped_widths_found": sorted(set(maxwidths)),
            })

    return findings


# ---------------------------------------------------------------------
# 3. Marges incohérentes entre panneaux
# ---------------------------------------------------------------------

def find_margins(func_text, func_start_line):
    """Associe chaque setContentsMargins(...) à sa ligne de départ, en
    gérant les appels étalés sur plusieurs lignes (parenthèses équilibrées)."""
    results = []
    call_start = re.compile(r'(\w+)\.setContentsMargins\(')

    pos = 0
    while True:
        m = call_start.search(func_text, pos)
        if not m:
            break
        var = m.group(1)
        open_idx = m.end() - 1  # index de la parenthèse ouvrante
        depth = 0
        i = open_idx
        close_idx = None
        while i < len(func_text):
            if func_text[i] == "(":
                depth += 1
            elif func_text[i] == ")":
                depth -= 1
                if depth == 0:
                    close_idx = i
                    break
            i += 1
        pos = m.end()
        if close_idx is None:
            continue
        args_text = func_text[open_idx + 1:close_idx]
        nums = re.findall(r'-?\d+', args_text)
        line_no = func_start_line + func_text[:m.start()].count("\n")
        if len(nums) == 4:
            margins = tuple(int(n) for n in nums)
            results.append((line_no, var, margins))
    return results


# ---------------------------------------------------------------------
# 4. Champs sans placeholder / valeur par défaut visible
# ---------------------------------------------------------------------

def find_empty_lineedits(func_text, func_start_line, whole_source):
    """Repère les QLineEdit créés dans la fonction et vérifie, dans TOUT
    le fichier, si un .setPlaceholderText( ou .setText( leur est appliqué
    quelque part."""
    creation_pattern = re.compile(r'self\.(\w+)\s*=\s*QLineEdit\(\)')
    findings = []
    for i, line in enumerate(func_text.splitlines()):
        m = creation_pattern.search(line)
        if m:
            var = m.group(1)
            has_placeholder = f"self.{var}.setPlaceholderText(" in whole_source
            has_settext = f"self.{var}.setText(" in whole_source
            if not has_placeholder:
                findings.append({
                    "line": func_start_line + i,
                    "var": var,
                    "has_settext_elsewhere": has_settext,
                })
    return findings


# ---------------------------------------------------------------------
# Rapport
# ---------------------------------------------------------------------

def build_french_vocab(all_translated_texts):
    vocab = set()
    for text in all_translated_texts:
        for w in re.findall(r"[A-Za-zÀ-ÿ']+", text):
            vocab.add(w.lower())
    return vocab


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 diagnose_docking_ui.py chemin/vers/main_window.py")
        sys.exit(1)

    filepath = sys.argv[1]
    with open(filepath, "r", encoding="utf-8") as f:
        whole_source = f.read()

    funcs, _ = extract_function_sources(filepath)
    if not funcs:
        print("Aucune des fonctions cibles "
              f"({', '.join(sorted(TARGET_FUNCTIONS))}) n'a été trouvée.")
        sys.exit(1)

    # Vocabulaire français basé sur TOUT le fichier (pas seulement docking)
    # pour réduire les faux positifs (termes déjà utilisés ailleurs).
    all_translated = []
    tree = ast.parse(whole_source, filename=filepath)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name in ("_t_label", "_t_button") and len(node.args) >= 2:
                if isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                    all_translated.append(node.args[1].value)
    french_vocab = build_french_vocab(all_translated)

    print("=" * 78)
    print("DIAGNOSTIC ERGONOMIQUE STATIQUE — SECTION DOCKING")
    print(f"Fichier : {filepath}")
    print("=" * 78)
    print(
        "\nRappel : analyse de code, pas de rendu réel. Sert à prioriser,"
        " pas à trancher seul.\n"
    )

    total_issues = 0

    for fname, data in funcs.items():
        print("-" * 78)
        print(f"FONCTION : {fname}()  (lignes {data['start']}–{data['end']})")
        print("-" * 78)

        # --- 1. Chaînes brutes / anglicismes candidats ---
        raw_labels, _ = find_raw_labels(data["node"])
        if raw_labels:
            print(f"\n[1] Chaînes hors système de traduction "
                  f"({len(raw_labels)} trouvée(s)) :")
            for line, text in raw_labels:
                words = re.findall(r"[A-Za-zÀ-ÿ']+", text)
                flagged = [w for w in words if looks_english(w, french_vocab)]
                tag = "  ⚠ anglicisme probable" if flagged else ""
                print(f"    L{line:>5}  \"{text}\"{tag}")
                total_issues += 1
        else:
            print("\n[1] Aucune chaîne brute hors traduction détectée.")

        # --- 2. Colonnes élastiques + contenu plafonné ---
        dead = find_dead_stretch_columns(data["text"], data["start"])
        if dead:
            print(f"\n[2] Colonnes extensibles au-dessus de contenu plafonné "
                  f"({len(dead)} bloc(s)) :")
            for d in dead:
                print(
                    f"    L{d['line']:>5}  grid='{d['grid_var']}' — "
                    f"colonnes élastiques {d['elastic_columns']} mais "
                    f"largeurs plafonnées trouvées {d['capped_widths_found']}px "
                    f"→ espace mort probable à droite de chaque champ"
                )
                total_issues += 1
        else:
            print("\n[2] Pas de conflit stretch/largeur plafonnée détecté.")

        # --- 3. Marges ---
        margins = find_margins(data["text"], data["start"])
        if margins:
            distinct = {m[2] for m in margins}
            print(f"\n[3] Marges de contenu relevées ({len(margins)} panneau(x)) :")
            for line, var, m in margins:
                print(f"    L{line:>5}  {var}.setContentsMargins{m}")
            if len(distinct) > 1:
                print(
                    f"    ⚠ {len(distinct)} jeux de marges différents dans "
                    f"cette fonction — pas de rythme d'espacement unique."
                )
                total_issues += 1

        # --- 4. Champs vides sans placeholder ---
        empties = find_empty_lineedits(data["text"], data["start"], whole_source)
        if empties:
            print(f"\n[4] QLineEdit sans setPlaceholderText "
                  f"({len(empties)} trouvé(s)) :")
            for e in empties:
                note = " (valeur posée ailleurs via setText, mais pas de " \
                       "placeholder si vide)" if e["has_settext_elsewhere"] else \
                       " (aucune valeur par défaut trouvée dans le fichier)"
                print(f"    L{e['line']:>5}  self.{e['var']}{note}")
                total_issues += 1
        else:
            print("\n[4] Tous les QLineEdit ont un placeholder.")

        print()

    print("=" * 78)
    print(f"TOTAL : {total_issues} point(s) à examiner.")
    print("=" * 78)


if __name__ == "__main__":
    main()
