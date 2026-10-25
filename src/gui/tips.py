"""Astuces de premier lancement de VinaStudio (v3).

La visite guidee navigue elle-meme vers le bon onglet et pointe le bon endroit.
Deux sortes d'etapes :
  * "info"   : une carte qui decrit l'endroit, bouton « Compris ».
  * "action" : une carte qui dit quoi faire et attend un vrai geste. Aucune etape
               ne se valide dans la premiere seconde. Au bout de 25 s, un bouton
               « Passer cette étape » apparait pour ne bloquer personne.

Pour ajouter une astuce : ajoute un dictionnaire dans TOUR (visite du premier
lancement) ou dans BEACONS (bulles « ? » discretes, apres la visite).

Raccourcis :
  * Ctrl+F1             : rejoue la visite
  * variable VINA_TIPS=1 : force la visite au prochain lancement
  * tips.notify("nom")  : valide depuis le code une etape qui attend cet evenement
"""
from __future__ import annotations

import math
import os
import time

from PySide6.QtCore import QEvent, QObject, QPoint, QRectF, QSettings, Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (
    QAbstractButton, QApplication, QFrame, QHBoxLayout, QLabel,
    QPushButton, QToolButton, QVBoxLayout, QWidget,
)

_ORG = ("VINA Studio", "VINA Studio")
_KEY_DONE = "tips/tour2_done"
PREFS_DIALOG = "GlassPreferencesDialog"
_CARD_W = 360
_DWELL = 1.0        # secondes avant qu'une etape puisse se valider
_LATE = 25.0        # secondes avant « Passer cette etape »
_events = set()
_ALL_EVENTS = ("import_clicked", "prefs_pressed", "phyto_tab_pressed", "phyto_result")


def notify(name):
    """Signale qu'une action a eu lieu (valide l'etape qui l'attend)."""
    _events.add(name)


# ---------------------------------------------------------------- reglages
def _settings():
    return QSettings(*_ORG)


def _get_seen():
    raw = str(_settings().value("tips/seen", "") or "")
    return {x for x in raw.split(",") if x}


def _add_seen(tip_id):
    seen = _get_seen()
    seen.add(tip_id)
    _settings().setValue("tips/seen", ",".join(sorted(seen)))


def _tour_done():
    return str(_settings().value(_KEY_DONE, False)).lower() in ("1", "true")


def _set_tour_done(flag):
    _settings().setValue(_KEY_DONE, bool(flag))


# ---------------------------------------------------------------- couleurs
def _lum(c):
    def ch(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c.red()) + 0.7152 * ch(c.green()) + 0.0722 * ch(c.blue())


def _colors():
    """(couleur des titres, fond de carte, texte de carte).

    La surbrillance reprend la couleur des gros titres, relue a chaque fois
    (elle suit donc les themes). Le fond de carte est choisi pour qu'elle
    reste toujours lisible dessus.
    """
    try:
        from src.gui import main_window as mw
        title = QColor(mw._theme_color("title_color"))
    except Exception:
        title = QColor("#6bd18d")
    title.setAlpha(255)
    if _lum(title) > 0.45:
        return title, QColor(16, 21, 28), QColor(238, 243, 248)
    return title, QColor(251, 252, 254), QColor(24, 32, 42)


# ---------------------------------------------------------------- outils de recherche
def _alive(w):
    try:
        return w is not None and w.isVisible() and w.width() > 0 and w.height() > 0
    except RuntimeError:
        return False


def _find_button(win, needle, prefer_obj=None):
    """Version simple (sans cache) : utilisee par les bulles BEACONS."""
    cands = []
    for b in win.findChildren(QAbstractButton):
        try:
            if needle in b.text().lower() and _alive(b):
                cands.append(b)
        except RuntimeError:
            continue
    if prefer_obj:
        pref = [b for b in cands if b.objectName() == prefer_obj]
        if pref:
            return pref[0]
    return cands[0] if cands else None


def _toolbar_button(win, action_name):
    act = getattr(win, action_name, None)
    if act is None:
        return None
    try:
        for w in act.associatedObjects():
            if isinstance(w, QToolButton) and _alive(w):
                return w
    except Exception:
        pass
    return None


# ---------------------------------------------------------------- cibles (recoivent le gestionnaire m)
def _sec_button(i):
    def f(m):
        try:
            b = m.win.docking_page.secondary.buttons[i]
            return b if _alive(b) else None
        except Exception:
            return None
    return f


def _t_import(m):
    return m.find_button("importer un récepteur")


def _t_prefs_button(m):
    return _toolbar_button(m.win, "preferences_action")


def _t_quickbar(m):
    d = m.find_dialog(PREFS_DIALOG)
    if d is None:
        return None
    for w in d.findChildren(QWidget):
        try:
            if w.property("tips_quickbar") and _alive(w):
                return w
        except RuntimeError:
            pass
    for w in d.findChildren(QWidget):
        try:
            name = (w.objectName() + type(w).__name__).lower()
            if "quick" in name and _alive(w):
                return w
        except RuntimeError:
            pass
    return None


def _t_phyto_tab(m):
    try:
        b = m.win.primary_tabs[3]
        return b if _alive(b) else None
    except Exception:
        return None


def _t_phyto_input(m):
    page = getattr(m.win, "phyto_page", None)
    try:
        if page is None or not page.isVisible():
            return None
        if page.plant_input.text().strip():
            return page.btn_search_plant if _alive(page.btn_search_plant) else None
        return page.plant_input if _alive(page.plant_input) else None
    except Exception:
        return None


def _t_phyto_download(m):
    page = getattr(m.win, "phyto_page", None)
    try:
        return page.btn_download_family if _alive(page.btn_download_family) else None
    except Exception:
        return None


# ---------------------------------------------------------------- navigation
def _nav_sec(i):
    def f(m):
        w = m.win
        try:
            tab = w.primary_tabs[0]
            if not tab.isChecked():
                tab.click()
        except Exception:
            pass
        try:
            b = w.docking_page.secondary.buttons[i]
            if not b.isChecked():
                b.click()
        except Exception:
            pass
        m.invalidate_buttons()
    return f


def _nav_import(m):
    if m.find_button("importer un récepteur"):
        return
    for i in range(3):
        _nav_sec(i)(m)
        QApplication.processEvents()
        m.invalidate_buttons()
        if m.find_button("importer un récepteur"):
            return


def _nav_phyto_search(m):
    try:
        m.win.phyto_page._switch_mode(0)
    except Exception:
        pass


# ---------------------------------------------------------------- validations
def _done_prefs_open(m):
    return m.find_dialog(PREFS_DIALOG) is not None or "prefs_pressed" in _events


def _done_quick_theme(m):
    if m.find_dialog(PREFS_DIALOG) is None:
        return False
    if m.base is None:
        m.base = m.snapshot()
        return False
    return m.snapshot() != m.base


def _done_phyto_open(m):
    if "phyto_tab_pressed" in _events:
        return True
    try:
        return bool(m.win.phyto_page.isVisible())
    except Exception:
        return False


def _hint_phyto_search(m):
    page = getattr(m.win, "phyto_page", None)
    try:
        if page is not None and page.plant_input.text().strip():
            return "Clique sur le bouton Rechercher entouré."
    except Exception:
        pass
    return "Écris un nom de plante dans le champ entouré."


# ---------------------------------------------------------------- CONTENU
# Champs d'une etape :
#   id, kind ("info" | "action"), title, body
#   target(m) : widget a entourer          fallback(m) : cible de secours
#   nav(m)    : navigation faite au debut  host : classe de dialogue qui porte la carte
#   done(m)   : validation (action)        do : consigne affichee tant que ce n'est pas fait
#   press_event : evenement emis quand on appuie sur la cible
#   missing : message si la cible est introuvable      dynamic : cible recalculee a chaque tick
TOUR = [
    dict(
        id="sdf", kind="info",
        title="Ici, tu prépares tes molécules",
        body=("Importe des fichiers SDF, ou un dossier entier : VinaStudio les convertit "
              "en PDBQT, le format que Vina sait docker. C'est le point de départ "
              "du logiciel."),
        nav=_nav_sec(0), target=_sec_button(0),
    ),
    dict(
        id="pdbqt", kind="info",
        title="Tes ligands sont déjà prêts ?",
        body=("Si tes molécules sont déjà en PDBQT, charge-les ici. Tu peux filtrer une "
              "longue liste, retrouver tes fichiers, puis valider ta sélection pour "
              "passer au docking."),
        nav=_nav_sec(1), target=_sec_button(1),
    ),
    dict(
        id="docking", kind="info",
        title="Le moment du calcul",
        body=("Choisis le récepteur, règle la grid box et les paramètres de Vina, puis "
              "lance. Le visualiseur 3D montre la boîte autour du site et le journal "
              "suit le calcul en direct."),
        nav=_nav_sec(2), target=_sec_button(2),
    ),
    dict(
        id="import", kind="action",
        title="Importe un récepteur",
        body=("Ce bouton charge ta propre structure (PDB ou PDBQT), ou la télécharge. "
              "VinaStudio la nettoie et place la grid box. Il peut aussi docker des "
              "molécules de référence : des inhibiteurs connus de la cible, traités "
              "exactement comme les tiens, pour que tu puisses comparer tes résultats."),
        do="Clique sur le bouton entouré (tu pourras fermer la fenêtre qui s'ouvre).",
        nav=_nav_import, target=_t_import, press_event="import_clicked",
        done=lambda m: "import_clicked" in _events,
        missing="Je t'ouvre l'étape où se trouve ce bouton.",
    ),
    dict(
        id="prefs_open", kind="action",
        title="Les paramètres",
        body="Le bouton Paramètres ouvre tous les réglages du logiciel.",
        do="Clique sur le bouton Paramètres entouré.",
        target=_t_prefs_button, press_event="prefs_pressed", done=_done_prefs_open,
        missing="Le bouton Paramètres se trouve dans la barre du haut.",
    ),
    dict(
        id="quick_theme", kind="action", host=PREFS_DIALOG,
        title="Les thèmes rapides",
        body=("Dans les paramètres, cette rangée change toute l'ambiance en un clic : "
              "couleurs, verre, reflets."),
        do="Clique sur l'un des thèmes rapides.",
        target=_t_quickbar, fallback=_t_prefs_button, done=_done_quick_theme,
        missing="Rouvre les Paramètres, puis clique sur un thème rapide.",
    ),
    dict(
        id="prefs_info", kind="info", host=PREFS_DIALOG,
        title="Et ce n'est pas tout",
        body=("Sous les thèmes rapides, tu règles chaque détail : transparence, reflets, "
              "couleurs du verre, textes. Tout s'applique en direct. Ferme la fenêtre "
              "quand tu as fini."),
        target=_t_quickbar, fallback=_t_prefs_button,
    ),
    dict(
        id="phyto_open", kind="action",
        title="Les molécules d'une plante",
        body="L'onglet Phytomolécules explore ce que contient une plante.",
        do="Clique sur l'onglet Phytomolécules entouré.",
        target=_t_phyto_tab, press_event="phyto_tab_pressed", done=_done_phyto_open,
        missing="L'onglet se trouve dans la barre du haut.",
    ),
    dict(
        id="phyto_search", kind="action",
        title="Lance une recherche",
        body=("Cherche une plante, par exemple « Annona muricata » (le corossol). "
              "Les molécules connues de la plante vont s'afficher."),
        nav=_nav_phyto_search, target=_t_phyto_input, dynamic=True,
        done=lambda m: "phyto_result" in _events, hint=_hint_phyto_search,
        missing="Ouvre l'onglet Phytomolécules pour continuer.",
    ),
    dict(
        id="phyto_result", kind="info",
        title="Voilà ce que donne la recherche",
        body=("Chaque ligne est une molécule connue de la plante. Choisis une famille "
              "puis télécharge ses structures pour les docker en lot."),
        target=_t_phyto_download,
    ),
]

# Bulles « ? » discretes, apres la visite. Modele :
#   dict(id="grid", title="Grid box", text="...", target=lambda w: _find_button(w, "grid"))
# Si la cible est introuvable, la bulle n'apparait pas. Aucune erreur.
BEACONS = []


# ---------------------------------------------------------------- widgets
class _Ring(QWidget):
    """Anneau pulsant autour de la cible. Laisse passer tous les clics."""

    def __init__(self, host):
        super().__init__(host)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.rect_t = None
        self.phase = 0.0
        self.setGeometry(host.rect())

    def paintEvent(self, _event):
        if self.rect_t is None:
            return
        title, _bg, _fg = _colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        grow = 3.0 + 4.0 * abs(math.sin(self.phase))
        r = QRectF(self.rect_t).adjusted(-grow, -grow, grow, grow)
        glow = QColor(title)
        glow.setAlpha(70)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(glow, 9))
        p.drawRoundedRect(r, 12, 12)
        p.setPen(QPen(title, 3))
        p.drawRoundedRect(r, 10, 10)


class _Beacon(QWidget):
    """Petite bulle « ? » pulsante."""

    def __init__(self, win, callback):
        super().__init__(win)
        self.setFixedSize(26, 26)
        self.setCursor(Qt.PointingHandCursor)
        self.phase = 0.0
        self._cb = callback

    def mousePressEvent(self, _event):
        self._cb()

    def paintEvent(self, _event):
        title, _bg, _fg = _colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pulse = 0.5 + 0.5 * math.sin(self.phase)
        halo = QColor(title)
        halo.setAlpha(int(40 + 100 * pulse))
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QRectF(0, 0, self.width(), self.height()))
        inner = QRectF(4, 4, self.width() - 8, self.height() - 8)
        p.setBrush(title)
        p.drawEllipse(inner)
        p.setPen(QColor(16, 21, 28) if _lum(title) > 0.45 else QColor(255, 255, 255))
        f = self.font()
        f.setBold(True)
        f.setPointSize(11)
        p.setFont(f)
        p.drawText(inner, Qt.AlignCenter, "?")


_CARD_QSS = """
#TipCard { background: rgba(@BR@, @BG@, @BB@, 244); border: 2px solid @T@; border-radius: 14px; }
#TipCard QLabel { background: transparent; color: @F@; font-size: 13px; }
#TipCard QLabel#TipTitle { color: @T@; font-size: 16px; font-weight: 700; }
#TipCard QLabel#TipStep { color: @T@; font-size: 11px; font-weight: 600; }
#TipCard QLabel#TipState { color: @T@; font-weight: 600; }
#TipCard QPushButton { background: transparent; color: @T@; border: 1px solid @T@;
    border-radius: 8px; padding: 5px 14px; font-weight: 600; }
#TipCard QPushButton#TipSkip { border: none; color: rgba(@FR@, @FG@, @FB@, 170);
    font-size: 11px; font-weight: 400; padding: 5px 2px; }
"""


class _Card(QFrame):
    def __init__(self, host, on_next, on_skip):
        super().__init__(host)
        self.setObjectName("TipCard")
        self.setFixedWidth(_CARD_W)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        self.step = QLabel()
        self.step.setObjectName("TipStep")
        self.title = QLabel()
        self.title.setObjectName("TipTitle")
        self.title.setWordWrap(True)
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setTextFormat(Qt.PlainText)
        self.state = QLabel()
        self.state.setObjectName("TipState")
        self.state.setWordWrap(True)
        row = QHBoxLayout()
        self.skip = QPushButton("Passer les astuces")
        self.skip.setObjectName("TipSkip")
        self.skip.setFlat(True)
        self.skip.setCursor(Qt.PointingHandCursor)
        self.next = QPushButton("Suivant")
        row.addWidget(self.skip)
        row.addStretch(1)
        row.addWidget(self.next)
        for w in (self.step, self.title, self.body, self.state):
            lay.addWidget(w)
        lay.addLayout(row)
        self.next.clicked.connect(lambda *_: on_next())
        self.skip.clicked.connect(lambda *_: on_skip())
        self._sig = None
        self.restyle()

    def restyle(self):
        title, bg, fg = _colors()
        sig = (title.name(), bg.name(), fg.name())
        if sig == self._sig:
            return
        self._sig = sig
        qss = (_CARD_QSS
               .replace("@BR@", str(bg.red())).replace("@BG@", str(bg.green()))
               .replace("@BB@", str(bg.blue()))
               .replace("@FR@", str(fg.red())).replace("@FG@", str(fg.green()))
               .replace("@FB@", str(fg.blue()))
               .replace("@T@", title.name()).replace("@F@", fg.name()))
        self.setStyleSheet(qss)
        self._polish()

    def _polish(self):
        self.ensurePolished()
        for ch in self.findChildren(QWidget):
            ch.ensurePolished()

    def fit(self):
        """Hauteur exacte pour la largeur fixe : evite le texte rogne."""
        lay = self.layout()
        lay.activate()
        h = lay.totalHeightForWidth(_CARD_W)
        if h > 0 and self.height() != h:
            self.setFixedHeight(h)

    def set_content(self, step, title, body, state, next_text, show_next, show_skip):
        self.step.setText(step)
        self.step.setVisible(bool(step))
        self.title.setText(title)
        self.body.setText(body)
        self.state.setText(state)
        self.state.setVisible(bool(state))
        self.next.setText(next_text)
        self.next.setVisible(show_next)
        self.skip.setVisible(show_skip)
        self._polish()
        self.fit()


class _Layer:
    """Un anneau + une carte poses sur une fenetre hote (principale ou dialogue)."""

    def __init__(self, host, on_next, on_skip):
        self.host = host
        self.ring = _Ring(host)
        self.card = _Card(host, on_next, on_skip)
        self.key = None
        self.hide()

    def alive(self):
        try:
            self.host.objectName()
            self.card.objectName()
            return True
        except RuntimeError:
            return False

    def hide(self):
        try:
            self.ring.hide()
            self.card.hide()
        except RuntimeError:
            pass

    def show(self):
        self.ring.setGeometry(self.host.rect())
        self.ring.show()
        self.card.show()
        self.card.raise_()


# ---------------------------------------------------------------- gestionnaire
class _Manager(QObject):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.main_layer = _Layer(win, self._on_next, self._on_skip_all)
        self.dlg_layer = None
        self.beacons = {}
        self.mode = "idle"        # idle | tour | info
        self.i = -1
        self.done = False
        self.focus = None
        self.base = None
        self.navigated = False
        self.step_ticks = 0
        self.t0 = time.monotonic()
        self.ticks = 0
        self._btns = []
        self._btn_t = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(80)
        self.timer.timeout.connect(self._tick)
        win.installEventFilter(self)
        sc = QShortcut(QKeySequence("Ctrl+F1"), win)
        sc.activated.connect(self.replay)

    def eventFilter(self, obj, event):
        if obj is self.win and event.type() == QEvent.Resize:
            self.main_layer.ring.setGeometry(self.win.rect())
        return False

    # -------- utilitaires
    def buttons(self):
        now = time.monotonic()
        if not self._btns or now - self._btn_t > 1.0:
            try:
                self._btns = self.win.findChildren(QAbstractButton)
            except RuntimeError:
                self._btns = []
            self._btn_t = now
        return self._btns

    def invalidate_buttons(self):
        self._btn_t = 0.0

    def find_button(self, needle, prefer_obj=None):
        cands = []
        for b in self.buttons():
            try:
                if needle in b.text().lower() and _alive(b):
                    cands.append(b)
            except RuntimeError:
                continue
        if prefer_obj:
            pref = [b for b in cands if b.objectName() == prefer_obj]
            if pref:
                return pref[0]
        return cands[0] if cands else None

    def find_dialog(self, cls_name):
        for w in QApplication.topLevelWidgets():
            try:
                if type(w).__name__ == cls_name and w.isVisible():
                    return w
            except RuntimeError:
                continue
        return None

    def theme_name(self):
        try:
            return self.win.theme_background.current_theme_name()
        except Exception:
            return ""

    def snapshot(self):
        try:
            from src.gui import main_window as mw
            items = sorted((str(k), str(v)) for k, v in mw.GLASS_PREFERENCES.items())
            return repr(items) + mw._theme_color("title_color").name() + self.theme_name()
        except Exception:
            return ""

    def _late(self):
        return time.monotonic() - self.t0 > _LATE

    def _layer_for(self, host):
        if host is self.win:
            return self.main_layer
        if self.dlg_layer is not None and self.dlg_layer.alive() and self.dlg_layer.host is host:
            return self.dlg_layer
        self.dlg_layer = _Layer(host, self._on_next, self._on_skip_all)
        return self.dlg_layer

    def _hide_layers(self):
        self.main_layer.hide()
        if self.dlg_layer is not None and self.dlg_layer.alive():
            self.dlg_layer.hide()

    def _hide_others(self, layer):
        if layer is not self.main_layer:
            self.main_layer.hide()
        if self.dlg_layer is not None and self.dlg_layer is not layer and self.dlg_layer.alive():
            self.dlg_layer.hide()

    # -------- demarrage
    def start(self, force=False):
        if force or not _tour_done():
            self._begin_tour()
        else:
            self._show_beacons()
        self.timer.start()

    def replay(self):
        _set_tour_done(False)
        _settings().remove("tips/seen")
        for b in list(self.beacons.values()):
            b["w"].deleteLater()
        self.beacons.clear()
        self._begin_tour()
        self.timer.start()

    # -------- visite guidee
    def _begin_tour(self):
        self.mode = "tour"
        self.i = -1
        self._advance()

    def _advance(self):
        self.i += 1
        if self.i >= len(TOUR):
            self._finish_tour()
            return
        self.done = False
        self.focus = None
        self.base = None
        self.navigated = False
        self.step_ticks = 0
        self.t0 = time.monotonic()
        for ev in _ALL_EVENTS:
            _events.discard(ev)
        for lay in (self.main_layer, self.dlg_layer):
            if lay is not None:
                lay.key = None

    def _finish_tour(self):
        _set_tour_done(True)
        self.mode = "idle"
        self.focus = None
        self._hide_layers()
        self._show_beacons()

    def _on_skip_all(self):
        self._finish_tour()

    def _on_next(self):
        if self.mode == "tour" and 0 <= self.i < len(TOUR):
            tip = TOUR[self.i]
            if tip["kind"] == "info" or self.done or self._late():
                self.done = True
                self._advance()
        elif self.mode == "info":
            self.mode = "idle"
            self.focus = None
            self._hide_layers()

    def _auto_advance(self, index):
        if self.mode == "tour" and self.i == index and self.done:
            self._advance()

    def _pick_host(self, tip):
        want = tip.get("host")
        if want:
            d = self.find_dialog(want)
            return d if d is not None else self.win
        if QApplication.activeModalWidget() is not None:
            return None
        return self.win

    def _resolve(self, tip):
        w = None
        try:
            w = tip["target"](self)
        except Exception:
            w = None
        if w is None and tip.get("fallback"):
            try:
                w = tip["fallback"](self)
            except Exception:
                w = None
        return w

    def _rect_of(self, w, host):
        try:
            g = w.mapToGlobal(QPoint(0, 0))
            tl = host.mapFromGlobal(g)
            return QRectF(tl.x(), tl.y(), w.width(), w.height())
        except RuntimeError:
            return None

    def _place_card(self, layer, tr, host):
        c = layer.card
        W, H = host.width(), host.height()
        w, h = c.width(), c.height()
        if tr is None:
            x, y = (W - w) // 2, H - h - 40
        else:
            x = int(tr.center().x() - w / 2)
            y = int(tr.bottom() + 18)
            if y + h > H - 10:
                y = int(tr.top() - h - 18)
        c.move(max(10, min(x, W - w - 10)), max(10, min(y, H - h - 10)))

    def _wire_press(self, tip):
        ev = tip.get("press_event")
        if not ev or not _alive(self.focus):
            return
        key = "_tips_press_" + tip["id"]
        try:
            if not self.focus.property(key):
                self.focus.setProperty(key, True)
                self.focus.pressed.connect(lambda e=ev: notify(e))
        except (RuntimeError, AttributeError):
            pass

    def _tick_tour(self):
        if not (0 <= self.i < len(TOUR)):
            return
        tip = TOUR[self.i]
        elapsed = time.monotonic() - self.t0

        # 1. validation : evaluee a chaque tick, meme si un dialogue modal est ouvert
        if tip["kind"] == "action" and not self.done:
            try:
                ok = bool(tip["done"](self))
            except Exception:
                ok = False
            if ok and elapsed >= _DWELL:
                self.done = True
                QTimer.singleShot(500, lambda k=self.i: self._auto_advance(k))

        # 2. ou afficher la carte
        host = self._pick_host(tip)
        if host is None:
            self._hide_layers()          # un dialogue est ouvert : on attend sa fermeture
            return
        layer = self._layer_for(host)
        self._hide_others(layer)
        self.step_ticks += 1

        # 3. cible (cache : la recherche des boutons ne se refait pas a chaque tick)
        if tip.get("dynamic") or not _alive(self.focus) or self.step_ticks % 4 == 0:
            self.focus = self._resolve(tip)
        found = _alive(self.focus)
        self._wire_press(tip)

        # 4. contenu de la carte
        n = len(TOUR)
        step_txt = "Astuce %d sur %d" % (self.i + 1, n)
        if tip["kind"] == "info":
            state, next_text, show_next = "", "Compris", True
        elif self.done:
            state, next_text, show_next = "Fait. On passe à la suite.", "Suivant", True
        else:
            if not found and tip.get("missing"):
                state = tip["missing"]
            elif tip.get("hint"):
                try:
                    state = tip["hint"](self)
                except Exception:
                    state = tip.get("do", "")
            else:
                state = tip.get("do", "Fais l'action pour continuer.")
            late = self._late()
            next_text = "Passer cette étape"
            show_next = late
        content = (step_txt, tip["title"], tip["body"], state, next_text, show_next, True)
        if layer.key != content:
            layer.card.set_content(*content)
            layer.key = content

        # 5. affichage immediat, puis navigation au tick suivant
        layer.show()
        layer.card.fit()
        tr = self._rect_of(self.focus, host) if found else None
        layer.ring.rect_t = tr
        layer.ring.phase += 0.15
        layer.ring.update()
        layer.card.restyle()
        self._place_card(layer, tr, host)
        layer.card.raise_()

        if not self.navigated and self.step_ticks >= 2:
            self.navigated = True
            nav = tip.get("nav")
            if nav is not None:
                try:
                    nav(self)
                except Exception:
                    pass

    def _tick_info(self):
        layer = self.main_layer
        tr = self._rect_of(self.focus, self.win) if _alive(self.focus) else None
        layer.show()
        layer.card.fit()
        layer.ring.rect_t = tr
        layer.ring.phase += 0.15
        layer.ring.update()
        layer.card.restyle()
        self._place_card(layer, tr, self.win)
        layer.card.raise_()

    # -------- bulles
    def _show_beacons(self):
        seen = _get_seen()
        for spec in BEACONS:
            if spec["id"] in seen or spec["id"] in self.beacons:
                continue
            w = _Beacon(self.win, lambda bid=spec["id"]: self._open_beacon(bid))
            w.hide()
            self.beacons[spec["id"]] = dict(w=w, spec=spec, target=None)

    def _open_beacon(self, bid):
        entry = self.beacons.pop(bid, None)
        if entry is None:
            return
        entry["w"].deleteLater()
        _add_seen(bid)
        spec = entry["spec"]
        self.mode = "info"
        self.focus = entry["target"]
        self.main_layer.card.set_content("", spec["title"], spec["text"], "", "Compris", True, False)
        self.main_layer.key = None

    def _tick_beacons(self):
        for entry in self.beacons.values():
            spec, w = entry["spec"], entry["w"]
            if self.mode == "tour":
                w.hide()
                continue
            if not _alive(entry["target"]) and self.ticks % 8 == 0:
                try:
                    entry["target"] = spec["target"](self.win)
                except Exception:
                    entry["target"] = None
            if _alive(entry["target"]):
                r = self._rect_of(entry["target"], self.win)
                if r is not None:
                    w.move(int(r.right() - 13), int(r.top() - 13))
                    w.phase += 0.12
                    w.show()
                    w.raise_()
                    w.update()
                    continue
            w.hide()

    def _tick(self):
        self.ticks += 1
        if self.mode == "tour":
            self._tick_tour()
        elif self.mode == "info":
            self._tick_info()
        self._tick_beacons()
        if self.mode == "idle" and not self.beacons:
            self.timer.stop()


# ---------------------------------------------------------------- branchement
def _splash_visible():
    for w in QApplication.topLevelWidgets():
        if w.objectName() == "StartupSplash" and w.isVisible():
            return True
    return False


def _tag_quick_theme_bar():
    """Marque la rangee des themes rapides pour pouvoir la pointer."""
    try:
        from src.gui import quick_themes as q
    except Exception:
        return
    orig = getattr(q, "build_quick_theme_bar", None)
    if orig is None or getattr(orig, "_tips_wrapped", False):
        return

    def wrapped(*a, **k):
        r = orig(*a, **k)
        try:
            items = r if isinstance(r, (tuple, list)) else (r,)
            for x in items:
                if isinstance(x, QWidget):
                    x.setProperty("tips_quickbar", True)
                    break
        except Exception:
            pass
        return r

    wrapped._tips_wrapped = True
    q.build_quick_theme_bar = wrapped


def _wrap_phyto(win):
    page = getattr(win, "phyto_page", None)
    if page is None or getattr(page, "_tips_wrapped", False):
        return
    orig = getattr(page, "_on_lotus_result", None)
    if orig is None:
        return

    def wrapped(*a, **k):
        try:
            return orig(*a, **k)
        finally:
            notify("phyto_result")

    page._on_lotus_result = wrapped
    page._tips_wrapped = True


def _start(win):
    try:
        _wrap_phyto(win)
        m = _Manager(win)
        win._tips_manager = m
        m.start(force=os.environ.get("VINA_TIPS") == "1")
    except Exception as exc:
        print("Astuces desactivees :", exc)


def _wait_for_splash(win):
    t = QTimer(win)
    t.setInterval(200)
    st = {"n": 0, "calm": 0}

    def check():
        st["n"] += 1
        if st["n"] > 3000:
            t.stop()
            return
        if _splash_visible() or not win.isVisible():
            st["calm"] = 0
            return
        st["calm"] += 1
        if st["calm"] >= 2:
            t.stop()
            _start(win)

    t.timeout.connect(check)
    t.start()


def hook_main_window(cls):
    """Demarre les astuces quand l'ecran de demarrage est ferme et la fenetre visible."""
    _tag_quick_theme_bar()
    orig = cls.showEvent

    def showEvent(self, ev):
        orig(self, ev)
        if getattr(self, "_tips_scheduled", False):
            return
        self._tips_scheduled = True
        _wait_for_splash(self)

    cls.showEvent = showEvent
