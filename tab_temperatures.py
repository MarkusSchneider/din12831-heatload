"""Tab für die Temperaturverwaltung."""

import streamlit as st
from src.din12831.models import Temperature
from utils import save_building


def render_temperature_add_form() -> None:
    """Zeigt Formular zum Hinzufügen einer neuen Temperatur."""
    is_empty = len(st.session_state.building.temperature_catalog) == 0

    with st.expander("➕ Neue Temperatur hinzufügen", expanded=is_empty):
        # Reset flag prüfen und Session State leeren
        if st.session_state.get("reset_temperature_form", False):
            for key in ["temp_name", "temp_value"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["reset_temperature_form"] = False

        # Eingaben in einer Zeile
        cols = st.columns([3, 2, 1])

        with cols[0]:
            temp_name = st.text_input(
                "Bezeichnung",
                placeholder="z.B. Wohnraum, Außen, Keller, Bad",
                key="temp_name"
            )

        with cols[1]:
            temp_value = st.number_input(
                "Temperatur (°C)",
                min_value=-30.0,
                max_value=30.0,
                value=20.0,
                step=0.5,
                key="temp_value"
            )

        with cols[2]:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button("Hinzufügen", type="primary", key="add_temperature"):
                if not temp_name:
                    st.error("Bitte geben Sie eine Bezeichnung ein.")
                    return

                # Prüfe ob Name bereits existiert
                existing_names = [t.name for t in st.session_state.building.temperature_catalog]
                if temp_name in existing_names:
                    st.error(f"Eine Temperatur mit dem Namen '{temp_name}' existiert bereits.")
                    return

                new_temperature = Temperature(
                    name=temp_name,
                    value_celsius=temp_value,
                )
                st.session_state.building.temperature_catalog.append(new_temperature)
                save_building(st.session_state.building)

                # Form zurücksetzen
                st.session_state["reset_temperature_form"] = True
                st.success(f"Temperatur '{temp_name}' wurde hinzugefügt!")
                st.rerun()


def render_temperature_list() -> None:
    """Zeigt Liste aller Temperaturen im Katalog."""
    catalog = st.session_state.building.temperature_catalog

    if not catalog:
        st.info("👆 Fügen Sie Temperaturen zu Ihrem Katalog hinzu, um sie bei der Raumplanung wiederzuverwenden.")
        return

    st.subheader(f"Vorhandene Temperaturen ({len(catalog)})")

    for idx, temperature in enumerate(catalog):
        cols = st.columns([3, 2, 1, 1])

        with cols[0]:
            # Inline-Edit für Namen
            new_name = st.text_input(
                "Name",
                value=temperature.name,
                key=f"temp_name_edit_{idx}",
                label_visibility="collapsed"
            )
            if new_name != temperature.name:
                temperature.name = new_name
                save_building(st.session_state.building)

        with cols[1]:
            # Inline-Edit für Wert
            new_value = st.number_input(
                "Wert",
                value=temperature.value_celsius,
                min_value=-30.0,
                max_value=30.0,
                step=0.5,
                key=f"temp_value_edit_{idx}",
                label_visibility="collapsed"
            )
            if new_value != temperature.value_celsius:
                temperature.value_celsius = new_value
                save_building(st.session_state.building)
                st.rerun()

        with cols[2]:
            # Zeige Verwendung an
            usage_count = count_temperature_usage(temperature)
            if usage_count > 0:
                st.write(f"🔗 {usage_count}× verwendet")
            else:
                st.write("—")

        with cols[3]:
            if st.button("🗑️", key=f"delete_temp_{idx}"):
                # Prüfe ob Temperatur verwendet wird
                if count_temperature_usage(temperature) > 0:
                    st.error("Diese Temperatur wird noch verwendet und kann nicht gelöscht werden.")
                else:
                    catalog.pop(idx)
                    save_building(st.session_state.building)
                    st.rerun()


def count_temperature_usage(temperature: Temperature) -> int:
    """Zählt wie oft eine Temperatur im Gebäude verwendet wird."""
    count = 0
    building = st.session_state.building

    # Prüfe ob es die Außentemperatur ist
    if building.outside_temperature_name == temperature.name:
        count += 1

    # Prüfe ob es die Standard-Raumtemperatur ist
    if building.default_room_temperature_name == temperature.name:
        count += 1

    # Prüfe alle Räume
    for room in building.rooms:
        if room.room_temperature_name == temperature.name:
            count += 1

        # Prüfe alle Wände im Raum
        for wall in room.walls:
            if wall.adjacent_room_temperature_name == temperature.name:
                count += 1

    return count


def render_outside_temperature_selection() -> None:
    """Zeigt Auswahl für die Normaußentemperatur."""
    st.subheader("Normaußentemperatur")

    catalog = st.session_state.building.temperature_catalog
    if not catalog:
        st.warning("Bitte fügen Sie zuerst Temperaturen zum Katalog hinzu.")
        return

    temp_by_name = {t.name: t for t in catalog}
    temp_names = list(temp_by_name.keys())

    # Aktuelle Auswahl
    current_temp_name = st.session_state.building.outside_temperature_name
    current_index = 0
    if current_temp_name and current_temp_name in temp_names:
        current_index = temp_names.index(current_temp_name)

    cols = st.columns([2, 2, 1])
    with cols[0]:
        selected_name = st.selectbox(
            "Wählen Sie die Normaußentemperatur",
            options=temp_names,
            index=current_index,
            format_func=lambda name: f"{name} ({temp_by_name[name].value_celsius:.1f} °C)",
            key="outside_temp_select",
            help="Siehe: https://www.waermepumpe.de/werkzeuge/klimakarte/"
        )

    if selected_name:
        if st.session_state.building.outside_temperature_name != selected_name:
            st.session_state.building.outside_temperature_name = selected_name
            save_building(st.session_state.building)
            st.rerun()


def render_default_room_temperature_selection() -> None:
    """Zeigt Auswahl für die Standard-Raumtemperatur."""
    st.subheader("Standard-Raumtemperatur")

    catalog = st.session_state.building.temperature_catalog
    if not catalog:
        st.warning("Bitte fügen Sie zuerst Temperaturen zum Katalog hinzu.")
        return

    temp_by_name = {t.name: t for t in catalog}
    temp_names = list(temp_by_name.keys())

    # Aktuelle Auswahl
    current_temp_name = st.session_state.building.default_room_temperature_name
    current_index = 0
    if current_temp_name and current_temp_name in temp_names:
        current_index = temp_names.index(current_temp_name)

    cols = st.columns([2, 2, 1])
    with cols[0]:
        selected_name = st.selectbox(
            "Wählen Sie die Standard-Raumtemperatur",
            options=temp_names,
            index=current_index,
            format_func=lambda name: f"{name} ({temp_by_name[name].value_celsius:.1f} °C)",
            key="default_room_temp_select",
            help="Diese Temperatur wird beim Erstellen neuer Räume vorgeschlagen."
        )

    if selected_name:
        if st.session_state.building.default_room_temperature_name != selected_name:
            st.session_state.building.default_room_temperature_name = selected_name
            save_building(st.session_state.building)
            st.rerun()


def render_temperatures_tab() -> None:
    """Rendert den kompletten Temperatur-Tab."""
    st.header("🌡️ Temperaturverwaltung")
    st.caption("Verwalten Sie wiederverwendbare Temperaturen für Räume und Außenbedingungen.")

    render_temperature_add_form()
    st.divider()

    # Normtemperaturen zweispaltig anzeigen
    col1, col2 = st.columns(2)
    with col1:
        render_outside_temperature_selection()
    with col2:
        render_default_room_temperature_selection()

    st.divider()

    render_temperature_list()
