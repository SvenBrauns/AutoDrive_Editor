# Roadmap

Geplante Funktionen des AutoDrive FS25 Editors in der Reihenfolge, in der sie umgesetzt werden sollen. Erledigte Punkte werden abgehakt.

Der Editor unterstützt ausschließlich den Landwirtschafts-Simulator 25.

## 1. Abgleich mit dem alten Editor — hohe Priorität

Ziel ist, dass der Editor alles kann, was der bisherige AutoDrive Course Editor für FS25 kann. Das Ergebnis des Abgleichs bestimmt, welche Funktionen noch in diese Roadmap kommen.

- [ ] Liste der Funktionen des alten Editors abgleichen und fehlende Funktionen hier eintragen

## 2. Netz prüfen — hohe Priorität

Menü `Prüfen` mit einer Ergebnisliste, die zur jeweiligen Stelle springt. Dieselbe Prüfung läuft vor dem Speichern: Gefundene Probleme werden angezeigt, gespeichert werden kann trotzdem.

- [ ] ungültige Verbindungsverweise
- [ ] Nodes ohne Verbindung
- [ ] übereinanderliegende Nodes zusammenführen
- [ ] Nodes außerhalb der Karte
- [ ] alle Höhen aus der Heightmap neu berechnen
- [ ] Prüfung vor dem Speichern

## 3. Projekt und Anwendung — mittlere Priorität

- [ ] zuletzt geöffnete Routen, Savegames und Dateien (Menü `Datei` und Startseite)
- [ ] zuletzt Geöffnetes beim Start wieder öffnen
- [ ] verständliche Fehlerdialoge

## 4. Englische Oberfläche — mittlere Priorität

AutoDrive wird international genutzt; für die Veröffentlichung sollte der Editor auch auf Englisch bedienbar sein.

- [ ] Oberfläche auf Englisch umschaltbar (Sprache in den Einstellungen)
- [ ] englische README

## 5. Anzeige — niedrige Priorität

Neue Darstellungsoptionen werden dauerhaft gespeichert.

- [ ] Nodes und einzelne Connection-Typen ein- und ausblenden
- [ ] Node-IDs anzeigen
- [ ] Mindest- und Höchstgröße von Nodes am Bildschirm

## 6. Veröffentlichung — sobald Funktionsgleichheit mit dem alten Editor erreicht ist

- [x] Lizenz festlegen
- [x] Lizenzen der verwendeten Bibliotheken prüfen (PySide6/LGPL, Pillow)
- [x] als Windows-Programm (.exe) bereitstellen
- [ ] alle Punkte aus Phase 1 umgesetzt

## Technische Punkte nebenher

Werden erledigt, wenn eine Phase den betroffenen Code ohnehin berührt.

- [ ] kurzer Hänger beim ersten Hineinzoomen über Zoom 1.0
- [ ] Heightmap-Werte zwischen Pixeln interpolieren statt den nächsten Pixel zu nehmen
- [ ] an Nodes gebundene Messpunkte folgen verschobenen Nodes
- [ ] `scene_renderer.py` aufteilen
