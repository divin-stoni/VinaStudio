# -*- coding: utf-8 -*-
"""Bibliotheque d'images d'arriere-plan : images du depot + images ajoutees par l'utilisateur.
Les images ajoutees vivent hors du depot (dossier de donnees de l'utilisateur)."""
import shutil
from pathlib import Path

from PySide6.QtCore import QSize, QStandardPaths, Qt
from PySide6.QtGui import QIcon, QImage, QImageReader, QPixmap

QT_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
IMPORT_EXT = QT_EXT | {".avif", ".heic", ".heif", ".pcx", ".tga", ".jfif"}
BUILTIN_EXCLUDE = {"um6ss_logo.png", "umng.png"}
THUMB = QSize(150, 84)


def builtin_dir():
    return Path(__file__).resolve().parents[2] / "image_theme"


def user_dir():
    base = QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation)
    if not base:
        base = str(Path.home() / ".local" / "share")
    d = Path(base) / "VinaStudio-backgrounds"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _scan(d, exclude=()):
    if not d.is_dir():
        return []
    out = [p for p in d.iterdir()
           if p.is_file() and p.suffix.lower() in QT_EXT and p.name.lower() not in exclude]
    return sorted(out, key=lambda p: p.name.lower())


def list_images():
    """Liste de (chemin, ajoutee_par_l_utilisateur)."""
    return ([(p, False) for p in _scan(builtin_dir(), BUILTIN_EXCLUDE)]
            + [(p, True) for p in _scan(user_dir())])


def _unique(dest):
    if not dest.exists():
        return dest
    i = 2
    while True:
        c = dest.with_name("%s_%d%s" % (dest.stem, i, dest.suffix))
        if not c.exists():
            return c
        i += 1


def import_file(src):
    """Copie (ou convertit en PNG) une image dans le dossier de l'utilisateur."""
    src = Path(src)
    udir = user_dir()
    readable = QImageReader(str(src)).canRead()
    if readable and src.suffix.lower() in QT_EXT:
        dest = _unique(udir / src.name)
        shutil.copy2(str(src), str(dest))
        return dest
    if readable:
        img = QImage(str(src))
        if not img.isNull():
            dest = _unique(udir / (src.stem + ".png"))
            img.save(str(dest))
            return dest
    try:
        try:
            import pillow_avif  # noqa: F401
        except Exception:
            pass
        from PIL import Image
        pil = Image.open(str(src)).convert("RGB")
    except Exception as exc:
        raise RuntimeError("format illisible (%s)" % exc)
    dest = _unique(udir / (src.stem + ".png"))
    pil.save(str(dest))
    if QImage(str(dest)).isNull():
        dest.unlink()
        raise RuntimeError("conversion impossible")
    return dest


def remove_user_image(path):
    path = Path(path)
    if path.parent.resolve() != user_dir().resolve():
        raise ValueError("seules les images ajoutees peuvent etre retirees")
    path.unlink()


def thumbnail(path):
    cache = user_dir() / ".thumbs"
    cache.mkdir(parents=True, exist_ok=True)
    st = path.stat()
    f = cache / ("%s_%d_%d.png" % (path.stem, st.st_size, int(st.st_mtime)))
    if f.exists():
        pm = QPixmap(str(f))
        if not pm.isNull():
            return pm
    r = QImageReader(str(path))
    sz = r.size()
    if sz.isValid() and sz.width() > 0:
        r.setScaledSize(sz.scaled(THUMB.width() * 2, THUMB.height() * 2,
                                  Qt.KeepAspectRatioByExpanding))
    img = r.read()
    if img.isNull():
        return QPixmap()
    img = img.scaled(THUMB, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = max(0, (img.width() - THUMB.width()) // 2)
    y = max(0, (img.height() - THUMB.height()) // 2)
    img = img.copy(x, y, THUMB.width(), THUMB.height())
    img.save(str(f))
    return QPixmap.fromImage(img)


def _has_legacy_index(settings):
    """Ancien réglage numérique (theme/index) : présent seulement chez les anciens utilisateurs."""
    try:
        return settings.contains("theme/index")
    except Exception:
        try:
            return settings.value("theme/index", None) is not None
        except Exception:
            return False


def initial_choice(settings, preset):
    """Image de depart : choix memorise (par nom), sinon ancien numero, sinon theme par defaut."""
    key = settings.value("theme/background_key", None)
    if key is not None:
        key = str(key)
        if key == "none":
            return None
        kind, _, name = key.partition(":")
        p = (user_dir() if kind == "u" else builtin_dir()) / name
        if name and p.is_file():
            return p
    elif _has_legacy_index(settings):
        old = sorted(builtin_dir().glob("*.jpg"))
        try:
            idx = int(settings.value("theme/index", 0))
        except Exception:
            idx = 0
        if old:
            return old[idx % len(old)]
    name = (preset or {}).get("background")
    if name and (builtin_dir() / name).is_file():
        return builtin_dir() / name
    imgs = list_images()
    return imgs[0][0] if imgs else None


def save_choice(settings, path):
    if path is None:
        key = "none"
    else:
        path = Path(path)
        key = ("u:" if path.parent.resolve() == user_dir().resolve() else "b:") + path.name
    settings.setValue("theme/background_key", key)
    settings.sync()


def _accent_rgb():
    try:
        from src.gui import checkbox_style as cs
        return cs._accent()
    except Exception:
        return (107, 209, 141)


def build_menu(host):
    from PySide6.QtWidgets import (QApplication, QFileDialog, QFrame, QGridLayout, QMenu,
                                   QMessageBox, QScrollArea, QToolButton, QWidget,
                                   QWidgetAction)
    bg = host.theme_background
    t = host.lang_mgr.t
    menu = QMenu(host)

    def say(text):
        try:
            host.status.showMessage(text)
        except Exception:
            pass

    def apply(path):
        name = bg.set_background(path) or t("bg_menu_none")
        say(t("status_theme_applied", name=name))
        try:
            host.theme_action.setToolTip(t("toolbar_theme_tooltip_applied", name=name))
        except Exception:
            pass

    def add_files(paths):
        first, errs = None, []
        for p in paths:
            try:
                dest = import_file(p)
                first = first or dest
            except Exception as exc:
                errs.append("%s : %s" % (Path(p).name, exc))
        if first is not None:
            apply(first)
        if errs:
            QMessageBox.warning(host, t("toolbar_theme"),
                                "\n".join(t("bg_menu_unreadable", name=e) for e in errs))

    def pick_images(*_):
        flt = "Images (%s)" % " ".join("*" + e for e in sorted(IMPORT_EXT))
        files, _f = QFileDialog.getOpenFileNames(host, t("bg_menu_add_image"),
                                                 str(Path.home()), flt)
        if files:
            add_files(files)

    def pick_folder(*_):
        d = QFileDialog.getExistingDirectory(host, t("bg_menu_add_folder"), str(Path.home()))
        if d:
            add_files(sorted(p for p in Path(d).iterdir()
                             if p.is_file() and p.suffix.lower() in IMPORT_EXT))

    def remove(path):
        try:
            cur = getattr(bg, "_current", None)
            was_current = cur is not None and Path(cur).resolve() == Path(path).resolve()
            remove_user_image(path)
            if was_current:
                apply(initial_choice(_NoSettings(), None))
        except Exception as exc:
            say(str(exc))

    imgs = list_images()
    cur = getattr(bg, "_current", None)
    cur_res = Path(cur).resolve() if cur else None
    r, g, b = _accent_rgb()
    box = QWidget()
    grid = QGridLayout(box)
    grid.setContentsMargins(6, 6, 6, 6)
    grid.setSpacing(6)
    cols = 4
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        for i, (p, is_user) in enumerate(imgs):
            btn = QToolButton()
            try:
                pm = thumbnail(p)
                if not pm.isNull():
                    btn.setIcon(QIcon(pm))
                    btn.setIconSize(THUMB)
            except Exception:
                pass
            btn.setToolTip(p.stem)
            btn.setCursor(Qt.PointingHandCursor)
            is_cur = cur_res is not None and p.resolve() == cur_res
            btn.setStyleSheet(
                "QToolButton { border: 3px solid %s; border-radius: 7px; padding: 2px; }"
                "QToolButton:hover { border-color: rgb(255, 255, 255); }"
                % ("rgb(%d, %d, %d)" % (r, g, b) if is_cur else "transparent"))
            btn.clicked.connect(lambda *_a, pp=p: (menu.close(), apply(pp)))
            grid.addWidget(btn, i // cols, i % cols)
    finally:
        QApplication.restoreOverrideCursor()
    scroll = QScrollArea()
    scroll.setWidget(box)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidgetResizable(True)
    scroll.setFixedSize(cols * (THUMB.width() + 22) + 28, 390)
    wa = QWidgetAction(menu)
    wa.setDefaultWidget(scroll)
    menu.addAction(wa)
    menu.addSeparator()
    menu.addAction(t("bg_menu_none")).triggered.connect(lambda *_a: apply(None))
    menu.addAction(t("bg_menu_add_image")).triggered.connect(pick_images)
    menu.addAction(t("bg_menu_add_folder")).triggered.connect(pick_folder)
    sub = menu.addMenu(t("bg_menu_remove"))
    users = [p for p, u in imgs if u]
    for p in users:
        sub.addAction(p.stem).triggered.connect(lambda *_a, pp=p: remove(pp))
    sub.setEnabled(bool(users))
    menu.addSeparator()
    menu.addAction(t("bg_menu_advanced")).triggered.connect(
        lambda *_a: host._open_preferences())
    return menu


class _NoSettings:
    def value(self, key, default=None):
        return "none" if key == "theme/background_key" and False else default


def show_menu(host, pos):
    menu = build_menu(host)
    menu.exec(pos)
