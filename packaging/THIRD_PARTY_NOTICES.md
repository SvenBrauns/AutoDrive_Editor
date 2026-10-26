# Third-party notices

The Windows build of the AutoDrive FS25 Editor bundles the following software.

| Component | License | Source |
|---|---|---|
| Python | PSF License | https://www.python.org/ |
| PySide6 / Qt for Python, Qt 6 | LGPL-3.0 (see `LGPL-3.0.txt` and `LICENSE`) | https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| Pillow | MIT-CMU (HPND) | https://github.com/python-pillow/Pillow |

The Qt and PySide6 libraries are included as separate DLL and .pyd files in
the `_internal` folder. You may replace them with your own compatible build.

The editor ships no files from Farming Simulator or any map mod. Map images
and heightmaps are read from the user's own game installation and mods. The
project is not affiliated with GIANTS Software.
