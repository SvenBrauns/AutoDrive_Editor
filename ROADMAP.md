# Roadmap

Geplante Funktionen des AutoDrive FS25 Editors in der Reihenfolge, in der sie umgesetzt werden sollen. Erledigte Punkte werden abgehakt.

Bereits vorhanden: Laden von AutoDrive-XML, Karte und Heightmap; Werkzeugpanel mit Nodes erstellen (Regular/Subprio), Typ wechseln, verschieben, rotieren, löschen und verbinden (Regular/Dual/Reverse); Undo/Redo; Auswahl; Abstand- und Winkelmessung; Raster; Ansichtsrotation.

## 1. Marker — hohe Priorität

Neue Werkzeuggruppe `Marker`.

- [ ] Marker hinzufügen (an einer Node, Name und Gruppe)
- [ ] Marker bearbeiten (Name, Gruppe)
- [ ] Marker löschen
- [ ] Übersicht der Markergruppen
- [ ] Markernamen auf der Karte ein- und ausblenden
- [ ] alles rückgängig machbar

Für das spätere Speichern muss diese Phase schon beachten: Markergruppen sind eine eigene Liste mit ID (`<g i n>` im RoutesManager-Format). In der Savegame-Config ist die Reihenfolge der Marker zugleich ihre Nummer (`mm1`, `mm2`, …), auf die Fahrzeuge als Parkziel verweisen. Gruppenliste und Markerreihenfolge müssen deshalb im Datenmodell erhalten bleiben.

## 2. Schneller bearbeiten — hohe Priorität

- [ ] Kopieren, Ausschneiden, Einfügen (auch an der ursprünglichen Position)
- [ ] Werkzeug „Richtung umkehren“ (freier Platz neben „Typ wechseln“ im Panel)
- [ ] Ausrichten: horizontal, vertikal und in der Höhe
- [ ] Position einer Node als Zahlen eingeben
- [ ] Einrasten am Raster beim Erstellen und Verschieben
- [ ] Freihand-Auswahl (Lasso)

Hinweis zum Ausrichten: Die Werkzeuge müssen auch bei gedrehter Kartenansicht funktionieren. „Horizontal“ und „vertikal“ beziehen sich dann auf die Bildschirmachsen der aktuellen Ansicht, nicht auf die Kartenachsen. Das macht sie aufwendiger als die übrigen Punkte dieser Phase.

## 3. Linien und Kurven — mittlere Priorität

Neue Werkzeuggruppe für ganze Streckenabschnitte.

- [ ] gerade Linie mit gleichmäßigem Node-Abstand
- [ ] Bézierkurve
- [ ] Kreisbogen
- [ ] Höhen der neuen Nodes aus der Heightmap

## 4. Projekt und Anwendung — mittlere Priorität

- [ ] zuletzt geöffnete Dateien
- [ ] letztes Projekt beim Start wieder öffnen
- [ ] fehlende Projektdateien neu zuordnen
- [ ] Einstellungsdialog mit änderbaren Tastenkürzeln
- [ ] verständliche Fehlerdialoge
- [ ] Logging
- [ ] Laden über den RoutesManager: `routes.xml` öffnen, Route aus der Liste wählen (bevorzugter Weg, da AutoDrive Routen im laufenden Spiel neu laden kann)
- [ ] Laden der Savegame-Config (`AutoDrive_config.xml`)
- [ ] Kartenerkennung: Kartenname aus `routes.xml` (`map`) bzw. Savegame (`MapName`); passendes Kartenbild und Heightmap automatisch laden
- [ ] Kartenbild und Heightmap aus einem Mod-Zip importieren und für die Erkennung ablegen
- [ ] Kartengröße je Karte merken

## 5. Anzeige — niedrige Priorität

Neue Werkzeuggruppe oder Menü `Anzeige`.

- [ ] Nodes und einzelne Connection-Typen ein- und ausblenden
- [ ] Node-IDs anzeigen
- [ ] Mindest- und Höchstgröße von Nodes am Bildschirm
- [ ] Ansicht zurücksetzen
- [ ] dunkles Design
- [ ] Darstellungsoptionen dauerhaft speichern

## 6. Netz prüfen — sehr niedrige Priorität

Menü `Prüfen` mit einer Ergebnisliste, die zur jeweiligen Stelle springt.

- [ ] ungültige Verbindungsverweise
- [ ] Nodes ohne Verbindung
- [ ] übereinanderliegende Nodes zusammenführen
- [ ] Nodes außerhalb der Karte
- [ ] alle Höhen aus der Heightmap neu berechnen

## 7. Speichern — bewusst spät

Speichern kommt erst gegen Ende, damit jede Änderung vorher ohne Speichern getestet werden kann. Die Funktion ist aufwendiger als ein einfacher XML-Export; die Details werden unten unter „Hinweise zum Speichern“ gesammelt.

- [ ] Speichern und Speichern unter (AutoDrive-XML)
- [ ] Node-IDs lückenlos ab 1 vergeben und alle Verweise und Marker umschreiben
- [ ] Prüfung vor dem Speichern
- [ ] Sicherungskopie der Originaldatei
- [ ] Nachfrage bei ungespeicherten Änderungen vor dem Laden und Schließen
- [ ] Fenstertitel-`*` nach dem Speichern zurücksetzen (`EditHistory.mark_clean()`)
- [ ] Autosave

### Hinweise zum Speichern

Gespeichert wird in das Format, aus dem geladen wurde. Es gibt drei Wege:

**RoutesManager (bevorzugt)**

- `routes.xml` (Wurzel `autoDriveRoutesManager`) listet die Routen mit `name`, `fileName`, `map`, `revision`, `date` und `serverId`.
- Die Routendateien liegen im Unterordner `routes/` (Wurzel `routeExport`).
- `<waypoints c="Anzahl">` mit `x`, `y`, `z`, `out`, `in`, `flags`; Werte durch `;` getrennt, mehrere Verbindungen einer Node durch `,`, `-1` für keine Verbindung.
- Marker als `<markers><m i n g/>`, Markergruppen als `<groups><g i n/>`.
- AutoDrive kann Routen im laufenden Spiel neu laden; deshalb ist dies der bevorzugte Weg.
- Offen: ob beim Speichern `revision` und `date` in `routes.xml` angepasst werden müssen.

**Savegame-Config (`AutoDrive_config.xml`)**

- Wurzel `AutoDrive`; `version` bestimmt das Spiel (1 = FS19, 2 = FS22, 3 = FS25); `MapName` nennt die Karte.
- `<waypoints>` mit `id`, `x`, `y`, `z`, `out`, `incoming`, `flags`; Koordinaten und Flags durch `,` getrennt, Verbindungen je Node durch `;`, `-1` für keine Verbindung.
- Marker als `<mapmarker><mm1><id/><name/><group/></mm1>…`.
- Sehr alte Configs (vor AutoDrive 1.1.0.6, erkennbar an `markerID`) nur anzeigen, nicht bearbeiten.
- Speichern bearbeitet die vorhandene Datei, damit alle übrigen Einstellungen erhalten bleiben; fehlt `flags`, wird es ergänzt.
- `vehicles.xml` im selben Ordner: Fahrzeuge speichern ihr Parkziel als Markernummer (`parkDestination`, FS25 mit `uniqueId`). Ändert sich die Markerreihenfolge, müssen diese Verweise mit angepasst werden.
- Eine `terrain.heightmap.png` neben der Config ist die passende Heightmap.

**Einzelne XML-Datei**

- Kann jedes der beiden Formate enthalten; gespeichert wird im selben Format.

**Für alle Formate**

- Node-IDs sind die Positionen in den Listen; Lücken durch gelöschte Nodes müssen beim Speichern geschlossen und alle Verweise und Marker umgeschrieben werden.
- Flags `2` und `4` unverändert zurückschreiben.

## 8. Veröffentlichung — sobald Funktionsgleichheit mit dem alten Editor erreicht ist

Ziel ist, dass der Editor alles kann, was der bisherige AutoDrive Course Editor kann. Erst dann wird veröffentlicht.

- [ ] Liste der Funktionen des alten Editors abgleichen
- [ ] Lizenz festlegen
- [ ] Lizenzen der verwendeten Bibliotheken prüfen (PySide6/LGPL, Pillow)
- [ ] als Windows-Programm (.exe) bereitstellen
- [ ] Kartenbilder und Heightmaps der beliebtesten Karten für die Kartenerkennung mitliefern
- [ ] vorher klären, ob die Kartenbilder weitergegeben werden dürfen (Rechte bei Giants bzw. den Mod-Autoren); der alte Editor liefert keine Bilder mit, sondern verlinkt einen separaten Download
- [ ] englische README, optional englische Oberfläche

## Technische Punkte nebenher

Werden erledigt, wenn eine Phase den betroffenen Code ohnehin berührt.

- [ ] kurzer Hänger beim ersten Hineinzoomen über Zoom 1.0
- [ ] Heightmap-Werte zwischen Pixeln interpolieren statt den nächsten Pixel zu nehmen
- [ ] an Nodes gebundene Messpunkte folgen verschobenen Nodes
- [ ] leere Einträge in der `flags`-Liste der XML verschieben nachfolgende Flags
- [ ] Flags `2` und `4` (FS22/FS25: von AutoDrive aus Karten-Splines erzeugt) im Datenmodell unverändert behalten und als Regular anzeigen; bisher gilt jedes Flag ungleich `0` als Subprio
- [ ] `scene_renderer.py` aufteilen
