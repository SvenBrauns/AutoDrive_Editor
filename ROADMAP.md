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
- [ ] Karten automatisch erkennen oder aus einem Mod-Zip importieren

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

_Noch zu ergänzen._

## 8. Veröffentlichung — sobald Funktionsgleichheit mit dem alten Editor erreicht ist

Ziel ist, dass der Editor alles kann, was der bisherige AutoDrive Course Editor kann. Erst dann wird veröffentlicht.

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
- [ ] leere Einträge in der `flags`-Liste der XML verschieben nachfolgende Flags
- [ ] `scene_renderer.py` aufteilen
