# Third-party notices

The Windows build of the AutoDrive FS25 Editor bundles the following software.

| Component | License | Source |
|---|---|---|
| Python | PSF License | https://www.python.org/ |
| PySide6 / Qt for Python, Qt 6 | LGPL-3.0 (see `LGPL-3.0.txt` and `LICENSE`) | https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| Pillow | MIT-CMU (HPND) | https://github.com/python-pillow/Pillow |
| I3DShapesTool (cipher of `.i3d.shapes` files, ported to Python in `file_io/i3d_shapes.py` with its key table `resources/i3d_shapes_key.bin`) | MIT (below) | https://github.com/Donkie/I3DShapesTool |

The Qt and PySide6 libraries are included as separate DLL and .pyd files in
the `_internal` folder. You may replace them with your own compatible build.

The editor ships no files from Farming Simulator or any map mod. Map images
and heightmaps are read from the user's own game installation and mods. The
project is not affiliated with GIANTS Software.

## I3DShapesTool

MIT License

Copyright (c) 2017 Daniel Hultgren

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
