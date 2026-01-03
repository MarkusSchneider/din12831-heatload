#!/bin/bash
# Build-Script für Standalone-Executable

echo "🏗️  Building DIN 12831 Heizlast Standalone App..."
echo ""

# Prüfen ob Virtual Environment aktiv ist
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Aktiviere Virtual Environment..."
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    elif [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo "❌ Kein Virtual Environment gefunden!"
        echo "   Bitte erstellen: python -m venv .venv"
        exit 1
    fi
fi

# PyInstaller installieren falls nicht vorhanden
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "📦 Installiere PyInstaller..."
    pip install pyinstaller
fi

# Build-Verzeichnis aufräumen
if [ -d "dist" ]; then
    echo "🧹 Lösche altes dist-Verzeichnis..."
    rm -rf dist
fi

if [ -d "build" ]; then
    echo "🧹 Lösche altes build-Verzeichnis..."
    rm -rf build
fi

# App bauen
echo ""
echo "🔨 Baue Executable..."
pyinstaller app.spec --clean

# Prüfen ob erfolgreich
if [ -f "dist/din12831-heatload" ]; then
    echo ""
    echo "✅ Build erfolgreich!"
    echo ""
    echo "📦 Executable: $(pwd)/dist/din12831-heatload"
    echo ""
    echo "🚀 Starten mit: ./dist/din12831-heatload"
    echo ""
    
    # Dateigrößen anzeigen
    SIZE=$(du -h dist/din12831-heatload | cut -f1)
    echo "📊 Größe: $SIZE"
else
    echo ""
    echo "❌ Build fehlgeschlagen!"
    exit 1
fi
