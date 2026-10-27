# AutoDrive FS25 Editor

[English](README.md) | **Deutsch**

Editor für AutoDrive-Routennetze im Landwirtschafts-Simulator 25. Er zeigt das Netz auf dem Kartenbild mit Geländehöhen und bietet Werkzeuge, um Nodes, Connections, Marker und ganze Streckenabschnitte zu bearbeiten. Alle Änderungen lassen sich rückgängig machen.

Der Editor unterstützt nur den LS25.

## Download

Die Windows-Version gibt es als Zip unter [Releases](https://github.com/SvenBrauns/AutoDrive_Editor/releases). Entpacken und `AutoDrive Editor.exe` starten. Eine Python-Installation ist nicht nötig.

## Sprache

Den Editor gibt es auf Deutsch und Englisch. Beim ersten Start ist er auf einem deutschen Windows deutsch, sonst englisch. Die Sprache lässt sich unter `Datei → Einstellungen` ändern; sie wirkt nach einem Neustart.

## Erster Start

Der Editor sucht den LS25-Benutzerordner (meist `Dokumente\My Games\FarmingSimulator2025`) und den Installationsordner des Spiels und zeigt beide zur Kontrolle an. Beide lassen sich später unter `Datei → Einstellungen` ändern.

Kartenbilder werden nicht mit dem Editor ausgeliefert. Über `Karte → Karten scannen` durchsucht der Editor den `mods`-Ordner und die Grundspiel-Karten und importiert Kartenbild, Heightmap und Kartengröße. Das ist pro Karte nur einmal nötig. Danach lädt beim Öffnen einer Route automatisch die passende Karte. Fehlt die Karte, bietet der Editor den Scan direkt an.

## Netz öffnen

- **Route öffnen** (empfohlen): Routen aus dem RoutesManager von AutoDrive. AutoDrive kann sie im laufenden Spiel neu laden, das Spiel muss also nicht neu gestartet werden.
- **Savegame öffnen**: die `AutoDrive_config.xml` eines Savegames. Die Heightmap des Savegames wird mitgeladen.
- **XML-Datei öffnen**: eine einzelne Datei in einem der beiden Formate.

## Bedienung

- **Mausrad** zoomt, **linkes Ziehen** verschiebt die Karte, **mittleres Ziehen** dreht die Ansicht.
- **Rechtsklick** oder **Esc** bricht den aktuellen Schritt eines Werkzeugs ab; **Enter** bestätigt ihn (zum Beispiel bei Kurven).
- Die Werkzeuge liegen im Werkzeugbereich; die Statusleiste zeigt, was das aktive Werkzeug als Nächstes erwartet. Werkzeuge mit Optionen haben auf ihrem Knopf einen kleinen Pfeil, der sie öffnet.

| Werkzeug | Taste | Was es tut |
| --- | --- | --- |
| Navigation | `N` | Karte verschieben und drehen |
| Auswahl | `A` | Per Klick oder Rechtsziehen auswählen; Umschalt + Rechtsziehen für freie Auswahl; Strg ergänzt die Auswahl |
| Verschieben | `V` | Node oder Auswahl ziehen; Umschalt bewegt nur entlang einer Rasterachse |
| Rotieren | `R` | Auswahl am Ring drehen; Umschalt rastet in Schritten ein (Standard 15°, über den Pfeil einstellbar) |
| Erstellen (Regular / Subprio) | `E` / `Umschalt+E` | Node auf freier Fläche erstellen |
| Typ wechseln | `T` | Zwischen Regular und Subprio wechseln |
| Löschen | `L` | Node oder Auswahl löschen |
| Verbinden (Regular / Dual / Reverse) | `1` / `2` / `3` | Nodes nacheinander anklicken, um sie zu verbinden |
| Richtung umkehren | `U` | Connection anklicken, um sie umzukehren; in einer Auswahl werden alle Connections der Auswahl umgekehrt |
| Position eingeben | `P` | X/Y/Z einer Node als Zahlen eingeben |
| Horizontal / vertikal ausrichten | `H` / `J` | Auswahl auf die Linie durch eine Referenz-Node legen |
| Höhe wie Referenz / Höhe aus Heightmap | `Y` / `Umschalt+Y` | Höhen der Auswahl setzen |
| Linie | `I` | Gerader Streckenabschnitt mit gleichmäßigem Node-Abstand (Abstand, Connection-Art und Node-Typ unter dem Pfeil) |
| Bézierkurve / Kreisbogen | `B` / `K` | Start und Ende anklicken, Griffe ziehen, Enter drücken; die Bézierkurve hat einen oder zwei Kontrollpunkte |
| Marker hinzufügen / bearbeiten | `M` / `Umschalt+M` | Marker hinzufügen oder bearbeiten; Name und Gruppe eingeben |
| Marker verschieben / löschen | `Strg+M` / `Strg+Umschalt+M` | Marker auf eine andere Node verschieben oder löschen |

Außerdem: Rückgängig und Wiederholen (`Strg+Z` / `Strg+Y`), Kopieren, Ausschneiden und Einfügen (`Strg+C/X/V`; `Strg+Umschalt+V` fügt an der Originalposition ein), das Raster mit Einrasten (`G`), Abstands- und Winkelmessung sowie das Fenster `Marker` mit allen Markergruppen.

## Darstellung

`Ansicht → Anzeigen` blendet Nodes, Node-IDs, jede Connection-Art (Regular, Dual, Reverse, Subprio), Marker, Markernamen und die Parkpositionen der Fahrzeuge ein und aus. Subprio-Connections sind die, die in eine Subprio-Node führen. Node-IDs erscheinen erst beim Hineinzoomen; Parkpositionen (ein „P“ neben dem Marker) werden aus der `vehicles.xml` eines Spielstands gelesen. Ausgeblendete Nodes und Connections lassen sich nur anklicken und auswählen, wenn `Ausgeblendete Elemente auswählbar` an ist. Größen und Farben stellt man unter `Ansicht → Darstellungsoptionen` ein. Alle Einstellungen bleiben gespeichert.

## Netz prüfen

`Prüfen → Netz prüfen` listet übereinanderliegende Nodes, Nodes außerhalb der Karte und, wenn eine Heightmap geladen ist, Nodes, deren Höhe zu stark vom Gelände abweicht. Der Abstand für übereinanderliegende Nodes und der erlaubte Höhenunterschied werden oben im Fenster eingestellt. Ein Klick auf einen Eintrag zeigt ihn auf der Karte. `Auswahl beheben` oder `Alle beheben` führt übereinanderliegende Nodes zu einer zusammen (die Node mit Marker, sonst die mit der kleinsten ID), verschiebt Nodes zurück auf die Karte und setzt Höhen aus der Heightmap. Jede Art von Korrektur ist ein Rückgängig-Schritt.

Einträge, die so in Ordnung sind, etwa Nodes auf einer Brücke, lassen sich mit `Ignorieren` ausblenden. Sie wandern in die Gruppe `Ignoriert` und werden von `Alle beheben` nicht verändert; `Nicht ignorieren` holt sie zurück. Ein ignorierter Eintrag erscheint auch wieder, wenn eine seiner Nodes verschoben wird. Mit den Kontrollkästchen lässt sich eine ganze Prüfung ausschalten. Ignorierte Einträge und ausgeschaltete Prüfungen werden für jede Route und jedes Savegame gespeichert.

## Speichern

`Datei → Speichern` (`Strg+S`) schreibt in dasselbe Format und dieselbe Datei, aus der geladen wurde. Vor dem ersten Überschreiben legt der Editor eine Sicherungskopie (`.bak`) an. Bei Savegames werden auch die Markerziele der Fahrzeuge in der `vehicles.xml` angepasst.

`Speichern unter` speichert eine Route als neue Route im RoutesManager.

Ungespeicherte Änderungen werden alle paar Minuten automatisch gesichert (Abstand unter `Datei → Einstellungen`). Wird der Editor unerwartet beendet, bietet er beim nächsten Start an, sie wiederherzustellen.

`Datei → Zuletzt geöffnet` und der Startbildschirm listen die letzten fünf geöffneten Routen, Savegames, XML-Dateien und Projekte.

## Hilfe und Fehler

`Hilfe → Versionsverlauf` zeigt, was sich in jeder Version geändert hat (auf Englisch), `Hilfe → Über` zeigt Version und Lizenz. Tritt ein unerwarteter Fehler auf, zeigt der Editor eine Meldung und läuft weiter. Die Details landen in einer Log-Datei (`Hilfe → Log-Ordner öffnen`, in `%APPDATA%\AutoDrive Editor\logs`); bitte bei Fehlermeldungen anhängen.

## Lizenz

GNU General Public License v3.0 oder neuer, siehe [LICENSE](LICENSE). Die Windows-Version enthält PySide6/Qt (LGPLv3) und Pillow, siehe [THIRD_PARTY_NOTICES.md](packaging/THIRD_PARTY_NOTICES.md).

Der Editor enthält keine Dateien aus dem Landwirtschafts-Simulator oder aus Kartenmods. Kartenbilder und Heightmaps werden aus der eigenen Installation gelesen. Dieses Projekt steht in keiner Verbindung zu GIANTS Software.

Hinweise zur Entwicklung (auf Englisch) stehen in [DEVELOPMENT.md](DEVELOPMENT.md).
