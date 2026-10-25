"""
phyto_page.py
# --- patch16 phytomolecules tab ---
# --- patch20 : image agrandie, tableau resserre, LOTUS via ID GBIF ---
# --- patch21 : mise en page 2 colonnes pleine hauteur, erreurs distinctes, repli genre ---
# --- patch22 : bloc Espece en petit onglet, photos representatives (clic = autre photo), extraction SDF avec prefix ---
# --- patch23 : suggestions cliquables si le nom est ambigu, "Autres molecules" en tableau, structure 2D au clic ---

Onglet "Phytomolécules" de VinaStudio.
Pattern suivi : credits_page.py (QWidget autonome, réseau en arrière-plan
via QThread, styles hérités de l'app, traductions via lang_mgr.t() avec
repli défensif comme le patch12 : chaque clé a un texte français de repli).

Mode Phytomolécules :
  colonne gauche (stretch 2) : photo de la plante OU structure 2D de la molécule
                               sélectionnée dans le tableau (bouton retour photo) ;
  colonne droite (stretch 3) : recherche, carte Espèce, tableau de suggestions
                               (uniquement si le nom est ambigu), arbre des familles
                               chimiques, bouton de téléchargement.

Mode Autres molécules :
  tableau des résultats PubChem ; un clic sur une molécule ouvre sa fiche
  (structure 2D + propriétés) ; « Retour » réaffiche le tableau intact.
"""

import html
import inspect
import re
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QRect, QRectF
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QTextOption
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTreeWidget, QTreeWidgetItem, QMessageBox, QFileDialog, QStackedWidget,
    QHeaderView, QSizePolicy, QFrame, QTableWidget, QTableWidgetItem,
    QAbstractItemView,
)

from src import phyto_api
from src.docking.sdf_preparer import _split_sdf

LIGAND_DIR = Path("docking/ligands/prepared")
FAMILY_ROLE = Qt.UserRole
ACCENT = "#2e7d4f"          # vert « plante » du bloc Espèce
LINK_ACCENT = "#66de8f"     # vert clair « ça se clique » (même teinte que la
                             # surbrillance de sélection déjà utilisée ailleurs
                             # dans l'appli) : sert de nuance discrète sur les
                             # noms de molécules qui ouvrent une structure 2D

RANK_LABELS = {
    "SPECIES": ("phyto_rank_species", "Espèce"),
    "SUBSPECIES": ("phyto_rank_subspecies", "Sous-espèce"),
    "VARIETY": ("phyto_rank_variety", "Variété"),
    "GENUS": ("phyto_rank_genus", "Genre"),
    "FAMILY": ("phyto_rank_family", "Famille"),
}
ITALIC_RANKS = {"SPECIES", "SUBSPECIES", "VARIETY", "GENUS"}

# Noms de paramètres reconnus dans la signature de _split_sdf (liaison par nom)
_SDF_PATH_PARAMS = {"sdf_path", "sdf_file", "sdf", "input_path", "input_file", "in_path",
                    "src", "source", "path", "file", "filepath", "file_path"}
_DIR_PARAMS = {"work_dir", "out_dir", "output_dir", "dest_dir", "dest", "target_dir",
               "outdir", "directory", "folder", "dir"}
_PREFIX_PARAMS = {"prefix", "basename", "base_name", "stem"}


def split_sdf_by_cid(sdf_path, out_dir, prefix="mol"):
    """Decoupe un SDF PubChem groupe en fichiers <CID>.sdf (le titre de
    chaque bloc est le CID). Retourne une liste de (cid, chemin)."""
    import re
    text = Path(sdf_path).read_text(encoding="utf-8", errors="replace")
    blocks = [b.strip("\r\n") + "\n$$$$\n" for b in text.split("$$$$") if b.strip()]
    if not blocks:
        raise ValueError("Le fichier SDF ne contient aucune molécule : " + str(sdf_path))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for index, block in enumerate(blocks, start=1):
        lines = block.splitlines()
        first = lines[0].strip() if lines else ""
        mcid = re.match(r"(?i)^CID[_\- ]?(\d+)$", first)
        cid = first if first.isdigit() else (mcid.group(1) if mcid else None)
        if cid is None:
            m = re.search(r">\s*<PUBCHEM_COMPOUND_CID>\s*\n\s*(\d+)", block)
            if m:
                cid = m.group(1)
        name = ("CID_" + cid) if cid else (str(prefix) + "_" + format(index, "06d"))
        if cid:
            block = "\n".join(["CID_" + cid] + lines[1:]) + "\n"
        path = out_dir / (name + ".sdf")
        path.write_text(block, encoding="utf-8")
        outputs.append((cid, path))
    return outputs


def call_split_sdf(sdf_path, out_dir, prefix):
    """Appelle _split_sdf en liant les arguments PAR NOM d'après sa signature réelle
    (sdf_path, work_dir, prefix...). Lève TypeError avec la signature si un paramètre
    obligatoire n'est pas reconnu."""
    sig = inspect.signature(_split_sdf)
    kwargs = {}
    for name, param in sig.parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        low = name.lower()
        if low in _SDF_PATH_PARAMS:
            kwargs[name] = Path(sdf_path)
        elif low in _DIR_PARAMS:
            kwargs[name] = Path(out_dir)
        elif low in _PREFIX_PARAMS:
            kwargs[name] = prefix
        elif param.default is inspect.Parameter.empty:
            raise TypeError("paramètre obligatoire non reconnu '" + name
                            + "' dans _split_sdf" + str(sig))
    return _split_sdf(**kwargs)


def _t_resolve(lang_mgr, key, fallback):
    try:
        text = lang_mgr.t(key)
    except Exception:
        text = ""
    if not text or text == key:
        return fallback
    return text


class _NetworkWorker(QThread):
    """Exécute fn en arrière-plan. Les callbacks voyagent avec le signal et
    sont appelés par le thread principal (slot de PhytoPage), jamais ici."""
    finished_ok = Signal(object, object)       # (on_ok, résultat)
    failed = Signal(object, str, str)          # (on_fail, kind, message)

    def __init__(self, fn, on_ok, on_fail, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._on_ok = on_ok
        self._on_fail = on_fail
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
        except phyto_api.PhytoError as exc:
            self.failed.emit(self._on_fail, exc.kind, str(exc))
            return
        except Exception as exc:
            self.failed.emit(self._on_fail, "other", str(exc))
            return
        self.finished_ok.emit(self._on_ok, result)


class _CoverImage(QWidget):
    """Image qui remplit tout son rectangle (KeepAspectRatioByExpanding),
    recadrée au centre : jamais de bandes vides, quelle que soit la taille."""

    clicked = Signal()

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._caption = ""
        self._placeholder = placeholder
        self._cache = None
        self._cache_size = None
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(120, 120)

    def set_image(self, pixmap, caption=""):
        self._pixmap = pixmap if (pixmap is not None and not pixmap.isNull()) else None
        self._caption = caption if self._pixmap is not None else ""
        self._cache = None
        self.update()

    def set_placeholder(self, text):
        self._placeholder = text
        self._pixmap = None
        self._caption = ""
        self._cache = None
        self.set_clickable(False)
        self.update()

    def set_clickable(self, clickable):
        self._clickable = bool(clickable)
        self.setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)
        self.setToolTip("Cliquer pour voir une autre photo" if clickable else "")

    def mouseReleaseEvent(self, event):
        if getattr(self, "_clickable", False) and event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = self.rect()
        if self._pixmap is not None:
            if self._cache is None or self._cache_size != rect.size():
                self._cache = self._pixmap.scaled(
                    rect.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                self._cache_size = rect.size()
            sx = (self._cache.width() - rect.width()) // 2
            sy = (self._cache.height() - rect.height()) // 2
            painter.drawPixmap(rect, self._cache, QRect(sx, sy, rect.width(), rect.height()))
        else:
            painter.setPen(QColor(255, 255, 255, 140))
            option = QTextOption(Qt.AlignCenter)
            option.setWrapMode(QTextOption.WordWrap)
            painter.drawText(QRectF(rect.adjusted(12, 12, -12, -12)), self._placeholder, option)
        if self._caption:
            bar = QRect(0, rect.height() - 24, rect.width(), 24)
            painter.fillRect(bar, QColor(0, 0, 0, 150))
            painter.setPen(QColor(255, 255, 255, 230))
            painter.drawText(QRectF(bar.adjusted(8, 0, -8, 0)), self._caption,
                             QTextOption(Qt.AlignLeft | Qt.AlignVCenter))
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        painter.end()


class _StructureView(QWidget):
    """Structure 2D d'une molécule : fond blanc (les images PubChem sont noires
    sur blanc), centrée, sans déformation, avec légende. Sans image : un message."""

    def __init__(self, message="", parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._message = message
        self._caption = ""
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(160, 160)

    def show_message(self, text):
        self._pixmap = None
        self._caption = ""
        self._message = text
        self.update()

    def show_pixmap(self, pixmap, caption=""):
        self._pixmap = pixmap if (pixmap is not None and not pixmap.isNull()) else None
        self._caption = caption if self._pixmap is not None else ""
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = self.rect().adjusted(0, 0, -1, -1)
        painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRoundedRect(rect, 8, 8)
        caption_h = 26 if self._caption else 0
        area = rect.adjusted(14, 14, -14, -14 - caption_h)
        if self._pixmap is not None:
            scaled = self._pixmap.scaled(area.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = area.x() + (area.width() - scaled.width()) // 2
            y = area.y() + (area.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.setPen(QColor(90, 90, 90))
            option = QTextOption(Qt.AlignCenter)
            option.setWrapMode(QTextOption.WordWrap)
            painter.drawText(QRectF(area), self._message, option)
        if self._caption:
            painter.setPen(QColor(70, 70, 70))
            painter.drawText(QRectF(rect.x() + 10, rect.bottom() - caption_h, rect.width() - 20, caption_h),
                             self._caption, QTextOption(Qt.AlignCenter))
        painter.end()


def _make_table(headers, first_stretch=True):
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
    return table


# Seuils de taille (atomes lourds), d'après le test de docking : jusqu'à 43 atomes
# (15 torsions) le docking aboutit ; à 65 atomes (24 torsions) il dépasse 7 minutes.
# Provisoires : rien n'a été mesuré entre les deux.
SIZE_ORANGE_HA = 46
SIZE_RED_HA = 65


def _sdf_metrics(path):
    """(poids moléculaire, liaisons rotatives, atomes lourds) d'un SDF ; None si inconnu."""
    import re
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None, None, None

    def prop(name):
        m = re.search(r">\s*<" + name + r">\s*\r?\n\s*([^\r\n]+)", text)
        return m.group(1).strip() if m else None

    mw = rb = ha = None
    try:
        v = prop("PUBCHEM_MOLECULAR_WEIGHT")
        mw = float(v) if v else None
        v = prop("PUBCHEM_CACTVS_ROTATABLE_BOND")
        rb = int(v) if v else None
        v = prop("PUBCHEM_HEAVY_ATOM_COUNT")
        ha = int(v) if v else None
    except ValueError:
        mw = rb = ha = None
    if mw is None or rb is None or ha is None:
        try:
            from rdkit import Chem, RDLogger
            from rdkit.Chem import Descriptors, rdMolDescriptors
            RDLogger.DisableLog("rdApp.*")
            mol = next((m for m in Chem.SDMolSupplier(str(path), removeHs=False) if m is not None), None)
            if mol is not None:
                frags = Chem.GetMolFrags(mol, asMols=True)
                g = max(frags, key=lambda x: x.GetNumHeavyAtoms())
                mw = mw if mw is not None else float(Descriptors.MolWt(g))
                rb = rb if rb is not None else int(rdMolDescriptors.CalcNumRotatableBonds(g))
                ha = ha if ha is not None else int(g.GetNumHeavyAtoms())
        except Exception:
            pass
    return mw, rb, ha


def _size_class(ha):
    if ha is None:
        return "inconnu"
    if ha >= SIZE_RED_HA:
        return "rouge"
    if ha >= SIZE_ORANGE_HA:
        return "orange"
    return "vert"


from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QProgressBar, QVBoxLayout


class _ProgressBridge(QObject):
    message = Signal(str)


class _ProgressDialog(QDialog):
    """Fenêtre d'attente : aucune couleur codée en dur, tout vient du thème actif.
    Les étapes à venir sont affichées « désactivées » (grisées par le thème)."""

    STAGES = [
        ("download", "Téléchargement des structures depuis PubChem"),
        ("gen3d", "Récupération 2D et génération des structures 3D manquantes"),
        ("write", "Assemblage du fichier groupé"),
        ("split", "Découpe en fichiers individuels"),
        ("index", "Calcul des tailles et écriture de l'index"),
    ]

    def __init__(self, parent=None, total=0):
        super().__init__(parent)
        self.setWindowTitle("Traitement en cours")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.setMinimumWidth(500)
        self._idx = 0
        self._detail = ""
        self._seen = set()
        self._dots = 0
        self._total = total
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        self._title = QLabel()
        self._title.setTextFormat(Qt.TextFormat.PlainText)
        tf = self._title.font()
        tf.setBold(True)
        self._title.setFont(tf)
        lay.addWidget(self._title)
        if total:
            sub = QLabel("%d molécule(s) à traiter" % total)
            sub.setTextFormat(Qt.TextFormat.PlainText)
            sub.setEnabled(False)
            lay.addWidget(sub)
        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setTextVisible(False)
        lay.addWidget(bar)
        self._rows = []
        for _key, _label in self.STAGES:
            lb = QLabel()
            lb.setTextFormat(Qt.TextFormat.PlainText)
            lb.setWordWrap(True)
            self._rows.append(lb)
            lay.addWidget(lb)
        note = QLabel("Cela peut durer de quelques secondes à quelques minutes. "
                      "Ne fermez pas le logiciel.")
        note.setTextFormat(Qt.TextFormat.PlainText)
        note.setWordWrap(True)
        note.setEnabled(False)
        lay.addWidget(note)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(400)
        self._render()

    def reject(self):
        pass

    def _tick(self):
        self._dots = (self._dots + 1) % 4
        self._render()

    def set_stage(self, stage, detail=""):
        keys = [k for k, _ in self.STAGES]
        if stage not in keys:
            return
        i = keys.index(stage)
        if i <= 1 and self._idx <= 1:
            self._idx = i
        else:
            self._idx = max(self._idx, i)
        self._seen.add(stage)
        if i == self._idx:
            self._detail = detail
        self._render()

    def _render(self):
        dots = "." * self._dots
        self._title.setText("Veuillez patienter" + dots)
        for j, (key, label) in enumerate(self.STAGES):
            lb = self._rows[j]
            f = lb.font()
            f.setBold(j == self._idx)
            lb.setFont(f)
            if j < self._idx:
                if key == "gen3d" and "gen3d" not in self._seen:
                    lb.setText("–  %s (non nécessaire)" % label)
                    lb.setEnabled(False)
                else:
                    lb.setText("✓  %s" % label)
                    lb.setEnabled(True)
            elif j == self._idx:
                extra = ("  (%s)" % self._detail) if self._detail else ""
                lb.setText("●  %s%s%s" % (label, extra, dots))
                lb.setEnabled(True)
            else:
                lb.setText("○  %s" % label)
                lb.setEnabled(False)

    def finish(self):
        try:
            self._timer.stop()
            self.hide()
            self.deleteLater()
        except Exception:
            pass


class PhytoPage(QWidget):
    def __init__(self, lang_mgr=None, parent=None):
        super().__init__(parent)
        self.lang_mgr = lang_mgr
        self._current_families = {}
        self._current_usage_key = None
        self._last_query = ""
        self._info_text = ""
        self._img_candidates = []
        self._img_index = -1
        self._img_loading = False
        self._candidates = []            # suggestions du dernier nom ambigu
        self._sugg_expanded = True       # tableau de suggestions déplié / enroulé
        self._sugg_selected_name = None  # nom retenu quand le tableau est enroulé
        self._struct_cache = {}          # CID -> QPixmap (aller-retour instantané)
        self._plant_struct_cid = None    # CID affiché à gauche (None = photo)
        self._other_query = ""
        self._other_rows = []            # lignes du tableau « autres molécules »
        self._other_current = None       # molécule ouverte dans la fiche
        self._workers = []
        self._build_ui()

    def _t(self, key, fallback):
        if self.lang_mgr is None:
            return fallback
        return _t_resolve(self.lang_mgr, key, fallback)

    def retranslate(self):
        """Refresh every persistent Phytomolecules control after a language change."""
        self.btn_mode_phyto.setText(self._t("phyto_mode_plant", "Phytomolecules"))
        self.btn_mode_other.setText(self._t("phyto_mode_other", "Other organic molecules"))
        self.btn_back_photo.setText(self._t("phyto_back_photo", "← Plant photo"))
        self.plant_input.setPlaceholderText(self._t(
            "phyto_plant_placeholder", "Plant name (scientific or common)..."
        ))
        self.btn_search_plant.setText(self._t("phyto_search_btn", "Search"))
        self.species_tab.setText(self._t("phyto_rank_species", "Species"))
        self.plant_image.set_placeholder(self._t("phyto_no_image_yet", "No image."))
        self.family_tree.setHeaderLabels([
            self._t("phyto_col_family", "Chemical family / molecule"),
            self._t("phyto_col_cid", "PubChem CID"),
        ])
        self.btn_download_family.setText(self._t(
            "phyto_download_family", "Download this family from PubChem"
        ))
        self.other_input.setPlaceholderText(self._t(
            "phyto_other_placeholder", "Molecule name (drug, organic compound)..."
        ))
        self.btn_search_other.setText(self._t("phyto_search_btn", "Search"))
        self.other_table.setHorizontalHeaderLabels([
            self._t("phyto_other_col_name", "Molecule"),
            self._t("phyto_col_cid_short", "CID"),
            self._t("phyto_other_col_formula", "Formula"),
            self._t("phyto_other_col_weight", "Mass (g/mol)"),
        ])
        self.btn_other_back.setText(self._t("phyto_back_results", "← Back to results"))
        self.btn_other_download.setText(self._t(
            "phyto_download_molecule", "Download this molecule from PubChem"
        ))
        self.sugg_table.setHorizontalHeaderLabels([
            self._t("phyto_sugg_col_name", "Name"),
            self._t("phyto_sugg_col_rank", "Rank"),
            self._t("phyto_sugg_col_family", "Family"),
            self._t("phyto_sugg_col_match", "Match"),
        ])
        if self._sugg_selected_name is not None:
            self._collapse_suggestions(self._sugg_selected_name)

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        root = QVBoxLayout(self)

        mode_row = QHBoxLayout()
        self.btn_mode_phyto = QPushButton(self._t("phyto_mode_plant", "Phytomolécules"))
        self.btn_mode_other = QPushButton(self._t("phyto_mode_other", "Autres molécules organiques"))
        self.btn_mode_phyto.setObjectName("PrimaryButton")
        self.btn_mode_phyto.setCheckable(True)
        self.btn_mode_other.setCheckable(True)
        self.btn_mode_phyto.setChecked(True)
        self.btn_mode_phyto.clicked.connect(lambda: self._switch_mode(0))
        self.btn_mode_other.clicked.connect(lambda: self._switch_mode(1))
        mode_row.addWidget(self.btn_mode_phyto)
        mode_row.addWidget(self.btn_mode_other)
        mode_row.addStretch(1)
        root.addLayout(mode_row)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.stack.addWidget(self._build_plant_panel())
        self.stack.addWidget(self._build_other_panel())

    def _switch_mode(self, index):
        self.btn_mode_phyto.setChecked(index == 0)
        self.btn_mode_other.setChecked(index == 1)
        self.stack.setCurrentIndex(index)

    def _build_species_box(self):
        """Petit onglet « Espèce » collé à un cadre qui affiche la plante confirmée."""
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.species_tab = QLabel(self._t("phyto_rank_species", "Espèce"))
        self.species_tab.setStyleSheet(
            "QLabel { background: " + ACCENT + "; color: white; font-weight: bold;"
            " padding: 3px 16px; border: none;"
            " border-top-left-radius: 8px; border-top-right-radius: 8px;"
            " border-bottom-left-radius: 0px; border-bottom-right-radius: 0px; }")
        tab_row = QHBoxLayout()
        tab_row.setContentsMargins(0, 0, 0, 0)
        tab_row.addWidget(self.species_tab)
        tab_row.addStretch(1)
        lay.addLayout(tab_row)

        self.species_card = QFrame()
        self.species_card.setObjectName("SpeciesCard")
        self.species_card.setStyleSheet(
            "QFrame#SpeciesCard { border: 2px solid " + ACCENT + ";"
            " border-top-left-radius: 0px; border-top-right-radius: 8px;"
            " border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;"
            " background: rgba(46, 125, 79, 45); }")
        card_lay = QVBoxLayout(self.species_card)
        card_lay.setContentsMargins(14, 8, 14, 10)
        card_lay.setSpacing(2)
        self.species_name = QLabel("")
        self.species_name.setWordWrap(True)
        self.species_name.setStyleSheet(
            "font-size: 20px; font-weight: bold; font-style: italic;"
            " background: transparent; border: none;")
        self.species_detail = QLabel("")
        self.species_detail.setWordWrap(True)
        self.species_detail.setStyleSheet("background: transparent; border: none;")
        card_lay.addWidget(self.species_name)
        card_lay.addWidget(self.species_detail)
        lay.addWidget(self.species_card)

        box.setVisible(False)
        return box

    def _build_suggestions_box(self):
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

    def _build_plant_panel(self):
        panel = QWidget()
        outer = QHBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        # --- colonne gauche : photo OU structure 2D, toute la hauteur ----
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(6)
        self.btn_back_photo = QPushButton(self._t("phyto_back_photo", "← Photo de la plante"))
        self.btn_back_photo.clicked.connect(self._show_plant_photo)
        self.btn_back_photo.setVisible(False)
        left.addWidget(self.btn_back_photo)

        self.left_stack = QStackedWidget()
        self.plant_image = _CoverImage(self._t("phyto_no_image_yet", "Aucune image."))
        self.plant_image.clicked.connect(self._on_image_clicked)
        self.plant_struct = _StructureView()
        self.left_stack.addWidget(self.plant_image)     # 0 : photo
        self.left_stack.addWidget(self.plant_struct)    # 1 : structure 2D
        left.addWidget(self.left_stack, 1)
        outer.addLayout(left, 2)

        # --- colonne droite ---------------------------------------------
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(8)

        search_row = QHBoxLayout()
        self.plant_input = QLineEdit()
        self.plant_input.setPlaceholderText(
            self._t("phyto_plant_placeholder", "Nom de la plante (scientifique ou courant)..."))
        self.plant_input.returnPressed.connect(self._on_search_plant)
        self.btn_search_plant = QPushButton(self._t("phyto_search_btn", "Rechercher"))
        self.btn_search_plant.setObjectName("PrimaryButton")
        self.btn_search_plant.clicked.connect(self._on_search_plant)
        search_row.addWidget(self.plant_input, 1)
        search_row.addWidget(self.btn_search_plant)
        right.addLayout(search_row)

        self.species_box = self._build_species_box()
        right.addWidget(self.species_box)

        self.plant_name_label = QLabel(self._t("phyto_no_plant", "Aucune plante confirmée."))
        self.plant_name_label.setWordWrap(True)
        right.addWidget(self.plant_name_label)

        self.sugg_box = self._build_suggestions_box()
        right.addWidget(self.sugg_box)

        self.family_tree = QTreeWidget()
        self.family_tree.setHeaderLabels([
            self._t("phyto_col_family", "Famille chimique / molécule"),
            self._t("phyto_col_cid", "CID PubChem"),
        ])
        self.family_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.family_tree.setUniformRowHeights(True)
        header = self.family_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.family_tree.itemSelectionChanged.connect(self._on_family_selection_changed)
        self.family_tree.viewport().setCursor(Qt.PointingHandCursor)
        self.family_tree.setStyleSheet(
            "QTreeWidget::item { padding: 4px 6px; border-radius: 6px; }"
            "QTreeWidget::item:hover { background: rgba(46, 125, 79, 45); }"
            "QTreeWidget::item:selected { background: rgba(46, 125, 79, 95); }"
        )
        right.addWidget(self.family_tree, 1)

        self.btn_download_family = QPushButton(
            self._t("phyto_download_family", "Télécharger cette famille depuis PubChem"))
        self.btn_download_family.setObjectName("PrimaryButton")
        self.btn_download_family.clicked.connect(self._on_download_selected_family)
        self.btn_download_family.setEnabled(False)
        right.addWidget(self.btn_download_family)

        outer.addLayout(right, 3)
        return panel

    def _build_other_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        row = QHBoxLayout()
        self.other_input = QLineEdit()
        self.other_input.setPlaceholderText(
            self._t("phyto_other_placeholder", "Nom de la molécule (médicament, composé organique)..."))
        self.other_input.returnPressed.connect(self._on_search_other)
        self.btn_search_other = QPushButton(self._t("phyto_search_btn", "Rechercher"))
        self.btn_search_other.setObjectName("PrimaryButton")
        self.btn_search_other.clicked.connect(self._on_search_other)
        row.addWidget(self.other_input, 1)
        row.addWidget(self.btn_search_other)
        layout.addLayout(row)

        self.other_result_label = QLabel("")
        self.other_result_label.setWordWrap(True)
        layout.addWidget(self.other_result_label)

        self.other_stack = QStackedWidget()
        layout.addWidget(self.other_stack, 1)

        # page 0 : tableau des résultats
        self.other_table = _make_table([
            self._t("phyto_other_col_name", "Molécule"),
            self._t("phyto_col_cid_short", "CID"),
            self._t("phyto_other_col_formula", "Formule"),
            self._t("phyto_other_col_weight", "Masse (g/mol)"),
        ])
        self.other_table.cellClicked.connect(self._on_other_row_clicked)
        self.other_stack.addWidget(self.other_table)

        # page 1 : fiche d'une molécule (structure 2D + propriétés)
        detail = QWidget()
        dl = QVBoxLayout(detail)
        dl.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        self.btn_other_back = QPushButton(self._t("phyto_back_results", "← Retour aux résultats"))
        self.btn_other_back.clicked.connect(self._on_other_back)
        top.addWidget(self.btn_other_back)
        top.addStretch(1)
        dl.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(12)
        self.other_struct = _StructureView()
        body.addWidget(self.other_struct, 3)
        info = QVBoxLayout()
        self.other_detail_title = QLabel("")
        self.other_detail_title.setWordWrap(True)
        self.other_detail_title.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.other_detail_info = QLabel("")
        self.other_detail_info.setWordWrap(True)
        self.other_detail_info.setTextFormat(Qt.RichText)
        self.other_detail_info.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.btn_other_download = QPushButton(
            self._t("phyto_download_molecule", "Télécharger cette molécule depuis PubChem"))
        self.btn_other_download.setObjectName("PrimaryButton")
        self.btn_other_download.clicked.connect(self._on_download_other)
        info.addWidget(self.other_detail_title)
        info.addWidget(self.other_detail_info, 1)
        info.addWidget(self.btn_other_download)
        body.addLayout(info, 2)
        dl.addLayout(body, 1)
        self.other_stack.addWidget(detail)
        return panel

    # ------------------------------------------------------- réseau (async)

    def _run_async(self, fn, on_ok, *args, on_fail=None, **kwargs):
        worker = _NetworkWorker(fn, on_ok, on_fail, *args, **kwargs)
        worker.finished_ok.connect(self._dispatch_ok)
        worker.failed.connect(self._dispatch_failed)
        self._workers.append(worker)
        worker.start()

    def _dispatch_ok(self, callback, result):
        if callback is not None:
            callback(result)

    def _dispatch_failed(self, callback, kind, message):
        if callback is None:
            callback = self._on_generic_error
        callback(kind, message)

    def _on_generic_error(self, kind, message):
        QMessageBox.warning(self, self._t("phyto_error_title", "Erreur réseau"), message)

    # --------------------------------------------------- structure 2D (commun)

    def _fetch_structure(self, cid, on_ready, on_error):
        """Structure 2D d'un CID : cache mémoire, sinon PubChem en arrière-plan.
        Appelle on_ready(QPixmap) ou on_error(message) dans le thread principal."""
        if cid in self._struct_cache:
            on_ready(self._struct_cache[cid])
            return

        def ok(data):
            pix = QPixmap()
            if pix.loadFromData(data):
                self._struct_cache[cid] = pix
                on_ready(pix)
            else:
                on_error(self._t("phyto_struct_bad", "Image illisible."))

        self._run_async(phyto_api.pubchem_fetch_2d_png, ok, cid,
                        on_fail=lambda kind, message: on_error(message))

    # ------------------------------------------------------------- plante

    def _set_info(self, text):
        self._info_text = text
        self.plant_name_label.setText(text)

    def _hide_species(self):
        self.species_box.setVisible(False)

    def _match_note(self, cand):
        """Phrase courte expliquant pourquoi cette plante correspond à la saisie."""
        mode = cand.get("_lookup_mode")
        query = " « " + self._last_query + " »"
        if mode == "vernacular":
            return (self._t("phyto_via_common_name", "reconnu via le nom courant")
                    + " « " + (cand.get("matched") or self._last_query) + " »")
        if mode == "fuzzy":
            note = self._t("phyto_via_fuzzy", "orthographe proche de") + query
            if cand.get("confidence") is not None:
                note += " (" + str(cand["confidence"]) + " %)"
            return note
        if mode == "prefix":
            return self._t("phyto_via_prefix", "nom commençant par") + query
        if mode == "synonym":
            return self._t("phyto_via_synonym", "synonyme reconnu pour") + query
        return self._t("phyto_via_scientific", "nom scientifique")

    def _show_species(self, match):
        rank = match.get("rank") or "SPECIES"
        key, fallback = RANK_LABELS.get(rank, RANK_LABELS["SPECIES"])
        self.species_tab.setText(self._t(key, fallback))
        self.species_name.setText(
            match.get("canonicalName") or match.get("scientificName") or "?")
        parts = []
        if match.get("family") and rank != "FAMILY":
            parts.append(self._t("phyto_family_label", "Famille") + " : " + match["family"])
        if match.get("_lookup_mode") not in (None, "scientific"):
            parts.append(self._match_note(match))
        self.species_detail.setText("  ·  ".join(parts))
        self.species_detail.setVisible(bool(parts))
        self.species_box.setVisible(True)

    def _reset_results(self, keep_suggestions=False):
        self._current_families = {}
        self._current_usage_key = None
        self._img_candidates = []
        self._img_index = -1
        self._img_loading = False
        self._info_text = ""
        self.family_tree.clear()
        self.btn_download_family.setEnabled(False)
        self._hide_species()
        self._show_plant_photo()
        self.plant_image.set_placeholder(self._t("phyto_no_image_yet", "Aucune image."))
        if not keep_suggestions:
            self._hide_suggestions()

    def _hide_suggestions(self):
        self._candidates = []
        self.sugg_table.setRowCount(0)
        self._sugg_expanded = True
        self._sugg_selected_name = None
        self.sugg_toggle.setVisible(False)
        self.sugg_table.setVisible(True)
        self.sugg_box.setVisible(False)

    def _on_search_plant(self):
        name = self.plant_input.text().strip()
        if not name:
            return
        self._last_query = name
        self._reset_results()
        self._set_info(self._t("phyto_searching", "Recherche en cours..."))
        self.btn_search_plant.setEnabled(False)
        self._run_async(phyto_api.gbif_find_candidates, self._on_candidates, name,
                        on_fail=self._on_match_failed)

    def _on_match_failed(self, kind, message):
        self.btn_search_plant.setEnabled(True)
        self._reset_results()
        if kind == "not_found":
            self._set_info(self._t("phyto_not_found", "Aucune plante trouvée pour ce nom."))
            return
        self._set_info(self._t("phyto_search_failed", "La recherche a échoué."))
        self._on_generic_error(kind, message)

    def _on_candidates(self, result):
        self.btn_search_plant.setEnabled(True)
        if result.get("query") != self._last_query:
            return  # résultat d'une recherche précédente
        cands = result.get("candidates") or []
        if not cands:
            self._on_match_failed("not_found", "")
            return
        if not result.get("ambiguous"):
            self._hide_suggestions()
            self._load_candidate(cands[0])
            return
        # Nom ambigu : on n'impose pas un choix, on propose les correspondances.
        self._candidates = cands
        self._fill_suggestions(cands)
        self._set_info(self._t(
            "phyto_ambiguous_hint",
            "Le nom « {q} » correspond à plusieurs plantes : cliquez sur celle que vous cherchez."
        ).replace("{q}", self._last_query))
        self.plant_image.set_placeholder(
            self._t("phyto_choose_match", "Choisissez une correspondance dans le tableau."))

    def _fill_suggestions(self, cands):
        self.sugg_title.setText(self._t("phyto_sugg_title", "Correspondances possibles"))
        self.sugg_table.setRowCount(0)
        for cand in cands:
            row = self.sugg_table.rowCount()
            self.sugg_table.insertRow(row)
            rank = cand.get("rank") or "SPECIES"
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
        self._collapse_suggestions(name)

    def _load_candidate(self, match):
        """Affiche la plante choisie (carte Espèce) et lance photo + molécules."""
        canonical = match.get("canonicalName") or match.get("scientificName") or "?"
        self._show_species(match)
        self._set_info(self._t("phyto_loading_molecules", "Recherche des molécules..."))

        usage_key = match.get("usageKey")
        self._current_usage_key = usage_key
        self._current_plant_name = canonical
        self.plant_image.set_placeholder(
            self._t("phyto_image_loading", "Recherche de l'image de référence..."))
        self._run_async(
            phyto_api.fetch_reference_image, self._on_gbif_image,
            usage_key, canonical, species_name=match.get("species"),
            on_fail=self._on_image_failed,
        )
        self._run_async(
            phyto_api.lotus_compounds_for_taxon, self._on_lotus_result,
            usage_key, canonical,
            accepted_key=match.get("acceptedUsageKey"),
            genus_key=match.get("genusKey"),
            genus_name=match.get("genus"),
            rank=match.get("rank"),
            on_fail=self._on_lotus_failed,
        )

    # ---- image : meilleure photo d'abord, clic = photo suivante -----------

    def _show_image(self, data, index, source):
        pix = QPixmap()
        if not (data and pix.loadFromData(data)):
            return False
        total = len(self._img_candidates)
        caption = source or ""
        if total > 1:
            caption += "  ·  " + self._t("phyto_click_next", "clic : autre photo") \
                       + " (" + str(index + 1) + "/" + str(total) + ")"
        self.plant_image.set_image(pix, caption)
        self.plant_image.set_clickable(total > 1)
        self._img_index = index
        return True

    def _on_gbif_image(self, result):
        if result.get("usage_key") != self._current_usage_key:
            return  # résultat d'une recherche précédente
        self._img_candidates = result.get("candidates") or []
        if not self._show_image(result.get("data"), result.get("index", 0), result.get("source")):
            self.plant_image.set_placeholder(
                self._t("phyto_no_reference_image", "Aucune image de référence disponible."))

    def _on_image_failed(self, kind, message):
        self.plant_image.set_placeholder(
            self._t("phyto_no_reference_image", "Aucune image de référence disponible."))

    def _on_image_clicked(self):
        total = len(self._img_candidates)
        if self._img_loading or total < 2:
            return
        self._img_loading = True
        self._run_async(
            phyto_api.fetch_next_image, self._on_next_image,
            self._current_usage_key, self._img_candidates,
            (self._img_index + 1) % total, self._img_index,
            on_fail=self._on_next_image_failed,
        )

    def _on_next_image(self, result):
        if result.get("usage_key") != self._current_usage_key:
            return
        self._img_loading = False
        if result.get("data"):
            self._show_image(result["data"], result.get("index", 0), result.get("source"))

    def _on_next_image_failed(self, kind, message):
        self._img_loading = False

    # ---- colonne gauche : photo <-> structure 2D --------------------------

    def _show_plant_photo(self):
        self._plant_struct_cid = None
        self.left_stack.setCurrentIndex(0)
        self.btn_back_photo.setVisible(False)

    def _show_plant_structure(self, cid, name):
        self._plant_struct_cid = cid
        self.left_stack.setCurrentIndex(1)
        self.btn_back_photo.setVisible(True)
        if cid is None:
            self.plant_struct.show_message(self._t(
                "phyto_struct_no_cid", "Pas de CID PubChem pour cette molécule : structure 2D indisponible."))
            return
        caption = name + "  ·  CID " + str(cid)
        self.plant_struct.show_message(self._t("phyto_struct_loading", "Chargement de la structure 2D..."))

        def ready(pix):
            if self._plant_struct_cid == cid:
                self.plant_struct.show_pixmap(pix, caption)

        def failed(message):
            if self._plant_struct_cid == cid:
                self.plant_struct.show_message(
                    self._t("phyto_struct_unavailable", "Structure 2D indisponible.") + "\n" + message)

        self._fetch_structure(cid, ready, failed)

    # ---- molécules --------------------------------------------------------

    def _on_lotus_failed(self, kind, message):
        self._set_info(self._t("phyto_molecules_failed", "Molécules indisponibles : ") + message)

    def _on_lotus_result(self, result):
        if result.get("usage_key") != self._current_usage_key:
            return  # résultat d'une recherche précédente
        compounds = result.get("compounds", [])
        level = result.get("level")
        genus = result.get("genus") or "?"
        self._current_families = phyto_api.group_by_family(compounds)
        self.family_tree.clear()

        if not compounds:
            self._set_info(self._t(
                "phyto_no_compounds",
                "Aucune molécule trouvée dans LOTUS/Wikidata pour cette plante."))
            return

        lines = []
        if level == "genus":
            lines.append(self._t(
                "phyto_genus_fallback",
                "Aucune donnée pour l'espèce, molécules du genre {genus} affichées."
            ).replace("{genus}", genus))
        lines.append(
            str(len(compounds)) + " " + self._t("phyto_molecules_count", "molécule(s) dans")
            + " " + str(len(self._current_families))
            + " " + self._t("phyto_families_count", "famille(s)."))
        if len(compounds) >= 490:
            lines.append(self._t(
                "phyto_truncated",
                "⚠ Liste probablement incomplète : LOTUS limite chaque requête à 500 lignes."))
        self._set_info("\n".join(lines))

        for family, mols in self._current_families.items():
            fam_item = QTreeWidgetItem([family + " (" + str(len(mols)) + ")", ""])
            fam_item.setData(0, FAMILY_ROLE, family)
            for m in mols:
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
            self.family_tree.addTopLevelItem(fam_item)
        self.family_tree.collapseAll()

    # ---------------------------------------------------------- téléchargement

    def _selected_family_name(self):
        items = self.family_tree.selectedItems()
        if not items:
            return None
        item = items[0]
        top = item.parent() or item
        return top.data(0, FAMILY_ROLE)

    def _update_download_button(self):
        self.btn_download_family.setEnabled(self._selected_family_name() is not None)

    def _on_family_selection_changed(self):
        """Famille -> retour à la photo ; molécule -> sa structure 2D à gauche."""
        self._update_download_button()
        items = self.family_tree.selectedItems()
        if items and items[0].parent() is not None:
            item = items[0]
            cid_text = item.text(1).strip()
            self._show_plant_structure(int(cid_text) if cid_text.isdigit() else None,
                                       item.text(0))
        else:
            self._show_plant_photo()

    def _on_download_selected_family(self):
        family_name = self._selected_family_name()
        if family_name is None:
            return
        mols = self._current_families.get(family_name, [])
        cids = []
        for m in mols:
            try:
                cid = int(m["pubchem_cid"])
            except (KeyError, TypeError, ValueError):
                continue
            if cid not in cids:
                cids.append(cid)
        if not cids:
            QMessageBox.information(
                self, self._t("phyto_info_title", "Information"),
                self._t("phyto_no_cid", "Aucun CID PubChem disponible pour cette famille."))
            return
        chosen = QFileDialog.getExistingDirectory(
            self, self._t("phyto_choose_dir", "Dossier de destination"), str(LIGAND_DIR))
        if not chosen:
            return
        out_dir = Path(chosen)
        safe_name = re.sub(r"[^\w\-]+", "_", family_name).strip("_") or "famille"
        out_file = out_dir / (safe_name + "_batch.sdf")
        self.btn_download_family.setEnabled(False)
        self.plant_name_label.setText(
            self._t("phyto_downloading", "Téléchargement PubChem en cours : ")
            + str(len(cids)) + " CID...")
        self._open_progress(len(cids))
        self._run_async(
            self._download_with_progress,
            lambda path: self._on_family_downloaded(path, out_dir, safe_name),
            cids, out_file,
            on_fail=self._on_download_failed,
        )

    def _on_download_failed(self, kind, message):
        self._close_progress()
        self._update_download_button()
        self.plant_name_label.setText(self._info_text)
        self._on_generic_error(kind, message)

    def _on_family_downloaded(self, sdf_path, out_dir, prefix):
        self._update_download_button()
        self.plant_name_label.setText(self._info_text)
        self._split_and_report(sdf_path, out_dir, prefix,
                               self._t("phyto_done_msg",
                                       "Famille téléchargée et extraite dans le dossier ligand."))

    def _write_cid_index(self, pairs, out_dir, prefix):
        """Ecrit <prefix>_index.csv : CID, nom, famille, fichier (Excel FR)."""
        try:
            import csv
            names, families = {}, {}
            for fam, mols in (getattr(self, "_current_families", None) or {}).items():
                for m in mols:
                    try:
                        key = int(m.get("pubchem_cid"))
                    except (TypeError, ValueError):
                        continue
                    names.setdefault(key, m.get("name", ""))
                    families.setdefault(key, fam)
            for m in (getattr(self, "_other_rows", None) or []):
                try:
                    key = int(m.get("cid"))
                except (TypeError, ValueError):
                    continue
                names.setdefault(key, m.get("title", ""))
            cur = getattr(self, "_other_current", None)
            if isinstance(cur, dict) and cur.get("cid"):
                names.setdefault(int(cur["cid"]), cur.get("title", ""))
            index_path = Path(out_dir) / (str(prefix) + "_index.csv")
            with index_path.open("w", encoding="utf-8-sig", newline="") as fh:
                writer = csv.writer(fh, delimiter=";")
                self._last_size_counts = {"vert": 0, "orange": 0, "rouge": 0, "inconnu": 0}
                writer.writerow(["cid", "nom", "famille", "fichier", "plante",
                                 "poids_moleculaire", "liaisons_rotatives", "atomes_lourds", "taille"])
                for cid, path in pairs:
                    try:
                        key = int(cid)
                    except (TypeError, ValueError):
                        key = None
                    _mw, _rb, _ha = _sdf_metrics(path)
                    _cls = _size_class(_ha)
                    self._last_size_counts[_cls] = self._last_size_counts.get(_cls, 0) + 1
                    _plant = (getattr(self, "_current_plant_name", "") or "") if key in families else ""
                    writer.writerow([
                        cid or "", names.get(key, ""), families.get(key, ""), Path(path).name,
                        _plant,
                        ("%.1f" % _mw).replace(".", ",") if _mw is not None else "",
                        _rb if _rb is not None else "",
                        _ha if _ha is not None else "",
                        _cls,
                    ])
        except Exception as _exc:
            print('[PHYTO] index CSV non écrit :', _exc)

    # ---- fenêtre de progression -------------------------------------------

    def _open_progress(self, total):
        self._close_progress()
        self._progress_bridge = _ProgressBridge()
        self._progress_bridge.message.connect(self._on_progress_msg)
        self._progress_dlg = _ProgressDialog(self.window(), total)
        self._progress_dlg.show()
        QApplication.processEvents()

    def _download_with_progress(self, cids, out_file):
        return phyto_api.pubchem_download_sdf_batch(cids, out_file, progress=self._progress_cb)

    def _progress_cb(self, stage, detail=""):
        try:
            self._progress_bridge.message.emit(str(stage) + "|" + str(detail))
        except Exception:
            pass

    def _on_progress_msg(self, text):
        dlg = getattr(self, "_progress_dlg", None)
        if dlg is not None:
            stage, _, detail = text.partition("|")
            dlg.set_stage(stage, detail)

    def _progress_step(self, stage, detail=""):
        dlg = getattr(self, "_progress_dlg", None)
        if dlg is not None:
            dlg.set_stage(stage, detail)
            QApplication.processEvents()

    def _close_progress(self):
        dlg = getattr(self, "_progress_dlg", None)
        self._progress_dlg = None
        if dlg is not None:
            dlg.finish()

    def _split_and_report(self, sdf_path, out_dir, prefix, done_msg):
        try:
            self._progress_step("split")
            pairs = split_sdf_by_cid(sdf_path, out_dir, prefix)
            result = [p for _, p in pairs]
            self._progress_step("index")
            self._write_cid_index(pairs, out_dir, prefix)
        except Exception as exc:
            self._close_progress()
            QMessageBox.warning(
                self, self._t("phyto_error_title", "Erreur"),
                "Extraction SDF impossible (" + str(exc) + "). "
                "Fichier SDF groupé disponible ici : " + str(sdf_path))
            return
        self._close_progress()
        msg = done_msg
        if isinstance(result, (list, tuple, set, dict)):
            msg += "\n" + str(len(result)) + " " + self._t("phyto_files_extracted", "fichier(s) extrait(s).")
        msg += "\n" + str(out_dir)
        _c = getattr(self, "_last_size_counts", None) or {}
        if _c.get("orange") or _c.get("rouge"):
            msg += "\n\n" + self._t(
                "phyto_size_warning",
                "Attention : {orange} molécule(s) orange et {rouge} rouge sur {total} "
                "(grosses ou très flexibles : Vina sera lent ou peu fiable). "
                "Détail dans la colonne « taille » du fichier index."
            ).replace("{orange}", str(_c.get("orange", 0))).replace("{rouge}", str(_c.get("rouge", 0))).replace("{total}", str(sum(_c.values())))
        QMessageBox.information(self, self._t("phyto_done_title", "Terminé"), msg)

    # ------------------------------------------------ autres molécules organiques

    def _on_search_other(self):
        name = self.other_input.text().strip()
        if not name:
            return
        self._other_query = name
        self._other_current = None
        self.other_stack.setCurrentIndex(0)
        self.other_result_label.setText(self._t("phyto_searching", "Recherche en cours..."))
        self.btn_search_other.setEnabled(False)
        self._run_async(phyto_api.pubchem_search_molecules, self._on_other_found, name,
                        on_fail=self._on_other_failed)

    def _on_other_failed(self, kind, message):
        self.btn_search_other.setEnabled(True)
        self.other_result_label.setText(message)

    def _on_other_found(self, result):
        self.btn_search_other.setEnabled(True)
        if result.get("query") != self._other_query:
            return  # résultat d'une recherche précédente
        molecules = result.get("molecules") or []
        suggestions = result.get("suggestions") or []
        self.other_table.setRowCount(0)
        self._other_rows = []

        if molecules:
            for m in molecules:
                self._other_rows.append(m)
                self._add_other_row([m.get("title") or ("CID " + str(m["cid"])),
                                     str(m["cid"]), m.get("formula", ""), m.get("weight", "")],
                                    highlight=True)
            text = (str(len(molecules)) + " " + self._t("phyto_other_found", "molécule(s) trouvée(s)")
                    + " — " + self._t("phyto_other_click_hint",
                                      "cliquez sur une ligne pour voir sa structure 2D."))
            total = result.get("total") or len(molecules)
            if total > len(molecules):
                text += "\n" + self._t("phyto_other_truncated", "Affichage des premiers résultats sur") \
                        + " " + str(total) + "."
            self.other_result_label.setText(text)
        elif suggestions:
            for s in suggestions:
                self._other_rows.append({"kind": "sugg", "title": s})
                self._add_other_row([s, "", "", ""])
            self.other_result_label.setText(
                self._t("phyto_other_no_exact", "Aucun résultat exact pour « {q} ». "
                        "Suggestions — cliquez pour relancer la recherche :").replace("{q}", result["query"]))
        else:
            self.other_result_label.setText(self._t("phyto_no_result", "Aucun résultat."))

    def _add_other_row(self, cells, highlight=False):
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
            self.other_table.setItem(row, col, item)

    def _on_other_row_clicked(self, row, col):
        if not (0 <= row < len(self._other_rows)):
            return
        entry = self._other_rows[row]
        if entry.get("kind") == "sugg":
            self.other_input.setText(entry["title"])
            self._on_search_other()
            return
        self._open_other_detail(entry)

    def _open_other_detail(self, mol):
        cid = mol["cid"]
        self._other_current = mol
        title = mol.get("title") or ("CID " + str(cid))
        self.other_detail_title.setText(title)
        lines = ["<b>" + html.escape(self._t("phyto_col_cid", "CID PubChem")) + "</b> : " + str(cid)]
        if mol.get("formula"):
            lines.append("<b>" + html.escape(self._t("phyto_other_col_formula", "Formule"))
                         + "</b> : " + html.escape(mol["formula"]))
        if mol.get("weight"):
            lines.append("<b>" + html.escape(self._t("phyto_other_col_weight", "Masse (g/mol)"))
                         + "</b> : " + html.escape(mol["weight"]))
        if mol.get("iupac"):
            lines.append("<b>" + html.escape(self._t("phyto_other_iupac", "Nom IUPAC"))
                         + "</b> : " + html.escape(mol["iupac"]))
        self.other_detail_info.setText("<br><br>".join(lines))
        self.btn_other_download.setEnabled(True)
        self.other_struct.show_message(self._t("phyto_struct_loading", "Chargement de la structure 2D..."))
        self.other_stack.setCurrentIndex(1)

        def ready(pix):
            if self._other_current is mol:
                self.other_struct.show_pixmap(pix, title + "  ·  CID " + str(cid))

        def failed(message):
            if self._other_current is mol:
                self.other_struct.show_message(
                    self._t("phyto_struct_unavailable", "Structure 2D indisponible.") + "\n" + message)

        self._fetch_structure(cid, ready, failed)

    def _on_other_back(self):
        self._other_current = None
        self.other_stack.setCurrentIndex(0)

    def _on_download_other(self):
        mol = self._other_current
        if not mol:
            return
        chosen = QFileDialog.getExistingDirectory(
            self, self._t("phyto_choose_dir", "Dossier de destination"), str(LIGAND_DIR))
        if not chosen:
            return
        out_dir = Path(chosen)
        base = mol.get("title") or "CID"
        safe_name = (re.sub(r"[^\w\-]+", "_", base).strip("_") or "molecule") + "_CID" + str(mol["cid"])
        out_file = out_dir / (safe_name + "_batch.sdf")
        self.btn_other_download.setEnabled(False)
        self._open_progress(1)
        self._run_async(
            self._download_with_progress,
            lambda path: self._on_other_downloaded(path, out_dir, safe_name),
            [mol["cid"]], out_file,
            on_fail=self._on_other_download_failed,
        )

    def _on_other_download_failed(self, kind, message):
        self._close_progress()
        self.btn_other_download.setEnabled(True)
        self._on_generic_error(kind, message)

    def _on_other_downloaded(self, sdf_path, out_dir, prefix):
        self.btn_other_download.setEnabled(True)
        self._split_and_report(sdf_path, out_dir, prefix,
                               self._t("phyto_done_molecule", "Molécule téléchargée et extraite dans le dossier ligand."))

    def shutdown(self):
        for w in self._workers:
            if w.isRunning():
                w.wait(500)
