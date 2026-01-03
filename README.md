# din12831-heatload

Kleines, community-freundliches Tool zur **raumweisen Heizlastberechnung** (MVP) auf Basis von Python + Streamlit.

> Hinweis: Aktuell ist das ein MVP ohne normgerechte Report-Ausgabe.

## Was macht diese Anwendung?

Diese Anwendung berechnet die **Heizlast nach DIN EN 12831** für Gebäude auf Raumebene. Sie ermöglicht die systematische Erfassung von:

- **Räumen** mit individuellen Grundflächen, Raumhöhen und Raumtemperaturen
- **Bauteilen** (Wände, Fenster, Türen, Böden, Decken) mit U-Werten und Abmessungen
- **Temperaturen** für Innen- und Außenbereiche sowie angrenzende Räume

Die Anwendung berechnet:
- **Transmissionswärmeverluste** über alle Bauteile (berücksichtigt U-Werte, Flächen und Temperaturdifferenzen)
- **Lüftungswärmeverluste** basierend auf Luftwechselrate und Raumvolumen
- **Gesamte Heizlast** pro Raum und für das gesamte Gebäude

## Hauptfunktionen

Die Anwendung ist in fünf Tabs strukturiert:

### 📐 Räume
- Räume anlegen mit Namen, Flächen (mehrere Flächen möglich) und Raumhöhe
- Raumtemperatur zuweisen
- Lüftungskonzept definieren (Luftwechselrate n50)
- Wände, Fenster und Türen hinzufügen
- Boden und Decke mit angrenzenden Temperaturen zuweisen
- Pro Raum wird die Heizlast direkt angezeigt

### 🏗️ Bauteilkatalog
- Konstruktionen für Wände, Fenster, Türen, Böden und Decken anlegen
- U-Werte und Wandstärken definieren
- Wiederverwendbare Konstruktionen für alle Räume
- Vorgefertigte Bauteile können angelegt und mehrfach verwendet werden

### 🌡️ Temperaturen
- Temperaturen definieren (z.B. Wohnraum 20°C, Außen -12°C, Keller 10°C)
- **Normaußentemperatur** festlegen für die Heizlastberechnung
- **Standard-Raumtemperatur** für neue Räume definieren
- Temperaturen für angrenzende unbeheizte Räume

### 📊 Report
- Übersicht aller Räume mit berechneten Heizlasten
- Aufschlüsselung nach Transmission und Lüftung
- Gesamte Gebäude-Heizlast in W und kW
- Tabellarische Darstellung aller Ergebnisse
- Detailansicht mit Bauteil-Aufschlüsselung möglich

### 🔍 Debug
- JSON-Ausgabe der gesamten Gebäude-Datenstruktur
- Nützlich für Entwicklung und Fehlersuche

## Typischer Workflow

1. **Temperaturen definieren** (Tab 🌡️ Temperaturen)
   - Normaußentemperatur festlegen (z.B. -12°C für Ihre Region)
   - Raumtemperaturen anlegen (z.B. Wohnraum 20°C, Bad 24°C)
   - Optional: Temperaturen für unbeheizte Bereiche (Keller, Dachboden)

2. **Bauteilkatalog erstellen** (Tab 🏗️ Bauteilkatalog)
   - Außenwände mit U-Werten definieren
   - Fenster und Türen anlegen
   - Boden- und Deckenkonstruktionen

3. **Räume anlegen** (Tab 📐 Räume)
   - Raum mit Grundfläche und Höhe anlegen
   - Raumtemperatur und Lüftung festlegen
   - Wände mit Ausrichtung und Abmessungen hinzufügen
   - Fenster und Türen in Wänden platzieren
   - Boden und Decke mit angrenzenden Temperaturen zuweisen

4. **Ergebnisse prüfen** (Tab 📊 Report)
   - Heizlast für jeden Raum einsehen
   - Gesamte Gebäude-Heizlast ablesen
   - Detailansicht für einzelne Räume öffnen

## Gebäude-Einstellungen

In der Sidebar können globale Einstellungen vorgenommen werden:
- **Gebäudename**: Bezeichnung des Projekts
- **U-Wert-Korrekturfaktor**: Zuschlag für Wärmebrücken (Standard: 0.05)
- **Gebäudeübersicht**: Anzahl Räume, Konstruktionen und Temperaturen

## DevContainer (empfohlen)

1. In VS Code: **Reopen in Container**
2. Im Container-Terminal:

```bash
streamlit run app.py
```

Dann öffnet VS Code automatisch den weitergeleiteten Port **8501**.

## Lokal (optional)

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
