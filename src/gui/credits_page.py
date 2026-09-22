# -*- coding: utf-8 -*-
"""
Page "Crédits" : visionneuse type artbook pour le dossier
``credit_du_logiciel/`` (photos + vidéos souvenirs classées par
événement, un dossier = un événement).

Règles de navigation :
  - chaque dossier devient un onglet ; le nom de l'onglet est le seul
    indice de "dans quel dossier on est" ;
  - à l'intérieur d'un dossier, les fichiers défilent dans un ordre
    fixe (chronologique) : pas d'accès aléatoire à une image ;
  - "Suivant" sur le dernier fichier d'un dossier enchaîne
    automatiquement sur le premier fichier du dossier suivant (et
    inversement pour "Précédent") ;
  - cliquer directement sur un onglet saute en revanche tout de
    suite au dossier voulu.

Apparence
---------
Aucune couleur n'est écrite en dur ici : la page reprend le thème du
logiciel (main_window.py).
  - titres / descriptions : objectName SectionTitle / SectionDescription ;
  - panneau principal : objectName ContentPanel (verre du thème) ;
  - boutons et onglets : LiquidGlassButton / LiquidGlassToolButton
    (même matériau « liquide glace » que la barre du haut) ;
  - cadre du média : objectName Viewer = « Cadre du visualiseur » ;
  - légende : cartes de verre, liseré des boutons, reflet et texte du thème.
Aucune couleur n'est mémorisée dans cette page : soit elle vient de la
feuille de style globale (reconstruite à chaque changement de réglage),
soit elle est relue à chaque repaint (légende). Changer un réglage dans
« Paramètres » met donc la page à jour immédiatement.

Média
-----
Le cadre s'adapte à CHAQUE photo / vidéo : portrait, paysage, carré.
Il épouse exactement le format du média (plus de bandes noires ni de
vidéo perdue au milieu d'une zone trop large) et occupe toute la
hauteur disponible. La légende est une courte pastille de verre collée
sous le média, de la même largeur que lui (100 caractères max).

Rien de tout cela (scan du dossier, décodage des images) ne se fait
sur le thread d'interface : le scan tourne dans un QThread dédié, et
chaque image est décodée/réduite dans un second QThread persistant ;
l'image suivante est préchargée. Les vidéos ne sont pas préchargées :
QMediaPlayer les décode déjà de façon asynchrone.

Réglages rapides
----------------
CREDITS_EDIT_MODE : mettre à False avant la publication finale.
Tant que c'est True, chaque photo/vidéo peut recevoir une légende
écrite depuis l'interface (enregistrée dans captions.json à la
racine du dossier credit_du_logiciel). Une fois à False, les
légendes restent visibles mais ne sont plus modifiables.

Chiffrement des médias : volontairement PAS traité ici (chantier à
part, il faudrait le paquet ``cryptography``).
"""

from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import (
    Qt, QObject, QThread, Signal, Slot, QSize, QTimer, QEvent, QRect, QRectF, QUrl,
)
from PySide6.QtGui import (
    QImage, QPixmap, QPainter, QColor, QLinearGradient,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QSizePolicy, QStackedWidget, QLineEdit, QToolButton,
)

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    _MULTIMEDIA_OK = True
except Exception:
    _MULTIMEDIA_OK = False


# ============================================================================
# REGLAGES
# ============================================================================

# Mettre a False avant la publication finale du logiciel : desactive
# l'ecriture/modification des legendes depuis l'interface (lecture
# seule des legendes deja enregistrees).
CREDITS_EDIT_MODE = True

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

CAPTIONS_FILENAME = "captions.json"
ORDER_FILENAME = "ordre_albums.json"

_MAX_PIXMAP_CACHE = 10
_MAX_IMG_W, _MAX_IMG_H = 1920, 1200

# Legende : un petit mot de contexte, pas un paragraphe.
_CAPTION_MAX_CHARS = 100
_CAPTION_MAX_LINES = 3

# Geometrie du cadre du media (pixels)
_CARD_PAD = 6          # marge entre le cadre et le media
_CAPTION_GAP = 6       # espace entre le media et la legende
_CAP_PADX, _CAP_PADY = 12, 6
_UPSCALE_LIMIT = 1.5   # une petite image n'est pas agrandie au-dela de 1.5x
_DEFAULT_RATIO = 16 / 9

_THEME_MODULE = {"mod": None, "searched": False}


def _theme_module():
    """Module main_window deja charge (aucun import : pas de cycle)."""
    if _THEME_MODULE["searched"]:
        return _THEME_MODULE["mod"]
    for name, mod in list(sys.modules.items()):
        if (
            name.rsplit(".", 1)[-1] in ("main_window", "__main__")
            and hasattr(mod, "COLORS")
            and hasattr(mod, "LiquidGlassButton")
        ):
            _THEME_MODULE["mod"] = mod
            _THEME_MODULE["searched"] = True
            return mod
    # Pas encore charge : on re-essaiera (on ne memorise pas l'echec).
    return None


def _theme_pref(key: str, default):
    """Valeur COURANTE d'un reglage de « Parametres » (lue a chaque appel,
    donc toujours a jour). `default` ne sert que si le theme est absent."""
    mod = _theme_module()
    if mod is not None:
        try:
            return mod.GLASS_PREFERENCES.get(key, default)
        except Exception:
            pass
    return default


def _theme_qcolor(key: str, fallback: str, opacity_key: str | None = None) -> QColor:
    """Couleur COURANTE d'un reglage du theme, avec son opacite si donnee."""
    mod = _theme_module()
    if mod is not None:
        try:
            if opacity_key:
                return QColor(mod._overlay(key, opacity_key))
            return QColor(mod._theme_color(key))
        except Exception:
            pass
    return QColor(fallback)


def _glass_button(text: str = "") -> QPushButton:
    """Bouton « liquide glace » du logiciel (ou QPushButton de secours)."""
    mod = _theme_module()
    cls = getattr(mod, "LiquidGlassButton", None) if mod is not None else None
    button = cls(text) if cls is not None else QPushButton(text)
    button.setCursor(Qt.PointingHandCursor)
    return button


def _glass_tab() -> QToolButton:
    """Onglet « liquide glace » du logiciel, style sous-onglet."""
    mod = _theme_module()
    cls = getattr(mod, "LiquidGlassToolButton", None) if mod is not None else None
    button = cls() if cls is not None else QToolButton()
    button.setObjectName("SecondaryTab")
    button.setCheckable(True)
    button.setAutoExclusive(True)
    button.setToolButtonStyle(Qt.ToolButtonTextOnly)
    button.setCursor(Qt.PointingHandCursor)
    return button


def _fit_ratio(ratio, max_w, max_h, cap=None):
    """Plus grand rectangle de rapport `ratio` (l/h) tenant dans max_w x max_h.
    `cap` = (largeur, hauteur) maximales (limite d'agrandissement)."""
    if not ratio or ratio <= 0 or max_w < 1 or max_h < 1:
        return 0, 0
    if cap is not None:
        max_w = min(max_w, cap[0])
        max_h = min(max_h, cap[1])
    w = max_w
    h = w / ratio
    if h > max_h:
        h = max_h
        w = h * ratio
    return max(1, int(w)), max(1, int(h))


def _flag_int(flag) -> int:
    try:
        return int(flag)
    except TypeError:
        return int(getattr(flag, "value", 0))


def _frame_rotation(frame) -> int:
    """Rotation (0/90/180/270) que Qt applique a l'affichage de l'image
    video. Les videos de telephone sont souvent stockees en 1920x1080 avec
    une rotation de 90 degres : l'affichage reel est alors 1080x1920."""
    getters = (
        lambda f: f.rotation(),
        lambda f: f.rotationAngle(),
        lambda f: f.surfaceFormat().rotation(),
    )
    for getter in getters:
        try:
            value = getter(frame)
        except Exception:
            continue
        try:
            return int(getattr(value, "value", value)) % 360
        except (TypeError, ValueError):
            continue
    return 0


def _credits_root() -> Path | None:
    """Racine du dossier credit_du_logiciel, cote du dossier src/ (ou de l'executable en mode compile)."""
    if getattr(sys, "frozen", False):
        here = Path(sys.executable).resolve()
        candidates = [here.parent]
    else:
        here = Path(__file__).resolve()
        candidates = []
        if len(here.parents) > 2:
            candidates.append(here.parents[2])
        if len(here.parents) > 1:
            candidates.append(here.parents[1])
    for base in candidates:
        candidate = base / "credit_du_logiciel"
        if candidate.is_dir():
            return candidate
    return None


def _pretty_label(folder_name: str) -> str:
    label = folder_name.replace("_", " ").replace("-", " ").strip()
    return label[:1].upper() + label[1:] if label else folder_name


# ============================================================================
# SCAN DU DOSSIER (thread dedie, une fois par ouverture / actualisation)
# ============================================================================

class _AlbumScanWorker(QObject):
    finished = Signal(list, dict, str)  # albums, captions, erreur

    def __init__(self, root: Path):
        super().__init__()
        self.root = root

    @Slot()
    def run(self):
        try:
            albums = self._scan_albums()
            captions = self._load_captions()
            self.finished.emit(albums, captions, "")
        except Exception as exc:
            self.finished.emit([], {}, str(exc))

    def _load_captions(self) -> dict:
        captions_path = self.root / CAPTIONS_FILENAME
        if not captions_path.exists():
            return {}
        try:
            return json.loads(captions_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _scan_albums(self):
        order_file = self.root / ORDER_FILENAME
        manual_order = []
        if order_file.exists():
            try:
                manual_order = json.loads(order_file.read_text(encoding="utf-8"))
            except Exception:
                manual_order = []

        albums = []
        for entry in sorted(self.root.iterdir()):
            if not entry.is_dir():
                continue

            items = []
            for f in entry.iterdir():
                ext = f.suffix.lower()
                if ext in IMAGE_EXTS:
                    kind = "image"
                elif ext in VIDEO_EXTS:
                    kind = "video"
                else:
                    continue
                try:
                    mtime = f.stat().st_mtime
                except OSError:
                    mtime = 0.0
                items.append({"path": str(f), "name": f.name, "type": kind, "mtime": mtime})

            if not items:
                continue

            items.sort(key=lambda it: (it["mtime"], it["name"]))

            albums.append({
                "key": entry.name,
                "label": _pretty_label(entry.name),
                "items": items,
                "first_mtime": items[0]["mtime"],
            })

        if manual_order:
            rank = {name: i for i, name in enumerate(manual_order)}
            albums.sort(key=lambda a: (rank.get(a["key"], len(manual_order)), a["first_mtime"]))
        else:
            albums.sort(key=lambda a: a["first_mtime"])

        return albums


# ============================================================================
# CHARGEMENT D'IMAGE (thread persistant, file de demandes)
# ============================================================================

class _ImageLoaderWorker(QObject):
    # QPixmap n'est fiable que sur le thread GUI : on ne fait circuler que
    # des QImage (thread-safe) ; la conversion en QPixmap se fait cote
    # thread principal, dans _on_image_ready.
    imageReady = Signal(str, int, int, QImage)  # album_key, item_index, requete, image
    failed = Signal(str, int, int, str)

    @Slot(str, int, int, str)
    def load(self, album_key, item_index, request_id, path_str):
        try:
            image = QImage(path_str)
            if image.isNull():
                self.failed.emit(album_key, item_index, request_id, "Image illisible")
                return
            if image.width() > _MAX_IMG_W or image.height() > _MAX_IMG_H:
                image = image.scaled(
                    _MAX_IMG_W, _MAX_IMG_H, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            self.imageReady.emit(album_key, item_index, request_id, image)
        except Exception as exc:
            self.failed.emit(album_key, item_index, request_id, str(exc))


# ============================================================================
# LEGENDE : pastille de verre peinte a partir du theme COURANT
# ----------------------------------------------------------------------------
# Rien n'est fige : a chaque repeinture, la pastille relit tes reglages
# (cartes de verre, liseré, reflet, texte, rayon). Changer une couleur dans
# « Parametres » la met donc a jour immediatement.
# ============================================================================

class _CaptionPill(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def text(self) -> str:
        return self._text

    def setText(self, text: str):
        self._text = text or ""
        self.update()

    def text_height(self, width: int) -> int:
        """Hauteur necessaire pour afficher le texte sur `width` pixels."""
        if not self._text:
            return 0
        self.ensurePolished()
        metrics = self.fontMetrics()
        inner_w = max(60, width - 2 * _CAP_PADX - 2)
        rect = metrics.boundingRect(
            QRect(0, 0, inner_w, 10000), _flag_int(Qt.TextWordWrap), self._text
        )
        text_h = min(rect.height(), metrics.lineSpacing() * _CAPTION_MAX_LINES)
        return text_h + 2 * _CAP_PADY + 2

    def paintEvent(self, event):
        if self.width() < 3 or self.height() < 3 or not self._text:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = min(float(_theme_pref("button_radius", 12)), rect.height() / 2.0)

        # Fond : « Cartes et cadres de verre » (couleur + opacite du theme).
        fill = _theme_qcolor("card_color", "#111c26", "card_opacity")
        fill.setAlpha(min(255, fill.alpha() + 45))
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, radius, radius)

        # Reflet du haut : « Reflet de lumiere » du theme.
        try:
            reflection = float(_theme_pref("reflection", 72))
        except (TypeError, ValueError):
            reflection = 72.0
        sheen = QLinearGradient(0, rect.top(), 0, rect.bottom())
        sheen.setColorAt(0.0, QColor(255, 255, 255, int(max(0.0, min(100.0, reflection)) * 0.6)))
        sheen.setColorAt(0.55, QColor(255, 255, 255, 0))
        painter.setBrush(sheen)
        painter.drawRoundedRect(rect, radius, radius)

        # Lisere : meme couleur / opacite que le lisere des boutons.
        painter.setBrush(Qt.NoBrush)
        painter.setPen(_theme_qcolor("button_border_color", "#ffffff", "button_border_opacity"))
        painter.drawRoundedRect(rect, radius, radius)

        # Texte : « Texte principal » du theme, police et taille du theme.
        painter.setPen(_theme_qcolor("text_color", "#edf5ff"))
        text_rect = self.rect().adjusted(_CAP_PADX, _CAP_PADY, -_CAP_PADX, -_CAP_PADY)
        flags = _flag_int(Qt.AlignCenter) | _flag_int(Qt.TextWordWrap)
        painter.drawText(text_rect, flags, self._text)
        painter.end()


# ============================================================================
# ZONE D'AFFICHAGE (le cadre du media y est place a la main, centre)
# ============================================================================

class _MediaStage(QWidget):
    """Zone libre : la page y positionne le cadre du media (pas de layout,
    pour que la taille du media ne bloque jamais le redimensionnement)."""

    resized = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()


# ============================================================================
# WIDGET PRINCIPAL
# ============================================================================

class CreditsPage(QWidget):
    """
    Page "Crédits" : un onglet horizontal par dossier d'événement, et
    à l'intérieur, un défilement séquentiel photos/vidéos avec
    légende courte optionnelle.
    """

    requestImageLoad = Signal(str, int, int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

        self._root = _credits_root()
        self._albums = []
        self._captions = {}
        self._pixmap_cache = OrderedDict()   # (album_key, item_index) -> QPixmap
        self._ratio_cache = {}               # (album_key, item_index) -> largeur/hauteur
        self._last_ratio = _DEFAULT_RATIO
        self._album_index = 0
        self._item_index = 0
        self._request_seq = 0
        self._scanning = False
        self._loaded_once = False
        self._tab_buttons = []

        # Etat du media affiche
        self._current_key = None
        self._current_is_video = False
        self._current_pixmap = None
        self._native_cap = None              # (w, h) max d'agrandissement (images)
        self._current_caption = ""
        self._video_ratio_pending = False

        self._image_thread = None
        self._image_worker = None
        self._scan_thread = None
        self._scan_worker = None

        # Le lissage de l'image n'est refait qu'une fois le redimensionnement
        # de la fenetre termine (sinon, cout inutile a chaque pixel).
        self._rescale_timer = QTimer(self)
        self._rescale_timer.setSingleShot(True)
        self._rescale_timer.setInterval(40)
        self._rescale_timer.timeout.connect(self._apply_pixmap_to_label)

        self._build_ui()
        self._start_image_loader()
        # Actif seulement une fois la page construite (voir changeEvent).
        self._theme_refresh_pending = False

    # ------------------------------------------------------------------
    # CONSTRUCTION DE L'INTERFACE
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Aucun fond ici : l'image de theme du logiciel reste visible
        # derriere la page, comme sur les autres onglets.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 16)
        outer.setSpacing(12)

        # --- En-tete (plus de bouton "Actualiser") -----------------------
        header = QHBoxLayout()
        header.setSpacing(14)

        title = QLabel("Crédits")
        title.setObjectName("SectionTitle")
        header.addWidget(title)

        self.subtitle_label = QLabel("")
        self.subtitle_label.setObjectName("SectionDescription")
        header.addWidget(self.subtitle_label, 0, Qt.AlignVCenter)
        header.addStretch()

        outer.addLayout(header)

        # --- Corps : media a gauche (recentre, prend le plus de place),
        # dossiers en dock vertical a droite. -----------------------------
        body = QHBoxLayout()
        body.setSpacing(12)

        # --- Panneau de contenu : meme verre que les autres pages -------
        content = QFrame()
        content.setObjectName("ContentPanel")
        # Pas d'ombre portee (effet graphique) : elle ferait rendre la video
        # dans une image intermediaire, au risque d'un ecran noir.
        content.setProperty("skip_glass_elevation", True)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 14)
        content_layout.setSpacing(10)

        # Zone du media : occupe toute la place restante, recentree.
        self.stage = _MediaStage()
        self.stage.setMinimumHeight(260)
        self.stage.resized.connect(self._relayout_media)
        content_layout.addWidget(self.stage, 1)

        # Cadre du media : couleur "Cadre du visualiseur" du theme, mais
        # fond force transparent ici (un seul cadre visible, pas de bloc
        # noir superpose derriere l'image/la video).
        self.media_card = QFrame(self.stage)
        # objectName "Viewer" = le cadre du visualiseur 3D : le lisere /
        # rayon viennent du theme, mais on annule son fond pour ne garder
        # qu'un seul cadre transparent (celui du theme, pas un second noir).
        self.media_card.setObjectName("Viewer")
        self.media_card.setAttribute(Qt.WA_StyledBackground, True)
        self.media_card.setStyleSheet("QFrame#Viewer { background: transparent; }")
        self.media_card.hide()

        self.media_stack = QStackedWidget(self.media_card)
        self.media_stack.setFrameShape(QFrame.NoFrame)
        self.media_stack.setAttribute(Qt.WA_StyledBackground, True)
        self.media_stack.setStyleSheet("QStackedWidget { background: transparent; }")

        # Page "image"
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setMinimumSize(1, 1)
        self.image_label.setObjectName("SectionDescription")
        self.image_label.setStyleSheet("background: transparent;")
        self.media_stack.addWidget(self.image_label)

        # Page "video"
        if _MULTIMEDIA_OK:
            self.video_widget = QVideoWidget()
            self.video_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            self.video_widget.setMinimumSize(1, 1)
            self.media_player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.media_player.setVideoOutput(self.video_widget)
            self.media_player.setAudioOutput(self.audio_output)
            self._video_page = self.video_widget
            self.media_player.playbackStateChanged.connect(self._on_playback_state)
            self.media_player.mediaStatusChanged.connect(self._on_media_status)

            # Le format reel de la video (portrait / paysage, rotation du
            # telephone comprise) n'est connu qu'a la premiere image.
            try:
                sink = self.video_widget.videoSink()
            except Exception:
                sink = None
            if sink is not None:
                sink.videoFrameChanged.connect(self._on_video_frame)
        else:
            self.video_widget = None
            self.media_player = None
            no_video = QLabel("Lecture vidéo indisponible (QtMultimedia manquant).")
            no_video.setAlignment(Qt.AlignCenter)
            no_video.setWordWrap(True)
            no_video.setObjectName("SectionDescription")
            self._video_page = no_video

        self.media_stack.addWidget(self._video_page)

        # Legende : pastille de verre collee sous le media, meme largeur.
        self.caption_label = _CaptionPill(self.media_card)
        self.caption_label.hide()

        # --- Position courante, puis nav precedent / lecture / suivant,
        # resserrees et centrees sous l'image (plus de legende editable). --
        self.position_label = QLabel("")
        self.position_label.setAlignment(Qt.AlignCenter)
        self.position_label.setObjectName("SectionDescription")
        content_layout.addWidget(self.position_label)

        nav_row = QHBoxLayout()
        nav_row.setSpacing(6)
        nav_row.addStretch()

        self.prev_button = _glass_button("◀ Précédent")
        self.prev_button.clicked.connect(self._go_prev)

        self.play_button = _glass_button("⏸ Pause")
        self.play_button.clicked.connect(self._toggle_video_playback)
        self.play_button.hide()

        self.next_button = _glass_button("Suivant ▶")
        self.next_button.clicked.connect(self._go_next)

        nav_row.addWidget(self.prev_button)
        nav_row.addWidget(self.play_button)
        nav_row.addWidget(self.next_button)
        nav_row.addStretch()
        content_layout.addLayout(nav_row)

        # Legende editable retiree de l'interface (l'affichage des legendes
        # deja enregistrees, la pastille de verre sur le media, reste actif).
        self.caption_edit = None
        self.caption_counter = None
        self.save_caption_button = None

        body.addWidget(content, 1)

        # --- Dock vertical des dossiers, a droite : meme verre transparent
        # que les autres menus du logiciel. -------------------------------
        tabs_dock = QFrame()
        tabs_dock.setObjectName("CreditsTabsDock")
        tabs_dock.setStyleSheet(
            "QFrame#CreditsTabsDock { background: transparent; border: none; }"
        )
        tabs_dock.setFixedWidth(200)
        tabs_dock_layout = QVBoxLayout(tabs_dock)
        tabs_dock_layout.setContentsMargins(0, 0, 0, 0)
        tabs_dock_layout.setSpacing(0)

        self.tabs_scroll = QScrollArea()
        self.tabs_scroll.setObjectName("CreditsTabsScroll")
        self.tabs_scroll.setWidgetResizable(True)
        self.tabs_scroll.setFrameShape(QFrame.NoFrame)
        self.tabs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tabs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tabs_scroll.setStyleSheet(
            "QScrollArea#CreditsTabsScroll { background: transparent; border: none; }"
        )

        self.tabs_container = QWidget()
        self.tabs_container.setObjectName("CreditsTabsContainer")
        self.tabs_container.setStyleSheet(
            "QWidget#CreditsTabsContainer { background: transparent; }"
        )
        self.tabs_layout = QVBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(2, 2, 2, 2)
        self.tabs_layout.setSpacing(6)
        self.tabs_layout.addStretch()
        self.tabs_scroll.setWidget(self.tabs_container)

        tabs_dock_layout.addWidget(self.tabs_scroll)
        body.addWidget(tabs_dock, 0)

        outer.addLayout(body, 1)

        # --- Statut ---------------------------------------------------------
        self.status_label = QLabel(
            "Ouvre l'onglet Crédits pour charger la collection." if self._root
            else "Dossier « credit_du_logiciel » introuvable à côté du projet."
        )
        self.status_label.setObjectName("SectionDescription")
        outer.addWidget(self.status_label)

        self._set_nav_enabled(False)

    # ------------------------------------------------------------------
    # CHARGEMENT ASYNCHRONE DES IMAGES (thread persistant)
    # ------------------------------------------------------------------

    def _start_image_loader(self):
        self._image_thread = QThread(self)
        self._image_worker = _ImageLoaderWorker()
        self._image_worker.moveToThread(self._image_thread)

        self.requestImageLoad.connect(self._image_worker.load)
        self._image_worker.imageReady.connect(self._on_image_ready)
        self._image_worker.failed.connect(self._on_pixmap_failed)

        self._image_thread.start()

    def stop_playback(self):
        """A appeler quand on quitte l'onglet Credits (changement d'onglet) :
        coupe une video en cours de lecture pour qu'elle ne continue pas en
        arriere-plan. Contrairement a shutdown(), ne touche pas aux threads
        (scan / chargement d'images), qui restent utiles si on revient."""
        if self.media_player is not None:
            try:
                self.media_player.stop()
            except Exception:
                pass

    def shutdown(self):
        """A appeler depuis MainWindow.closeEvent pour arreter proprement
        les threads d'arriere-plan de la page Credits."""
        if self.media_player is not None:
            try:
                self.media_player.stop()
            except Exception:
                pass
        for thread in (self._scan_thread, self._image_thread):
            if thread is None:
                continue
            try:
                if thread.isRunning():
                    thread.quit()
                    thread.wait(2000)
            except RuntimeError:
                # Le thread de scan est detruit (deleteLater) des que le
                # scan est termine : rien a arreter, on passe au suivant.
                continue

    # ------------------------------------------------------------------
    # OUVERTURE PARESSEUSE (appelee par MainWindow au premier clic sur
    # l'onglet "Crédits" — le scan ne demarre pas avant)
    # ------------------------------------------------------------------

    def ensure_loaded(self):
        if self._loaded_once or self._scanning:
            return
        self._loaded_once = True
        self._start_scan()

    # ------------------------------------------------------------------
    # SCAN DU DOSSIER
    # ------------------------------------------------------------------

    def _start_scan(self):
        if self._root is None:
            self.status_label.setText(
                "Dossier « credit_du_logiciel » introuvable à côté du projet."
            )
            return
        if self._scanning:
            return

        self._scanning = True
        self.status_label.setText("Chargement de la collection en arrière-plan…")

        self._scan_thread = QThread(self)
        self._scan_worker = _AlbumScanWorker(self._root)
        self._scan_worker.moveToThread(self._scan_thread)
        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_thread.finished.connect(self._scan_thread.deleteLater)
        self._scan_thread.start()

    def _on_scan_finished(self, albums, captions, error):
        self._scanning = False

        if error:
            self.status_label.setText(f"Erreur pendant le chargement : {error}")
            return

        self._albums = albums
        self._captions = captions
        self._pixmap_cache.clear()
        self._ratio_cache.clear()

        if not albums:
            self.status_label.setText(
                "Aucune photo ni vidéo trouvée dans « credit_du_logiciel »."
            )
            self.subtitle_label.setText("")
            self.media_card.hide()
            self._set_nav_enabled(False)
            return

        n_items = sum(len(a["items"]) for a in albums)
        self.subtitle_label.setText(
            f"{len(albums)} dossier(s) — {n_items} photo(s)/vidéo(s)"
        )
        self.status_label.setText("Collection chargée.")

        self._build_tabs()
        self._set_nav_enabled(True)
        self._go_to(0, 0)

    def _build_tabs(self):
        while self.tabs_layout.count() > 1:
            item = self.tabs_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._tab_buttons = []

        for index, album in enumerate(self._albums):
            button = _glass_tab()
            button.setText(f"{album['label']} ({len(album['items'])})")
            # Onglets verticaux : chaque bouton occupe toute la largeur du dock.
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(lambda checked=False, i=index: self._go_to(i, 0))
            self.tabs_layout.insertWidget(index, button)
            self._tab_buttons.append(button)

        self._fit_tabs_height()

    def _fit_tabs_height(self):
        """Rafraichit l'apparence des onglets verticaux (largeur pleine du
        dock). Reappele quand le theme change (taille de texte, rayon...)."""
        if self._tab_buttons:
            self._tab_buttons[0].ensurePolished()
            for button in self._tab_buttons:
                button.updateGeometry()

    # ------------------------------------------------------------------
    # NAVIGATION
    # ------------------------------------------------------------------

    def _set_nav_enabled(self, enabled: bool):
        self.prev_button.setEnabled(enabled)
        self.next_button.setEnabled(enabled)

    def _go_to(self, album_index: int, item_index: int):
        if not self._albums:
            return
        album_index %= len(self._albums)
        items = self._albums[album_index]["items"]
        if not items:
            return
        item_index %= len(items)

        self._album_index = album_index
        self._item_index = item_index

        if 0 <= album_index < len(self._tab_buttons):
            button = self._tab_buttons[album_index]
            button.setChecked(True)
            self.tabs_scroll.ensureWidgetVisible(button, 40, 0)

        self._show_current()
        self._prefetch_next()

    def _go_next(self):
        if not self._albums:
            return
        album = self._albums[self._album_index]
        if self._item_index + 1 < len(album["items"]):
            self._go_to(self._album_index, self._item_index + 1)
        else:
            next_album = (self._album_index + 1) % len(self._albums)
            if next_album == 0:
                self.status_label.setText(
                    "Fin de la collection — retour au début."
                )
            self._go_to(next_album, 0)

    def _go_prev(self):
        if not self._albums:
            return
        if self._item_index > 0:
            self._go_to(self._album_index, self._item_index - 1)
        else:
            prev_album = (self._album_index - 1) % len(self._albums)
            last_index = len(self._albums[prev_album]["items"]) - 1
            self._go_to(prev_album, last_index)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Right, Qt.Key_Down, Qt.Key_Space):
            self._go_next()
            return
        if event.key() in (Qt.Key_Left, Qt.Key_Up):
            self._go_prev()
            return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # AFFICHAGE DE L'ELEMENT COURANT
    # ------------------------------------------------------------------

    def _current_item(self):
        album = self._albums[self._album_index]
        return album, album["items"][self._item_index]

    def _caption_key(self, album_key: str, item_name: str) -> str:
        return f"{album_key}/{item_name}"

    def _show_current(self):
        if self.media_player is not None:
            self._video_ratio_pending = False
            self.media_player.stop()

        album, item = self._current_item()
        total = len(album["items"])
        self.position_label.setText(
            f"{album['label']} — {self._item_index + 1}/{total}"
        )

        self._current_key = (album["key"], self._item_index)
        self._current_is_video = item["type"] == "video"

        caption_key = self._caption_key(album["key"], item["name"])
        self._current_caption = self._captions.get(caption_key, "")
        if self.caption_edit is not None:
            self.caption_edit.blockSignals(True)
            self.caption_edit.setText(self._current_caption)
            self.caption_edit.blockSignals(False)
            self._update_caption_counter()

        self.media_card.show()
        self.play_button.setVisible(
            self._current_is_video and self.media_player is not None
        )

        if self._current_is_video:
            self._current_pixmap = None
            self._native_cap = None
            self.media_stack.setCurrentWidget(self._video_page)
            self._relayout_media()
            if self.media_player is not None:
                self.media_player.setSource(QUrl.fromLocalFile(item["path"]))
                self.media_player.play()
            return

        # Image : cache d'abord, sinon demande de chargement en arriere-plan.
        self.media_stack.setCurrentWidget(self.image_label)
        cached = self._pixmap_cache.get(self._current_key)
        if cached is not None:
            self._display_pixmap(cached)
        else:
            self._current_pixmap = None
            self._native_cap = None
            self.image_label.clear()
            self.image_label.setText("Chargement…")
            self._relayout_media()
            self._request_seq += 1
            self.requestImageLoad.emit(
                album["key"], self._item_index, self._request_seq, item["path"]
            )

    def _prefetch_next(self):
        """Charge en tache de fond l'image suivante, sans l'afficher,
        pour que le clic sur "Suivant" paraisse instantane."""
        if not self._albums:
            return
        album = self._albums[self._album_index]
        if self._item_index + 1 < len(album["items"]):
            next_album, next_index = album, self._item_index + 1
        else:
            next_album_idx = (self._album_index + 1) % len(self._albums)
            next_album = self._albums[next_album_idx]
            next_index = 0

        if not next_album["items"]:
            return
        next_item = next_album["items"][next_index]
        if next_item["type"] != "image":
            return
        cache_key = (next_album["key"], next_index)
        if cache_key in self._pixmap_cache:
            return
        self._request_seq += 1
        self.requestImageLoad.emit(
            next_album["key"], next_index, self._request_seq, next_item["path"]
        )

    def _remember_pixmap(self, album_key, item_index, pixmap):
        cache_key = (album_key, item_index)
        self._pixmap_cache[cache_key] = pixmap
        self._pixmap_cache.move_to_end(cache_key)
        while len(self._pixmap_cache) > _MAX_PIXMAP_CACHE:
            self._pixmap_cache.popitem(last=False)

    def _on_image_ready(self, album_key, item_index, request_id, image):
        # Conversion QImage -> QPixmap ici, sur le thread GUI.
        pixmap = QPixmap.fromImage(image)
        self._remember_pixmap(album_key, item_index, pixmap)
        if pixmap.height() > 0:
            # Le format est retenu meme pour une image prechargee : quand on
            # l'ouvrira, le cadre aura tout de suite la bonne forme.
            self._ratio_cache[(album_key, item_index)] = pixmap.width() / pixmap.height()

        if not self._albums:
            return
        current_album = self._albums[self._album_index]
        is_current = (
            current_album["key"] == album_key and item_index == self._item_index
        )
        if is_current and not self._current_is_video:
            self._display_pixmap(pixmap)

    def _on_pixmap_failed(self, album_key, item_index, request_id, message):
        if not self._albums:
            return
        current_album = self._albums[self._album_index]
        is_current = (
            current_album["key"] == album_key and item_index == self._item_index
        )
        if is_current:
            self._current_pixmap = None
            self.image_label.clear()
            self.image_label.setText(f"Impossible d'afficher ce fichier : {message}")

    def _display_pixmap(self, pixmap: QPixmap):
        self._current_pixmap = pixmap
        if pixmap.width() > 0 and pixmap.height() > 0:
            ratio = pixmap.width() / pixmap.height()
            self._last_ratio = ratio
            if self._current_key is not None:
                self._ratio_cache[self._current_key] = ratio
            dpr = pixmap.devicePixelRatio() or 1.0
            self._native_cap = (
                pixmap.width() / dpr * _UPSCALE_LIMIT,
                pixmap.height() / dpr * _UPSCALE_LIMIT,
            )
        self._relayout_media(immediate=True)

    # ------------------------------------------------------------------
    # MISE EN PAGE DU MEDIA : le cadre epouse le format de chaque media
    # ------------------------------------------------------------------

    def _current_ratio(self) -> float:
        ratio = self._ratio_cache.get(self._current_key) if self._current_key else None
        return ratio or self._last_ratio or _DEFAULT_RATIO

    def _caption_height(self, text: str, media_w: int) -> int:
        """Hauteur de la pastille de legende pour une largeur donnee."""
        if not text:
            return 0
        self.caption_label.setText(text)
        return self.caption_label.text_height(media_w)

    def _relayout_media(self, immediate: bool = False):
        if not self._albums or self._current_key is None:
            return
        stage_w, stage_h = self.stage.width(), self.stage.height()
        if stage_w < 50 or stage_h < 50:
            return

        pad = _CARD_PAD
        text = self._current_caption
        ratio = self._current_ratio()
        cap = None if self._current_is_video else self._native_cap

        # La hauteur de la legende depend de la largeur du media, qui depend
        # elle-meme de la place laissee a la legende : 3 passes suffisent.
        caption_h = 0
        media_w = media_h = 0
        for _ in range(3):
            avail_w = stage_w - 2 * pad
            avail_h = stage_h - 2 * pad - ((caption_h + _CAPTION_GAP) if caption_h else 0)
            media_w, media_h = _fit_ratio(ratio, avail_w, avail_h, cap)
            new_caption_h = self._caption_height(text, media_w)
            if new_caption_h == caption_h:
                break
            caption_h = new_caption_h
        if media_w < 1 or media_h < 1:
            return

        extra = (caption_h + _CAPTION_GAP) if caption_h else 0
        card_w = media_w + 2 * pad
        card_h = media_h + 2 * pad + extra
        card_x = (stage_w - card_w) // 2
        card_y = (stage_h - card_h) // 2

        self.media_card.setGeometry(card_x, card_y, card_w, card_h)
        self.media_stack.setGeometry(pad, pad, media_w, media_h)

        if caption_h:
            self.caption_label.setText(text)
            self.caption_label.setGeometry(
                pad, pad + media_h + _CAPTION_GAP, media_w, caption_h
            )
            self.caption_label.show()
            self.caption_label.raise_()
        else:
            self.caption_label.hide()

        if not self._current_is_video and self._current_pixmap is not None:
            if immediate:
                self._rescale_timer.stop()
                self._apply_pixmap_to_label()
            else:
                self._rescale_timer.start()

    def _apply_pixmap_to_label(self):
        pixmap = self._current_pixmap
        if pixmap is None or self._current_is_video:
            return
        size = self.media_stack.size()
        if size.width() < 4 or size.height() < 4:
            return
        dpr = self.devicePixelRatioF()
        scaled = pixmap.scaled(
            QSize(int(size.width() * dpr), int(size.height() * dpr)),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        scaled.setDevicePixelRatio(dpr)
        self.image_label.setPixmap(scaled)

    def showEvent(self, event):
        super().showEvent(event)
        self._relayout_media()

    # ------------------------------------------------------------------
    # SYNCHRONISATION AVEC LES REGLAGES D'APPARENCE
    # ------------------------------------------------------------------
    # Quand tu modifies un reglage, apply_runtime_preferences() reconstruit
    # la feuille de style de l'application : Qt envoie alors StyleChange /
    # PaletteChange / FontChange a chaque widget, dont cette page. On en
    # profite pour refaire la mise en page (la taille du texte change la
    # hauteur des onglets et de la legende) et repeindre la legende. Les
    # couleurs, elles, ne sont jamais memorisees : tout est relu a chaque
    # repeinture ou vient de la feuille de style globale.

    def changeEvent(self, event):
        super().changeEvent(event)
        if getattr(self, "_theme_refresh_pending", None) is not False:
            return
        if event.type() in (
            QEvent.StyleChange, QEvent.FontChange, QEvent.PaletteChange,
        ):
            self._theme_refresh_pending = True
            QTimer.singleShot(0, self._refresh_theme)

    def _refresh_theme(self):
        self._theme_refresh_pending = False
        self._fit_tabs_height()
        self.caption_label.update()
        self._relayout_media(immediate=True)

    # ------------------------------------------------------------------
    # VIDEO
    # ------------------------------------------------------------------

    def _on_media_status(self, status):
        """Des que la video est chargee, on attend sa premiere image pour
        en lire le format reel. (On n'ecoute pas avant : une image de la
        video precedente encore en file pourrait fausser le format.)"""
        if not self._current_is_video or self._current_key is None:
            return
        loaded = (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia)
        if status in loaded and self._current_key not in self._ratio_cache:
            self._video_ratio_pending = True

    def _on_video_frame(self, frame):
        if not self._video_ratio_pending:
            return
        try:
            if not frame.isValid():
                return
            size = frame.size()
            width, height = size.width(), size.height()
        except Exception:
            return
        if width <= 0 or height <= 0:
            return
        # Telephone tenu en portrait : 1920x1080 stocke + rotation de 90 deg.
        if _frame_rotation(frame) in (90, 270):
            width, height = height, width

        self._video_ratio_pending = False
        ratio = width / height
        self._last_ratio = ratio
        if self._current_key is not None:
            self._ratio_cache[self._current_key] = ratio
        self._relayout_media()

    def _on_playback_state(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_button.setText("⏸ Pause")
        else:
            self.play_button.setText("▶ Lecture")

    def _toggle_video_playback(self):
        if self.media_player is None:
            return
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    # ------------------------------------------------------------------
    # LEGENDES
    # ------------------------------------------------------------------

    def _update_caption_counter(self, *_):
        if self.caption_counter is None or self.caption_edit is None:
            return
        self.caption_counter.setText(
            f"{len(self.caption_edit.text())}/{_CAPTION_MAX_CHARS}"
        )

    def _save_current_caption(self):
        if not CREDITS_EDIT_MODE or not self._albums or self._root is None:
            return
        album, item = self._current_item()
        key = self._caption_key(album["key"], item["name"])
        text = self.caption_edit.text().strip()

        if text:
            self._captions[key] = text
        else:
            self._captions.pop(key, None)

        try:
            captions_path = self._root / CAPTIONS_FILENAME
            captions_path.write_text(
                json.dumps(self._captions, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.status_label.setText("Légende enregistrée.")
        except Exception as exc:
            self.status_label.setText(f"Échec de l'enregistrement de la légende : {exc}")
            return

        # La pastille apparait / se met a jour tout de suite sous le media.
        self._current_caption = text
        self._relayout_media(immediate=True)
