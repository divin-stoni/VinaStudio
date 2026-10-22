# -*- coding: utf-8 -*-
"""
startup.py

Ecran de demarrage et instance unique pour VINA Studio.

- begin() : cree le QApplication, verifie qu'aucune autre instance ne tourne
  (sinon la ramene au premier plan et renvoie None), affiche le splash.
- Startup.preload() : charge les bibliotheques lourdes dans un thread pendant
  que le splash reste anime (chrono, barre), puis importe main_window.
- Startup.ready(window) : ferme le splash quand la fenetre est affichee et
  memorise la duree pour estimer le prochain lancement.
"""

from __future__ import annotations

import getpass
import importlib
import json
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import (
    QCoreApplication,
    QEventLoop,
    QLockFile,
    QObject,
    QStandardPaths,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

# (libelle affiche, modules a importer) : charges dans un thread
PRELOAD = [
    ("Calcul numérique (numpy, pandas)", ("numpy", "pandas")),
    ("Graphiques (matplotlib)", ("matplotlib", "matplotlib.backends.backend_qtagg")),
    ("Moteur de docking", ("src.docking.vina_engine",)),
    ("Analyse statistique", ("src.analysis.statistics_pipeline",)),
]


def _log(msg: str) -> None:
    try:
        if sys.stderr:
            print(f"[startup] {msg}", file=sys.stderr, flush=True)
    except Exception:
        pass


def _fmt(seconds: float) -> str:
    s = int(round(seconds))
    if s < 60:
        return f"{s} s"
    return f"{s // 60} min {s % 60:02d} s"


# ------------------------------------------------------------ duree memorisee
def _timing_file() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
    return Path(base) / "startup_time.json"


def _read_expected():
    try:
        data = json.loads(_timing_file().read_text(encoding="utf-8"))
        value = float(data["seconds"])
        if 1.0 <= value <= 900.0:
            return value
    except Exception:
        pass
    return None


def _write_duration(seconds: float) -> None:
    try:
        old = _read_expected()
        value = seconds if old is None else 0.5 * old + 0.5 * seconds
        path = _timing_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"seconds": round(value, 1)}), encoding="utf-8")
    except Exception:
        pass


# --------------------------------------------------------------------- splash
class StartupSplash(QWidget):

    def __init__(self, expected=None):
        super().__init__(None, Qt.SplashScreen | Qt.FramelessWindowHint)
        self._t0 = time.monotonic()
        self._expected = expected
        self._stage_frac = 0.0
        self._shown_frac = 0.0

        self.setObjectName("StartupSplash")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(540, 230)
        self.setStyleSheet(
            """
            #StartupSplash { background: #ffffff; border: 1px solid #aeb8c4; }
            #SplashTitle { color: #1f4fbf; font-size: 22px; font-weight: 700; background: transparent; }
            #SplashSub   { color: #1f2933; font-size: 13px; background: transparent; }
            #SplashStep  { color: #1f2933; font-size: 13px; font-weight: 600; background: transparent; }
            #SplashTime  { color: #44505c; font-size: 12px; background: transparent; }
            #SplashHint  { color: #6b7785; font-size: 11px; background: transparent; }
            QProgressBar { background: #e4e9f0; border: none; border-radius: 5px; }
            QProgressBar::chunk { background: #2f6fed; border-radius: 5px; }
            """
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 18)
        lay.setSpacing(8)

        title = QLabel("VINA Studio")
        title.setObjectName("SplashTitle")
        sub = QLabel("Démarrage en cours, veuillez patienter...")
        sub.setObjectName("SplashSub")
        self.step_label = QLabel("Initialisation...")
        self.step_label.setObjectName("SplashStep")
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(10)
        self.time_label = QLabel("")
        self.time_label.setObjectName("SplashTime")
        hint = QLabel("Ne relancez pas le logiciel : il est en train de démarrer.")
        hint.setObjectName("SplashHint")

        for w in (title, sub):
            lay.addWidget(w)
        lay.addSpacing(6)
        lay.addWidget(self.step_label)
        lay.addWidget(self.bar)
        lay.addWidget(self.time_label)
        lay.addStretch()
        lay.addWidget(hint)

        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(geo.center() - self.rect().center())

        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._tick()

    @Slot(str, float)
    def set_step(self, text: str, frac: float) -> None:
        self.step_label.setText(text)
        self._stage_frac = max(self._stage_frac, float(frac))
        self._tick()

    def _tick(self) -> None:
        elapsed = time.monotonic() - self._t0
        text = f"Temps écoulé : {_fmt(elapsed)}"
        frac = self._stage_frac
        if self._expected:
            text += f"   |   durée habituelle : environ {_fmt(self._expected)}"
            frac = max(frac, min(0.97, elapsed / self._expected))
        self._shown_frac = max(self._shown_frac, frac)
        self.bar.setValue(int(self._shown_frac * 1000))
        self.time_label.setText(text)

    def stop(self) -> None:
        self._timer.stop()


class _Bridge(QObject):
    step = Signal(str, float)
    done = Signal()


# ------------------------------------------------------------------- Startup
def _front(widget) -> None:
    try:
        if widget.isMinimized():
            widget.showNormal()
        widget.show()
        widget.raise_()
        widget.activateWindow()
    except Exception:
        pass


class Startup:

    def __init__(self, app, splash, lock, server):
        self.app = app
        self.splash = splash
        self._lock = lock
        self._server = server
        self.target = splash
        self.t0 = time.monotonic()
        self._total = len(PRELOAD) + 2
        if server is not None:
            server.newConnection.connect(self._on_connection)

    def _on_connection(self) -> None:
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            if sock is not None:
                sock.disconnectFromServer()
        _front(self.target)

    def step(self, text: str, frac: float) -> None:
        self.splash.set_step(text, frac)
        self.app.processEvents()

    def preload(self):
        bridge = _Bridge()
        bridge.step.connect(self.splash.set_step)
        loop = QEventLoop()
        bridge.done.connect(loop.quit)
        total = self._total

        def work():
            for i, (label, modules) in enumerate(PRELOAD):
                bridge.step.emit(f"Chargement : {label}", i / total)
                t = time.monotonic()
                for name in modules:
                    try:
                        importlib.import_module(name)
                    except Exception:
                        pass  # l'erreur reelle sera levee a l'import final
                _log(f"{label} : {time.monotonic() - t:.1f} s")
            bridge.done.emit()

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        loop.exec()
        thread.join()

        self.step("Chargement : interface principale", len(PRELOAD) / total)
        t = time.monotonic()
        module = importlib.import_module("src.gui.main_window")
        _log(f"Interface principale (import) : {time.monotonic() - t:.1f} s")
        return module

    def building_window(self) -> None:
        self.step(
            "Construction de l'interface principale (dernière étape)",
            (len(PRELOAD) + 1) / self._total,
        )

    def ready(self, window) -> None:
        duration = time.monotonic() - self.t0
        _log(f"Total jusqu'a la fenetre : {duration:.1f} s")
        _write_duration(duration)
        self.target = window
        self.app.processEvents()
        self.close()
        _front(window)

    def close(self) -> None:
        try:
            self.splash.stop()
            self.splash.close()
        except Exception:
            pass


def _notify_running(name: str) -> None:
    sock = QLocalSocket()
    sock.connectToServer(name)
    if sock.waitForConnected(800):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(500)
        sock.disconnectFromServer()


def begin():
    """Retourne un objet Startup, ou None si une autre instance tourne deja."""
    # Necessaire pour QtWebEngine quand QApplication est cree avant son import
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("VINA Studio")
    app.setOrganizationName("VINA Studio")

    lock = None
    server = None
    try:
        try:
            user = getpass.getuser()
        except Exception:
            user = "user"
        name = f"VinaStudio-{user}"
        tmp = QStandardPaths.writableLocation(QStandardPaths.TempLocation)
        lock = QLockFile(str(Path(tmp) / f"vinastudio-{user}.lock"))
        lock.setStaleLockTime(0)  # seul un processus mort rend le verrou perime
        if not lock.tryLock(0):
            if lock.error() == QLockFile.LockError.LockFailedError:
                _notify_running(name)
                return None
            lock = None  # verrou inutilisable (droits...) : on demarre quand meme
        else:
            QLocalServer.removeServer(name)
            server = QLocalServer()
            if not server.listen(name):
                server = None
    except Exception:
        pass

    splash = StartupSplash(expected=_read_expected())
    splash.show()
    app.processEvents()
    return Startup(app, splash, lock, server)
