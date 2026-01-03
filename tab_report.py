"""Tab für den Heizlast-Report."""

import streamlit as st
import pandas as pd
from src.din12831.calc_heat_load import calc_building_heat_load


def render_report_tab() -> None:
    """Zeigt einen Report mit allen Räumen und der Gesamt-Heizlast des Gebäudes."""
    st.header("📊 Heizlast-Report")

    building = st.session_state.building

    if not building.rooms:
        st.info("ℹ️ Noch keine Räume im Gebäude definiert. Fügen Sie Räume im Tab '📐 Räume' hinzu.")
        return

    # Prüfe ob Außentemperatur gesetzt ist
    if not building.outside_temperature_name:
        st.warning("⚠️ Bitte definieren Sie eine Normaußentemperatur im Tab '🌡️ Temperaturen'.")
        return

    # Berechne Heizlast für alle Räume
    results = calc_building_heat_load(building)

    # Erstelle DataFrame für die Tabelle
    data = []
    for result in results:
        data.append({
            "Raum": result.room_name,
            "Transmission [W]": f"{result.transmission_w:.0f}",
            "Lüftung [W]": f"{result.ventilation_w:.0f}",
            "Gesamt [W]": f"{result.total_w:.0f}",
            "Gesamt [kW]": f"{result.total_w / 1000:.2f}"
        })

    df = pd.DataFrame(data)

    # Berechne Gesamtsummen
    total_transmission = sum(r.transmission_w for r in results)
    total_ventilation = sum(r.ventilation_w for r in results)
    total_heat_load = sum(r.total_w for r in results)

    # Gebäudeinformationen
    st.subheader(f"🏠 {building.name}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Anzahl Räume", len(building.rooms))
    with col2:
        st.metric("Normaußentemperatur", f"{building.outside_temperature.value_celsius:.1f} °C")
    with col3:
        st.metric("U-Wert-Korrekturfaktor", f"{building.u_value_correction_factor:.3f}")

    st.divider()

    # Heizlast-Übersicht
    st.subheader("🔥 Heizlast-Übersicht")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Transmission", f"{total_transmission:.0f} W", help="Gesamte Transmissionswärmeverluste")
    with col2:
        st.metric("Lüftung", f"{total_ventilation:.0f} W", help="Gesamte Lüftungswärmeverluste")
    with col3:
        st.metric("Gesamt", f"{total_heat_load:.0f} W", help="Gesamte Heizlast des Gebäudes")
    with col4:
        st.metric("Gesamt", f"{total_heat_load / 1000:.2f} kW", help="Gesamte Heizlast des Gebäudes in kW")

    st.divider()

    # Detaillierte Raumtabelle
    st.subheader("📋 Detaillierte Raumübersicht")
    st.dataframe(
        df,
        width='stretch',
        hide_index=True
    )

    # Optionale Detailansicht pro Raum
    with st.expander("🔍 Detaillierte Heizlast pro Raum und Bauteil", expanded=False):
        for result in results:
            st.markdown(f"### {result.room_name}")

            # Erstelle DataFrame für Bauteile
            element_data = []
            for element in result.element_transmissions:
                element_data.append({
                    "Bauteil": element.element_name,
                    "U-Wert [W/(m²·K)]": f"{element.u_value_w_m2k:.3f}",
                    "U-Wert korr. [W/(m²·K)]": f"{element.u_value_corrected_w_m2k:.3f}",
                    "Fläche [m²]": f"{element.area_m2:.2f}",
                    "ΔT [K]": f"{element.delta_temp_k:.1f}",
                    "Transmission [W]": f"{element.transmission_w:.0f}"
                })

            if element_data:
                element_df = pd.DataFrame(element_data)
                st.dataframe(element_df, width='stretch', hide_index=True)
            else:
                st.info("Keine Bauteile für diesen Raum definiert.")

            # Zusammenfassung für diesen Raum
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Transmission", f"{result.transmission_w:.0f} W")
            with col2:
                st.metric("Lüftung", f"{result.ventilation_w:.0f} W")
            with col3:
                st.metric("Gesamt", f"{result.total_w:.0f} W ({result.total_w / 1000:.2f} kW)")

            if result != results[-1]:  # Divider nur zwischen Räumen, nicht am Ende
                st.divider()
