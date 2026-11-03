# AutoDrive FS25 Editor – Anleitung

[English](MANUAL.md) | **Deutsch** · zurück zur [README](README.de.md)

- [Erster Start](#erster-start)
- [Öffnen](#öffnen)
- [Das Fenster](#das-fenster)
- [Werkzeuge](#werkzeuge)
- [Darstellung](#darstellung)
- [Spielbild](#spielbild)
- [Gebäude des Savegames](#gebäude-des-savegames)
- [Planen und Erzeugen](#planen-und-erzeugen)
- [Netz prüfen](#netz-prüfen)
- [Speichern](#speichern)
- [Einstellungen](#einstellungen)
- [Hilfe und Fehler](#hilfe-und-fehler)

## Erster Start

Der Editor sucht den LS25-Benutzerordner (meist `Dokumente\My Games\FarmingSimulator2025`) und den Installationsordner des Spiels und zeigt beide zur Kontrolle an. Beide lassen sich später unter `Datei → Einstellungen` ändern.

Kartenbilder werden nicht mit dem Editor ausgeliefert. Sie werden aus dem `mods`-Ordner oder dem Grundspiel importiert, wenn zum ersten Mal eine Datei dieser Karte geöffnet wird (siehe [Öffnen](#öffnen)).

## Öffnen

**Öffnen-Bildschirm.** Solange nichts geöffnet ist, liegt der Öffnen-Bildschirm auf der Karte. `Datei → Öffnen…` (`Strg+O`) und der Knopf Öffnen der Werkzeugleiste zeigen denselben Bildschirm als Dialog. Er listet:

- **Savegames**, das neueste zuerst, mit Nummer, Name, Karte und Speicherzeit. Ein Savegame ohne AutoDrive-Daten steht auch in der Liste („kein AutoDrive-Netz“); es öffnet mit leerem Netz, und Speichern legt seine `AutoDrive_config.xml` an.
- **Routen (RoutesManager)**: alle Routen aus dem RoutesManager von AutoDrive, mit Karte, Revision und Datum.
- **Andere Datei öffnen…**: eine beliebige AutoDrive-XML-Datei in einem der beiden Formate.

Doppelklick auf einen Eintrag oder `Öffnen` öffnet ihn. Ohne Spielordner oder Savegames zeigt der Bildschirm „Keine Savegames gefunden“ und einen Link zu den Einstellungen. `Datei → Zuletzt geöffnet` listet die letzten fünf geöffneten Dateien. Beim Start öffnet der Editor die zuletzt geöffnete wieder, außer es wird eine automatische Sicherung wiederhergestellt; das lässt sich unter `Datei → Einstellungen` abschalten.

**Savegame oder Route.** Das **Savegame** öffnen, um das Netz zu bearbeiten, mit dem gefahren wird: AutoDrive kopiert eine importierte Route ins Savegame, das Savegame hat also sein eigenes vollständiges Netz. Ein Savegame bringt alles mit: die Karte, die Heightmap des Savegames (mit seinem Terraforming), die Parkpositionen seiner Fahrzeuge, seine Hallen und Stationen, die Befahrbarkeitskarte und das Spielbild. Eine **Route** öffnen, um eine Route zu bearbeiten, die in keinem Savegame aktiv ist, oder eine zum Weitergeben. Eine Route öffnet allein: ihr Netz auf der Karte, die im RoutesManager steht, ohne Fahrzeuge, Hallen, Stationen oder Befahrbarkeitskarte.

**Karten.** Eine noch nicht importierte Karte wird beim Öffnen der Datei ohne Nachfrage importiert, mit Fortschrittsbalken: Ein Savegame nennt seinen Karten-Mod, für eine Route werden die Mods nach ihrem Kartennamen durchsucht. Nur eine Karte, die nicht gefunden wird, fragt nach: `Mod-Zip wählen…` oder `Ohne Karte weiter`. Ohne Karte passt die Kartengröße zum Netz (2, 4, 8 oder 16 km). Eine Datei, die zu keiner importierten Karte gehört, etwa eine Routendatei außerhalb des RoutesManagers, öffnet ohne Karte; eine Karte dafür wählt man unter `Datei → Einstellungen → Karten → Diese Karte für die offene Datei verwenden` (siehe [Einstellungen](#einstellungen)). Wurde der Mod der Karte seit dem Import aktualisiert, bietet der Editor an, sie neu zu importieren: `Importieren`, `Jetzt nicht` (beim nächsten Start wieder gefragt) oder `Nicht für diese Version` (nach dem nächsten Update des Mods wieder gefragt).

## Das Fenster

- **Menüs** oben: `Datei`, `Bearbeiten`, `Ansicht`, `Erzeugen`, `Prüfen`, `Hilfe`.
- **Werkzeugleiste** darunter: Öffnen, Speichern · Rückgängig, Wiederholen · Kopieren, Ausschneiden, Einfügen · Hintergrund (Kartenbild, Bodenkarte oder Spielbild) · Raster (anzeigen, Abstand, Drehung) · Am Raster einrasten · Rotation der Ansicht (Winkel, Schritt) · Spielbild-Kacheln erneuern · Planungsmodus.
- **Werkzeugspalte** links: alle Werkzeuge in einer Spalte, siehe [Werkzeuge](#werkzeuge).
- **Optionsleiste** über der Karte: der Name des aktiven Werkzeugs, seine Variantenknöpfe und seine Optionen. Werkzeuge ohne Optionen zeigen nur ihren Namen.
- **Fenster** rechts: `Inspektor` (die ausgewählte Node: Typ, Koordinaten, Marker, Höhe aus der Datei und aus der Heightmap; sonst „Nichts ausgewählt“) und `Marker` (alle Markergruppen; Doppelklick zentriert einen Marker) teilen sich einen Platz als Reiter. Das Fenster `Netzprüfung` öffnet sich mit `Prüfen → Netz prüfen`. `Ansicht` blendet die Fenster ein und aus; `Hilfe → Debuganzeige` zeigt Laufzeitwerte.
- **Statusleiste** unten: was das aktive Werkzeug als Nächstes erwartet, und die Ergebnisse von Speichern und Prüfen.

**Gemerkt.** Das Fenster behält Größe, Position und Fenster rechts zwischen den Starts. Jede Datei unter `Datei → Zuletzt geöffnet` öffnet dort, wo ihre Ansicht zuletzt war (Position, Zoom, Drehung); eine zum ersten Mal geöffnete Datei zeigt das ganze Netz. `Ansicht → Ganze Karte anzeigen` (`Pos1`) passt das Netz ins Fenster ein und setzt die Drehung zurück. Während eine Datei lädt, zeigt die Karte „… wird geladen…“ und der Mauszeiger wartet.

Maus: Das **Mausrad** zoomt, **linkes Ziehen** auf freier Fläche verschiebt die Karte in jedem Werkzeug, **mittleres Ziehen** dreht die Ansicht. **Rechtsklick** oder **Esc** bricht den aktuellen Schritt eines Werkzeugs ab; **Enter** bestätigt ihn (zum Beispiel bei Kurven).

## Werkzeuge

Die Werkzeugspalte enthält 17 Werkzeuge in Gruppen. Anlegen, Verbinden, Zeichnen, Marker, Messen und Erzeugen haben **Varianten**: Knöpfe links in der Optionsleiste. Die Taste einer Variante wählt Werkzeug und Variante zugleich; ein Klick auf das Werkzeug in der Spalte wählt es mit der zuletzt benutzten Variante. Der Knopf in der Spalte zeigt die aktuelle Variante. Auswahl ist das Startwerkzeug.

| Werkzeug | Taste | Was es tut |
| --- | --- | --- |
| Auswahl | `A` | Per Klick oder Rechtsziehen auswählen; Umschalt + Rechtsziehen für freie Auswahl; Strg ergänzt die Auswahl |
| Verschieben | `V` | Node oder Auswahl ziehen; Umschalt bewegt nur entlang einer Rasterachse |
| Erzeugen | `G` | Startet den Planungsmodus und erzeugt eine Route, eine Einmündung, die Parkplätze einer Halle oder die Spuren von Stationen (siehe [Planen und Erzeugen](#planen-und-erzeugen)) |
| Anlegen (Regular / Subprio) | `E` / `Umschalt+E` | Node auf freier Fläche anlegen |
| Verbinden (Regular / Dual / Reverse) | `1` / `2` / `3` | Nodes nacheinander anklicken, um sie zu verbinden |
| Löschen | `L` | Node oder Auswahl löschen |
| Typ wechseln | `T` | Zwischen Regular und Subprio wechseln |
| Richtung umkehren | `U` | Connection anklicken, um sie umzukehren; in einer Auswahl werden alle Connections der Auswahl umgekehrt |
| Rotieren | `R` | Auswahl am Ring drehen; Umschalt rastet in Schritten ein (Standard 15°, `Rasterschritt` in der Optionsleiste) |
| Position eingeben | `P` | X/Y/Z einer Node als Zahlen eingeben |
| Horizontal / vertikal ausrichten | `H` / `J` | Auswahl auf die Linie durch eine Referenz-Node legen |
| Höhe wie Referenz / Höhe aus Heightmap | `Y` / `Umschalt+Y` | Höhen der Auswahl setzen |
| Zeichnen (Linie / Kreisbogen / Bézier) | `I` / `K` / `B` | Linie: gerader Abschnitt mit gleichmäßigem Node-Abstand. Kreisbogen und Bézier: Start und Ende anklicken, Griffe ziehen, Enter drücken; die Bézierkurve hat einen oder zwei Kontrollpunkte. Abstand, Connection-Art, Node-Typ und Kontrollpunkte stehen in der Optionsleiste. Ein Wechsel der Variante beim Zeichnen behält Start und Ende |
| Marker (Hinzufügen / Bearbeiten / Verschieben / Löschen) | `M` / `Umschalt+M` / `Strg+M` / `Strg+Umschalt+M` | Marker hinzufügen oder bearbeiten (Name und Gruppe), auf eine andere Node verschieben oder löschen |
| Messen (Abstand / Winkel) | `D` / `Umschalt+D` | Punkt A und Punkt B anklicken (Node oder freie Fläche), einen Punkt ziehen, um ihn zu verschieben. `Ansicht an Linie ausrichten` in der Optionsleiste dreht die Ansicht entlang der Linie. Esc ohne etwas zu löschen kehrt zum vorher benutzten Werkzeug zurück |

Außerdem im Menü `Bearbeiten` und in der Werkzeugleiste: Rückgängig und Wiederholen (`Strg+Z` / `Strg+Y`), Kopieren, Ausschneiden und Einfügen (`Strg+C/X/V`; `Strg+Umschalt+V` fügt an der Originalposition ein; eingefügte Nodes bekommen die Geländehöhe am neuen Ort, außer `Beim Einfügen Höhen beibehalten` ist an, z. B. für eine Brücke oder Rampe), Auswahl löschen (`Entf`) und Am Raster einrasten (`S`). Alle Tasten lassen sich unter `Datei → Einstellungen → Tastenkürzel` ändern.

## Darstellung

`Ansicht → Anzeigen` blendet Nodes, Node-IDs, jede Connection-Art (Regular, Dual, Reverse), Marker, Markernamen, die Parkpositionen der Fahrzeuge, Hallen, Stationen und die Befahrbarkeitskarte (siehe [Route finden](#route-finden)) ein und aus. Die Linienfarbe zeigt die Connection-Art, Pfeile zeigen die Richtung; Dual-Connections bekommen zu jedem Ende einen. Subprio-Nodes sind orange. Node-IDs erscheinen erst beim Hineinzoomen; Parkpositionen (ein „P“ neben dem Marker) werden aus der `vehicles.xml` des Savegames gelesen und erscheinen daher nur bei geöffnetem Savegame, siehe [Gebäude des Savegames](#gebäude-des-savegames); dort sind auch Hallen und Stationen erklärt. Ausgeblendete Nodes und Connections lassen sich nur anklicken und auswählen, wenn `Ausgeblendete Elemente auswählbar` an ist. Größen und Farben stellt man unter `Ansicht → Darstellungsoptionen…` ein. Alle Einstellungen bleiben gespeichert.

**Hintergrund.** `Ansicht → Hintergrund` (auch der Knopf Hintergrund der Werkzeugleiste) wählt, was unter dem Netz liegt: das `Kartenbild`, die `Bodenkarte` oder das `Spielbild`. Die Bodenkarte ist aus den Bodentexturen der Karte gezeichnet: Asphalt, Beton, Schotter, Gras, Matsch, Wald, Fels und Sand je in einer eigenen Farbe, darüber die Feldgrenzen und Feldnummern. Sie zeigt die Karte so, wie das Spiel sie bemalt, was hilft, wo das Kartenbild veraltet ist. Mit einer älteren Version des Editors importierte Karten haben keine Bodenkarte; dafür die Karte unter `Datei → Einstellungen → Karten` neu importieren. Der Import einer großen Karte dauert dadurch etwas länger (etwa 15 Sekunden bei einer 16x-Karte).

## Spielbild

Das Spielbild ist die Karte, wie das Spiel sie von oben zeichnet, schärfer und aktueller als das Kartenbild: Straßen, Höfe, Gebäude und Felder so, wie sie in deinem Savegame sind. Der Begleit-Mod `FS25_AutoDriveEditorLink` rendert es im laufenden Spiel; der Editor speichert es pro Karte und Savegame und zeigt es als Hintergrund.

**Aufnehmen.** Das Spiel mit aktivem Mod starten, das Savegame laden und dasselbe Savegame im Editor öffnen. Dann `Ansicht → Hintergrund → Spielbild aufnehmen…` wählen. Oben im Dialog steht, ob das Spiel verbunden ist; nur dann geht `Start`. Man wählt die Auflösung, 0,25 m/px (schärfer) oder 0,5 m/px (schneller, kleiner), jeweils mit Kachelzahl, Zeit und Speicherplatz. Eine Aufnahme in der anderen Auflösung ersetzt das aktuelle Bild. `Wartezeit pro Kachel` ist die Zeit, die das Spiel bekommt, um einen Ort zu laden, bevor es ihn rendert; bei Kacheln mit Löchern erhöhen.

Während der Aufnahme wird das Spiel auf 12:00 Uhr und Sonne gestellt, und es friert für jede Kachel kurz ein. Im Spiel weder die Kamera bewegen noch Menüs öffnen. Danach, auch nach `Abbrechen` oder einem Fehler, bekommt das Spiel sein Wetter zurück, und seine Uhr läuft ab der alten Zeit plus der Dauer der Aufnahme weiter. Der Editor bleibt bedienbar: Die Statusleiste zeigt `Spielbild 37/289 · noch 4 Min.` mit einer Schaltfläche `Abbrechen`, und die Kacheln erscheinen auf der Karte, sobald sie ankommen. Ob abgebrochen oder fertig, die bis dahin aufgenommenen Kacheln bleiben. Beim Öffnen einer anderen Datei oder beim Schließen des Editors während einer Aufnahme fragt der Editor, ob sie abgebrochen werden soll.

**Anzeigen.** `Ansicht → Hintergrund → Spielbild` zeigt das Bild; nach einer Aufnahme wird es automatisch gewählt. Wo nichts aufgenommen wurde, scheint das Kartenbild durch. Das Bild eines Savegames bleibt erhalten, auch wenn das Savegame gelöscht wird.

**Kacheln erneuern.** Nach einer Änderung auf der Karte nimmt `Spielbild-Kacheln erneuern` (Werkzeugleiste oder `Ansicht → Hintergrund`) nur die betroffenen Kacheln neu auf. Dafür braucht es ein aufgenommenes Bild und das verbundene Spiel wie bei einer Aufnahme. Das Werkzeug zeigt das Kachelraster: Klick auf eine Kachel oder mit rechts einen Rahmen ziehen markiert Kacheln, `Strg` + Rechtsziehen hebt die Markierung auf, Linksziehen verschiebt die Ansicht. Die Statusleiste zeigt die Zahl der markierten Kacheln und die nötige Zeit; `Enter` startet die Aufnahme, `Esc` löscht die Markierungen und beendet dann das Werkzeug. Die neuen Kacheln ersetzen die alten, sobald sie ankommen.

## Gebäude des Savegames

Bei geöffnetem Savegame liest der Editor seine Gebäude: die Hallen zum Parken und die Stationen, an denen Fahrzeuge laden und abladen. Das Werkzeug Erzeugen baut darauf auf. Eine allein geöffnete Route hat keine.

**Hallen.** `Ansicht → Anzeigen → Hallen` zeichnet die Innenbereiche der Gebäude des Savegames als lila Umrisse: die im Spiel gebauten und die, die mit der Karte kommen, sofern sie nicht abgerissen wurden. Die Gebäudedateien werden aus dem Installationsordner des Spiels und dem Mods-Ordner gelesen; Gebäude, deren Dateien fehlen, werden weggelassen und in der Statusleiste gezählt. Das Gelesene behält der Editor in `%APPDATA%\AutoDrive Editor\cache` und liest es erst neu, wenn sich die Dateien ändern; ein Savegame öffnet daher beim zweiten Mal schneller. Nur Gebäude der Gruppe Hallen werden als Hallen gezeichnet (siehe Gebäudetypen unten).

**Stationen.** `Ansicht → Anzeigen → Stationen` zeichnet einen gelben Pfeil an jeder Haltestelle der Stationen des Savegames: die Stellen, an denen Fahrzeuge an Verkaufsstellen, Produktionen, Silos, Ställen und Dieseltanks abladen oder laden. Der Pfeil liegt längs der Spur über dem Trigger. Die meisten Gebäude legen die Stelle fest, die der KI-Helfer des Spiels anfährt; dort sitzt der Pfeil. Hat ein Gebäude keine (viele Dieseltanks und Ställe), sitzt der Pfeil auf dem Trigger. Mit der Befahrbarkeitskarte des Savegames nimmt der Pfeil die Richtung mit dem meisten freien Platz durch die Haltestelle (wo das Gebäude die KI-Stelle festlegt: längs oder quer zu ihr), und alle Haltestellen eines Gebäudes umrunden es gegen den Uhrzeigersinn, sodass eine Route an allen vorbeiführen kann; eine Spur, die auf das Gebäude zeigt, führt zur Seite mit mehr Platz. Sie kann trotzdem falsch sein; beim Anlegen lässt sich die Spur drehen. Trigger derselben Art fast an derselben Stelle, einer je Füllart, werden als eine Haltestelle gezeigt.

**Gebäudetypen.** `Erzeugen → Gebäudetypen…` listet die Gebäudetypen des Savegames mit Innenbereichen, Stationen oder einem Fahrsilo in vier Gruppen: Stationen (Ablade- oder Ladetrigger), Hallen (nur Innenbereiche), Fahrsilos und Sonstige. Eine Produktion mit Halle ist eine Station, keine Halle; Wohnhäuser und Waagen stehen unter Sonstige, da nur die Spielfigur hineingeht oder Fahrzeuge nur darüberfahren. Steht ein Typ in der falschen Gruppe, in seiner Spalte `Gruppe` eine andere wählen; nicht angehakte Typen oder Gruppen werden ausgeblendet. `Zurücksetzen` setzt jeden aufgeführten Typ in seine eigene Gruppe zurück und zeigt ihn an. Beides gilt auf jeder Karte.

## Planen und Erzeugen

Der Planungsknopf am rechten Ende der Werkzeugleiste (`Bearbeiten → Planungsmodus`, `Strg+P`) beginnt einen Plan. Alle Werkzeuge arbeiten wie gewohnt, die Änderungen werden aber im Plan gesammelt: Ein blauer Balken über der Karte zeigt, wie viele Nodes der Plan geändert hat, und diese Nodes bekommen einen blauen Hof. Rückgängig und Wiederholen arbeiten innerhalb des Plans und halten an seinem Anfang. `Plan übernehmen` fügt den ganzen Plan als einen Rückgängig-Schritt in den Verlauf ein; `Plan verwerfen` nimmt ihn vollständig zurück. Ein weiterer Klick auf den Planungsknopf, das Öffnen einer anderen Datei oder das Schließen des Editors fragt, ob der Plan übernommen oder verworfen werden soll. Solange ein Plan offen ist, kann nicht gespeichert werden; beim Start eines Plans werden die Änderungen davor gesichert, danach pausiert die automatische Sicherung, bis der Plan übernommen oder verworfen ist.

Das Werkzeug Erzeugen (`G`) startet den Planungsmodus und erzeugt, was mit den Aufgabenknöpfen in der Optionsleiste gewählt ist: eine Route, eine Einmündung, die Parkplätze einer Halle oder die Spuren von Stationen. Das Menü `Erzeugen` enthält dieselben vier Aufgaben.

### Route finden

Beim Werkzeug Erzeugen die Aufgabe `Route` wählen, dann Nodes, Connections oder freie Stellen nacheinander als Wegpunkte anklicken. Der Editor sucht eine befahrbare Einbahn-Route in dieser Reihenfolge durch sie und zeigt sie an; Teile, die Gebäude, Zäune, Bäume oder Wasser kreuzen, sind rot. Die Route fährt nur vorwärts und ist gebaut wie ein von Hand gezeichneter Kurs: gerade Stücke mit Kreisbögen des Kurvenradius durch die Ecken. Ihre Nodes liegen so, wie AutoDrive eine Fahrt aufzeichnet, auf Geraden bis zu dem unter `Datei → Einstellungen → Generatoren` eingestellten Abstand auseinander (Standard 12 m), umso dichter, je enger sie abbiegt. Sie hält die halbe Fahrzeugbreite plus einen Sicherheitsabstand von Hindernissen fern; Kurvenradius, Fahrzeugbreite und Abstand stellt man ebenfalls dort ein. Sie bevorzugt Straßen und Höfe und folgt einer Straße um eine Wiese oder Obstwiese herum, statt sie zu queren, fährt aber über Gras, wo das deutlich kürzer ist; sie meidet Felder und verlässt den ersten und erreicht den letzten Node in der Richtung ihrer Connections. An den Wegpunkten dazwischen nimmt sie die Richtung, die zum nächsten Stück passt. Nahe den Wegpunkten darf gesperrter Boden befahren werden, da Nodes unter einem Dach oder in einer Halle liegen können. Freie Wegpunkte oder beliebige Nodes ziehen, um die Route zu ändern; nach jeder Änderung wird sie neu gesucht. Drücken auf die Route setzt dort einen Wegpunkt, der sich gleich ziehen lässt.

Der Wegpunkt unter dem Mauszeiger wird hervorgehoben; `Entf` oder ein Rechtsklick entfernt ihn. `Letzten entfernen (Rücktaste)` und `Leeren (Esc)` in der Optionsleiste entfernen den letzten oder alle Wegpunkte. `Strg+Z` nimmt zuerst Wegpunkt-Änderungen (hinzufügen, verschieben, entfernen) der Route im Bau zurück, danach die Änderungen des Plans. Wo die Route rot ist, Nodes verschieben oder einen Wegpunkt auf dem Umweg setzen. `Enter` fügt eine Route ohne rote Teile als ein Rückgängig-Schritt dem Plan hinzu; freie Wegpunkte werden zu Nodes, und ein Wegpunkt auf einer Connection teilt sie mit einem neuen Node (gleicher Typ und gleiche Richtung). Danach beginnt das Werkzeug leer, und der nächste Klick wählt einen neuen Start. Schließt die gefundene Route an einem ungünstigen Node an, sagt die Statusleiste warum, z. B. ein Marker-Node (andere Routen würden durch den Marker führen), ein erster Node, zu dem nichts führt, oder ein letzter Node, der nirgendwohin führt; die Route lässt sich trotzdem hinzufügen.

Gibt es keinen befahrbaren Weg, zeigt der Editor den befahrbaren Teil und eine rot gestrichelte Linie zum Wegpunkt, der nicht erreicht wurde; die Statusleiste nennt diesen Wegpunkt, und `Enter` fügt nichts hinzu, bis dort Wegpunkte verschoben oder hinzugefügt sind. Zwei Wegpunkte, die für den Kurvenradius zu nah liegen, werden schon vor der Suche genauso markiert. Schlägt eine Suche mit einem Fehler fehl, sagt die Statusleiste das; die Details stehen in der Logdatei.

Routen, die schon im Plan sind, werden mitbenutzt: Eine Route in derselben Richtung schließt sich ihnen an. Der Rückweg (die Nodes andersherum auswählen) bekommt eine eigene Spur, wo Platz ist; wo nicht, teilt er sich die Spur, die dort Dual wird. Ist gar kein Platz zum Wenden, meldet der Editor, dass keine befahrbare Route gefunden wurde.

Die Routensuche nutzt die Befahrbarkeitskarte des Spiels, die der Landwirtschafts-Simulator bei jedem Speichern in den Spielstand schreibt (`vehicleNavigationCostmap.dat`); sie braucht daher ein geöffnetes Savegame. Nach dem Platzieren von Gebäuden erneut im Spiel speichern, damit die Karte sie kennt. `Ansicht → Anzeigen → Befahrbarkeitskarte` zeichnet sie: gesperrter Boden rot (in Wäldern blau), unwegsamer Boden orange, Gras gelb, Felder grün; Straßen und Höfe bleiben frei.

### Einmündungen

Beim Werkzeug Erzeugen die Aufgabe `Einmündung` wählen, um eine Hofzufahrt an eine Straße anzuschließen. Auf die Straße drücken und zum Hof ziehen: Die Einmündung wandert mit der Maus an der Straße entlang, und die Zufahrt verlässt die Straße im rechten Winkel so weit, wie die Maus reicht. Nach dem Loslassen sitzt ein Griff an der Spitze der Zufahrt; ihn ziehen, um die Zufahrt zu biegen, oder auf einem Node ablegen, um die Zufahrt dort anzuschließen. `Enter` oder ein Klick neben den Griff fügt die Einmündung dem Plan hinzu, `Esc` bricht ab. Rückgängig beim Zeichnen macht zuerst eine gebogene Zufahrt wieder gerade, geht dann zum Setzen der Einmündung zurück und bricht danach ab.

Die Optionen in der Optionsleiste legen fest, wie die Einmündung gebaut wird, und bleiben für das nächste Mal gespeichert:

- **Bauart**: *Box* (Standard) baut eine kompakte Kreuzungsbox, wo eine Straße aus zwei Einbahnspuren auf eine Zufahrt mit zwei Spuren trifft: Die Spuren teilen sich einen Node, wo sie sich kreuzen, ein Mittel-Node nimmt das Linksabbiegen und Wenden auf, kurze Kurven das Rechtsabbiegen. Die Stücke von den Kreuzungen bis zum Rand der Box fahren in beide Richtungen, damit AutoDrive-Fahrer sich in der Box sehen. *Kurven* baut stattdessen für jede Richtung eine Einbahn-Abbiegekurve. Haben Straße oder Zufahrt keine zwei Einbahnspuren, werden Kurven gebaut, und die Statusleiste sagt das.
- **Zufahrt**: *Automatisch* (Standard) nimmt zwei Spuren an einer Straße aus zwei Einbahnspuren und eine Spur in beide Richtungen an einer Straße in beide Richtungen oder an einer solchen Straße an der Spitze der Zufahrt. *Beide Richtungen* oder *Zwei Spuren* wählen es direkt. *Einbahn hinein* und *Einbahn hinaus* bauen eine Einbahn-Zufahrt nur mit den Kurven in den Hof oder aus ihm heraus, z. B. für einen Hof mit eigener Ausfahrt; eine Box braucht beide Richtungen, daher entstehen dabei Kurven. **Spurabstand** ist der Abstand der beiden Spuren (Standard 5,5 m).

Die Kurven verlassen die Straße und münden in sie mit einem leichten Knick (20°) und biegen dann in einem Bogen mit dem Kurvenradius ab (`Datei → Einstellungen → Generatoren`), wie die Abzweige handgemachter Kurse. Geht auf der anderen Seite eine Straße weiter, kommen Spuren geradeaus hinüber dazu. Kurven oder Spuren, die nach der Befahrbarkeitskarte nicht passen, sucht die Routensuche; was dann noch gesperrt ist, wird weggelassen, rot gestrichelt gezeichnet und in der Statusleiste genannt (z. B. „Kein Linksabbiegen in den Hof aus Richtung Norden“), ebenso Teile einer Box auf gesperrtem Boden. Der Rest der Einmündung lässt sich trotzdem hinzufügen.

### Parkplätze in Hallen

Der Editor legt AutoDrive-Parkplätze in den Hallen eines Savegames an. Beim Werkzeug Erzeugen die Aufgabe `Parkplätze` wählen; zeigt der Mauszeiger auf eine Halle, erscheinen Name und Kategorie des Gebäudes. Einen Hallenumriss mit links anklicken. Der Dialog zeigt die Halle von oben, so gedreht, dass die offene Seite unten liegt, mit einem Pfeil nach Norden, und aktualisiert sich bei jeder Eingabe. Die geplanten Parkplätze werden auch auf der Karte gezeichnet; solange der Dialog offen ist, lässt sich die Karte verschieben, zoomen und drehen, aber nicht bearbeiten.

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

### Stationsspuren

Beim Werkzeug Erzeugen die Aufgabe `Stationen` wählen. Einen Haltestellenpfeil oder die Fläche zwischen den Pfeilen eines Gebäudes mit links anklicken, um alle seine Haltestellen zu wählen, zusammen mit den Haltestellen von Gebäuden, die bis zu 15 m daneben stehen (z. B. zwei Tankstellen nebeneinander), oder mit rechts einen Rahmen ziehen (`Umschalt`: Lasso), um alle Haltestellen darin zu wählen; zeigt der Mauszeiger auf eine Station, erscheint ihr Name oder die Namen der Gebäude, die ein Klick wählen würde. Der Dialog öffnet sich neben den gewählten Haltestellen, sodass sie sichtbar bleiben. Er listet die Haltestellen mit Häkchen, Art, Fruchtsorten, Markername und Gruppe (z. B. „Getreidelager (Verkaufsstelle)“ in „Verkaufsstellen“), Spurwinkel und einem Hinweis (keine KI-Stelle im Gebäude, ein vorhandener Node, wo die Spur hinkommt). Der Marker sitzt ein Stück hinter der Haltestelle (Standard 8 m), denn der Traktor hält am Marker, und der Anhänger steht dann über dem Abladepunkt.

Die Spuren werden auf der Karte gezeichnet. Den Marker einer Spur ziehen, um sie um ihre Haltestelle zu drehen (`Umschalt`: 15°-Schritte), oder den Winkel eintippen. Den ersten oder letzten Node einer Spur ziehen, um dieses Ende in einem Bogen von der Haltestelle aus zu biegen, z. B. wo für eine gerade Spur kein Platz ist; Drehen macht die Spur wieder gerade. Ein Ende auf einem Node des Netzes ablegen, um die Spur dort anzuschließen; das Ende muss zur Fahrtrichtung des Nodes passen. `Anlegen` fügt je gewählter Haltestelle eine Einbahnspur aus Subprio-Nodes mit dem Marker auf dem Node an der Haltestelle in den Plan ein, als ein Rückgängig-Schritt. Spurenden, die nicht auf einem Node abgelegt wurden, sind noch offen und müssen ans Netz angeschlossen werden, z. B. mit Route finden.

`Generator-Einstellungen…` im Dialog öffnet die Seite `Datei → Einstellungen → Generatoren`. Dort stehen für Stationsspuren die Spurlänge vor der Haltestelle und nach dem Marker (Standard je 10 m), der Markerabstand, der Knotenabstand sowie Markername und Gruppe je Halteart. Ein Name ist ein Muster mit den Platzhaltern `{building}` (der Name des Gebäudes), `{type}` (die Halteart) und `{n}` (eine pro Gruppe gezählte Nummer, `{n:03}` mit drei Ziffern, beginnend bei `Nummern beginnen bei`), z. B. `VK-{n:02}`. Ein Name, der in derselben Gruppe schon im Netz steht, wird nicht noch einmal vergeben.

## Netz prüfen

`Prüfen → Netz prüfen` listet übereinanderliegende Nodes, Nodes außerhalb der Karte und, wenn eine Heightmap geladen ist, Nodes, deren Höhe zu stark vom Gelände abweicht, außerdem ungültige Connection-Verweise (auf eine nicht vorhandene Node, auf die Node selbst oder ein eingehender Eintrag ohne den ausgehenden Eintrag der anderen Node) und Nodes ganz ohne Connections. Der Abstand für übereinanderliegende Nodes und der erlaubte Höhenunterschied werden oben im Fenster eingestellt. Ein Klick auf einen Eintrag zeigt ihn auf der Karte. `Auswahl beheben` oder `Alle beheben` führt übereinanderliegende Nodes zu einer zusammen (die Node mit Marker, sonst die mit der kleinsten ID), verschiebt Nodes zurück auf die Karte, setzt Höhen aus der Heightmap, entfernt ungültige Verweise und löscht Nodes ohne Connections (Nodes mit Marker bleiben erhalten). Jede Art von Korrektur ist ein Rückgängig-Schritt.

Einträge, die so in Ordnung sind, etwa Nodes auf einer Brücke, lassen sich mit `Ignorieren` ausblenden. Sie wandern in die Gruppe `Ignoriert` und werden von `Alle beheben` nicht verändert; `Nicht ignorieren` holt sie zurück. Ein ignorierter Eintrag erscheint auch wieder, wenn eine seiner Nodes verschoben wird. Mit den Kontrollkästchen lässt sich eine ganze Prüfung ausschalten. Ignorierte Einträge und ausgeschaltete Prüfungen werden für jede Route und jedes Savegame gespeichert.

Beim Speichern läuft zuerst die Prüfung. Findet sie Probleme, die nicht ignoriert sind, zeigt das Fenster sie an und der Editor fragt, ob trotzdem gespeichert werden soll.

## Speichern

`Datei → Speichern` (`Strg+S`) schreibt in die geöffnete Datei. Vor dem ersten Überschreiben legt der Editor eine Sicherungskopie (`.bak`) an.

**Vom Spiel geändert.** Wurde das Netz in der Datei seit dem Öffnen oder letzten Speichern geändert, meist weil das Spiel gespeichert hat, warnt Speichern zuerst: `Trotzdem speichern` überschreibt die Änderungen des Spiels, `Neu laden (meine Änderungen gehen verloren)` lädt die Datei neu, `Abbrechen` tut nichts. Speichert das Spiel, ohne das Netz zu ändern, kommt keine Warnung. `Datei → Neu laden` (`F5`) lädt die geöffnete Datei jederzeit neu von der Festplatte und behält die Ansicht; bei ungespeicherten Änderungen fragt der Editor vorher.

**Savegame.** Speichern schreibt die `AutoDrive_config.xml` des Savegames und passt die Markerziele seiner Fahrzeuge in der `vehicles.xml` an. Haben Fahrzeuge einen gelöschten Marker als Ziel, listet Speichern sie zuerst auf und fragt `Speichern` oder `Abbrechen`: Beim Speichern wird ihr Ziel auf Marker 1 gesetzt und ein Parkziel entfernt. Läuft im Spiel genau dieses Savegame mit dem Begleit-Mod `FS25_AutoDriveEditorLink`, lädt der Editor das Netz danach im Spiel neu: Die Statusleiste zeigt `Gespeichert · im Spiel neu geladen`, und AutoDrive fährt sofort auf dem neuen Netz. Netzänderungen, die seit dem Öffnen im Spiel gemacht wurden, ersetzt das Neuladen. Meldet das Spiel einen Fehler oder antwortet es nicht innerhalb von 30 Sekunden, sagt eine Meldung, dass die Datei gespeichert, aber nicht neu geladen ist und dass das Spiel sie beim nächsten Speichern überschreibt. Läuft das Spiel ohne den Mod, sagt eine Warnung dasselbe, einmal pro Savegame und Sitzung: das Spiel ohne Speichern beenden oder den Mod installieren. Bei geschlossenem Spiel ist das neue Netz einfach da, wenn das Savegame das nächste Mal geladen wird.

**Route.** Speichern bei einer geöffneten Route schreibt nur die Routendatei. Um sie in einem laufenden Spiel zu nutzen, im RoutesManager von AutoDrive `Import` drücken und im Spiel speichern.

**Als Route speichern…** (`Strg+Umschalt+S`) bewahrt eine Version des Netzes als Route im RoutesManager auf. Als Name wird die zuletzt gespeicherte oder geladene Route vorgeschlagen, sonst der Kartenname; bei einem vorhandenen Namen fragt der Editor, ob die Route ersetzt werden soll, deren Revision dann steigt. Ein Savegame bleibt danach geöffnet; eine Route oder XML-Datei geht als die gespeicherte Route weiter.

**Route ins Savegame laden…** (bei geöffnetem Savegame) ersetzt das Netz durch eine Route der Karte des Savegames aus dem RoutesManager (Name, Revision und Datum, die neueste zuerst), als ein Rückgängig-Schritt. Steckt das aktuelle Netz noch in keiner Route, bietet der Editor zuerst an, es als Route zu speichern. Fahrzeuge behalten ihre Ziele an Markern mit demselben Namen und derselben Gruppe. Speichern schreibt die Route dann ins Savegame und lädt sie im Spiel neu.

Ungespeicherte Änderungen werden alle paar Minuten automatisch gesichert (Abstand unter `Datei → Einstellungen`). Wird der Editor unerwartet beendet, bietet er beim nächsten Start an, sie wiederherzustellen.

## Einstellungen

`Datei → Einstellungen…` hat vier Reiter:

- **Allgemein**: Sprache (Deutsch oder Englisch; beim ersten Start deutsch auf einem deutschen Windows, sonst englisch; wirkt nach einem Neustart), Design (wie Windows, hell oder dunkel), der Abstand der automatischen Sicherung, das Öffnen der letzten Datei beim Start, die Suche nach Updates beim Start und die Spielordner.
- **Karten**: die importierten Karten mit Mod, Größe, Heightmap und Spielbild. `Neu importieren` liest die gewählten Karten erneut aus ihren Mods (mehrere mit `Strg` oder `Umschalt`+Klick wählen; der Import läuft im Hintergrund, `Abbrechen` hört nach der gerade importierten Karte auf), `Entfernen` löscht die importierte Karte und ihr Spielbild (die Frage nennt die Größe), `Aus Mod-Zip importieren…` importiert eine Karte aus einer Zip-Datei an beliebiger Stelle. `Diese Karte für die offene Datei verwenden` legt die gewählte Karte unter die offene Datei; das merkt sich der Editor für die Datei.
- **Generatoren**: Kurvenradius (Standard 6 m) und Knotenabstand auf Geraden (Standard 12 m) für Route finden, Einmündung und die Stationsspuren; Fahrzeugbreite und Sicherheitsabstand (siehe [Route finden](#route-finden)); die Spurlängen der Stationsspuren sowie Markername und Gruppe je Halteart (siehe [Stationsspuren](#stationsspuren)).
- **Tastenkürzel**: die Tasten aller Menüeinträge und Werkzeuge, ein Eintrag pro Werkzeugvariante.

`Hilfe → Nach Updates suchen` fragt bei GitHub nach, ob es eine neuere Version gibt. Die Suche bei jedem Start ist anfangs aus, weil sie sich mit github.com verbindet. Ein Update wird installiert, indem man die Zip-Datei von der Release-Seite herunterlädt und den alten Programmordner damit ersetzt; Einstellungen und importierte Karten bleiben erhalten.

## Hilfe und Fehler

`Hilfe → Versionsverlauf` zeigt, was sich in jeder Version geändert hat (auf Englisch), `Hilfe → Über` zeigt Version und Lizenz. Tritt ein unerwarteter Fehler auf, zeigt der Editor eine Meldung und läuft weiter. Die Details landen in einer Log-Datei (`Hilfe → Log-Ordner öffnen`, in `%APPDATA%\AutoDrive Editor\logs`); bitte bei Fehlermeldungen anhängen. `Hilfe → Debug-Log` schreibt zusätzlich ausführliche Einträge ins Log, z. B. zu jeder Routensuche (Start, Ziel, Richtungen, warum keine Route gefunden wurde); einschalten, das Problem wiederholen und das Log anhängen. `Hilfe → Debuganzeige` zeigt Laufzeitwerte wie die Zahl der Nodes und der zwischengespeicherten Kartenkacheln.
