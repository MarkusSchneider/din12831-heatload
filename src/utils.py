"""Gemeinsame Hilfsfunktionen für die App."""

import json
from pathlib import Path

import streamlit as st

from src.models import Building, Construction, ConstructionType

DEFAULT_BUILDING_NAME = "Mein Gebäude"


def find_building_file() -> Path | None:
    """Sucht nach building_data*.json Dateien im Root-Verzeichnis.

    Returns:
        Path zur ersten gefundenen Datei oder None
    """
    root = Path(".")
    building_files = sorted(root.glob("building_data*.json"))
    return building_files[0] if building_files else None


def get_building_filename(building_name: str) -> Path:
    """Generiert Dateinamen basierend auf Gebäudenamen.

    Args:
        building_name: Name des Gebäudes

    Returns:
        Path zur Gebäude-Datei
    """
    if not building_name or building_name == DEFAULT_BUILDING_NAME:
        return Path("building_data.json")

    # Entferne ungültige Zeichen für Dateinamen
    safe_name = "".join(c for c in building_name if c.isalnum() or c in (" ", "-", "_")).strip()
    safe_name = safe_name.replace(" ", "_")

    return Path(f"building_data_{safe_name}.json")


def load_building(file_path: Path | None = None) -> Building:
    """Lädt Gebäudedaten aus JSON-Datei oder erstellt ein neues Gebäude.

    Args:
        file_path: Optional spezifischer Pfad zur Datei. Wenn None, wird automatisch gesucht.

    Returns:
        Building-Objekt
    """
    if file_path is None:
        file_path = find_building_file()

    if file_path is None or not file_path.exists():
        return Building(name=DEFAULT_BUILDING_NAME)

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        return Building.model_validate(data)
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return Building(name=DEFAULT_BUILDING_NAME)


def save_building(building: Building) -> None:
    """Speichert Gebäudedaten automatisch in JSON-Datei.

    Der Dateiname wird basierend auf dem Gebäudenamen generiert.
    """
    file_path = get_building_filename(building.name)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(building.model_dump(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")


def get_catalog_by_type(construction_type: ConstructionType) -> list[Construction]:
    """Filtert den Katalog nach Bauteiltyp."""
    return [c for c in st.session_state.building.construction_catalog if c.element_type == construction_type]
