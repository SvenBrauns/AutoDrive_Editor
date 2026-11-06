# AutoDrive FS25 Editor – Anleitung

[English](MANUAL.md) | **Deutsch** · zurück zur [README](README.de.md)

Neu hier? Am besten mit dem [Schnellstart](#schnellstart) beginnen. Die übrigen Teile lassen sich in beliebiger Reihenfolge lesen.

1. [Schnellstart](#schnellstart)
2. [Grundlagen](#grundlagen)
3. [Das Netz bearbeiten](#das-netz-bearbeiten)
4. [Planen und Generatoren](#planen-und-generatoren)
5. [Die Karte darunter](#die-karte-darunter)
6. [Begleit-Mod](#begleit-mod)
7. [Prüfen und Speichern](#prüfen-und-speichern)
8. [Nachschlagen](#nachschlagen)

## Schnellstart

Diese Schritte führen durch eine erste kleine Änderung: ein Savegame öffnen, eine Straße zeichnen, einen Marker setzen und speichern.

1. **Editor starten.** Beim ersten Start zeigt er den gefundenen LS25-Benutzerordner (meist `Dokumente\My Games\FarmingSimulator2025`) und den Installationsordner des Spiels. Beide prüfen und bestätigen.
2. **Ein Savegame öffnen.** Der Öffnen-Bildschirm listet die Savegames, das neueste zuerst. Eines doppelt anklicken. Beim ersten Mal wird seine Karte aus dem `mods`-Ordner oder dem Grundspiel importiert; ein Fortschrittsbalken zeigt, wie weit es ist.
3. **Eine Stelle suchen.** Mit dem Mausrad zoomen, mit der linken Maustaste die Karte ziehen. `Pos1` zeigt die ganze Karte.
4. **Eine Straße zeichnen.** `1` drücken (Verbinden). Auf freie Fläche klicken, dann ein Stück weiter noch einmal und noch einmal: Jeder Klick legt eine Node an und verbindet sie von der vorigen aus. Ein Klick auf eine vorhandene Node schließt die Straße dort an. `Esc` beendet die Straße.
5. **Einen Marker setzen.** `M` drücken (Marker) und die letzte Node der Straße anklicken. Einen Namen eingeben, z. B. „Mein Hof“, und eine Gruppe, dann bestätigen.
6. **Einen Fehler zurücknehmen** mit `Strg+Z`. Jede Änderung lässt sich rückgängig machen.
7. **Speichern** mit `Strg+S`. Läuft im Spiel dieses Savegame mit dem [Begleit-Mod](#begleit-mod), fährt AutoDrive sofort auf der neuen Straße. Sonst ist sie da, wenn das Savegame das nächste Mal geladen wird.

> **Tipp:** Einmündungen, Stationsspuren oder ganze Routen von Hand zu bauen dauert lange. Die [Generatoren](#planen-und-generatoren) nehmen einem das meiste davon ab.

## Grundlagen

### Begriffe in dieser Anleitung

- **Node**: ein Punkt des AutoDrive-Netzes. Fahrzeuge fahren von Node zu Node.
- **Connection**: die Linie zwischen zwei Nodes. Ihre Farbe zeigt ihre Art:
  - **Regular**: Einbahn, in Pfeilrichtung.
  - **Dual**: in beide Richtungen.
  - **Reverse**: Einbahn, rückwärts gefahren.
- **Regular- und Subprio-Nodes**: AutoDrive bevorzugt Regular-Nodes. Subprio-Nodes (orange gezeichnet) nutzt es nur, wo eine Route muss, z. B. für Spuren in Parkplätze oder Stationen, damit andere Routen nicht durch sie führen.
- **Marker**: eine Node mit Namen, die Fahrzeuge anfahren können, z. B. ein Feld, eine Halle oder eine Verkaufsstelle. Marker sind in **Gruppen** sortiert, die AutoDrive als Ordner zeigt.
- **Savegame**: ein Spielstand. Er enthält seine eigene Kopie des Netzes, dazu Karte, Fahrzeuge und Gebäude.
- **Route**: ein Netz, das im **RoutesManager** von AutoDrive gespeichert ist, um Versionen aufzubewahren oder weiterzugeben. Eine Route lässt sich in ein Savegame importieren.
- **Plan**: eine Gruppe von Änderungen, die man noch verwerfen kann, siehe [Planungsmodus](#planungsmodus).

### Das Fenster

- **Menüs** oben: `Datei`, `Bearbeiten`, `Ansicht`, `Erzeugen`, `Prüfen`, `Hilfe`.
- **Werkzeugleiste** darunter: Öffnen, Speichern · Rückgängig, Wiederholen · Kopieren, Ausschneiden, Einfügen · Hintergrund · Raster (anzeigen, Abstand, Drehung) · Am Raster einrasten · Rotation der Ansicht (Winkel, Schritt) · Spielbild-Kacheln erneuern · Planungsmodus.
- **Werkzeugspalte** links: alle Werkzeuge in einer Spalte, siehe [Alle Werkzeuge und Tasten](#alle-werkzeuge-und-tasten).
- **Optionsleiste** über der Karte: der Name des aktiven Werkzeugs, seine Variantenknöpfe und seine Optionen.
- **Fenster** rechts: `Inspektor` (die ausgewählte Node: Typ, Koordinaten, Marker, Höhe aus der Datei und aus der Heightmap) und `Marker` (alle Marker nach Gruppen) teilen sich einen Platz als Reiter. Das Fenster `Netzprüfung` öffnet sich mit `Prüfen → Netz prüfen`. `Ansicht` blendet die Fenster ein und aus.
- **Statusleiste** unten: was das aktive Werkzeug als Nächstes erwartet, Ergebnisse von Speichern und Prüfen, und rechts die Kartenposition unter dem Mauszeiger (X und Z in Metern).

### Auf der Karte bewegen

| Aktion | So geht's |
| --- | --- |
| Zoomen | Mausrad; `+` und `-` zoomen um die Mitte |
| Karte verschieben | Linksziehen auf freier Fläche (in jedem Werkzeug) |
| Ansicht drehen | Mittleres Ziehen |
| Ganze Karte zeigen | `Pos1` (`Ansicht → Ganze Karte anzeigen`), setzt auch die Drehung zurück |
| Auf die Auswahl zoomen | `F` (`Ansicht → Auf Auswahl zoomen`), behält die Drehung |
| Aktuellen Schritt eines Werkzeugs abbrechen | Rechtsklick oder `Esc` |
| Schritt eines Werkzeugs bestätigen | `Enter`, z. B. bei Kurven |

Das Fenster behält Größe, Position und Fenster rechts. Jede zuletzt geöffnete Datei öffnet dort, wo ihre Ansicht war; eine zum ersten Mal geöffnete Datei zeigt das ganze Netz.

### Marker oder Node suchen

`Strg+F` drücken (`Bearbeiten → Marker oder Node suchen…`). Das Fenster `Marker` öffnet sich mit dem Cursor im Suchfeld.

- Einen Teil eines Namens eintippen: Die Marker werden gefiltert. Eine Gruppe, deren Name passt, behält alle ihre Marker.
- Eine Node-Nummer eintippen: Diese Node erscheint oben (`Node 123`).
- `Enter` oder ein Klick zentriert und wählt das erste Ergebnis, `Esc` leert das Feld.

Im Fenster `Marker` zentriert ein Klick einen Marker, ein Doppelklick bearbeitet ihn.

### Dateien öffnen

`Datei → Öffnen…` (`Strg+O`) zeigt den Öffnen-Bildschirm, der auch auf der Karte liegt, solange nichts geöffnet ist. Er listet:

- **Savegames**, das neueste zuerst, mit Nummer, Name, Karte und Speicherzeit. Ein Savegame ohne AutoDrive-Daten steht auch in der Liste („kein AutoDrive-Netz“); es öffnet mit leerem Netz, und Speichern legt seine `AutoDrive_config.xml` an.
- **Routen (RoutesManager)**, mit Karte, Revision und Datum.
- **Andere Datei öffnen…**: eine beliebige AutoDrive-XML-Datei in einem der beiden Formate.

`Datei → Zuletzt geöffnet` listet die letzten fünf Dateien. Beim Start öffnet der Editor die letzte wieder (abschaltbar unter `Datei → Einstellungen`), außer er stellt eine automatische Sicherung wieder her.

**Savegame oder Route?**

- Das **Savegame** öffnen, um das Netz zu bearbeiten, mit dem man fährt. Es bringt alles mit: die Karte, die Heightmap mit ihrem Terraforming, die Parkpositionen der Fahrzeuge, Hallen und Stationen, die Befahrbarkeitskarte und das Spielbild.
- Eine **Route** öffnen, um ein Netz zu bearbeiten, das in keinem Savegame aktiv ist, oder eines zum Weitergeben. Eine Route öffnet allein: ihr Netz auf ihrer Karte, ohne Fahrzeuge, Gebäude oder Befahrbarkeitskarte.

**Karten.** Eine Karte wird automatisch importiert, wenn zum ersten Mal eine Datei von ihr geöffnet wird. Ein Savegame nennt seinen Karten-Mod; für eine Route werden die Mods nach ihrem Kartennamen durchsucht.

- Wird die Karte nicht gefunden: `Mod-Zip wählen…` oder `Ohne Karte weiter`. Ohne Karte passt die Kartengröße zum Netz (2, 4, 8 oder 16 km).
- Eine Datei, die zu keiner Karte gehört (z. B. eine Routendatei außerhalb des RoutesManagers), öffnet ohne Karte. Eine Karte wählt man unter `Datei → Einstellungen → Karten → Diese Karte für die offene Datei verwenden`.
- Wurde der Mod der Karte aktualisiert, bietet der Editor an, sie neu zu importieren: `Importieren`, `Jetzt nicht` (beim nächsten Start wieder gefragt) oder `Nicht für diese Version` (nach dem nächsten Update wieder gefragt).

## Das Netz bearbeiten

Jedes Werkzeug hat eine Taste; alle Tasten stehen unter [Alle Werkzeuge und Tasten](#alle-werkzeuge-und-tasten). Manche Werkzeuge haben **Varianten**, als Knöpfe links in der Optionsleiste. Die Taste einer Variante wählt Werkzeug und Variante zugleich.

> **Tipp:** In jedem Werkzeug werden die Nodes, die mit der Node unter dem Mauszeiger verbunden sind, lila gezeichnet.

### Auswählen

`A` drücken (Auswahl).

- Eine Node anklicken oder mit rechts einen Rahmen ziehen. `Umschalt` + Rechtsziehen zeichnet ein freies Lasso. `Strg` ergänzt die Auswahl.
- Ein Doppelklick auf eine Node oder Connection wählt ihr ganzes **Straßenstück**: bis zu den nächsten Abzweigungen oder Straßenenden oder bis dahin, wo sich Connection-Art oder Node-Typ ändert.
- `Strg+A` wählt alles; `Bearbeiten → Straßenstück auswählen` erweitert die Auswahl auf ganze Straßenstücke.

Ausgeblendete Nodes und Connections lassen sich nur auswählen, wenn `Ausgeblendete Elemente auswählbar` an ist (siehe [Darstellungsoptionen](#darstellungsoptionen)).

### Nodes anlegen und verbinden

- **Anlegen** (`E` Regular, `Umschalt+E` Subprio): auf freie Fläche klicken, um eine Node anzulegen. Ein Klick auf eine Connection fügt eine Node in sie ein; sie liegt auf der Linie, in der Höhe zwischen den Enden, und Art und Richtung der Connection bleiben.
- **Verbinden** (`1` Regular, `2` Dual, `3` Reverse): Nodes nacheinander anklicken, um sie zu verbinden. Ein Klick auf freie Fläche legt eine Node an, ein Klick auf eine Connection fügt eine ein, und beide werden von der vorigen Node aus verbunden. So zeichnet man eine ganze Straße mit diesem einen Werkzeug. Der Node-Typ steht in der Optionsleiste. `Esc` oder Rechtsklick beendet die Kette.
- **Typ wechseln** (`T`): eine Node anklicken, um zwischen Regular und Subprio zu wechseln.
- **Richtung umkehren** (`U`): eine Connection anklicken, um sie umzudrehen. In einer Auswahl werden alle ihre Connections umgedreht.

### Linien und Kurven zeichnen

`I` (Linie), `K` (Kreisbogen) oder `B` (Bézier) drücken.

1. Start und Ende anklicken.
2. Bei Kreisbogen und Bézier die Griffe ziehen, um die Kurve zu formen. Eine Bézierkurve hat einen oder zwei Kontrollpunkte.
3. `Enter` drücken.

Die Nodes liegen gleichmäßig verteilt. Abstand, Connection-Art, Node-Typ und Zahl der Kontrollpunkte stehen in der Optionsleiste. Ein Wechsel der Variante beim Zeichnen behält Start und Ende.

### Parallele Spuren

`Umschalt+I` (Zeichnen → Parallel) legt neben jede ausgewählte Straße eine Spur, z. B. die zweite Spur eines Paars von Einbahnstraßen.

1. Die Straßen auswählen, vorher oder im Werkzeug: Rechtsziehen für ein Rechteck, `Umschalt` + Rechtsziehen für ein Lasso, `Strg`+Klick schaltet eine Node um, Rechtsklick leert die Auswahl.
2. Neben eine Straße zeigen. Die gestrichelte Vorschau folgt dem Zeiger, der Seite und Abstand bestimmt (in Schritten von 0,5 m, angezeigt in `Spurabstand`).
3. Klicken, um die Spuren dort anzulegen, oder `Enter` (`Anwenden`) drücken, um den Abstand aus dem Feld zu nehmen.

- Jede Straße bekommt ihre Spur auf derselben Seite ihrer eigenen Fahrtrichtung; so entstehen die Spuren mehrerer Einbahnstraßen auf einmal.
- Die Spur wird wie ihre Straße verbunden (Regular, Dual oder Reverse). `Richtung` wählt die gleiche oder die Gegenrichtung. `Abstand` und `Node-Typ` bestimmen die Nodes; sie bekommen die Geländehöhe oder die Höhe der Straße daneben.
- Die Enden bleiben offen, und die neuen Nodes werden nicht ausgewählt. Ein Rückgängig entfernt alle Spuren.
- Abgelehnt, mit einer Meldung: eine Abzweigung in der Auswahl, ein geschlossener Ring, eine Straße mit Connections verschiedener Art oder Richtung oder eine Kurve, die auf der Innenseite enger ist als der Abstand.

### Verschieben, drehen und ausrichten

- **Verschieben** (`V`): eine Node oder die Auswahl ziehen. `Umschalt` bewegt nur entlang einer Rasterachse. `S` schaltet das Einrasten am Raster.
- **Rotieren** (`R`): die Auswahl am Ring drehen. `Umschalt` rastet in Schritten ein (`Rasterschritt`, Standard 15°).
- **Position eingeben** (`P`): X/Y/Z einer Node eintippen.
- **Horizontal / vertikal ausrichten** (`H` / `J`): die Auswahl auf die Linie durch eine Referenz-Node legen.

### Höhen

- **Höhe wie Referenz** (`Y`): der Auswahl die Höhe einer Referenz-Node geben.
- **Höhe aus Heightmap** (`Umschalt+Y`): die Auswahl aufs Gelände setzen.

### Löschen

- **Node löschen** (`L`, oder `Entf` für die Auswahl): löscht Nodes und ihre Connections.
- **Löschen und verbinden** (`Umschalt+L`, oder `Umschalt+Entf` für die Auswahl): löscht Nodes mitten in einer Straße und verbindet ihre beiden Enden gleich: A→N→B wird A→B, Dual bleibt Dual. Abgelehnt bei Abzweigungen, Straßenenden und Connections verschiedener Art.

### Marker

`M` drücken und eine Node anklicken, um einen Marker mit Name und Gruppe hinzuzufügen. Ein neuer Gruppenname legt die Gruppe an. Die anderen Varianten:

- **Bearbeiten** (`Umschalt+M`): Name und Gruppe ändern.
- **Verschieben** (`Strg+M`): den Marker auf eine andere Node setzen.
- **Löschen** (`Strg+Umschalt+M`).

### Messen

`D` (Abstand) oder `Umschalt+D` (Winkel) drücken, dann Punkt A und Punkt B anklicken (eine Node oder freie Fläche). Einen Punkt ziehen, um ihn zu verschieben. `Ansicht an Linie ausrichten` dreht die Ansicht entlang der Linie. `Esc` ohne etwas zu löschen kehrt zum vorher benutzten Werkzeug zurück.

### Kopieren und einfügen

`Strg+C`, `Strg+X`, `Strg+V` kopieren, schneiden aus und fügen die Auswahl ein. `Strg+Umschalt+V` fügt an der Originalposition ein. Eingefügte Nodes bekommen die Geländehöhe am neuen Ort, außer `Beim Einfügen Höhen beibehalten` ist an, z. B. für eine Brücke oder Rampe.

### Rückgängig

`Strg+Z` macht jede Änderung rückgängig, `Strg+Y` stellt sie wieder her. Um etwas Größeres erst auszuprobieren, den [Planungsmodus](#planungsmodus) nutzen.

## Planen und Generatoren

### Planungsmodus

Ein Plan sammelt Änderungen, damit man sie ansehen kann, bevor man sie behält.

1. Den Planungsknopf am rechten Ende der Werkzeugleiste anklicken (`Strg+P`, `Bearbeiten → Planungsmodus`). Über der Karte erscheint ein blauer Balken.
2. Mit beliebigen Werkzeugen bearbeiten. Der Balken zählt die geänderten Nodes, die einen blauen Hof bekommen. Rückgängig und Wiederholen arbeiten innerhalb des Plans.
3. `Plan übernehmen` anklicken, um alles als einen Rückgängig-Schritt zu behalten, oder `Plan verwerfen`, um ihn wegzuwerfen.

Ein weiterer Klick auf den Planungsknopf, das Öffnen einer anderen Datei oder das Schließen des Editors fragt, ob übernommen oder verworfen werden soll. Solange ein Plan offen ist, kann nicht gespeichert werden; die Änderungen vor dem Plan werden gesichert, und die automatische Sicherung pausiert bis zum Ende des Plans.

### Das Werkzeug Erzeugen

`G` drücken und in der Optionsleiste (oder im Menü `Erzeugen`) eine Aufgabe wählen. Das Werkzeug startet den Planungsmodus von selbst.

| Aufgabe | Baut | Braucht |
| --- | --- | --- |
| [Route](#route) | eine befahrbare Route durch angeklickte Wegpunkte | ein Savegame |
| [Einmündung](#einmündung) | eine Kreuzungsbox oder Abbiegekurven von einer Straße in einen Hof | |
| [Stationen](#stationen) | Spuren mit Markern über den Haltestellen von Verkaufsstellen, Produktionen, Silos, Ställen | ein Savegame |
| [Straßen](#straßen) | AutoDrive-Straßen entlang der Verkehrsspuren der Karte | ein Savegame |
| [Parkplätze](#parkplätze) | Parkplätze mit Markern in Hallen | ein Savegame |
| [Fahrsilos](#fahrsilos) | Spuren mit Markern in Fahrsilos | ein Savegame |

Kurvenradius, Knotenabstand, Fahrzeugbreite und die Markermuster stellt man unter `Datei → Einstellungen → Generatoren` ein.

> **Tipp:** Erzeugte Spuren enden meist offen. Danach ans Netz anschließen, z. B. mit der Aufgabe Route.

### Route

Findet eine befahrbare Einbahn-Route durch Wegpunkte, um Gebäude, Zäune, Bäume und Wasser herum.

1. Die Aufgabe **Route** wählen.
2. Nodes, Connections oder freie Fläche nacheinander als Wegpunkte anklicken. Die Route wird gesucht und gezeigt; Teile, die Hindernisse kreuzen, sind rot.
3. Ändern: einen Wegpunkt oder eine beliebige Node ziehen, oder auf die Route drücken, um dort einen Wegpunkt zu setzen und ihn zu ziehen. Nach jeder Änderung wird neu gesucht.
4. `Enter` drücken, um sie dem Plan hinzuzufügen. Freie Wegpunkte werden zu Nodes; ein Wegpunkt auf einer Connection teilt sie mit einer neuen Node.

Danach beginnt das Werkzeug leer, und der nächste Klick wählt einen neuen Start.

**Wegpunkte bearbeiten.** Der Wegpunkt unter dem Mauszeiger wird hervorgehoben. `Entf` oder Rechtsklick entfernt ihn, die `Rücktaste` den letzten, `Esc` alle. `Strg+Z` nimmt zuerst Wegpunkt-Änderungen zurück, danach die Änderungen des Plans.

**Wie die Route gebaut wird.** Sie fährt nur vorwärts, wie ein von Hand gezeichneter Kurs: gerade Stücke, verbunden durch Bögen mit dem Kurvenradius. Die Nodes liegen so, wie AutoDrive eine Fahrt aufzeichnet: auf Geraden bis zum Knotenabstand (Standard 12 m) auseinander, in engen Kurven dichter. Sie hält die halbe Fahrzeugbreite plus einen Sicherheitsabstand von Hindernissen fern. Sie bevorzugt Straßen und Höfe, fährt um eine Wiese oder Obstwiese herum statt hindurch, quert Gras aber, wo das deutlich kürzer ist, und meidet Felder. Sie verlässt die erste und erreicht die letzte Node in der Richtung ihrer Connections. Nahe den Wegpunkten darf sie gesperrten Boden queren, da Nodes unter einem Dach oder in einer Halle liegen können.

**An andere Routen anschließen.** Routen, die schon im Plan sind, werden mitbenutzt: Eine Route in derselben Richtung schließt sich ihnen an. Der Rückweg bekommt eine eigene Spur, wo Platz ist, und teilt sich die Spur (als Dual), wo nicht.

**Mehrere Starts und Ziele.** `Umschalt`+Klick auf eine Node fügt einen weiteren Start hinzu, `Strg`+Klick ein weiteres Ziel. Der Editor sucht dann eine Route von jedem Start zu jedem Ziel und baut sie als Baum: Routen vom selben Start fahren zusammen und zweigen später ab, Routen zum selben Ziel vereinen sich.

- Ein Klick setzt einen Wegpunkt, den alle Routen teilen; bis dorthin fahren sie als eine.
- Drücken auf eine Route setzt einen Wegpunkt nur in diese Route oder in alle Routen, die dort zusammen fahren (auch bis 5 m hinter der Stelle, wo sie sich teilen).
- `Entf` oder Rechtsklick auf einen Start oder ein Ziel entfernt ihn mit seinen Routen.
- Während einer Suche werden alle Routen blass gezeichnet. `Enter` braucht alle Routen frei; die Statusleiste nennt die übrigen.

**Wenn keine Route gefunden wird.** Der Editor zeigt den befahrbaren Teil und eine rot gestrichelte Linie zum Wegpunkt, der nicht erreicht wurde; die Statusleiste nennt ihn. Dort Wegpunkte verschieben oder hinzufügen. Zwei Wegpunkte, die für den Kurvenradius zu nah liegen, werden genauso markiert. Schließt die Route an einer ungünstigen Node an (einer Marker-Node, einer ersten Node, zu der nichts führt, einer letzten Node, die nirgendwohin führt), sagt die Statusleiste das; hinzufügen lässt sie sich trotzdem.

**Die Befahrbarkeitskarte.** Die Routensuche nutzt die Karte, die der Landwirtschafts-Simulator bei jedem Speichern ins Savegame schreibt (`vehicleNavigationCostmap.dat`). Nach dem Platzieren von Gebäuden erneut im Spiel speichern, damit die Karte sie kennt. `Ansicht → Anzeigen → Befahrbarkeitskarte` zeigt sie: gesperrter Boden rot (in Wäldern blau), unwegsamer Boden orange, Gras gelb, Felder grün; Straßen und Höfe bleiben frei.

### Einmündung

Schließt eine Hofzufahrt an eine Straße an, mit einer Kreuzungsbox oder Abbiegekurven.

1. Die Aufgabe **Einmündung** wählen.
2. Auf die Straße drücken und zum Hof ziehen. Die Einmündung gleitet an der Straße entlang, und die Zufahrt wächst im rechten Winkel heraus.
3. Loslassen. Den Griff an der Spitze der Zufahrt ziehen, um sie zu biegen, oder auf einer Node ablegen, um dort anzuschließen.
4. `Enter` drücken (oder neben den Griff klicken), um die Einmündung dem Plan hinzuzufügen. `Esc` bricht ab.

`Strg+Z` beim Zeichnen macht zuerst eine gebogene Zufahrt wieder gerade, geht dann zum Setzen zurück und bricht danach ab.

| Option | Auswahl |
| --- | --- |
| Bauart | **Box** (Standard): eine kompakte Kreuzungsbox, wo eine Straße aus zwei Einbahnspuren auf eine Zufahrt mit zwei Spuren trifft. Die Spuren teilen sich eine Node, wo sie sich kreuzen, eine Mittel-Node nimmt Linksabbiegen und Wenden auf, kurze Kurven das Rechtsabbiegen. Die Stücke in der Box fahren in beide Richtungen, damit AutoDrive-Fahrer sich dort sehen. **Kurven**: je Richtung eine Einbahn-Abbiegekurve. |
| Zufahrt | **Automatisch** (Standard): zwei Spuren an einer Straße aus zwei Einbahnspuren, eine Spur in beide Richtungen an einer Straße in beide Richtungen. **Beide Richtungen** oder **Zwei Spuren** wählen direkt. **Einbahn hinein** / **Einbahn hinaus**: nur die Kurven in den Hof oder heraus, z. B. für einen Hof mit eigener Ausfahrt. |
| Spurabstand | Abstand zweier Spuren (Standard 5,5 m) |

Die Optionen bleiben für das nächste Mal gespeichert. Haben Straße oder Zufahrt keine zwei Einbahnspuren, entstehen Kurven statt einer Box, und die Statusleiste sagt das.

Die Kurven verlassen die Straße und münden in sie mit einem leichten Knick (20°) und biegen dann in einem Bogen mit dem Kurvenradius ab, wie die Abzweige handgemachter Kurse. Geht auf der anderen Seite eine Straße weiter, kommen Spuren geradeaus hinüber dazu.

**Wenn etwas nicht passt:** Kurven, die nach der Befahrbarkeitskarte nicht passen, sucht die Routensuche. Was dann noch gesperrt ist, wird rot gestrichelt gezeichnet und in der Statusleiste genannt, z. B. „Kein Linksabbiegen in den Hof aus Richtung Norden“. Den Rest kann man trotzdem hinzufügen.

### Stationen

Baut eine Einbahnspur mit Marker über jeder Haltestelle von Verkaufsstellen, Produktionen, Silos, Ställen und Dieseltanks.

1. Die Aufgabe **Stationen** wählen. Zeigt der Mauszeiger auf eine Station, erscheint ihr Name.
2. Einen Haltestellenpfeil oder die Fläche zwischen den Pfeilen eines Gebäudes anklicken, um alle seine Haltestellen zu wählen. Gebäude bis 15 m daneben werden mitgewählt (z. B. zwei Tankstellen nebeneinander). Oder mit rechts einen Rahmen (`Umschalt`: Lasso) um die Haltestellen ziehen.
3. Neben den Haltestellen öffnet sich ein Dialog. Er listet jede Haltestelle mit Häkchen, Art, Fruchtsorten, Markername und Gruppe, Spurwinkel und einem Hinweis (z. B. keine KI-Stelle im Gebäude oder eine vorhandene Node, wo die Spur hinkommt).
4. Bei Bedarf die Spuren auf der Karte anpassen (siehe unten).
5. `Anlegen` anklicken. Die Spuren kommen als ein Rückgängig-Schritt in den Plan.

Der Marker sitzt ein Stück hinter der Haltestelle (Standard 8 m): Der Traktor hält am Marker, und der Anhänger steht dann über dem Abladepunkt.

**Spuren anpassen.**

- Den Marker einer Spur ziehen, um die Spur um ihre Haltestelle zu drehen (`Umschalt`: 15°-Schritte), oder den Winkel eintippen.
- Die erste oder letzte Node ziehen, um dieses Ende in einem Bogen zu biegen, z. B. wo für eine gerade Spur kein Platz ist. Drehen macht die Spur wieder gerade.
- Ein Ende auf einer Node des Netzes ablegen, um die Spur dort anzuschließen; es muss zur Fahrtrichtung der Node passen. Nicht angeschlossene Enden bleiben offen.

**Hofstraße.** Für einen Hof mit mehreren Haltestellen, z. B. eine Produktion, `Hofstraße zeichnen` anklicken und eine Straße an ihnen vorbei zeichnen:

1. Ihre Ecken auf der Karte anklicken. Eine Ecke auf einer Node schließt die Straße dort an; Rechtsklick entfernt die letzte Ecke.
2. `Enter` drücken für eine Einbahnstraße von der ersten zur letzten Ecke. Oder eine frühere Ecke anklicken, um einen Ring zu schließen: Die Ecken bis zu ihr werden eine Straße in beide Richtungen hinein und hinaus, der Rest ein Einbahnring.
3. Die Ecken werden mit dem Kurvenradius abgerundet und lassen sich danach noch ziehen.

Die Spalte `Form` gibt dann an, wie jede Haltestelle an die Straße angeschlossen wird:

| Form | Bedeutung |
| --- | --- |
| Abzweig | eine Einbahnspur über die Haltestelle, die vor ihr von der Straße abzweigt und danach zurückführt |
| Kette | Haltestellen unter 15 m entlang der Straße teilen sich einen Abzweig |
| Rückwärts-Bucht | eine Linie vom Marker von der Straße weg und ein Stummel zum Vorbeifahren und Zurücksetzen. Standard für Tierställe |
| Spur | die Haltestelle behält ihre eigene Spur mit offenen Enden. Standard für Haltestellen mehr als 30 m von der Straße |

Der Hinweis sagt, wenn eine Form nicht passt. `Anlegen` fügt Straße, Abzweige, Buchten und Spuren als ein Rückgängig-Schritt ein. `Hofstraße entfernen` kehrt zu einer Spur je Haltestelle zurück.

**Namen.** `Generator-Einstellungen…` öffnet `Datei → Einstellungen → Generatoren`. Dort stellt man die Spurlänge vor der Haltestelle und nach dem Marker ein (Standard je 10 m), den Markerabstand, den Knotenabstand sowie Markername und Gruppe je Halteart. Namen sind Muster:

| Platzhalter | Wird zu |
| --- | --- |
| `{building}` | dem Namen des Gebäudes |
| `{type}` | der Halteart |
| `{fill}` | der ersten Fruchtsorte der Haltestelle |
| `{action}` | `abladen` oder `laden` |
| `{n}` | einer pro Gruppe gezählten Nummer, ab `Nummern beginnen bei`; `{n:03}` mit drei Ziffern |

Zum Beispiel `VK-{n:02}`, oder für Produktionen `{fill}-{action}` in `prod.{building}`, was `Diesel-abladen` in `prod.Destillerie` ergibt. Auch Gruppen sind Muster, ohne `{n}`. Ein Name, der in derselben Gruppe schon steht, wird nicht noch einmal vergeben.

### Straßen

Baut AutoDrive-Straßen entlang der Verkehrsspuren der Karte, auf denen der Verkehr des Spiels fährt.

1. Die Aufgabe **Straßen** wählen. Beim ersten Mal werden die Verkehrsspuren aus der Karte gelesen (mit Fortschrittsfenster und `Abbrechen`); sie erscheinen als dünne Linien.
2. Den **Modus** wählen:
   - **Ganze Karte**: `Anlegen` oder `Enter` drücken.
   - **Box**: mit rechts einen Rahmen ziehen. Die Straßen darin werden gebaut, am Rahmen abgeschnitten, mit den Kreuzungen, deren Mitte darin liegt.
   - **Straße anklicken**: eine Straße anklicken, um sie von Kreuzung zu Kreuzung zu bauen (die Kreuzungen selbst werden nicht gebaut).
3. Das Ergebnis in der Gruppe `Straßennetz` des Fensters `Netzprüfung` prüfen (siehe unten).

| Option | Auswahl |
| --- | --- |
| Vorhanden | **Überspringen und anschließen** (Standard): Vorhandene Straßen bleiben; neue entstehen nur, wo keine verläuft, und schließen an die vorhandenen Spuren an. Kreuzungen mit vorhandenen Nodes bleiben. **Ersetzen**: Vorhandene Regular-Nodes entlang der neuen Straßen werden entfernt, auch in Kreuzungsboxen; Abzweige schließen an die neuen Spuren an, und Marker wandern auf die nächste neue Node. Subprio-Spuren werden nie entfernt. |
| Spuren | **Zwei Einbahnspuren** (im Spurabstand der Aufgabe Einmündung), **Beide Richtungen** oder **Automatisch** (Standard): was das Netz größtenteils nutzt, in einem leeren Netz zwei Einbahnspuren |

Wo drei oder vier Straßen in beide Richtungen zusammentreffen, entsteht eine Kreuzungsbox wie bei der Aufgabe Einmündung (bei Spuren in beide Richtungen treffen sich die Straßen in einer gemeinsamen Node). Andere Kreuzungen wie Kreisverkehre, Abfahrten und Gabelungen nutzen die Spuren der Karte. Das Ergebnis kommt als ein Rückgängig-Schritt in den Plan.

**Das Ergebnis prüfen.** Der Editor prüft, ob jeder Abbiegeweg, den der Verkehr durch eine Kreuzung nehmen darf, befahrbar ist, ob die neuen Spuren weiterführen und erreicht werden und ob sie gesperrten Boden meiden. Stellen zum Ansehen werden gelistet, z. B. „Keine Kreuzungsbox“, „Bestehende Kreuzung beibehalten“, „2 von 6 Abbiegewegen fehlen“, „Sackgasse“ oder „Straßenende nicht mit dem Netz verbunden“; ein Klick zeigt die Stelle. Stellen am Rand eines Rahmens oder einer angeklickten Straße werden nicht gelistet, da die Straßen dort absichtlich enden.

Auf Karten ohne Verkehrsspuren geht diese Aufgabe nicht. Besteht das Verkehrsnetz einer Karte nur aus wenigen Schleifen ohne Kreuzungen, bittet die Statusleiste, die Straßen an den Kreuzungspunkten zu prüfen.

### Parkplätze

Legt AutoDrive-Parkplätze in den Hallen eines Savegames an.

1. Die Aufgabe **Parkplätze** wählen. Zeigt der Mauszeiger auf eine Halle, erscheinen Name und Kategorie.
2. Einen Hallenumriss anklicken. Für mehrere Hallen eines Typs diese mit `Umschalt`+Klick sammeln und `Enter` drücken, oder mit rechts einen Rahmen um sie ziehen. `Esc` verwirft die Auswahl.
3. Die Parkplätze im Dialog einstellen. Seine Draufsicht zeigt die Halle mit der offenen Seite unten und einem Pfeil nach Norden; die geplanten Plätze erscheinen auch auf der Karte. Die Karte lässt sich dabei verschieben und zoomen, aber nicht bearbeiten.
4. `Anlegen` anklicken. Alle Nodes entstehen als Subprio-Nodes auf der Höhe der Halle, als ein Rückgängig-Schritt.
5. Die vier offenen Enden von Zufahrts- und Abfahrtslinie ans Netz anschließen.

| Einstellung | Bedeutung |
| --- | --- |
| Modus | **Rückwärts einparken**: Die Fahrzeuge setzen rückwärts in den Stellplatz; der Marker liegt an der Rückwand. **Durchfahren**: eine Vorwärtslinie je Stellplatz; die Ausfahrt liegt gegenüber. |
| Offene Seite / Einfahrtseite | wo die Fahrzeuge hereinkommen. Zum Ändern eine Seite oder ihre Himmelsrichtung in der Draufsicht anklicken. |
| Anzahl Stellplätze | daraus wird die Stellplatzbreite berechnet. Stellplätze unter 3 m sind rot und lassen sich nicht anlegen. |
| Linke Wand, Rechte Wand, Rückwand (bzw. Abstand zur Ausfahrt), Alle Zwischenräume | Abstände in Metern. Eine Wand oder einen Zwischenraum in der Draufsicht anklicken, um nur diesen zu ändern (`Enter` übernimmt, `Esc` bricht ab). Einzeln geänderte Zwischenräume bleiben, wenn sich die Anzahl der Stellplätze ändert. |
| Parkpositionen pro Stellplatz, Abstand der Parkpositionen | nur Durchfahren: mehrere Parkpositionen hintereinander, jede mit eigenem Marker, die erste am Abstand zur Ausfahrt |
| Zufahrtslinie, Abfahrtslinie | die Fahrtrichtung der beiden Linien draußen, von außen gesehen |
| Markername, Startnummer, Gruppe | „Halle“ ab 3 ergibt „Halle 3“, „Halle 4“, … Bei mehreren Positionen pro Stellplatz zählen die Nummern durch jeden Stellplatz, ab der Ausfahrt. |

**Seitenansicht** (Rückwärts einparken): zeigt die Linie eines Stellplatzes, die für alle gilt. Ein Segment anklicken, um seine Länge zu ändern; „+“ teilt es, `Entf` löscht die ausgewählte Node. Die Punkte, an denen Zufahrts- und Abfahrtslinie abzweigen, lassen sich auf eine andere Node ziehen. Beim Durchfahren zeigt die Seitenansicht die Linie nur an.

**Mehrere Hallen.** Die Einstellungen gelten für alle gewählten Hallen; `Halle:` wählt, welche die Ansichten zeigen. Benachbarte Hallen in gleicher Richtung (bis 10° Unterschied, offene Seiten bis 3 m versetzt, höchstens 5 m auseinander) bilden eine Reihe und teilen sich eine Zufahrts- und eine Abfahrtslinie. Die Markernummern zählen Reihe für Reihe weiter, von links nach rechts von der offenen Seite gesehen: zwei Hallen mit je vier Stellplätzen ergeben „Halle 1“ … „Halle 8“. Hallen verschiedener Typen lassen sich nicht zusammen wählen.

**Vorlagen.** `Als Vorlage speichern…` speichert Modus, Seite, Stellplätze, Abstände, Positionen und Stellplatzlinie unter einem Namen für diesen Hallentyp; so gilt sie für dasselbe Gebäude auf jeder Karte. Linienrichtungen, Markername, Startnummer und Gruppe werden nicht gespeichert. `Vorlage laden…` listet die Vorlagen; dort lassen sie sich auch löschen. Der Dialog öffnet mit der zuletzt benutzten Vorlage. `Halleneinstellungen zurücksetzen` stellt die Standardaufteilung wieder her.

> **Hinweis:** Zweimal `Anlegen` legt die Parkplätze zweimal an.

### Fahrsilos

Legt die Spuren von Fahrsilos an, mit Markern.

1. Die Aufgabe **Fahrsilos** wählen. Zeigt der Mauszeiger auf ein Silo, erscheint der Name seines Gebäudes.
2. Einen Siloumriss anklicken. Für mehrere diese nacheinander mit `Umschalt`+Klick wählen (gewählte werden dunkler; ein weiterer `Umschalt`+Klick nimmt eines heraus) und `Enter` drücken, oder mit rechts einen Rahmen ziehen (`Umschalt`: Lasso), was den Dialog gleich öffnet. `Esc` verwirft die Auswahl.
3. Die Einstellungen anpassen. Der Dialog ist der von [Parkplätze](#parkplätze), mit den Spuren des Silos als Stellplätzen.
4. `Anlegen` anklicken. Die Spuren entstehen als Subprio-Nodes auf der Höhe des Silos, als ein Rückgängig-Schritt.
5. Die Enden von Zufahrts- und Abfahrtslinie ans Netz anschließen.

Der Dialog beginnt mit der Aufteilung des Silos:

- **Modus und offene Seite** kommen aus der Befahrbarkeitskarte: Ein an einem Ende geschlossenes Silo ist *Rückwärts einparken* vom anderen Ende, ein an beiden Enden offenes *Durchfahren*. Ohne Befahrbarkeitskarte: rückwärts einparken von vorn.
- **Anzahl Spuren**: eine Spur je etwa 5,5 m Innenbreite.
- **Rückwärts einparken**: Der Marker liegt 3 m vor der Rückwand. Die Fahrzeuge wenden etwa 31 m vor dem Silo, setzen zum Marker zurück und fahren vorwärts hinaus. Die Zufahrtslinie liegt etwa 5,5 m, die Abfahrtslinie etwa 22 m vor dem Silo.
- **Durchfahren**: Spuren von etwa 20 m vor dem Silo bis zu einem Marker hinter ihm (Standard 15 m), ohne Abfahrtslinie.
- **Markername und Gruppe** sind Muster mit `{building}`, `{letter}` (der Buchstabe des Silos A, B, … entlang der offenen Seite) und `{n}` (die Nummer der Spur von einer Wand zur anderen). Standard: `KS-{letter}-{n}` in `{building}-KS-{letter}` beim Rückwärts einparken, `DS-{letter}-{n}` in `{building}-DS-{letter}` beim Durchfahren (änderbar unter `Datei → Einstellungen → Generatoren`). Der Text unter den Einstellungen listet die Marker je Gruppe. Namen, die sich wiederholen, lassen sich nicht anlegen.
- **Silo** (bei mehreren Silos): welches Silo die Ansichten zeigen.

Reihen benachbarter Silos teilen sich eine Zufahrts- und eine Abfahrtslinie, wie bei Hallen. Vorlagen gelten je Silotyp.

## Die Karte darunter

### Hintergrund

`Ansicht → Hintergrund` (oder der Knopf Hintergrund der Werkzeugleiste) wählt, was unter dem Netz liegt:

- **Kartenbild**: das Kartenbild des Karten-Mods.
- **Bodenkarte**: aus den Bodentexturen der Karte gezeichnet. Asphalt, Beton, Schotter, Gras, Matsch, Wald, Fels und Sand bekommen je eine Farbe, dazu Feldgrenzen und Feldnummern. Sie zeigt die Karte so, wie das Spiel sie bemalt, was hilft, wo das Kartenbild veraltet ist. Mit einer älteren Version des Editors importierte Karten haben keine Bodenkarte; dafür die Karte unter `Datei → Einstellungen → Karten` neu importieren (etwa 15 Sekunden bei einer 16x-Karte).
- **Spielbild**: siehe unten.

### Spielbild

Das Spielbild ist die Karte, wie das Spiel sie von oben zeichnet: schärfer und aktueller als das Kartenbild, mit den eigenen Höfen, Straßen und Gebäuden so, wie sie im Savegame sind. Es braucht den [Begleit-Mod](#begleit-mod). Der Editor speichert es pro Karte und Savegame.

**Aufnehmen**

1. Das Spiel mit aktivem Mod starten und das Savegame laden. Dasselbe Savegame im Editor öffnen.
2. `Ansicht → Hintergrund → Spielbild aufnehmen…` wählen. Oben im Dialog steht, ob das Spiel verbunden ist; nur dann geht `Start`.
3. Die Auflösung wählen: 0,25 m/px (schärfer) oder 0,5 m/px (schneller, kleiner). Zu jeder stehen Kachelzahl, Zeit und Speicherplatz.
4. `Start` anklicken.

Während der Aufnahme im Spiel weder die Kamera bewegen noch Menüs öffnen. Das Spiel wird auf 12:00 Uhr und Sonne gestellt und friert für jede Kachel kurz ein. Danach (auch nach `Abbrechen` oder einem Fehler) bekommt es sein Wetter zurück, und seine Uhr läuft ab der alten Zeit plus der Dauer der Aufnahme weiter.

Der Editor bleibt währenddessen bedienbar. Die Statusleiste zeigt den Fortschritt (`Spielbild 37/289 · noch 4 Min.`) mit einer Schaltfläche `Abbrechen`, und die Kacheln erscheinen auf der Karte, sobald sie ankommen. Bis dahin aufgenommene Kacheln bleiben. Beim Öffnen einer anderen Datei oder Schließen des Editors fragt er, ob die Aufnahme abgebrochen werden soll.

> **Tipp:** Haben Kacheln Löcher, `Wartezeit pro Kachel` erhöhen: die Zeit, die das Spiel bekommt, um einen Ort zu laden, bevor es ihn rendert.

Eine Aufnahme in der anderen Auflösung ersetzt das aktuelle Bild. Wo nichts aufgenommen wurde, scheint das Kartenbild durch. Das Bild bleibt erhalten, auch wenn das Savegame gelöscht wird.

**Kacheln nach einer Änderung auf der Karte erneuern**

1. `Spielbild-Kacheln erneuern` anklicken (Werkzeugleiste oder `Ansicht → Hintergrund`). Das Kachelraster erscheint. Das Spiel muss wie bei einer Aufnahme verbunden sein.
2. Kacheln anklicken oder mit rechts einen Rahmen ziehen, um sie zu markieren; `Strg` + Rechtsziehen hebt die Markierung auf. Die Statusleiste zeigt Kachelzahl und Zeit.
3. `Enter` drücken. Die neuen Kacheln ersetzen die alten, sobald sie ankommen. `Esc` löscht die Markierungen und beendet dann das Werkzeug.

### Gebäude des Savegames

Bei geöffnetem Savegame liest der Editor seine Gebäude. Die Generatoren bauen darauf auf. Eine allein geöffnete Route hat keine.

- **Hallen** (`Ansicht → Anzeigen → Hallen`): die Innenbereiche der Gebäude als lila Umrisse, die im Spiel gebauten und die der Karte, sofern nicht abgerissen.
- **Fahrsilos** (`Ansicht → Anzeigen → Fahrsilos`): der Boden zwischen den Wänden als türkiser Umriss.
- **Stationen** (`Ansicht → Anzeigen → Stationen`): ein gelber Pfeil an jeder Haltestelle, an der Fahrzeuge abladen oder laden: Verkaufsstellen, Produktionen, Silos, Ställe und Dieseltanks.

Die Gebäudedateien werden aus dem Spiel und dem Mods-Ordner gelesen; Gebäude, deren Dateien fehlen, werden weggelassen und in der Statusleiste gezählt. Das Gelesene behält der Editor in `%APPDATA%\AutoDrive Editor\cache`, sodass ein Savegame beim zweiten Mal schneller öffnet.

**Wohin die Haltestellenpfeile zeigen.** Die meisten Gebäude legen die Stelle fest, die der KI-Helfer des Spiels anfährt; dort sitzt der Pfeil. Hat ein Gebäude keine (viele Dieseltanks und Ställe), sitzt er auf dem Trigger. Mit einer Befahrbarkeitskarte nimmt der Pfeil die Richtung mit dem meisten freien Platz, und alle Haltestellen eines Gebäudes umrunden es gegen den Uhrzeigersinn, sodass eine Route an allen vorbeiführen kann. Er kann trotzdem falsch sein; die Spur lässt sich beim Anlegen drehen. Trigger einer Art fast an derselben Stelle (einer je Füllart) werden als eine Haltestelle gezeigt.

**Gebäudetypen.** `Erzeugen → Gebäudetypen…` listet die Gebäudetypen des Savegames in vier Gruppen: Stationen, Hallen, Fahrsilos und Sonstige. Eine Produktion mit Halle ist eine Station, keine Halle; Wohnhäuser und Waagen stehen unter Sonstige. Steht ein Typ in der falschen Gruppe, in seiner Spalte `Gruppe` eine andere wählen. Nicht angehakte Typen oder Gruppen werden ausgeblendet. `Zurücksetzen` setzt jeden Typ zurück und zeigt ihn an. Beides gilt auf jeder Karte.

### Darstellungsoptionen

`Ansicht → Anzeigen` blendet jedes davon ein und aus: Nodes, Node-IDs (erst beim Hineinzoomen), jede Connection-Art, Marker, Markernamen, Parkpositionen der Fahrzeuge (ein „P“ neben dem Marker, aus der `vehicles.xml` des Savegames), Hallen, Fahrsilos, Stationen, die Befahrbarkeitskarte und den Maßstab. Pfeile zeigen die Fahrtrichtung; Dual-Connections bekommen an jedem Ende einen.

`Ansicht → Darstellungsoptionen…` stellt Größen und Farben ein, dazu `Ausgeblendete Elemente auswählbar`. Alle Einstellungen bleiben gespeichert.

## Begleit-Mod

Der Editor funktioniert ohne jeden Mod. Der kleine Begleit-Mod **FS25_AutoDriveEditorLink** verbindet ihn mit dem laufenden Spiel und bringt zwei Dinge:

- **Spielbild**: Das Spiel rendert die Karte von oben, und der Editor zeigt sie als Hintergrund. Siehe [Spielbild](#spielbild).
- **Neu laden beim Speichern**: Speichert man das Savegame, das im Spiel läuft, fährt AutoDrive sofort auf dem neuen Netz. Ohne den Mod behält das Spiel sein altes Netz und überschreibt die Änderungen beim nächsten Speichern.

### Installieren

1. `FS25_AutoDriveEditorLink.zip` vom [neuesten Release](https://github.com/SvenBrauns/FS25_AutoDriveEditorLink/releases/latest) herunterladen.
2. Die Zip-Datei in den `mods`-Ordner legen (meist `Dokumente\My Games\FarmingSimulator2025\mods`). Nicht entpacken und nicht umbenennen.
3. Das Spiel starten, das Savegame auswählen und den Mod in der Mod-Liste aktivieren, dann das Savegame laden.

Für ein Update die Zip-Datei durch die neue ersetzen.

### Verbindung prüfen

Das Savegame im Spiel laden und dasselbe Savegame im Editor öffnen. `Ansicht → Hintergrund → Spielbild aufnehmen…` wählen: Oben im Dialog steht, ob das Spiel verbunden ist.

Steht dort, dass das Spiel nicht verbunden ist:

- Ist der Mod in diesem Savegame aktiv?
- Ist im Spiel dasselbe Savegame geladen wie im Editor?
- Ist der Spielordner unter `Datei → Einstellungen → Allgemein` der, den das Spiel nutzt?

> **Hinweis:** Editor und Mod tauschen sich über Dateien im Ordner `modSettings\FS25_AutoDriveEditorLink` des LS25-Benutzerordners aus. Nichts wird über das Internet gesendet.

## Prüfen und Speichern

### Netzprüfung

`Prüfen → Netz prüfen` öffnet das Fenster `Netzprüfung` und listet:

- übereinanderliegende Nodes,
- Nodes außerhalb der Karte,
- Nodes, deren Höhe zu stark vom Gelände abweicht (mit Heightmap),
- ungültige Connections: auf eine nicht vorhandene Node, auf die Node selbst oder ein eingehender Eintrag ohne den ausgehenden Eintrag der anderen Node,
- Nodes ganz ohne Connections.

Der Abstand für übereinanderliegende Nodes und der erlaubte Höhenunterschied werden oben im Fenster eingestellt. Ein Klick auf einen Eintrag zeigt ihn auf der Karte.

**Beheben.** `Auswahl beheben` oder `Alle beheben` führt übereinanderliegende Nodes zusammen (die Node mit Marker bleibt, sonst die mit der kleinsten ID), verschiebt Nodes zurück auf die Karte, setzt Höhen aus der Heightmap, entfernt ungültige Verweise und löscht Nodes ohne Connections (Nodes mit Marker bleiben). Jede Art von Korrektur ist ein Rückgängig-Schritt.

**Ignorieren.** Einträge, die so in Ordnung sind, z. B. Nodes auf einer Brücke, lassen sich mit `Ignorieren` ausblenden. Sie wandern in die Gruppe `Ignoriert` und werden von `Alle beheben` nicht verändert; `Nicht ignorieren` holt sie zurück. Ein ignorierter Eintrag erscheint wieder, wenn eine seiner Nodes verschoben wird. Die Kontrollkästchen schalten eine ganze Prüfung aus. Beides wird je Route oder Savegame gespeichert.

Beim Speichern läuft zuerst die Prüfung. Findet sie Probleme, die nicht ignoriert sind, zeigt das Fenster sie an und der Editor fragt, ob trotzdem gespeichert werden soll.

### Speichern

`Datei → Speichern` (`Strg+S`) schreibt in die geöffnete Datei. Vor dem ersten Überschreiben entsteht eine Sicherungskopie (`.bak`).

**Ein Savegame speichern** schreibt seine `AutoDrive_config.xml` und passt die Markerziele seiner Fahrzeuge in der `vehicles.xml` an. Haben Fahrzeuge einen gelöschten Marker als Ziel, listet der Editor sie und fragt zuerst; beim Speichern wird ihr Ziel auf Marker 1 gesetzt und ein Parkziel entfernt. Dann:

- **Spiel läuft mit diesem Savegame und dem Begleit-Mod:** Das Netz wird im Spiel neu geladen, und die Statusleiste zeigt `Gespeichert · im Spiel neu geladen`. Netzänderungen, die seit dem Öffnen im Spiel gemacht wurden, werden ersetzt. Meldet das Spiel einen Fehler oder antwortet es nicht innerhalb von 30 Sekunden, sagt eine Meldung, dass die Datei gespeichert, aber nicht neu geladen ist.
- **Spiel läuft ohne den Mod:** Eine Warnung sagt, dass das Spiel die Datei beim nächsten Speichern überschreibt. Das Spiel ohne Speichern beenden oder den [Begleit-Mod](#begleit-mod) installieren.
- **Spiel geschlossen:** Das neue Netz ist da, wenn das Savegame das nächste Mal geladen wird.

**Eine Route speichern** schreibt nur die Routendatei. Um sie in einem laufenden Spiel zu nutzen, im RoutesManager von AutoDrive `Import` drücken und im Spiel speichern.

**Wenn das Spiel die Datei geändert hat.** Hat sich das Netz in der Datei seit dem Öffnen oder letzten Speichern geändert, meist weil das Spiel gespeichert hat, warnt Speichern zuerst: `Trotzdem speichern` überschreibt die Änderungen des Spiels, `Neu laden (meine Änderungen gehen verloren)` lädt die Datei neu, `Abbrechen` tut nichts. `Datei → Neu laden` (`F5`) lädt die geöffnete Datei jederzeit neu und behält die Ansicht; bei ungespeicherten Änderungen fragt der Editor vorher.

### Routen im RoutesManager

- **Als Route speichern…** (`Strg+Umschalt+S`) bewahrt eine Version des Netzes als Route auf. Vorgeschlagen wird der Name der zuletzt gespeicherten oder geladenen Route, sonst der Kartenname. Bei einem vorhandenen Namen fragt der Editor vor dem Ersetzen; die Revision steigt dann. Ein Savegame bleibt danach geöffnet; eine Route oder XML-Datei geht als die gespeicherte Route weiter.
- **Route ins Savegame laden…** (bei geöffnetem Savegame) ersetzt das Netz durch eine Route derselben Karte, als ein Rückgängig-Schritt. Ist das aktuelle Netz noch nicht als Route gespeichert, bietet der Editor das zuerst an. Fahrzeuge behalten ihre Ziele an Markern mit demselben Namen und derselben Gruppe. Speichern schreibt die Route dann ins Savegame und lädt sie im Spiel neu.

### Automatische Sicherung

Ungespeicherte Änderungen werden alle paar Minuten gesichert (Abstand unter `Datei → Einstellungen`). Wird der Editor unerwartet beendet, bietet er beim nächsten Start an, sie wiederherzustellen.

## Nachschlagen

### Alle Werkzeuge und Tasten

Alle Tasten lassen sich unter `Datei → Einstellungen → Tastenkürzel` ändern. Ein Klick auf ein Werkzeug in der Spalte wählt es mit der zuletzt benutzten Variante.

| Werkzeug | Taste | Was es tut |
| --- | --- | --- |
| Auswahl | `A` | Nodes auswählen, siehe [Auswählen](#auswählen) |
| Verschieben | `V` | Nodes ziehen; `Umschalt` entlang einer Rasterachse |
| Erzeugen | `G` | Generatoren, siehe [Das Werkzeug Erzeugen](#das-werkzeug-erzeugen) |
| Anlegen (Regular / Subprio) | `E` / `Umschalt+E` | Eine Node anlegen oder in eine Connection einfügen |
| Verbinden (Regular / Dual / Reverse) | `1` / `2` / `3` | Nodes nacheinander verbinden; zeichnet eine Straße |
| Löschen (Node / Verbinden) | `L` / `Umschalt+L` | Nodes löschen, oder löschen und die Enden verbinden |
| Typ wechseln | `T` | Regular ↔ Subprio |
| Richtung umkehren | `U` | Eine Connection umdrehen |
| Rotieren | `R` | Die Auswahl drehen |
| Position eingeben | `P` | Koordinaten einer Node eintippen |
| Horizontal / vertikal ausrichten | `H` / `J` | Die Auswahl auf eine Linie legen |
| Höhe wie Referenz / aus Heightmap | `Y` / `Umschalt+Y` | Höhen der Auswahl setzen |
| Zeichnen (Linie / Kreisbogen / Bézier / Parallel) | `I` / `K` / `B` / `Umschalt+I` | Linien, Kurven und parallele Spuren |
| Marker (Hinzufügen / Bearbeiten / Verschieben / Löschen) | `M` / `Umschalt+M` / `Strg+M` / `Strg+Umschalt+M` | Marker |
| Messen (Abstand / Winkel) | `D` / `Umschalt+D` | Zwischen zwei Punkten messen |

| Befehl | Taste |
| --- | --- |
| Öffnen / Speichern / Als Route speichern | `Strg+O` / `Strg+S` / `Strg+Umschalt+S` |
| Datei neu laden | `F5` |
| Rückgängig / Wiederholen | `Strg+Z` / `Strg+Y` |
| Kopieren / Ausschneiden / Einfügen / An Originalposition einfügen | `Strg+C` / `Strg+X` / `Strg+V` / `Strg+Umschalt+V` |
| Alles auswählen | `Strg+A` |
| Auswahl löschen / und verbinden | `Entf` / `Umschalt+Entf` |
| Am Raster einrasten | `S` |
| Marker oder Node suchen | `Strg+F` |
| Planungsmodus | `Strg+P` |
| Ganze Karte anzeigen / Auf Auswahl zoomen | `Pos1` / `F` |
| Anleitung | `F1` |

### Einstellungen

`Datei → Einstellungen…` hat vier Reiter:

- **Allgemein**: Sprache (Deutsch oder Englisch, nach einem Neustart; beim ersten Start deutsch auf einem deutschen Windows), Design (wie Windows, hell oder dunkel), Abstand der automatischen Sicherung, Öffnen der letzten Datei beim Start, Suche nach Updates beim Start und die Spielordner.
- **Karten**: die importierten Karten mit Mod, Größe, Heightmap und Spielbild.
  - `Neu importieren` liest die gewählten Karten erneut (mehrere mit `Strg` oder `Umschalt`+Klick; läuft im Hintergrund, `Abbrechen` hört nach der aktuellen Karte auf).
  - `Entfernen` löscht die importierte Karte und ihr Spielbild.
  - `Aus Mod-Zip importieren…` importiert eine Karte aus einer Zip-Datei an beliebiger Stelle.
  - `Diese Karte für die offene Datei verwenden` legt die gewählte Karte unter die offene Datei; das merkt sich der Editor für die Datei.
- **Generatoren**: Kurvenradius (Standard 6 m) und Knotenabstand auf Geraden (Standard 12 m) für Route, Einmündung und Stationen; Fahrzeugbreite und Sicherheitsabstand für Route; Spurlängen und Markermuster der [Stationen](#stationen); Markermuster der [Fahrsilos](#fahrsilos).
- **Tastenkürzel**: die Tasten aller Menüeinträge und Werkzeuge, ein Eintrag pro Werkzeugvariante.

### Updates

`Hilfe → Nach Updates suchen` fragt bei GitHub nach, ob es eine neuere Version gibt. Die Suche bei jedem Start ist anfangs aus, weil sie sich mit github.com verbindet. Für ein Update die Zip-Datei von der Release-Seite herunterladen und den alten Programmordner damit ersetzen; Einstellungen und importierte Karten bleiben erhalten.

### Hilfe und Fehler

- `Hilfe → Anleitung` (`F1`) öffnet diese Anleitung in der Sprache des Editors; `Hilfe → Versionsverlauf` zeigt, was sich geändert hat (auf Englisch); `Hilfe → Über` zeigt Version und Lizenz.
- Tritt ein unerwarteter Fehler auf, zeigt der Editor eine Meldung und läuft weiter. Die Details stehen in einer Log-Datei: `Hilfe → Log-Ordner öffnen` (`%APPDATA%\AutoDrive Editor\logs`). Bitte bei Fehlermeldungen anhängen.
- `Hilfe → Debug-Log` schreibt ausführliche Einträge ins Log, z. B. zu jeder Routensuche (Start, Ziel, Richtungen, warum keine Route gefunden wurde). Einschalten, das Problem wiederholen und das Log anhängen.
- `Hilfe → Debuganzeige` zeigt Laufzeitwerte wie die Zahl der Nodes und der zwischengespeicherten Kartenkacheln.
