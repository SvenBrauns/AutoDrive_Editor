# Entwicklung

Hinweise für die Arbeit am Code des AutoDrive FS25 Editors. Die Anleitung für Nutzer steht in der [README](README.md), geplante Funktionen in der [Roadmap](ROADMAP.md).

## Aus dem Quellcode starten

```text
pip install -r requirements.txt
python main.py
```

oder `python -m autodrive_editor`.

## Tests und Prüfungen

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

## Dateiformate beim Speichern

Gespeichert wird in das Format, aus dem geladen wurde.

**RoutesManager**: `routes.xml` (Wurzel `autoDriveRoutesManager`) listet die Routen mit `name`, `fileName`, `map`, `revision`, `date` und `serverId`; die Routendateien liegen in `routes/` (Wurzel `routeExport`). `<waypoints c="Anzahl">` mit `x`, `y`, `z`, `out`, `in`, `flags`: Werte durch `;`, mehrere Verbindungen einer Node durch `,`, `-1` für keine Verbindung. Marker als `<markers><m i n g/>`, Gruppen als `<groups><g i n/>`. Beim Speichern bekommt der Eintrag in `routes.xml` `revision` + 1 und das aktuelle Datum.

**Savegame-Config** (`AutoDrive_config.xml`, Wurzel `AutoDrive`, `version` 3 = FS25): `<waypoints>` mit `id`, `x`, `y`, `z`, `out`, `incoming`, `flags`: Werte durch `,`, Verbindungen je Node durch `;`. Marker als `<mapmarker><mm1><id/><name/><group/></mm1>…`; die Reihenfolge ist zugleich die Markernummer. Gespeichert wird in die vorhandene Datei, damit alle übrigen Einstellungen erhalten bleiben. Fahrzeuge in `vehicles.xml` verweisen per Markernummer auf Ziele (`firstMarker`, `secondMarker`, `parkDestination`); ändert sich die Reihenfolge, werden diese Verweise angepasst.

**Für alle Formate**: Koordinaten mit drei (Savegame) bzw. zwei (Route) Nachkommastellen. Node-IDs sind die Positionen in den Listen; Lücken durch gelöschte Nodes werden beim Speichern geschlossen und alle Verweise und Marker umgeschrieben. Flags werden unverändert zurückgeschrieben (auch `2` und `4`), außer der Typ einer Node wurde geändert.

## Leistung (Testnetz mit 113 058 Nodes und 116 260 Connections)

Bewährt: native `QGraphicsEllipseItem`-Nodes, Grafikobjekte nur für den sichtbaren Bereich plus Puffer (Kacheln 256 m, Puffer 128 m), drei gebündelte globale Connection-Pfade, räumliche Indizes, Auswahl nur als Node-IDs, getrennte Vorschau- und Endauswahl.

Nicht geeignet: eigenes `paint()` pro Node, dauerhaft alle NodeItems, ein Grafikobjekt pro Connection, große gespeicherte Pfeilpfade, dauerhafte Auswahlringe für alle ausgewählten Nodes.
