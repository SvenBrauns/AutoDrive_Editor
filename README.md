# AutoDrive FS25 Editor

Desktop-Editor für AutoDrive-Streckennetze aus dem Landwirtschafts-Simulator 25, entwickelt mit Python und PySide6.

Der Editor lädt eine AutoDrive-Konfiguration (XML), zeigt sie auf der Karte (`overview.dds`) mit Höhendaten (`dem.png`) und bietet Werkzeuge zum Bearbeiten des Netzes: Nodes erstellen, verschieben, rotieren, löschen, ihren Typ wechseln und Connections (Regular, Dual, Reverse) setzen. Alle Änderungen lassen sich rückgängig machen.

Geplante Funktionen stehen in der [Roadmap](ROADMAP.md).

## Starten

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
```

## Grundregeln im Code

- Jede Änderung am Datenmodell ist ein `EditCommand` und läuft über `EditHistory.push()`, damit sie rückgängig gemacht werden kann.
- Nach jeder Änderung meldet der Befehl ein `DataChange`; der `SceneRenderer` aktualisiert daraufhin nur die betroffenen Nodes.
- Nur Nodes, Marker und Auswahlringe im sichtbaren Bereich existieren als Grafikobjekte, damit auch Netze mit über 100 000 Nodes flüssig bleiben.
- Jedes Werkzeug ist eine `MapTool`-Unterklasse unter `ui/tools/` und wird in `ui/actions/tool_catalog.py` mit Symbol und Tastenkürzel beschrieben.
