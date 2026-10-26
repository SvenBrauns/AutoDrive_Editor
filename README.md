# AutoDrive FS25 Editor

Editor für AutoDrive-Streckennetze im Landwirtschafts-Simulator 25. Er zeigt das Netz auf dem Kartenbild mit Geländehöhen und bietet Werkzeuge, um Nodes, Connections, Marker und ganze Streckenabschnitte zu bearbeiten. Alle Änderungen lassen sich rückgängig machen.

Der Editor unterstützt ausschließlich den LS25.

## Herunterladen

Die Windows-Version liegt als Zip unter [Releases](https://github.com/SvenBrauns/AutoDrive_Editor/releases). Entpacken und `AutoDrive Editor.exe` starten; eine Python-Installation ist nicht nötig.

## Erster Start

Der Editor sucht den LS25-Benutzerordner (üblicherweise `Dokumente\My Games\FarmingSimulator2025`) und den Installationsordner des Spiels und zeigt beide zur Prüfung an. Beide lassen sich später unter `Datei → Einstellungen` ändern.

Kartenbilder werden nicht mit dem Editor ausgeliefert. Mit `Karte → Karten scannen` durchsucht der Editor den `mods`-Ordner und die Grundspiel-Karten und importiert Kartenbild, Heightmap und Kartengröße. Das ist je Karte nur einmal nötig; danach wird die passende Karte beim Öffnen einer Route automatisch geladen. Fehlt sie, bietet der Editor den Scan direkt an.

## Netz öffnen

- **Route öffnen** (empfohlen): Routen aus dem RoutesManager von AutoDrive. AutoDrive kann sie im laufenden Spiel neu laden, das Spiel muss also nicht neu gestartet werden.
- **Savegame öffnen**: `AutoDrive_config.xml` eines Savegames. Die Heightmap des Savegames wird dabei mitgeladen.
- **XML-Datei öffnen**: eine einzelne Datei in einem der beiden Formate.

## Bedienung

- **Mausrad** zoomt, **linkes Ziehen** verschiebt die Karte, **mittleres Ziehen** dreht die Ansicht.
- **Rechte Maustaste** oder **Esc** bricht den laufenden Schritt eines Werkzeugs ab, **Enter** bestätigt ihn (z. B. bei Kurven).
- Die Werkzeuge stehen im Werkzeugpanel; die Statusleiste zeigt, was das aktive Werkzeug erwartet.

| Werkzeug | Taste | |
| --- | --- | --- |
| Navigation | `N` | Karte verschieben und drehen |
| Auswahl | `A` | Klick oder Rechtsziehen; Umschalt+Rechtsziehen für Freihand-Auswahl, Strg ergänzt |
| Verschieben | `V` | Node oder Auswahl ziehen |
| Rotieren | `R` | Auswahl am Ring drehen (Umschalt: 15°-Schritte) |
| Erstellen Regular / Subprio | `E` / `Umschalt+E` | Node auf freier Fläche erstellen |
| Typ wechseln | `T` | zwischen Regular und Subprio umschalten |
| Löschen | `L` | Node oder Auswahl löschen |
| Verbinden Regular / Dual / Reverse | `1` / `2` / `3` | Nodes nacheinander anklicken |
| Richtung umkehren | `U` | Connection anklicken; in der Auswahl alle Connections der Auswahl |
| Position eingeben | `P` | X/Y/Z einer Node als Zahlen eingeben |
| Horizontal / vertikal ausrichten | `H` / `J` | Auswahl auf die Linie durch eine Referenz-Node legen |
| Höhe wie Referenz / aus Heightmap | `Y` / `Umschalt+Y` | Höhen der Auswahl setzen |
| Linie | `I` | gerade Strecke mit gleichmäßigem Node-Abstand |
| Bézierkurve / Kreisbogen | `B` / `K` | Start und Ende anklicken, Griffe ziehen, Enter |
| Marker hinzufügen / bearbeiten | `M` / `Umschalt+M` | Name und Gruppe eingeben |
| Marker verschieben / löschen | `Strg+M` / `Strg+Umschalt+M` | Marker auf andere Node legen oder entfernen |

Außerdem: Rückgängig und Wiederholen (`Strg+Z` / `Strg+Y`), Kopieren, Ausschneiden und Einfügen (`Strg+C/X/V`, `Strg+Umschalt+V` fügt an der ursprünglichen Stelle ein), Raster mit Einrasten (`G`), Abstand- und Winkelmessung sowie der Dock `Marker` mit allen Markergruppen.

## Speichern

`Datei → Speichern` (`Strg+S`) schreibt in das Format und die Datei, aus der geladen wurde. Vor dem ersten Überschreiben legt der Editor eine Sicherungskopie (`.bak`) an. Bei Savegames werden die Markerziele der Fahrzeuge in `vehicles.xml` mit angepasst.

`Speichern unter` legt Routen als neue Route im RoutesManager an.

Ungespeicherte Änderungen werden alle paar Minuten automatisch gesichert (Abstand unter `Datei → Einstellungen`). Endet der Editor unerwartet, bietet er sie beim nächsten Start zur Wiederherstellung an.

## Lizenz

GNU General Public License v3.0 oder später, siehe [LICENSE](LICENSE). Die Windows-Version enthält PySide6/Qt (LGPLv3) und Pillow, siehe [THIRD_PARTY_NOTICES.md](packaging/THIRD_PARTY_NOTICES.md).

Der Editor enthält keine Dateien aus dem Landwirtschafts-Simulator oder aus Karten-Mods; Kartenbilder und Heightmaps werden aus der eigenen Installation gelesen. Das Projekt steht in keiner Verbindung zu GIANTS Software.

Zum Mitentwickeln siehe [DEVELOPMENT.md](DEVELOPMENT.md).
