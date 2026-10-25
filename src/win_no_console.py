"""Masque les fenetres console des sous-processus sous Windows."""
import subprocess
import sys

if sys.platform == "win32":
    _orig_popen_init = subprocess.Popen.__init__

    def _popen_no_window(self, *args, **kwargs):
        kwargs["creationflags"] = (
            kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
        )
        if kwargs.get("startupinfo") is None:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = si
        _orig_popen_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = _popen_no_window
