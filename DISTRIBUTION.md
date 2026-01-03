# 📦 Standalone Distribution - DIN 12831 Heizlast

## Für Entwickler: Executable erstellen

### Voraussetzungen
- Python 3.9+
- Virtual Environment aktiviert
- Alle Dependencies installiert

### Build-Prozess

1. **Build-Script ausführbar machen:**
   ```bash
   chmod +x build_standalone.sh
   ```

2. **Executable bauen:**
   ```bash
   ./build_standalone.sh
   ```

3. **Fertige Executable befindet sich in:**
   ```
   dist/din12831-heatload
   ```

### Manueller Build (ohne Script)

```bash
# PyInstaller installieren
pip install pyinstaller

# App bauen
pyinstaller app.spec --clean
```

---

## Für Endbenutzer: App ausführen

### Linux

1. **Executable herunterladen**
   - Datei: `din12831-heatload`

2. **Ausführbar machen (nur einmal):**
   ```bash
   chmod +x din12831-heatload
   ```

3. **App starten:**
   ```bash
   ./din12831-heatload
   ```

4. **Browser öffnet sich automatisch** auf `http://localhost:8501`

### Windows

1. **Executable herunterladen**
   - Datei: `din12831-heatload.exe`

2. **Doppelklick auf die Datei** oder
   ```cmd
   din12831-heatload.exe
   ```

3. **Browser öffnet sich automatisch** auf `http://localhost:8501`

### App beenden

- Im Terminal: `Ctrl+C`
- Oder einfach das Terminal-Fenster schließen

---

## Troubleshooting

### "Permission denied" (Linux)
```bash
chmod +x din12831-heatload
```

### "Port bereits belegt"
Die App versucht standardmäßig Port 8501. Falls belegt:
1. Anderen Prozess beenden
2. Oder manuell anderen Port nutzen:
   ```bash
   ./din12831-heatload -- --server.port 8502
   ```

### Firewall-Warnung
Falls eine Firewall-Warnung erscheint: Erlauben Sie den lokalen Zugriff.

---

## Technische Details

- **Größe:** ~150-200 MB (enthält Python-Runtime und alle Dependencies)
- **Keine Installation nötig:** Alle Abhängigkeiten sind eingebettet
- **Plattform-spezifisch:** Linux-Build läuft nur auf Linux, Windows-Build nur auf Windows
- **Daten:** `building_data.json` wird mit ausgeliefert

---

## Distribution

### Dateien zum Verteilen

- **Linux:** `dist/din12831-heatload`
- **Windows:** `dist/din12831-heatload.exe` (wenn auf Windows gebaut)

Optional mit verteilen:
- Diese README-Datei
- Beispiel `building_data.json`

### Zip-Paket erstellen

```bash
cd dist
zip -r din12831-heatload-linux.zip din12831-heatload DISTRIBUTION.md
```
