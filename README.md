# AutoDrive FS25 Editor

Desktop-Editor für AutoDrive-Streckennetze aus dem Landwirtschafts-Simulator 25, entwickelt mit Python und PySide6.

Der Editor lädt eine AutoDrive-Konfiguration (XML), zeigt sie auf der Karte (`overview.dds`) mit Höhendaten (`dem.png`) und bietet Werkzeuge zum Bearbeiten des Netzes: Nodes erstellen, verschieben, rotieren, löschen, ihren Typ wechseln, Connections (Regular, Dual, Reverse) setzen sowie Linien, Bézierkurven und Kreisbögen mit gleichmäßigem Node-Abstand zeichnen. Alle Änderungen lassen sich rückgängig machen.

Geplante Funktionen stehen in der [Roadmap](ROADMAP.md).

## Herunterladen

Die fertige Windows-Version liegt als Zip unter [Releases](https://github.com/SvenBrauns/AutoDrive_Editor/releases). Entpacken und `AutoDrive Editor.exe` starten; eine Python-Installation ist nicht nötig.

## Aus dem Quellcode starten

```text
pip install -r requirements.txt
python main.py
```

oder `python -m autodrive_editor`.

## Entwicklung

```text
pip install -r requirements-dev.txt
python -m pytest
ruff check .
ruff format .
```

GitHub Actions prüft jeden Push und Pull Request mit `ruff` und `pytest`. Ein Tag wie `v0.1.0` baut mit PyInstaller die Windows-Version und veröffentlicht sie als Release:

```text
git tag v0.1.0
git push origin v0.1.0
```

## Aufbau

```text
autodrive_editor/
  model/        Datenmodell: Nodes, Marker, Connection-Typen
  file_io/      Dateiformate: AutoDrive-XML, Projektdateien, Heightmap, DDS
  terrain/      Hintergrundkarte, Heightmap, Gelände-Höhe für bewegte Nodes
  editing/
    commands/   rückgängig machbare Änderungen am Datenmodell
    operations/ Bearbeitungsabläufe der Werkzeuge (verschieben, verbinden, …)
    edit_history.py  gemeinsame Undo-/Redo-Historie
  selection/    Node-Auswahl
  measurement/  Abstand- und Winkelmessung
  project/      Laden von XML, Karte, Heightmap und Projekten
  rendering/    Darstellung der Karte
    spatial/    räumliche Indizes für Nodes und Connections
    visible/    Grafikobjekte nur für den sichtbaren Bereich
    connections/ Connection-Daten, -Geometrie und Detaildarstellung
    items/      einzelne Grafikobjekte
  ui/
    main_window.py  Hauptfenster, setzt alle Teile zusammen
    actions/    Werkzeugkatalog, Menüs, Werkzeugleisten
    map_view/   Kartenansicht mit Zoom, Rotation und Bereichsauswahl
    tools/      Mausbedienung je Werkzeug
    panels/     Werkzeugpanel, Debug-Dock, Darstellungsoptionen
    controls/   Raster- und Rotationseinstellungen
  resources/    Symbole
tests/          gleiche Ordnerstruktur wie autodrive_editor/
packaging/      Programmsymbol und Lizenztexte für die Windows-Version
.github/        CI und Release-Build
```

## Grundregeln im Code

- Jede Änderung am Datenmodell ist ein `EditCommand` und läuft über `EditHistory.push()`, damit sie rückgängig gemacht werden kann.
- Nach jeder Änderung meldet der Befehl ein `DataChange`; der `SceneRenderer` aktualisiert daraufhin nur die betroffenen Nodes.
- Nur Nodes, Marker und Auswahlringe im sichtbaren Bereich existieren als Grafikobjekte, damit auch Netze mit über 100 000 Nodes flüssig bleiben.
- Jedes Werkzeug ist eine `MapTool`-Unterklasse unter `ui/tools/` und wird in `ui/actions/tool_catalog.py` mit Symbol und Tastenkürzel beschrieben.

## Grundprinzipien

- Direkte Kompatibilität: `overview.dds` und `dem.png` werden ohne manuelle Umwandlung verwendet.
- Quelldaten werden nie automatisch überschrieben; geschrieben wird nur durch ausdrückliches Speichern (vorher `.bak`).
- Die Bedeutung von Nodes, Flags, Markern, Koordinaten und Heightmap-Werten wird an echten AutoDrive-Daten nachvollzogen.
- Eigene Symbole verwenden; vor einer Veröffentlichung Lizenzen, Kartenbilder und Fremdinhalte prüfen.

## Hintergrundwissen

- **Connections** zwischen A und B werden an beiden Nodes gespeichert (siehe `model/connections.py`):

  ```text
              A.outgoing∋B  A.incoming∋B  B.outgoing∋A  B.incoming∋A
  Regular          ja            -             -             ja
  Dual             ja            ja            ja            ja
  Reverse          ja            -             -             -
  ```

- **Flags**: `0` = Regular, `1` = Subprio. Die XML-IDs sind 1-basiert.
- **Karten**: `overview.dds` hat für FS22/FS25 ein zu beschneidendes mittleres Viertel (4096² → 2048²). Die Kartengröße (`map_scale` 1/2/4/8 für Original/4x/16x/64x) kommt aus der Kartenkonfiguration, nie aus den Netzgrenzen. Bei einer 16x-Karte: 8192 × 8192 m, Weltkoordinaten −4096 bis +4096.
- **Heightmap** (`dem.png`, 16-Bit-Graustufen): `height = raw_value / 65535.0 * 255.0`. Gegen die Y-Werte eines Testnetzes mit 113 058 Nodes weicht sie im Median um 0,02 m ab; größere Abweichungen gibt es nur an Brücken, Rampen und Gebäudeebenen.
- **Winkel**: Kartenwinkel 0° = oben, 90° = rechts; unabhängig von Ansichts- und Rasterrotation.
- **Zoom**: Unter technischem Zoom 1.0 werden nur drei gebündelte Connection-Pfade gezeichnet, ab 1.0 Nodes, Marker, Auswahlringe und Connections mit Pfeilen. Sichtbereichsänderungen werden 50 ms verzögert gemeldet.

## Leistung (Testnetz mit 113 058 Nodes und 116 260 Connections)

Bewährt: native `QGraphicsEllipseItem`-Nodes, Grafikobjekte nur für den sichtbaren Bereich plus Puffer (Kacheln 256 m, Puffer 128 m), drei gebündelte globale Connection-Pfade, räumliche Indizes, Auswahl nur als Node-IDs, getrennte Vorschau- und Endauswahl.

Nicht geeignet: eigenes `paint()` pro Node, dauerhaft alle NodeItems, ein Grafikobjekt pro Connection, große gespeicherte Pfeilpfade, dauerhafte Auswahlringe für alle ausgewählten Nodes.

## Lizenz

GNU General Public License v3.0 oder später, siehe [LICENSE](LICENSE). Die Windows-Version enthält PySide6/Qt (LGPLv3) und Pillow, siehe [THIRD_PARTY_NOTICES.md](packaging/THIRD_PARTY_NOTICES.md).

Der Editor enthält keine Dateien aus dem Landwirtschafts-Simulator oder aus Karten-Mods; Kartenbilder und Heightmaps werden aus der eigenen Installation gelesen. Das Projekt steht in keiner Verbindung zu GIANTS Software.
