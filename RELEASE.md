# 🚀 Release-Prozess

## Übersicht

Das Projekt nutzt GitHub Actions für automatisierte Releases. Bei jedem neuen Version-Tag wird automatisch:
- Die Anwendung gebaut
- Ein GitHub Release erstellt
- Die Executable als Download bereitgestellt

## Workflow-Datei

Der Workflow ist definiert in: [`.github/workflows/release.yml`](.github/workflows/release.yml)

## Release erstellen

### 1. Vorbereitung

Stelle sicher, dass alle Änderungen committed und gepusht sind:

```bash
git add .
git commit -m "Beschreibung der Änderungen"
git push
```

### 2. Version taggen

Erstelle einen neuen Git-Tag mit der gewünschten Version:

```bash
# Beispiel für Version 1.0.0
git tag v1.0.0

# Optional: Tag mit Nachricht
git tag -a v1.0.0 -m "Release Version 1.0.0"
```

**Versionierungsschema:** Wir empfehlen [Semantic Versioning](https://semver.org/):
- `v1.0.0` - Major Release (Breaking Changes)
- `v1.1.0` - Minor Release (neue Features)
- `v1.0.1` - Patch Release (Bugfixes)

### 3. Tag pushen

Pushe den Tag zu GitHub - dies startet den Workflow automatisch:

```bash
git push origin v1.0.0
```

### 4. Release überwachen

1. Öffne dein GitHub Repository im Browser
2. Gehe zu **Actions** Tab
3. Du siehst den laufenden Workflow "Build and Release"
4. Nach ca. 2-5 Minuten ist der Build fertig

### 5. Release veröffentlichen

Nach erfolgreichem Build:
1. Gehe zum **Releases** Tab
2. Dein neues Release wurde automatisch erstellt
3. Die Executable ist als Download verfügbar

## Was passiert automatisch?

### Build-Prozess

1. **Environment Setup**
   - Ubuntu Linux VM wird gestartet
   - Python 3.11 wird installiert

2. **Dependencies**
   - Alle Pakete aus `requirements.txt` werden installiert
   - PyInstaller wird installiert

3. **Build**
   - `build_standalone.sh` Script wird ausgeführt
   - PyInstaller erstellt die Executable aus `app.spec`

4. **Archivierung**
   - Executable wird in `.tar.gz` verpackt
   - Einzelne Executable bleibt auch verfügbar

5. **Release Creation**
   - GitHub Release wird erstellt
   - Beide Dateien werden hochgeladen:
     - `din12831-heatload` (einzelne Executable)
     - `din12831-heatload-linux-x64.tar.gz` (Archiv)
   - Release-Notes werden automatisch generiert

## Release-Artefakte

Nach jedem erfolgreichen Build werden folgende Dateien bereitgestellt:

| Datei | Beschreibung |
|-------|--------------|
| `din12831-heatload` | Direkt ausführbare Datei (Linux x64) |
| `din12831-heatload-linux-x64.tar.gz` | Komprimiertes Archiv |

## Manuelle Anpassungen

Falls du die Release-Notes anpassen möchtest:

1. Gehe zu deinem Release auf GitHub
2. Klicke auf **Edit release**
3. Passe den Text im **Description** Feld an
4. Klicke **Update release**

## Troubleshooting

### Build schlägt fehl

1. Prüfe die Logs im Actions Tab
2. Häufige Probleme:
   - Fehlende Dependencies in `requirements.txt`
   - Fehler in `app.spec`
   - Syntax-Fehler im Python-Code

### Tag löschen (bei Fehler)

Wenn du einen falschen Tag erstellt hast:

```bash
# Lokal löschen
git tag -d v1.0.0

# Remote löschen
git push origin :refs/tags/v1.0.0
```

### Release löschen

1. Gehe zum Release auf GitHub
2. Klicke auf **Delete**
3. Bestätige die Löschung

## Erweiterte Konfiguration

### Pre-Releases erstellen

Für Beta-Versionen kannst du Pre-Release Tags verwenden:

```bash
git tag v1.0.0-beta.1
git push origin v1.0.0-beta.1
```

Der Workflow erstellt dann automatisch ein Pre-Release.

### Multi-Platform Builds

Der aktuelle Workflow baut nur für Linux. Für Windows/macOS müsstest du:
1. Matrix-Strategie in der Workflow-Datei verwenden
2. Unterschiedliche Runner (ubuntu, windows, macos) definieren
3. Plattform-spezifische Build-Schritte anpassen

## Best Practices

1. **Teste vor dem Release**
   - Führe alle Tests lokal aus
   - Baue die App lokal und teste sie

2. **Versionsnummern**
   - Folge Semantic Versioning
   - Dokumentiere Breaking Changes

3. **Release-Notes**
   - Bearbeite die generierten Release-Notes
   - Füge Changelog hinzu
   - Liste neue Features und Bugfixes auf

4. **Häufigkeit**
   - Erstelle Releases nur für stabile Versionen
   - Nutze Pre-Releases für Tests

## Weitere Informationen

- GitHub Actions Dokumentation: https://docs.github.com/en/actions
- PyInstaller Dokumentation: https://pyinstaller.org/
- Semantic Versioning: https://semver.org/
