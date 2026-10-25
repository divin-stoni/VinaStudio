# -*- coding: utf-8 -*-
"""Cases a cocher tres visibles : coche nette sur fond plein (toute l'application).
La couleur vient de COLORS["accent"] du theme ; les images sont redessinees au demarrage."""
import re
import sys
import tempfile
from pathlib import Path

MARK = "/* vina-checkbox-style */"
SIZE = 20
CLASSES = ("QCheckBox", "QGroupBox", "QTableView", "QTableWidget", "QListView",
           "QListWidget", "QTreeView", "QTreeWidget")


def _parse_color(value, default):
    try:
        v = str(value).strip()
        m = re.match(r"#([0-9a-fA-F]{6})", v)
        if m:
            h = m.group(1)
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", v)
        if m:
            return tuple(int(x) for x in m.groups())
    except Exception:
        pass
    return default


def _accent():
    base = (47, 174, 95)
    try:
        mw = sys.modules.get("src.gui.main_window")
        if mw is not None:
            base = _parse_color(mw.COLORS["accent"], base)
    except Exception:
        pass
    return base


def _lum(c):
    return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255.0


def _shade(c, f):
    return tuple(max(0, min(255, int(x * f))) for x in c)


def _draw(path, state, hover, enabled, acc):
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen
    S = SIZE
    img = QImage(S, S, QImage.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    fill = _shade(acc, 0.62) if _lum(acc) > 0.45 else acc
    if state == "off":
        if enabled:
            bg = QColor(228, 237, 246) if hover else QColor(248, 250, 252)
            edge = QColor(*_shade(acc, 0.8)) if hover else QColor(70, 84, 98)
        else:
            bg, edge = QColor(222, 227, 232), QColor(150, 160, 170)
    else:
        if enabled:
            bg = QColor(*_shade(fill, 1.15 if hover else 1.0))
            edge = QColor(*_shade(fill, 0.78))
        else:
            bg, edge = QColor(92, 104, 98), QColor(150, 160, 155)
    p.setPen(QPen(edge, 2))
    p.setBrush(QBrush(bg))
    p.drawRoundedRect(QRectF(1.5, 1.5, S - 3, S - 3), 4, 4)
    mark = QColor(255, 255, 255) if enabled else QColor(205, 210, 205)
    if state == "on":
        pen = QPen(mark, 2.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        path_ = QPainterPath()
        path_.moveTo(QPointF(S * 0.24, S * 0.52))
        path_.lineTo(QPointF(S * 0.43, S * 0.72))
        path_.lineTo(QPointF(S * 0.78, S * 0.30))
        p.drawPath(path_)
    elif state == "partial":
        p.setPen(QPen(mark, 3.0, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(S * 0.28, S * 0.5), QPointF(S * 0.72, S * 0.5))
    p.end()
    img.save(str(path))


_SPECS = {
    "off": ("off", False, True),
    "off_hover": ("off", True, True),
    "off_dis": ("off", False, False),
    "on": ("on", False, True),
    "on_hover": ("on", True, True),
    "on_dis": ("on", False, False),
    "partial": ("partial", False, True),
    "partial_dis": ("partial", False, False),
}


def _fill(acc):
    return _shade(acc, 0.62) if _lum(acc) > 0.45 else acc


def _draw_arrow(path, direction, color):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
    S = 20
    img = QImage(S, S, QImage.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QPen(QColor(*color), 3.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    pth = QPainterPath()
    if direction == "down":
        pts = [(0.22, 0.36), (0.50, 0.66), (0.78, 0.36)]
    elif direction == "up":
        pts = [(0.22, 0.64), (0.50, 0.34), (0.78, 0.64)]
    else:
        pts = [(0.36, 0.22), (0.66, 0.50), (0.36, 0.78)]
    pth.moveTo(QPointF(S * pts[0][0], S * pts[0][1]))
    for x, y in pts[1:]:
        pth.lineTo(QPointF(S * x, S * y))
    p.drawPath(pth)
    p.end()
    img.save(str(path))


def arrows_css(d, tag, acc):
    normal, dis = (237, 245, 255), (120, 130, 140)
    hover = tuple(min(255, int(c * 1.35) + 20) for c in acc)
    specs = {
        "ar_down": ("down", normal), "ar_down_hover": ("down", hover),
        "ar_down_dis": ("down", dis), "ar_up": ("up", hover),
        "ar_right": ("right", normal), "ar_right_dis": ("right", dis),
    }
    u = {}
    for key, (direction, color) in specs.items():
        f = d / ("%s_%s.png" % (key, tag))
        if not f.exists():
            _draw_arrow(f, direction, color)
        u[key] = f.as_posix()
    fill = "rgb(%d, %d, %d)" % _fill(acc)
    return """
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 32px;
    border-left: 1px solid rgba(255, 255, 255, 70);
}
QComboBox::down-arrow { image: url("%(ar_down)s"); width: 16px; height: 16px; }
QComboBox::down-arrow:hover { image: url("%(ar_down_hover)s"); }
QComboBox::down-arrow:on { image: url("%(ar_up)s"); }
QComboBox::down-arrow:disabled { image: url("%(ar_down_dis)s"); }
QComboBox QAbstractItemView { outline: 0; }
QComboBox QAbstractItemView::item { min-height: 30px; padding: 4px 12px; }
QComboBox QAbstractItemView::item:selected,
QComboBox QAbstractItemView::item:hover { background-color: %(fill)s; color: #ffffff; }
QMenu::item { padding: 8px 34px 8px 16px; }
QMenu::item:selected { background-color: %(fill)s; color: #ffffff; }
QMenu::item:disabled { color: rgb(120, 130, 140); }
QMenu::right-arrow { image: url("%(ar_right)s"); width: 14px; height: 14px; margin-right: 10px; }
QMenu::right-arrow:disabled { image: url("%(ar_right_dis)s"); }
QMenuBar::item:selected { background-color: %(fill)s; color: #ffffff; }
QToolButton::menu-indicator {
    image: url("%(ar_down)s"); width: 12px; height: 12px;
    subcontrol-origin: padding; subcontrol-position: bottom right; right: 3px; bottom: 3px;
}
QToolButton::menu-indicator:pressed,
QToolButton::menu-indicator:open { image: url("%(ar_up)s"); }
""" % dict(u, fill=fill)


def css():
    acc = _accent()
    d = Path(tempfile.gettempdir()) / "vinastudio_checks"
    d.mkdir(parents=True, exist_ok=True)
    tag = "%02x%02x%02x_v2" % acc
    url = {}
    for key, (state, hover, enabled) in _SPECS.items():
        f = d / ("%s_%s.png" % (key, tag))
        if not f.exists():
            _draw(f, state, hover, enabled, acc)
        url[key] = f.as_posix()

    def rule(state_sel, key):
        sels = ",\n".join("%s::indicator%s" % (c, state_sel) for c in CLASSES)
        return ("%s {\n    image: url(\"%s\");\n    background: none;\n    border: none;\n"
                "    width: %dpx;\n    height: %dpx;\n}\n" % (sels, url[key], SIZE, SIZE))

    out = [MARK, "QCheckBox { spacing: 9px; }"]
    out.append(rule(":unchecked:enabled", "off"))
    out.append(rule(":unchecked:hover", "off_hover"))
    out.append(rule(":unchecked:disabled", "off_dis"))
    out.append(rule(":checked:enabled", "on"))
    out.append(rule(":checked:hover", "on_hover"))
    out.append(rule(":checked:disabled", "on_dis"))
    out.append(rule(":indeterminate:enabled", "partial"))
    out.append(rule(":indeterminate:disabled", "partial_dis"))
    out.append(arrows_css(d, tag, acc))
    return "\n".join(out)


def install():
    """Ajoute le style des cases a CHAQUE application de feuille de style globale."""
    try:
        from PySide6.QtWidgets import QApplication
        if getattr(QApplication, "_vina_cb_patched", False):
            return True
        orig = QApplication.setStyleSheet

        def patched(self, sheet):
            try:
                s = str(sheet or "")
                if MARK not in s:
                    s = s + "\n" + css()
            except Exception:
                s = sheet
            return orig(self, s)

        QApplication.setStyleSheet = patched
        QApplication._vina_cb_patched = True
        return True
    except Exception as exc:
        print("Style des cases non installe :", exc)
        return False
