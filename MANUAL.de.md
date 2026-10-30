# AutoDrive FS25 Editor – Anleitung

[English](MANUAL.md) | **Deutsch** · zurück zur [README](README.de.md)

- [Erster Start](#erster-start)
- [Netz öffnen](#netz-öffnen)
- [Bedienung](#bedienung)
- [Darstellung](#darstellung)
- [Parkplätze in Hallen](#parkplätze-in-hallen)
- [Netz prüfen](#netz-prüfen)
- [Speichern](#speichern)
- [Einstellungen](#einstellungen)
- [Hilfe und Fehler](#hilfe-und-fehler)

## Erster Start

Der Editor sucht den LS25-Benutzerordner (meist `Dokumente\My Games\FarmingSimulator2025`) und den Installationsordner des Spiels und zeigt beide zur Kontrolle an. Beide lassen sich später unter `Datei → Einstellungen` ändern.

Kartenbilder werden nicht mit dem Editor ausgeliefert. Über `Karte → Karten scannen` durchsucht der Editor den `mods`-Ordner und die Grundspiel-Karten und importiert Kartenbild, Heightmap und Kartengröße. Das ist pro Karte nur einmal nötig. Danach lädt beim Öffnen einer Route automatisch die passende Karte. Fehlt die Karte, bietet der Editor den Scan direkt an.

**Bodenkarte.** `Ansicht → Bodenkarte` ersetzt das Kartenbild durch eine Karte, die aus den Bodentexturen der Karte gezeichnet ist: Asphalt, Beton, Schotter, Gras, Matsch, Wald, Fels und Sand je in einer eigenen Farbe, darüber die Feldgrenzen und Feldnummern. Sie zeigt die Karte so, wie das Spiel sie bemalt, was hilft, wo das Kartenbild veraltet ist. Mit einer älteren Version des Editors importierte Karten haben keine Bodenkarte; dafür die Karte neu importieren. Der Import einer großen Karte dauert dadurch etwas länger (etwa 15 Sekunden bei einer 16x-Karte).

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
| Parkplätze | `S` | Eine Halle anklicken, um darin Parkplätze anzulegen, siehe [Parkplätze in Hallen](#parkplätze-in-hallen) |
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

## Planungsmodus

Der Planungsknopf am rechten Ende der Werkzeugleiste (`Bearbeiten → Planungsmodus`, `Strg+P`) beginnt einen Plan. Alle Werkzeuge arbeiten wie gewohnt, die Änderungen werden aber im Plan gesammelt: Ein blauer Balken über der Karte zeigt, wie viele Nodes der Plan geändert hat, und diese Nodes bekommen einen blauen Hof. Rückgängig und Wiederholen arbeiten innerhalb des Plans und halten an seinem Anfang. `Plan übernehmen` fügt den ganzen Plan als einen Rückgängig-Schritt in den Verlauf ein; `Plan verwerfen` nimmt ihn vollständig zurück. Ein weiterer Klick auf den Planungsknopf, das Öffnen einer anderen Datei oder das Schließen des Editors fragt, ob der Plan übernommen oder verworfen werden soll. Solange ein Plan offen ist, kann nicht gespeichert werden und die automatische Sicherung pausiert.

**Route finden.** Im Planungsmodus zwei Nodes auswählen und auf dem Planungsbalken `Route finden` klicken (`Bearbeiten → Route finden`, `Strg+R`). Der Editor baut eine befahrbare Einbahn-Route vom zuerst ausgewählten Node zum zuletzt angeklickten. Sie fährt nur vorwärts, keine engeren Kurven als den kleinsten Wenderadius und hält die halbe Fahrzeugbreite plus einen Sicherheitsabstand von Gebäuden, Zäunen, Bäumen und Wasser fern; diese Werte stellt man unter `Datei → Einstellungen → Routensuche` ein. Sie bleibt, wo es geht, auf Straßen und Höfen, fährt eher über Gras als über Felder und verlässt und erreicht jeden Node in der Richtung seiner Connections. Nahe den beiden Nodes und in ihrer Richtung darf gesperrter Boden befahren werden, da Nodes unter einem Dach oder in einer Halle liegen können. Die Suche läuft im Hintergrund; die Route kommt als ein Rückgängig-Schritt in den Plan. Um eine Route zu ändern, sie löschen, Nodes setzen, wo sie entlangführen soll, und die Route neu finden.

Routen, die schon im Plan sind, werden mitbenutzt: Eine Route in derselben Richtung schließt sich ihnen an. Der Rückweg (die Nodes andersherum auswählen) bekommt eine eigene Spur, wo Platz ist; wo nicht, teilt er sich die Spur, die dort Dual wird. Ist gar kein Platz zum Wenden, meldet der Editor, dass keine befahrbare Route gefunden wurde.

Die Routensuche nutzt die Befahrbarkeitskarte des Spiels, die der Landwirtschafts-Simulator bei jedem Speichern in den Spielstand schreibt (`vehicleNavigationCostmap.dat`). Eine Route braucht dafür ein verknüpftes Savegame. Nach dem Platzieren von Gebäuden erneut im Spiel speichern, damit die Karte sie kennt. `Ansicht → Anzeigen → Befahrbarkeitskarte` zeichnet sie: gesperrter Boden rot (in Wäldern blau), unwegsamer Boden orange, Gras gelb, Felder grün; Straßen und Höfe bleiben frei.

## Darstellung

`Ansicht → Anzeigen` blendet Nodes, Node-IDs, jede Connection-Art (Regular, Dual, Reverse), Marker, Markernamen, die Parkpositionen der Fahrzeuge, Hallen, Stationen und die Befahrbarkeitskarte (siehe [Planungsmodus](#planungsmodus)) ein und aus. Die Linienfarbe zeigt die Connection-Art, Pfeile zeigen die Richtung; Dual-Connections bekommen zu jedem Ende einen. Subprio-Nodes sind orange. Node-IDs erscheinen erst beim Hineinzoomen; Parkpositionen (ein „P“ neben dem Marker) werden aus der `vehicles.xml` eines Spielstands gelesen. Eine Route braucht dafür ein verknüpftes Savegame, siehe [Parkplätze in Hallen](#parkplätze-in-hallen); dort sind auch die Hallen erklärt. Ausgeblendete Nodes und Connections lassen sich nur anklicken und auswählen, wenn `Ausgeblendete Elemente auswählbar` an ist. Größen und Farben stellt man unter `Ansicht → Darstellungsoptionen` ein. Alle Einstellungen bleiben gespeichert.

## Parkplätze in Hallen

Der Editor legt AutoDrive-Parkplätze in den Hallen eines Savegames an.

**Savegame verknüpfen.** Eine Route hat kein Savegame. Beim Öffnen einer Route bietet der Editor an, eins zu verknüpfen (Savegames auf der Karte der Route zuerst); `Datei → Savegame verknüpfen…` ändert oder entfernt die Verknüpfung. Sie wird im Projekt der Route gespeichert; gibt es keins, bietet der Editor an, eins anzulegen. Mit „Für diese Route nicht mehr fragen“ kommt die Frage für diese Route nicht mehr. Die Heightmap des verknüpften Savegames ersetzt die der Karte, da Terraforming und Gebäude den Boden verändern. Ein geöffnetes Savegame braucht keine Verknüpfung.

**Hallen.** `Ansicht → Anzeigen → Hallen` zeichnet die Innenbereiche der Gebäude des Savegames als lila Umrisse: die im Spiel gebauten und die, die mit der Karte kommen, sofern sie nicht abgerissen wurden. Die Gebäudedateien werden aus dem Installationsordner des Spiels und dem Mods-Ordner gelesen; Gebäude, deren Dateien fehlen, werden weggelassen und in der Statusleiste gezählt. Nur Gebäude der Gruppe Hallen werden als Hallen gezeichnet (siehe Gebäudetypen unten).

**Stationen.** `Ansicht → Anzeigen → Stationen` zeichnet einen gelben Pfeil an jeder Haltestelle der Stationen des Savegames: die Stellen, an denen Fahrzeuge an Verkaufsstellen, Produktionen, Silos, Ställen und Dieseltanks abladen oder laden. Der Pfeil liegt längs der Spur über dem Trigger. Die meisten Gebäude legen die Stelle fest, die der KI-Helfer des Spiels anfährt; dort folgt der Pfeil ihr. Hat ein Gebäude keine (viele Dieseltanks und Ställe), sitzt der Pfeil auf dem Trigger und folgt der Ausrichtung des Gebäudes, kann also in die falsche Richtung zeigen. Trigger derselben Art fast an derselben Stelle, einer je Füllart, werden als eine Haltestelle gezeigt.

**Gebäudetypen.** `Erzeugen → Gebäudetypen…` listet die Gebäudetypen des Savegames mit Innenbereichen, Stationen oder einem Fahrsilo in vier Gruppen: Stationen (Ablade- oder Ladetrigger), Hallen (nur Innenbereiche), Fahrsilos und Sonstige. Eine Produktion mit Halle ist eine Station, keine Halle; Wohnhäuser und Waagen stehen unter Sonstige, da nur die Spielfigur hineingeht oder Fahrzeuge nur darüberfahren. Steht ein Typ in der falschen Gruppe, in seiner Spalte `Gruppe` eine andere wählen; nicht angehakte Typen oder Gruppen werden ausgeblendet. `Zurücksetzen` setzt jeden aufgeführten Typ in seine eigene Gruppe zurück und zeigt ihn an. Beides gilt auf jeder Karte.

**Parkplätze anlegen.** Das Werkzeug Parkplätze (`S`) wählen; zeigt der Mauszeiger auf eine Halle, erscheinen Name und Kategorie des Gebäudes. Einen Hallenumriss mit links anklicken. Der Dialog zeigt die Halle von oben, so gedreht, dass die offene Seite unten liegt, mit einem Pfeil nach Norden, und aktualisiert sich bei jeder Eingabe. Die geplanten Parkplätze werden auch auf der Karte gezeichnet; solange der Dialog offen ist, lässt sich die Karte verschieben, zoomen und drehen, aber nicht bearbeiten.

- **Modus**: *Rückwärts einparken* (die Fahrzeuge setzen rückwärts in den Stellplatz, der Marker liegt an der Rückwand) oder *Durchfahren* (eine Vorwärtslinie je Stellplatz durch die Halle, die Ausfahrt liegt auf der gegenüberliegenden Seite).
- **Offene Seite** / **Einfahrtseite**: die Seite, von der die Fahrzeuge kommen. Zum Ändern eine Seite oder ihre Himmelsrichtung in der Draufsicht anklicken.
- **Anzahl Stellplätze**: Daraus wird die Stellplatzbreite berechnet und darunter angezeigt. Stellplätze unter 3 m Breite werden rot angezeigt und lassen sich nicht anlegen.
- **Linke Wand**, **Rechte Wand**, **Rückwand** (bzw. **Abstand zur Ausfahrt**), **Alle Zwischenräume**: Abstände in Metern. Eine Wand oder einen Zwischenraum in der Draufsicht anklicken, um nur diesen zu ändern; an der Klickstelle öffnet sich ein kleines Feld (Enter übernimmt, Esc bricht ab). Einzeln geänderte Zwischenräume bleiben erhalten, wenn sich die Anzahl der Stellplätze ändert.
- **Parkpositionen pro Stellplatz**, **Abstand der Parkpositionen** (nur Durchfahren): mehrere Parkpositionen hintereinander in jedem Stellplatz, die erste am Abstand zur Ausfahrt, die weiteren Richtung Einfahrt, jede mit eigenem Marker.
- **Zufahrtslinie**, **Abfahrtslinie**: die Fahrtrichtung der beiden Linien vor der offenen Seite, von außen gesehen.
- **Markername**, **Startnummer**, **Gruppe**: „Halle“ ab 3 ergibt „Halle 3“, „Halle 4“, … Bei mehreren Parkpositionen pro Stellplatz zählen die Nummern durch die Positionen jedes Stellplatzes weiter, beginnend an der Ausfahrt. Ein neuer Gruppenname legt die Gruppe an.

Beim Rückwärts-Einparken zeigt die Seitenansicht darunter die Linie eines Stellplatzes, die für alle Stellplätze gilt. Ein Segment anklicken, um seine Länge zu ändern; „+“ teilt ein Segment in der Mitte, `Entf` löscht die ausgewählte Node. Die Punkte, an denen Zufahrts- und Abfahrtslinie abzweigen, lassen sich auf eine andere Node ziehen. Beim Durchfahren zeigt die Seitenansicht die Linie nur an.

`Anlegen` erzeugt alle Nodes als Subprio-Nodes auf der Höhe der Halle, als ein Rückgängig-Schritt. Zweimal ausgeführt entstehen die Parkplätze zweimal. Danach sind die vier offenen Enden von Zufahrts- und Abfahrtslinie ausgewählt, damit man sie ans Straßennetz anschließen kann. `Halleneinstellungen zurücksetzen` stellt die Standardaufteilung wieder her.

**Vorlagen.** `Als Vorlage speichern…` speichert Modus, Seite, Anzahl Stellplätze, Abstände, Parkpositionen und Stellplatzlinie unter einem Namen für diesen Hallentyp; die Vorlage gilt so für dasselbe Gebäude auf jeder Karte. Linienrichtungen, Markername, Startnummer und Gruppe werden nicht gespeichert. `Vorlage laden…` listet die Vorlagen des Hallentyps, dort lassen sie sich auch löschen. Der Dialog öffnet mit der zuletzt gespeicherten oder geladenen Vorlage des Hallentyps.

## Netz prüfen

`Prüfen → Netz prüfen` listet übereinanderliegende Nodes, Nodes außerhalb der Karte und, wenn eine Heightmap geladen ist, Nodes, deren Höhe zu stark vom Gelände abweicht, außerdem ungültige Connection-Verweise (auf eine nicht vorhandene Node, auf die Node selbst oder ein eingehender Eintrag ohne den ausgehenden Eintrag der anderen Node) und Nodes ganz ohne Connections. Der Abstand für übereinanderliegende Nodes und der erlaubte Höhenunterschied werden oben im Fenster eingestellt. Ein Klick auf einen Eintrag zeigt ihn auf der Karte. `Auswahl beheben` oder `Alle beheben` führt übereinanderliegende Nodes zu einer zusammen (die Node mit Marker, sonst die mit der kleinsten ID), verschiebt Nodes zurück auf die Karte, setzt Höhen aus der Heightmap, entfernt ungültige Verweise und löscht Nodes ohne Connections (Nodes mit Marker bleiben erhalten). Jede Art von Korrektur ist ein Rückgängig-Schritt.

Einträge, die so in Ordnung sind, etwa Nodes auf einer Brücke, lassen sich mit `Ignorieren` ausblenden. Sie wandern in die Gruppe `Ignoriert` und werden von `Alle beheben` nicht verändert; `Nicht ignorieren` holt sie zurück. Ein ignorierter Eintrag erscheint auch wieder, wenn eine seiner Nodes verschoben wird. Mit den Kontrollkästchen lässt sich eine ganze Prüfung ausschalten. Ignorierte Einträge und ausgeschaltete Prüfungen werden für jede Route und jedes Savegame gespeichert.

Beim Speichern läuft zuerst die Prüfung. Findet sie Probleme, die nicht ignoriert sind, zeigt das Fenster sie an und der Editor fragt, ob trotzdem gespeichert werden soll.

## Speichern

`Datei → Speichern` (`Strg+S`) schreibt in dasselbe Format und dieselbe Datei, aus der geladen wurde. Vor dem ersten Überschreiben legt der Editor eine Sicherungskopie (`.bak`) an. Bei Savegames werden auch die Markerziele der Fahrzeuge in der `vehicles.xml` angepasst.

`Speichern unter` speichert eine Route als neue Route im RoutesManager.

Ungespeicherte Änderungen werden alle paar Minuten automatisch gesichert (Abstand unter `Datei → Einstellungen`). Wird der Editor unerwartet beendet, bietet er beim nächsten Start an, sie wiederherzustellen.

`Datei → Zuletzt geöffnet` und der Startbildschirm listen die letzten fünf geöffneten Routen, Savegames, XML-Dateien und Projekte. Beim Start öffnet der Editor die zuletzt geöffnete wieder, außer es wird eine automatische Sicherung wiederhergestellt; das lässt sich unter `Datei → Einstellungen` abschalten.

## Einstellungen

Den Editor gibt es auf Deutsch und Englisch. Beim ersten Start ist er auf einem deutschen Windows deutsch, sonst englisch. Die Sprache lässt sich unter `Datei → Einstellungen` ändern; sie wirkt nach einem Neustart.

Der Editor folgt dem hellen oder dunklen Modus von Windows. Unter `Datei → Einstellungen` lässt sich stattdessen ein helles oder dunkles Design wählen, und im Reiter `Tastenkürzel` lassen sich die Tastenkürzel aller Menüeinträge und Werkzeuge ändern.

`Hilfe → Nach Updates suchen` fragt bei GitHub nach, ob es eine neuere Version gibt. Die automatische Suche bei jedem Start lässt sich im Einrichtungsdialog beim ersten Start oder unter `Datei → Einstellungen` einschalten. Sie ist anfangs aus, weil sie sich mit github.com verbindet. Ein Update wird installiert, indem man die Zip-Datei von der Release-Seite herunterlädt und den alten Programmordner damit ersetzt; Einstellungen und importierte Karten bleiben erhalten.

## Hilfe und Fehler

`Hilfe → Versionsverlauf` zeigt, was sich in jeder Version geändert hat (auf Englisch), `Hilfe → Über` zeigt Version und Lizenz. Tritt ein unerwarteter Fehler auf, zeigt der Editor eine Meldung und läuft weiter. Die Details landen in einer Log-Datei (`Hilfe → Log-Ordner öffnen`, in `%APPDATA%\AutoDrive Editor\logs`); bitte bei Fehlermeldungen anhängen. `Hilfe → Debug-Log` schreibt zusätzlich ausführliche Einträge ins Log, z. B. zu jeder Routensuche (Start, Ziel, Richtungen, warum keine Route gefunden wurde); einschalten, das Problem wiederholen und das Log anhängen.
