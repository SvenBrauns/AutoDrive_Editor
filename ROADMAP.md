# Roadmap

Geplante Funktionen des AutoDrive FS25 Editors in der Reihenfolge, in der sie umgesetzt werden sollen. Erledigte Punkte werden abgehakt.

Der Editor unterstützt ausschließlich den Landwirtschafts-Simulator 25.

Bereits vorhanden: Laden einer RoutesManager-Routendatei, Karte und Heightmap von Hand; Werkzeugpanel mit Nodes erstellen (Regular/Subprio), Typ wechseln, verschieben, rotieren, löschen und verbinden (Regular/Dual/Reverse); Undo/Redo; Auswahl; Abstand- und Winkelmessung; Raster; Ansichtsrotation.

## 1. Laden und Karten — hohe Priorität

Damit alle folgenden Funktionen mit echten Spieldaten getestet werden können.

**Spielordner**

- [x] FS25-Benutzerordner (üblicherweise `Dokumente\My Games\FarmingSimulator2025`) automatisch finden und in den Einstellungen änderbar machen

**Routen und Savegames**

- [x] RoutesManager: Routenliste direkt aus dem Spielordner anzeigen und eine Route laden (bevorzugter Weg, da AutoDrive Routen im laufenden Spiel neu laden kann)
- [x] Savegame-Config: Liste der Savegames anzeigen und `AutoDrive_config.xml` laden
- [x] einzelne XML-Datei weiterhin von Hand öffnen
- [x] nur FS25-Configs annehmen (`version` 3), sonst verständliche Meldung

**Karten**

- [x] Kartenname aus `routes.xml` (`map`) bzw. aus der Savegame-Config (`MapName`) lesen
- [x] Mod-Zip einer Karte importieren: Kartenbild und Heightmap auslesen und im Datenordner des Editors ablegen (z. B. `%APPDATA%\AutoDrive Editor\maps\<Kartenname>\`), zusammen mit der Kartengröße
- [x] Schaltfläche „Karten scannen“: `mods`-Ordner nach Kartenmods durchsuchen (Zips und entpackte Ordner) und zum Import anbieten; bereits importierte Karten kennzeichnen
- [ ] beim Laden einer Route oder eines Savegames die passende importierte Karte automatisch laden
- [ ] Savegame: `terrain.heightmap.png` neben der Config als Heightmap verwenden
- [ ] Kartengröße aus der Kartenkonfiguration im Mod übernehmen statt sie von Hand zu wählen
- [ ] Prüfen, ob die Grundspiel-Karten aus dem Installationsordner lesbar sind; vermutlich liegen sie in einem Archivformat von Giants und können nicht importiert werden

Kartenbilder werden nicht mit dem Editor ausgeliefert. Jeder Nutzer erzeugt sie aus seinen eigenen Mods; einmal importiert, werden sie ohne erneuten Zip-Import wiederverwendet.

**Flags**

- [x] unbekannte Flag-Werte unverändert im Datenmodell behalten, wie Regular-Nodes darstellen und von „Typ wechseln“ ausnehmen (bisher gilt jedes Flag ungleich `0` als Subprio)

Laut altem Editor stehen die Flags `2` und `4` für Nodes, die AutoDrive aus Karten-Splines erzeugt. In echten FS25-Daten kommen sie nicht vor: Alle sieben Routen im RoutesManager und die Savegame-Config enthalten nur `0` und `1`. Eine eigene Behandlung ist deshalb nicht nötig; unbekannte Werte werden lediglich erhalten.

**Erkenntnisse aus einer echten FS25-Installation**

- RoutesManager: `<FS25-Ordner>\modSettings\FS25_AutoDrive\routesManager\routes.xml`, Routendateien im Unterordner `routes\`. AutoDrive legt dort eigene Autosaves ab (`<Datei>_autosave_<n>.xml`); sie gehören nicht in die Routenliste.
- `routes.xml`: je Route `name`, `fileName`, `map`, `revision`, `date` (`JJJJ/MM/TT hh:mm:ss`) und `<serverId/>`. `revision` steigt bei jedem Speichern im Spiel.
- Savegame: `savegameN\AutoDrive_config.xml` mit `version` z. B. `3.0.1.4` (FS25 = Hauptversion 3) und `MapName`; daneben liegen `terrain.heightmap.png` und `vehicles.xml`.
- Kartenname: AutoDrive verwendet den Kartentitel aus der `modDesc.xml` des Kartenmods (`<maps><map><title>`), Leerzeichen und Punkte durch `_` ersetzt, z. B. `LS25 Thüringen 2.0 16x` → `LS25_Thüringen_2_0_16x`. Der Titel kann in mehreren Sprachen vorliegen; verglichen wird mit allen. Zip-Name und Karten-ID (oft `SampleModMap`) taugen nicht zur Zuordnung.
- Kartenmod: `modDesc.xml` → `<map configFilename>` → Kartenkonfiguration mit `width`/`height` (z. B. 8192) und `imageFilename`. Kartengröße = `width / 2048` (4096 → 2 = 4x-Karte, 8192 → 4 = 16x-Karte).
- Ein Mod kann mehrere Karten enthalten; der `mods`-Ordner kann auch nicht lesbare Zips enthalten, die beim Scan übersprungen werden.

## 2. Marker — hohe Priorität

Neue Werkzeuggruppe `Marker`.

- [ ] Marker hinzufügen (an einer Node, Name und Gruppe)
- [ ] Marker bearbeiten (Name, Gruppe)
- [ ] Marker löschen
- [ ] Übersicht der Markergruppen
- [ ] Markernamen auf der Karte ein- und ausblenden
- [ ] alles rückgängig machbar

Für das spätere Speichern muss diese Phase schon beachten: Markergruppen sind eine eigene Liste mit ID (`<g i n>` im RoutesManager-Format). In der Savegame-Config ist die Reihenfolge der Marker zugleich ihre Nummer (`mm1`, `mm2`, …), auf die Fahrzeuge als Parkziel verweisen. Gruppenliste und Markerreihenfolge müssen deshalb im Datenmodell erhalten bleiben.

## 3. Schneller bearbeiten — hohe Priorität

- [ ] Kopieren, Ausschneiden, Einfügen (auch an der ursprünglichen Position)
- [ ] Werkzeug „Richtung umkehren“ (freier Platz neben „Typ wechseln“ im Panel)
- [ ] Ausrichten: horizontal, vertikal und in der Höhe
- [ ] Position einer Node als Zahlen eingeben
- [ ] Einrasten am Raster beim Erstellen und Verschieben
- [ ] Freihand-Auswahl (Lasso)

Hinweis zum Ausrichten: Die Werkzeuge müssen auch bei gedrehter Kartenansicht funktionieren. „Horizontal“ und „vertikal“ beziehen sich dann auf die Bildschirmachsen der aktuellen Ansicht, nicht auf die Kartenachsen. Das macht sie aufwendiger als die übrigen Punkte dieser Phase.

## 4. Linien und Kurven — mittlere Priorität

Neue Werkzeuggruppe für ganze Streckenabschnitte.

- [ ] gerade Linie mit gleichmäßigem Node-Abstand
- [ ] Bézierkurve
- [ ] Kreisbogen
- [ ] Höhen der neuen Nodes aus der Heightmap

## 5. Projekt und Anwendung — mittlere Priorität

- [ ] zuletzt geöffnete Routen, Savegames und Dateien
- [ ] zuletzt Geöffnetes beim Start wieder öffnen
- [ ] fehlende Projektdateien neu zuordnen
- [ ] Einstellungsdialog mit änderbaren Tastenkürzeln
- [ ] verständliche Fehlerdialoge
- [ ] Logging

## 6. Anzeige — niedrige Priorität

Neue Werkzeuggruppe oder Menü `Anzeige`.

- [ ] Nodes und einzelne Connection-Typen ein- und ausblenden
- [ ] Node-IDs anzeigen
- [ ] Mindest- und Höchstgröße von Nodes am Bildschirm
- [ ] Ansicht zurücksetzen
- [ ] dunkles Design
- [ ] Darstellungsoptionen dauerhaft speichern

## 7. Netz prüfen — sehr niedrige Priorität

Menü `Prüfen` mit einer Ergebnisliste, die zur jeweiligen Stelle springt.

- [ ] ungültige Verbindungsverweise
- [ ] Nodes ohne Verbindung
- [ ] übereinanderliegende Nodes zusammenführen
- [ ] Nodes außerhalb der Karte
- [ ] alle Höhen aus der Heightmap neu berechnen

## 8. Speichern — bewusst spät

Speichern kommt erst gegen Ende, damit jede Änderung vorher ohne Speichern getestet werden kann. Die Funktion ist aufwendiger als ein einfacher XML-Export; die Details stehen unten unter „Hinweise zum Speichern“.

- [ ] Speichern und Speichern unter, jeweils im Format, aus dem geladen wurde
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
- Offen: ob beim Speichern `revision` und `date` in `routes.xml` angepasst werden müssen. Wird geklärt, wenn diese Phase ansteht.

**Savegame-Config (`AutoDrive_config.xml`)**

- Wurzel `AutoDrive`; `version` 3 steht für FS25; `MapName` nennt die Karte.
- `<waypoints>` mit `id`, `x`, `y`, `z`, `out`, `incoming`, `flags`; Koordinaten und Flags durch `,` getrennt, Verbindungen je Node durch `;`, `-1` für keine Verbindung.
- Marker als `<mapmarker><mm1><id/><name/><group/></mm1>…`.
- Speichern bearbeitet die vorhandene Datei, damit alle übrigen Einstellungen erhalten bleiben; fehlt `flags`, wird es ergänzt.
- `vehicles.xml` im selben Ordner: Fahrzeuge speichern ihr Parkziel als Markernummer (`parkDestination`, Fahrzeug über `uniqueId`). Ändert sich die Markerreihenfolge, müssen diese Verweise mit angepasst werden.

**Einzelne XML-Datei**

- Enthält eines der beiden Formate; gespeichert wird im selben Format.

**Für alle Formate**

- Genauigkeit wie im Original: Savegame-Configs speichern Koordinaten mit drei Nachkommastellen, Routendateien mit zwei.
- Node-IDs sind die Positionen in den Listen; Lücken durch gelöschte Nodes müssen beim Speichern geschlossen und alle Verweise und Marker umgeschrieben werden.
- Flags `2` und `4` je nach Ergebnis der Klärung in Phase 1 zurückschreiben.

## 9. Veröffentlichung — sobald Funktionsgleichheit mit dem alten Editor erreicht ist

Ziel ist, dass der Editor alles kann, was der bisherige AutoDrive Course Editor für FS25 kann. Erst dann wird veröffentlicht.

- [ ] Liste der Funktionen des alten Editors abgleichen
- [ ] Lizenz festlegen
- [ ] Lizenzen der verwendeten Bibliotheken prüfen (PySide6/LGPL, Pillow)
- [ ] als Windows-Programm (.exe) bereitstellen
- [ ] englische README, optional englische Oberfläche

## Technische Punkte nebenher

Werden erledigt, wenn eine Phase den betroffenen Code ohnehin berührt.

- [ ] kurzer Hänger beim ersten Hineinzoomen über Zoom 1.0
- [ ] Heightmap-Werte zwischen Pixeln interpolieren statt den nächsten Pixel zu nehmen
- [ ] an Nodes gebundene Messpunkte folgen verschobenen Nodes
- [x] leere Einträge in der `flags`-Liste der XML verschieben nachfolgende Flags
- [ ] `scene_renderer.py` aufteilen
