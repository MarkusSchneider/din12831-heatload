"""Tab für den Heizlast-Report."""

import streamlit as st
import pandas as pd
from typing import List, Tuple, Optional
from src.din12831.calc_heat_load import calc_building_heat_load, RoomHeatLoadResult
from src.din12831.models import Building


def _validate_building_data(building: Building) -> Optional[str]:
    """Validiert die Gebäudedaten und gibt eine Fehlermeldung zurück falls nötig.

    Args:
        building: Das zu validierende Gebäude

    Returns:
        Fehlermeldung als String oder None wenn alles OK ist
    """
    if not building.rooms:
        return "ℹ️ Noch keine Räume im Gebäude definiert. Fügen Sie Räume im Tab '📐 Räume' hinzu."

    if not building.outside_temperature_name:
        return "⚠️ Bitte definieren Sie eine Normaußentemperatur im Tab '🌡️ Temperaturen'."

    return None


def _create_rooms_dataframe(results: List[RoomHeatLoadResult]) -> pd.DataFrame:
    """Erstellt einen DataFrame mit allen Räumen und deren Heizlasten.

    Args:
        results: Liste der berechneten Heizlast-Ergebnisse

    Returns:
        DataFrame mit Raum-Übersicht
    """
    data = []
    for result in results:
        data.append({
            "Raum": result.room_name,
            "Transmission [W]": f"{result.transmission_w:.0f}",
            "Lüftung [W]": f"{result.ventilation_w:.0f}",
            "Gesamt [W]": f"{result.total_w:.0f}",
            "Gesamt [kW]": f"{result.total_w / 1000:.2f}"
        })
    return pd.DataFrame(data)


def _calculate_totals(results: List[RoomHeatLoadResult]) -> Tuple[float, float, float]:
    """Berechnet die Gesamtsummen für Transmission, Lüftung und Heizlast.

    Args:
        results: Liste der berechneten Heizlast-Ergebnisse

    Returns:
        Tuple mit (total_transmission, total_ventilation, total_heat_load)
    """
    total_transmission = sum(r.transmission_w for r in results)
    total_ventilation = sum(r.ventilation_w for r in results)
    total_heat_load = sum(r.total_w for r in results)
    return total_transmission, total_ventilation, total_heat_load


def _render_building_info(building: Building) -> None:
    """Zeigt die Gebäudeinformationen an.

    Args:
        building: Das Gebäude mit den anzuzeigenden Informationen
    """
    st.subheader(f"🏠 {building.name}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Anzahl Räume", len(building.rooms))
    with col2:
        st.metric("Normaußentemperatur", f"{building.outside_temperature.value_celsius:.1f} °C")
    with col3:
        st.metric("Wärmebrückenzuschlag", f"{building.thermal_bridge_surcharge:.3f}")


def _render_heat_load_overview(total_transmission: float, total_ventilation: float, total_heat_load: float) -> None:
    """Zeigt die Heizlast-Übersicht mit Gesamtwerten an.

    Args:
        total_transmission: Gesamte Transmissionswärmeverluste in W
        total_ventilation: Gesamte Lüftungswärmeverluste in W
        total_heat_load: Gesamte Heizlast in W
    """
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


def _render_rooms_table(df: pd.DataFrame) -> None:
    """Zeigt die detaillierte Raumübersicht als Tabelle an.

    Args:
        df: DataFrame mit den Raumdaten
    """
    st.subheader("📋 Detaillierte Raumübersicht")
    st.dataframe(
        df,
        width='stretch',
        hide_index=True
    )


def _render_room_details(result: RoomHeatLoadResult, is_last: bool) -> None:
    """Zeigt die detaillierten Informationen für einen einzelnen Raum an.

    Args:
        result: Heizlast-Ergebnis für den Raum
        is_last: Ob dies der letzte Raum in der Liste ist
    """
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
        st.dataframe(
            element_df,
            width='stretch',
            hide_index=True,
            column_config={"U-Wert korr. [W/(m²·K)]": st.column_config.TextColumn("U-Wert korr. [W/(m²·K)]", help="U-Wert mit Wärmebrückenzuschlag")}
        )
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

    if not is_last:  # Divider nur zwischen Räumen, nicht am Ende
        st.divider()


def _render_detailed_room_view(results: List[RoomHeatLoadResult]) -> None:
    """Zeigt die detaillierte Ansicht pro Raum und Bauteil in einem Expander an.

    Args:
        results: Liste der berechneten Heizlast-Ergebnisse
    """
    with st.expander("🔍 Detaillierte Heizlast pro Raum und Bauteil", expanded=False):
        for i, result in enumerate(results):
            is_last = (i == len(results) - 1)
            _render_room_details(result, is_last)


def render_report_tab() -> None:
    """Zeigt einen Report mit allen Räumen und der Gesamt-Heizlast des Gebäudes."""
    st.header("📊 Heizlast-Report")

    building = st.session_state.building

    # Validierung der Gebäudedaten
    error_message = _validate_building_data(building)
    if error_message:
        if error_message.startswith("ℹ️"):
            st.info(error_message)
        else:
            st.warning(error_message)
        return

    # Berechne Heizlast für alle Räume
    results = calc_building_heat_load(building)

    # Erstelle DataFrame und berechne Summen
    df = _create_rooms_dataframe(results)
    total_transmission, total_ventilation, total_heat_load = _calculate_totals(results)

    # Render alle Sektionen
    _render_building_info(building)
    st.divider()
    _render_heat_load_overview(total_transmission, total_ventilation, total_heat_load)
    st.divider()
    _render_rooms_table(df)
    _render_detailed_room_view(results)
