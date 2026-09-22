#!/usr/bin/env python3
"""
patch_phyto_table_ux.py
Patch phyto_page.py :
  1) colonnes de tableau redimensionnables à la main (nom plus large, plus
     de troncature) + info-bulle sur le nom complet
  2) nuance de couleur "lien" (vert clair, gras) sur les molécules qui
     ouvrent une structure 2D au clic, phytomolécules comme autres
     molécules — sans texte explicite
  3) tableau de suggestions de plante : s'enroule comme un menu déroulant
     une fois un choix fait, avec un petit triangle pour rouvrir

Sauvegarde horodatée automatique avant modification, remplacement de blocs
de texte exacts (échoue proprement si le fichier ne correspond pas à ce qui
est attendu), vérification syntaxique ast.parse après coup, rapport clair.

Usage :
    python3 patch_phyto_table_ux.py [chemin/vers/phyto_page.py]

Par défaut, cherche ./phyto_page.py
"""
import ast
import shutil
import sys
from datetime import datetime
from pathlib import Path

PATCHES = [
    ("constante LINK_ACCENT",
     '''LIGAND_DIR = Path("docking/ligands/prepared")
FAMILY_ROLE = Qt.UserRole
ACCENT = "#2e7d4f"          # vert « plante » du bloc Espèce
''',
     '''LIGAND_DIR = Path("docking/ligands/prepared")
FAMILY_ROLE = Qt.UserRole
ACCENT = "#2e7d4f"          # vert « plante » du bloc Espèce
LINK_ACCENT = "#66de8f"     # vert clair « ça se clique » (même teinte que la
                             # surbrillance de sélection déjà utilisée ailleurs
                             # dans l'appli) : sert de nuance discrète sur les
                             # noms de molécules qui ouvrent une structure 2D
'''),

    ("_make_table : colonnes redimensionnables à la main",
     '''def _make_table(headers, first_stretch=True):
    """Tableau en lecture seule, ligne entière sélectionnable, clic = sélection."""
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.setAlternatingRowColors(False)
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    for col in range(len(headers)):
        header.setSectionResizeMode(
            col, QHeaderView.Stretch if (col == 0 and first_stretch) else QHeaderView.ResizeToContents)
    table.viewport().setCursor(Qt.PointingHandCursor)
    return table''',
     '''def _make_table(headers, first_stretch=True):
    """Tableau en lecture seule, ligne entière sélectionnable, clic = sélection.
    Toutes les colonnes sont redimensionnables à la main (on peut tirer sur le
    bord d'une colonne pour l'élargir) ; la colonne de nom démarre large pour
    que les noms longs ne soient plus tronqués."""
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.setAlternatingRowColors(False)
    header = table.horizontalHeader()
    header.setStretchLastSection(True)
    for col in range(len(headers)):
        header.setSectionResizeMode(col, QHeaderView.Interactive)
    table.resizeColumnsToContents()
    if headers and first_stretch:
        header.resizeSection(0, max(header.sectionSize(0), 260))
    table.viewport().setCursor(Qt.PointingHandCursor)
    return table'''),

    ("état du tableau de suggestions (déplié/enroulé) dans __init__",
     '''        self._candidates = []            # suggestions du dernier nom ambigu
        self._struct_cache = {}''',
     '''        self._candidates = []            # suggestions du dernier nom ambigu
        self._sugg_expanded = True       # tableau de suggestions déplié / enroulé
        self._sugg_selected_name = None  # nom retenu quand le tableau est enroulé
        self._struct_cache = {}'''),

    ("bouton d'enroulement + méthodes _collapse/_expand_suggestions",
     '''    def _build_suggestions_box(self):
        """Tableau de suggestions, visible seulement si le nom est ambigu."""
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.sugg_title = QLabel("")
        self.sugg_title.setWordWrap(True)
        self.sugg_title.setStyleSheet("font-weight: bold;")
        self.sugg_table = _make_table([
            self._t("phyto_sugg_col_name", "Nom"),
            self._t("phyto_sugg_col_rank", "Rang"),
            self._t("phyto_sugg_col_family", "Famille"),
            self._t("phyto_sugg_col_match", "Correspondance"),
        ])
        self.sugg_table.setMaximumHeight(240)
        self.sugg_table.cellClicked.connect(self._on_suggestion_clicked)
        lay.addWidget(self.sugg_title)
        lay.addWidget(self.sugg_table)
        box.setVisible(False)
        return box

    def _build_plant_panel(self):''',
     '''    def _build_suggestions_box(self):
        """Tableau de suggestions, visible seulement si le nom est ambigu.
        Une fois une correspondance choisie, le tableau s'enroule comme un
        menu déroulant et laisse juste le nom retenu, avec un petit triangle
        pour le redéplier et changer de choix."""
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.sugg_title = QLabel("")
        self.sugg_title.setWordWrap(True)
        self.sugg_title.setStyleSheet("font-weight: bold;")

        self.sugg_toggle = QPushButton("")
        self.sugg_toggle.setObjectName("SuggToggle")
        self.sugg_toggle.setFlat(True)
        self.sugg_toggle.setCursor(Qt.PointingHandCursor)
        self.sugg_toggle.setStyleSheet(
            "QPushButton#SuggToggle {"
            " text-align: left; border: none; background: transparent;"
            " color: " + ACCENT + "; font-weight: bold; padding: 4px 2px; }"
            "QPushButton#SuggToggle:hover { color: " + LINK_ACCENT + "; }"
        )
        self.sugg_toggle.clicked.connect(self._on_toggle_suggestions)
        self.sugg_toggle.setVisible(False)

        self.sugg_table = _make_table([
            self._t("phyto_sugg_col_name", "Nom"),
            self._t("phyto_sugg_col_rank", "Rang"),
            self._t("phyto_sugg_col_family", "Famille"),
            self._t("phyto_sugg_col_match", "Correspondance"),
        ])
        self.sugg_table.setMaximumHeight(240)
        self.sugg_table.cellClicked.connect(self._on_suggestion_clicked)
        lay.addWidget(self.sugg_title)
        lay.addWidget(self.sugg_toggle)
        lay.addWidget(self.sugg_table)
        box.setVisible(False)
        return box

    def _on_toggle_suggestions(self):
        if self._sugg_expanded:
            self._collapse_suggestions(self._sugg_selected_name)
        else:
            self._expand_suggestions()

    def _collapse_suggestions(self, name):
        """Enroule le tableau et n'affiche plus que le nom retenu, cliquable
        pour rouvrir la liste des correspondances."""
        self._sugg_expanded = False
        self._sugg_selected_name = name
        self.sugg_table.setVisible(False)
        self.sugg_toggle.setText(
            "▶  " + (name or "?") + "   ·   "
            + self._t("phyto_sugg_reopen", "voir les autres correspondances"))
        self.sugg_toggle.setVisible(True)

    def _expand_suggestions(self):
        self._sugg_expanded = True
        self.sugg_table.setVisible(True)
        if self._sugg_selected_name:
            self.sugg_toggle.setText("▼  " + self._sugg_selected_name)
            self.sugg_toggle.setVisible(True)
        else:
            self.sugg_toggle.setVisible(False)

    def _build_plant_panel(self):'''),

    ("survol discret + curseur main sur l'arbre des familles",
     '''        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.family_tree.itemSelectionChanged.connect(self._on_family_selection_changed)
        right.addWidget(self.family_tree, 1)''',
     '''        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.family_tree.itemSelectionChanged.connect(self._on_family_selection_changed)
        self.family_tree.viewport().setCursor(Qt.PointingHandCursor)
        self.family_tree.setStyleSheet(
            "QTreeWidget::item { padding: 4px 6px; border-radius: 6px; }"
            "QTreeWidget::item:hover { background: rgba(46, 125, 79, 45); }"
            "QTreeWidget::item:selected { background: rgba(46, 125, 79, 95); }"
        )
        right.addWidget(self.family_tree, 1)'''),

    ("_hide_suggestions : réinitialise l'état déplié/enroulé",
     '''    def _hide_suggestions(self):
        self._candidates = []
        self.sugg_table.setRowCount(0)
        self.sugg_box.setVisible(False)''',
     '''    def _hide_suggestions(self):
        self._candidates = []
        self.sugg_table.setRowCount(0)
        self._sugg_expanded = True
        self._sugg_selected_name = None
        self.sugg_toggle.setVisible(False)
        self.sugg_table.setVisible(True)
        self.sugg_box.setVisible(False)'''),

    ("_fill_suggestions : info-bulle sur le nom + tableau redéplié",
     '''            rank = cand.get("rank") or "SPECIES"
            rank_key, rank_fb = RANK_LABELS.get(rank, RANK_LABELS["SPECIES"])
            name_item = QTableWidgetItem(
                cand.get("canonicalName") or cand.get("scientificName") or "?")
            if rank in ITALIC_RANKS:
                font = name_item.font()
                font.setItalic(True)
                name_item.setFont(font)
            family = cand.get("family") or ("—" if rank != "FAMILY" else "")
            for col, item in enumerate((
                    name_item,
                    QTableWidgetItem(self._t(rank_key, rank_fb)),
                    QTableWidgetItem(family),
                    QTableWidgetItem(self._match_note(cand)))):
                self.sugg_table.setItem(row, col, item)
        self.sugg_box.setVisible(True)

    def _on_suggestion_clicked(self, row, col):
        if not (0 <= row < len(self._candidates)):
            return
        cand = self._candidates[row]
        self._reset_results(keep_suggestions=True)
        self._load_candidate(cand)''',
     '''            rank = cand.get("rank") or "SPECIES"
            rank_key, rank_fb = RANK_LABELS.get(rank, RANK_LABELS["SPECIES"])
            name_text = cand.get("canonicalName") or cand.get("scientificName") or "?"
            name_item = QTableWidgetItem(name_text)
            name_item.setToolTip(name_text)
            if rank in ITALIC_RANKS:
                font = name_item.font()
                font.setItalic(True)
                name_item.setFont(font)
            family = cand.get("family") or ("—" if rank != "FAMILY" else "")
            for col, item in enumerate((
                    name_item,
                    QTableWidgetItem(self._t(rank_key, rank_fb)),
                    QTableWidgetItem(family),
                    QTableWidgetItem(self._match_note(cand)))):
                self.sugg_table.setItem(row, col, item)
        # nouvelle recherche : le tableau repart déplié, sans choix figé
        self._sugg_expanded = True
        self._sugg_selected_name = None
        self.sugg_toggle.setVisible(False)
        self.sugg_table.setVisible(True)
        self.sugg_box.setVisible(True)

    def _on_suggestion_clicked(self, row, col):
        if not (0 <= row < len(self._candidates)):
            return
        cand = self._candidates[row]
        name = cand.get("canonicalName") or cand.get("scientificName") or "?"
        self._reset_results(keep_suggestions=True)
        self._load_candidate(cand)
        self._collapse_suggestions(name)'''),

    ("arbre des familles : nuance de couleur + info-bulle sur les molécules",
     '''            for m in mols:
                QTreeWidgetItem(fam_item, [m.get("name", "?"), str(m.get("pubchem_cid") or "")])
            self.family_tree.addTopLevelItem(fam_item)''',
     '''            for m in mols:
                name = m.get("name", "?")
                cid = m.get("pubchem_cid")
                leaf = QTreeWidgetItem(fam_item, [name, str(cid or "")])
                leaf.setToolTip(0, name)
                if cid:
                    # nuance de couleur "lien" : incite discrètement au clic
                    # pour voir la structure 2D, sans texte explicite
                    leaf.setForeground(0, QColor(LINK_ACCENT))
                    leaf_font = leaf.font(0)
                    leaf_font.setBold(True)
                    leaf.setFont(0, leaf_font)
            self.family_tree.addTopLevelItem(fam_item)'''),

    ("tableau « autres molécules » : lignes de vraies molécules mises en évidence",
     '''            for m in molecules:
                self._other_rows.append(m)
                self._add_other_row([m.get("title") or ("CID " + str(m["cid"])),
                                     str(m["cid"]), m.get("formula", ""), m.get("weight", "")])''',
     '''            for m in molecules:
                self._other_rows.append(m)
                self._add_other_row([m.get("title") or ("CID " + str(m["cid"])),
                                     str(m["cid"]), m.get("formula", ""), m.get("weight", "")],
                                    highlight=True)'''),

    ("_add_other_row : info-bulle + nuance de couleur pour les vraies molécules",
     '''    def _add_other_row(self, cells):
        row = self.other_table.rowCount()
        self.other_table.insertRow(row)
        for col, text in enumerate(cells):
            self.other_table.setItem(row, col, QTableWidgetItem(text))''',
     '''    def _add_other_row(self, cells, highlight=False):
        row = self.other_table.rowCount()
        self.other_table.insertRow(row)
        for col, text in enumerate(cells):
            item = QTableWidgetItem(text)
            if col == 0:
                item.setToolTip(text)
                if highlight:
                    # nuance de couleur "lien" : incite discrètement au clic
                    # pour voir la structure 2D, sans texte explicite
                    item.setForeground(QColor(LINK_ACCENT))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
            self.other_table.setItem(row, col, item)'''),
]


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("phyto_page.py")
    if not target.exists():
        print("Fichier introuvable : " + str(target))
        print("Indique le chemin en argument : python3 " + sys.argv[0] + " chemin/vers/phyto_page.py")
        sys.exit(1)

    original = target.read_text(encoding="utf-8")
    text = original

    report = []
    failed = False
    for label, old, new in PATCHES:
        if new in text:
            report.append("  [SKIP]  " + label + "  (déjà appliqué)")
            continue
        count = text.count(old)
        if count == 1:
            text = text.replace(old, new, 1)
            report.append("  [OK]    " + label)
        elif count == 0:
            report.append("  [SKIP]  " + label + "  (bloc introuvable — déjà appliqué ou fichier différent)")
        else:
            report.append("  [ECHEC] " + label + "  (" + str(count) + " occurrences, pas unique)")
            failed = True

    if failed:
        print("Patch interrompu : au moins un bloc n'est pas unique dans le fichier.")
        print("\n".join(report))
        print("\nAucune modification écrite.")
        sys.exit(1)

    if text == original:
        print("Rien à faire : tous les blocs sont introuvables (patch déjà appliqué ?).")
        print("\n".join(report))
        sys.exit(0)

    try:
        ast.parse(text)
    except SyntaxError as exc:
        print("Vérification syntaxique ÉCHOUÉE après patch, rien n'est écrit sur disque :")
        print("  " + str(exc))
        sys.exit(1)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = target.with_name(target.stem + ".before_table_ux_" + stamp + target.suffix)
    shutil.copy2(target, backup)

    target.write_text(text, encoding="utf-8")

    print("Patch appliqué avec succès sur " + str(target))
    print("Sauvegarde : " + str(backup))
    print("Vérification syntaxique (ast.parse) : OK")
    print("\nDétail :")
    print("\n".join(report))


if __name__ == "__main__":
    main()
