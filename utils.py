"""Gemeinsame Hilfsfunktionen für die App."""

import streamlit as st
import json
from pathlib import Path
from src.din12831.models import Building, Construction, ConstructionType

DATA_FILE = Path("building_data.json")


def load_building() -> Building:
    """Lädt Gebäudedaten aus JSON-Datei oder erstellt ein neues Gebäude."""
    if not DATA_FILE.exists():
        return Building(name="Mein Gebäude")

    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Building.model_validate(data)
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return Building(name="Mein Gebäude")


def save_building(building: Building) -> None:
    """Speichert Gebäudedaten automatisch in JSON-Datei."""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(building.model_dump(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")


def get_catalog_by_type(construction_type: ConstructionType) -> list[Construction]:
    """Filtert den Katalog nach Bauteiltyp."""
    return [
        c
        for c in st.session_state.building.construction_catalog
        if c.element_type == construction_type
    ]
