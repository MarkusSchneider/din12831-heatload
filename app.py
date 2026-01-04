"""Hauptanwendung für die DIN EN 12831 Heizlastberechnung."""

import streamlit as st
import json
from pathlib import Path
from utils import load_building, save_building
from tab_catalog import render_catalog_tab
from tab_temperatures import render_temperatures_tab
from tab_rooms import render_rooms_tab
from tab_report import render_report_tab
from tab_debug import render_debug_tab
from src.din12831.models import Building

st.set_page_config(page_title="DIN EN 12831 Heizlast", layout="wide")


def initialize_session_state() -> None:
    """Initialisiert den Session State."""
    if 'building' not in st.session_state:
        st.session_state.building = load_building()


def render_sidebar() -> None:
    """Rendert die Sidebar mit Gebäude-Einstellungen und Speicher-Optionen."""
    with st.sidebar:
        st.header("Gebäude-Einstellungen")

        # File Upload für Gebäudedaten
        st.subheader("📂 Datei laden")
        uploaded_file = st.file_uploader(
            "Gebäudedaten laden",
            type=['json'],
            help="Wähle eine building_data*.json Datei zum Laden"
        )

        if uploaded_file is not None:
            try:
                data = json.load(uploaded_file)
                st.session_state.building = Building.model_validate(data)
                st.success(f"✅ Datei '{uploaded_file.name}' erfolgreich geladen!")
                # Speichere das geladene Gebäude direkt
                save_building(st.session_state.building)
            except Exception as e:
                st.error(f"❌ Fehler beim Laden der Datei: {e}")

        st.divider()

        building_name = st.text_input("Gebäudename", value=st.session_state.building.name)

        # Wenn sich der Name ändert, speichere unter neuem Dateinamen
        if building_name != st.session_state.building.name:
            st.session_state.building.name = building_name
            save_building(st.session_state.building)

        u_value_correction = st.number_input(
            "U-Wert-Korrekturfaktor",
            min_value=0.001,
            value=st.session_state.building.u_value_correction_factor,
            step=0.01,
            format="%.3f",
            help="Korrekturfaktor für U-Werte (Standard: 0.05)"
        )

        if u_value_correction != st.session_state.building.u_value_correction_factor:
            st.session_state.building.u_value_correction_factor = u_value_correction
            save_building(st.session_state.building)

        st.divider()
        st.subheader("Gebäudeübersicht")
        st.metric("Anzahl Räume", len(st.session_state.building.rooms))
        st.metric("Konstruktionen im Katalog", len(
            st.session_state.building.construction_catalog))
        st.metric("Temperaturen im Katalog", len(
            st.session_state.building.temperature_catalog))


def main() -> None:
    """Hauptfunktion der Streamlit-App."""
    initialize_session_state()

    st.title("🏠 DIN EN 12831 Heizlastberechnung")
    st.caption("Gebäude mit Räumen und Bauteilen definieren")

    render_sidebar()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Report", "📐 Räume", "🏗️ Bauteilkatalog", "🌡️ Temperaturen", "🔍 Debug"])

    with tab1:
        render_report_tab()

    with tab2:
        render_rooms_tab()

    with tab3:
        render_catalog_tab()

    with tab4:
        render_temperatures_tab()

    with tab5:
        render_debug_tab()


if __name__ == "__main__":
    main()
