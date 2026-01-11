"""Tab für die Räume - Refaktorierte Version mit kleineren, fokussierten Funktionen."""

from typing import cast

import pandas as pd
import streamlit as st

from src.din12831.calc_heat_load import calc_room_heat_load
from src.models import Area, ConstructionType, Element, ElementType, Room, Temperature, Ventilation, Wall
from src.utils import get_catalog_by_type, save_building


# ============================================================================
# Helper Funktionen für Temperatur- und Katalog-Handling
# ============================================================================
def format_temperature(temp: Temperature | None) -> str:
    """Formatiert eine Temperatur für die Anzeige."""
    if temp:
        return f"{temp.name} ({temp.value_celsius:.1f} °C)"
    return "Nicht zugewiesen"


def get_temperature_options() -> dict[str, Temperature]:
    """Gibt die verfügbaren Temperaturen aus dem Katalog zurück."""
    temp_catalog: list[Temperature] = st.session_state.building.temperature_catalog
    return {t.name: t for t in temp_catalog}


def get_default_temperature_index() -> int:
    """Bestimmt den Index der Standard-Raumtemperatur."""
    temp_by_name = get_temperature_options()
    default_temp_name = st.session_state.building.default_room_temperature_name

    if default_temp_name and default_temp_name in temp_by_name:
        return list(temp_by_name.keys()).index(default_temp_name)
    return 0


def get_wall_catalog():
    """Gibt alle Wandkonstruktionen (extern + intern) zurück."""
    external_walls = get_catalog_by_type(ConstructionType.EXTERNAL_WALL)
    internal_walls = get_catalog_by_type(ConstructionType.INTERNAL_WALL)
    return external_walls + internal_walls


# ============================================================================
# Render-Funktionen für Boden und Decke
# ============================================================================
def render_adjacent_temperature_info(element: Element | None, label: str) -> str:
    """Zeigt Informationen zur angrenzenden Temperatur eines Bauteils."""
    if not element or not element.adjacent_temperature_name:
        return ""
        return ""

    adj_temp = st.session_state.building.get_temperature_by_name(element.adjacent_temperature_name)
    if adj_temp:
        return f"*Angrenzende Temperatur:* {adj_temp.name} ({adj_temp.value_celsius:.1f} °C)"
    return ""


def render_floor_info(room: Room) -> None:
    """Zeigt Boden-Informationen eines Raums."""
    current_floor = room.floor.construction_name if room.floor else "Nicht zugewiesen"
    adj_temp_str = render_adjacent_temperature_info(room.floor, "Boden")

    st.write(f"**Boden:** {current_floor} - {adj_temp_str}")

    net_area = room.floor_area_m2
    gross_area = room.gross_floor_area_m2(st.session_state.building)
    st.write(f"*Nettofläche:* {net_area:.2f} m² | *Bruttofläche:* {gross_area:.2f} m²")


def render_ceiling_info(room: Room) -> None:
    """Zeigt Decken-Informationen eines Raums."""
    current_ceiling = room.ceiling.construction_name if room.ceiling else "Nicht zugewiesen"
    adj_temp_str = render_adjacent_temperature_info(room.ceiling, "Decke")

    st.write(f"**Decke:** {current_ceiling} - {adj_temp_str}")

    net_area = room.floor_area_m2
    gross_area = room.gross_ceiling_area_m2(st.session_state.building)
    st.write(f"*Nettofläche:* {net_area:.2f} m² | *Bruttofläche:* {gross_area:.2f} m²")


def render_room_floor_ceiling_assignment(room: Room) -> None:
    """Zeigt Boden- und Deckenzuweisung eines Raums."""
    col1, col2 = st.columns([2, 2])

    with col1:
        render_floor_info(room)
    with col2:
        render_ceiling_info(room)


# ============================================================================
# Formularkomponenten für neuen Raum
# ============================================================================
def render_temperature_selector(key: str, label: str = "Raumtemperatur") -> str | None:
    """Zeigt einen Temperatur-Auswahldialog."""
    temp_catalog = st.session_state.building.temperature_catalog
    if not temp_catalog:
        st.error("Bitte zuerst Temperaturen im Temperaturkatalog anlegen.")
        return None

    temp_by_name = get_temperature_options()
    default_index = get_default_temperature_index()

    selected_temp_name = st.selectbox(
        label,
        options=list(temp_by_name.keys()),
        index=default_index,
        format_func=lambda name: f"{name} ({temp_by_name[name].value_celsius:.1f} °C)",
        key=key,
    )
    return selected_temp_name


def render_construction_selector(construction_type: ConstructionType, key: str, label: str) -> str | None:
    """Zeigt einen Konstruktions-Auswahldialog."""
    options = get_catalog_by_type(construction_type)
    options = get_catalog_by_type(construction_type)

    if not options:
        type_name = "Boden" if construction_type == ConstructionType.FLOOR else "Decke"
        st.error(f"Im Bauteilkatalog fehlt mindestens eine {type_name}-Konstruktion.")
        return None

    return st.selectbox(label, options=[c.name for c in options], key=key, help=f"Aufbau des {label}")


def render_floor_ceiling_selectors() -> tuple[str | None, str | None, str | None, str | None]:
    """Zeigt Auswahldialoge für Boden und Decke."""
    # Boden-Sektion
    st.write("**Boden:**")
    col_floor_1, col_floor_2 = st.columns(2)

    with col_floor_1:
        floor_construction = render_construction_selector(
            ConstructionType.FLOOR, "new_room_floor_construction", "Konstruktion"
        )

    with col_floor_2:
        floor_temp = render_temperature_selector("new_floor_adjacent_temp", "Angrenzende Temperatur")

    # Decken-Sektion
    st.write("**Decke:**")
    col_ceiling_1, col_ceiling_2 = st.columns(2)

    with col_ceiling_1:
        ceiling_construction = render_construction_selector(
            ConstructionType.CEILING, "new_room_ceiling_construction", "Konstruktion"
        )

    with col_ceiling_2:
        ceiling_temp = render_temperature_selector("new_ceiling_adjacent_temp", "Angrenzende Temperatur")

    return floor_construction, floor_temp, ceiling_construction, ceiling_temp


def render_area_editor(rect_id: int, rect_ids: list[int]) -> Area:
    """Zeigt Editor für ein einzelnes Rechteck."""
    cols = st.columns([2, 2, 1])

    with cols[0]:
        r_len = st.number_input(
            "Länge (m)",
            min_value=0.0,
            value=0.0,
            step=0.1,
            key=f"new_room_rect_{rect_id}_len",
        )

    with cols[1]:
        r_wid = st.number_input(
            "Breite (m)",
            min_value=0.0,
            value=0.0,
            step=0.1,
            key=f"new_room_rect_{rect_id}_wid",
        )

    with cols[2]:
        st.write("")  # Spacer für vertikale Ausrichtung
        if len(rect_ids) > 1 and st.button("🗑️", key=f"new_room_rect_{rect_id}_del"):
            rect_ids.remove(rect_id)
            st.session_state["new_room_rect_ids"] = rect_ids
            st.rerun()

    return Area(
        length_m=float(r_len),
        width_m=float(r_wid),
    )


def render_areas_section() -> list[Area]:
    """Zeigt die Sektion zum Bearbeiten von Rechtecken."""
    rect_ids_key = "new_room_rect_ids"
    if rect_ids_key not in st.session_state:
        st.session_state[rect_ids_key] = [1]

    st.write("**Flächen**")
    rectangles_payload: list[Area] = []
    rect_ids: list[int] = st.session_state[rect_ids_key]

    for _, rect_id in enumerate(list(rect_ids), 1):
        area = render_area_editor(rect_id, rect_ids)
        rectangles_payload.append(area)

    if st.button("➕ Weitere Fläche hinzufügen", key="add_new_room_rect"):
        max_id = max(rect_ids) if rect_ids else 0
        rect_ids.append(max_id + 1)
        st.session_state[rect_ids_key] = rect_ids
        st.rerun()

    return rectangles_payload


def render_update_area_editor(room_idx: int, area: Area, area_idx: int, total_areas: int) -> Area:
    """Zeigt Editor für ein einzelnes Rechteck im Update-Formular."""
    cols = st.columns([2, 2, 1])

    with cols[0]:
        r_len = st.number_input(
            "Länge (m)",
            min_value=0.0,
            value=area.length_m,
            step=0.1,
            key=f"update_room_rect_{room_idx}_{area_idx}_len",
        )

    with cols[1]:
        r_wid = st.number_input(
            "Breite (m)",
            min_value=0.0,
            value=area.width_m,
            step=0.1,
            key=f"update_room_rect_{room_idx}_{area_idx}_wid",
        )

    with cols[2]:
        st.write("")  # Spacer für vertikale Ausrichtung
        if total_areas > 1:
            delete_key = f"update_room_rect_{room_idx}_{area_idx}_del"
            # Platzhalter für Löschen-Button (wird außerhalb gehandhabt)
            st.button("🗑️", key=delete_key, disabled=True, help="Wird beim nächsten Speichern entfernt")

    return Area(
        length_m=float(r_len),
        width_m=float(r_wid),
    )


def render_update_areas_section(room: Room, room_idx: int) -> list[Area]:
    """Zeigt die Sektion zum Bearbeiten von Flächen im Update-Formular."""
    st.write("**Flächen**")

    if room.areas is None:
        room.areas = []

    rectangles_payload: list[Area] = []

    for idx, area in enumerate(room.areas):
        cols = st.columns([2, 2, 1])

        with cols[0]:
            r_len = st.number_input(
                "Länge (m)",
                min_value=0.0,
                value=area.length_m,
                step=0.1,
                key=f"update_room_rect_{room_idx}_{idx}_len",
            )

        with cols[1]:
            r_wid = st.number_input(
                "Breite (m)",
                min_value=0.0,
                value=area.width_m,
                step=0.1,
                key=f"update_room_rect_{room_idx}_{idx}_wid",
            )

        with cols[2]:
            st.write("")  # Spacer für vertikale Ausrichtung
            if len(room.areas) > 1:
                delete_key = f"update_room_rect_{room_idx}_{idx}_del"
                if st.button("🗑️", key=delete_key):
                    room.areas.pop(idx)
                    # Halte Expander und Update-Formular offen
                    st.session_state[f"room_{room_idx}_expanded"] = True
                    st.session_state[f"show_room_update_form_{room_idx}"] = True
                    save_building(st.session_state.building)
                    st.rerun()

        rectangles_payload.append(Area(length_m=float(r_len), width_m=float(r_wid)))

    if st.button("➕ Weitere Fläche hinzufügen", key=f"add_update_room_rect_{room_idx}"):
        room.areas.append(Area(length_m=4.0, width_m=3.0))
        # Halte Expander und Update-Formular offen
        st.session_state[f"room_{room_idx}_expanded"] = True
        st.session_state[f"show_room_update_form_{room_idx}"] = True
        st.rerun()

    return rectangles_payload


def validate_new_room_inputs(
    room_name: str, rectangles: list[Area], temp_name: str | None, floor_constr: str | None, ceiling_constr: str | None
) -> str | None:
    """Validiert die Eingaben für einen neuen Raum. Gibt Fehlermeldung zurück oder None."""
    if not room_name:
        return "Bitte geben Sie einen Raumnamen ein."

    if not rectangles:
        return "Bitte mindestens eine Fläche angeben."

    for idx, area in enumerate(rectangles, 1):
        if area.length_m <= 0 or area.width_m <= 0:
            return f"Fläche {idx}: Länge und Breite müssen größer als 0 sein."

    if not temp_name:
        return "Bitte wählen Sie eine Raumtemperatur aus dem Katalog."

    if not floor_constr or not ceiling_constr:
        return "Bitte Boden und Decke aus dem Katalog auswählen."

    return None


def create_new_room(
    name: str,
    rectangles: list[Area],
    height: float,
    temp_name: str,
    air_change: float,
    floor_constr: str,
    floor_temp: str,
    ceiling_constr: str,
    ceiling_temp: str,
) -> Room:
    """Erstellt ein neues Room-Objekt."""
    new_room = Room(
        name=name,
        areas=rectangles,
        net_height_m=height,
        room_temperature_name=temp_name,
        ventilation=Ventilation(air_change_1_h=air_change),
    )

    new_room.floor = Element(
        type=ElementType.FLOOR,
        name="Boden",
        construction_name=floor_constr,
        adjacent_temperature_name=floor_temp,
    )

    new_room.ceiling = Element(
        type=ElementType.CEILING,
        name="Decke",
        construction_name=ceiling_constr,
        adjacent_temperature_name=ceiling_temp,
    )

    return new_room


def clear_new_room_form_state() -> None:
    """Löscht den Session State für das neue Raum-Formular."""
    rect_ids_key = "new_room_rect_ids"
    st.session_state[rect_ids_key] = [1]

    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("new_room_rect_"):
            del st.session_state[key]


def render_room_add_form() -> None:
    """Zeigt Formular zum Hinzufügen eines neuen Raums."""
    is_empty = len(st.session_state.building.rooms) == 0

    with st.expander("➕ Neuen Raum hinzufügen", expanded=is_empty):
        col1, col2 = st.columns(2)

        with col1:
            new_room_name = st.text_input("Raumname", key="new_room_name")
            rectangles_payload = render_areas_section()

        with col2:
            new_height = st.number_input("Höhe (m)", min_value=0.1, value=2.5, step=0.1, key="new_height")

            selected_temp_name = render_temperature_selector("new_temp")

            new_air_change = st.number_input(
                "Luftwechsel (1/h)",
                min_value=0.0,
                value=0.5,
                step=0.1,
                key="new_air_change",
                help="Anzahl der Luftwechsel pro Stunde. Die Norm empfiehlt mindestens 0.5 1/h für Wohnräume.",
            )

            floor_constr, floor_temp, ceiling_constr, ceiling_temp = render_floor_ceiling_selectors()

        if not st.button("Raum hinzufügen", type="primary"):
            return

        # Validierung
        error = validate_new_room_inputs(
            new_room_name, rectangles_payload, selected_temp_name, floor_constr, ceiling_constr
        )

        if error:
            st.error(error)
            return

        # Type-Sicherheit: Nach Validierung sind alle Werte garantiert nicht None
        assert selected_temp_name is not None
        assert floor_constr is not None
        assert floor_temp is not None
        assert ceiling_constr is not None
        assert ceiling_temp is not None

        # Raum erstellen und hinzufügen
        new_room = create_new_room(
            new_room_name,
            rectangles_payload,
            new_height,
            selected_temp_name,
            new_air_change,
            floor_constr,
            floor_temp,
            ceiling_constr,
            ceiling_temp,
        )

        st.session_state.building.rooms.append(new_room)
        clear_new_room_form_state()
        save_building(st.session_state.building)
        st.success(f"Raum '{new_room_name}' wurde hinzugefügt!")
        st.rerun()


# ============================================================================
# Heizlasten-Anzeige
# ============================================================================


def render_heat_load_metrics(result) -> None:
    """Zeigt die Heizlast-Metriken in drei Spalten."""
    heat_col1, heat_col2, heat_col3 = st.columns(3)

    with heat_col1:
        st.metric(
            "Transmissionswärmeverlust",
            f"{result.transmission_w:.0f} W",
            help="Wärmeverlust durch Bauteile (Wände, Decke, Boden, Fenster, Türen)",
        )
    with heat_col2:
        st.metric("Lüftungswärmeverlust", f"{result.ventilation_w:.0f} W", help="Wärmeverlust durch Luftwechsel")
    with heat_col3:
        st.metric(
            "Gesamt-Heizlast", f"{result.total_w:.0f} W", help="Summe aus Transmissions- und Lüftungswärmeverlust"
        )


def render_element_transmission_details(result) -> None:
    """Zeigt Details zu den Transmissionswärmeverlusten der einzelnen Bauteile."""
    if not result.element_transmissions:
        return

    with st.expander("📋 Details nach Bauteilen", expanded=False):
        st.write("**Transmissionswärmeverluste der einzelnen Bauteile:**")

        element_data = []
        for element in result.element_transmissions:
            element_data.append(
                {
                    "Bauteil": element.element_name,
                    "Fläche [m²]": f"{element.area_m2:.2f}",
                    "U-Wert [W/(m²·K)]": f"{element.u_value_w_m2k:.2f}",
                    "U-Wert korr. [W/(m²·K)]": f"{element.u_value_corrected_w_m2k:.2f}",
                    "ΔT [K]": f"{element.delta_temp_k:.1f}",
                    "Wärmeverlust [W]": f"{element.transmission_w:.0f}",
                }
            )

        element_df = pd.DataFrame(element_data)
        st.dataframe(
            element_df,
            width="stretch",
            hide_index=True,
            column_config={
                "U-Wert korr. [W/(m²·K)]": st.column_config.TextColumn(
                    "U-Wert korr. [W/(m²·K)]", help="U-Wert mit Wärmebrückenzuschlag"
                )
            },
        )


def render_room_heat_loads(room: Room, room_idx: int) -> None:
    """Berechnet und zeigt die Heizlasten eines Raums."""
    try:
        result = calc_room_heat_load(
            room, st.session_state.building.outside_temperature.value_celsius, st.session_state.building
        )

        st.subheader("🔥 Heizlasten")
        render_heat_load_metrics(result)
        render_element_transmission_details(result)
        st.divider()

    except Exception as e:
        st.warning(f"Heizlast konnte nicht berechnet werden: {str(e)}")


# ============================================================================
# Raum-Informationen
# ============================================================================


def render_room_update_form(room: Room, room_idx: int) -> None:
    """Zeigt Formular zum Aktualisieren der Raum-Grunddaten."""
    with st.container(border=True):
        st.write("**Raum-Grunddaten bearbeiten:**")

        col1, col2 = st.columns(2)

        with col1:
            updated_name = st.text_input("Raumname", value=room.name, key=f"update_room_name_{room_idx}")

            # Flächen im linken Bereich
            rectangles_payload = render_update_areas_section(room, room_idx)

        with col2:
            updated_height = st.number_input(
                "Höhe (m)", min_value=0.1, value=room.net_height_m, step=0.1, key=f"update_room_height_{room_idx}"
            )

            temp_options = get_temperature_options()
            current_temp_idx = 0
            if room.room_temperature_name and room.room_temperature_name in temp_options:
                current_temp_idx = list(temp_options.keys()).index(room.room_temperature_name)

            updated_temp_name = st.selectbox(
                "Raumtemperatur",
                options=list(temp_options.keys()),
                index=current_temp_idx,
                format_func=lambda name: f"{name} ({temp_options[name].value_celsius:.1f} °C)",
                key=f"update_room_temp_{room_idx}",
            )

            updated_air_change = st.number_input(
                "Luftwechsel (1/h)",
                min_value=0.0,
                value=room.ventilation.air_change_1_h,
                step=0.1,
                key=f"update_room_air_change_{room_idx}",
                help="Anzahl der Luftwechsel pro Stunde. Die Norm empfiehlt mindestens 0.5 1/h für Wohnräume.",
            )

            # Boden-Sektion
            st.write("**Boden:**")
            col_floor_1, col_floor_2 = st.columns(2)

            with col_floor_1:
                floor_options = get_catalog_by_type(ConstructionType.FLOOR)
                if floor_options:
                    current_floor_idx = 0
                    if room.floor and room.floor.construction_name:
                        floor_names = [c.name for c in floor_options]
                        if room.floor.construction_name in floor_names:
                            current_floor_idx = floor_names.index(room.floor.construction_name)

                    updated_floor_construction = st.selectbox(
                        "Konstruktion",
                        options=[c.name for c in floor_options],
                        index=current_floor_idx,
                        key=f"update_room_floor_construction_{room_idx}",
                        help="Aufbau des Boden",
                    )
                else:
                    st.error("Im Bauteilkatalog fehlt mindestens eine Boden-Konstruktion.")
                    updated_floor_construction = None

            with col_floor_2:
                temp_catalog = st.session_state.building.temperature_catalog
                if temp_catalog:
                    temp_by_name = get_temperature_options()
                    current_floor_temp_idx = 0
                    if (
                        room.floor
                        and room.floor.adjacent_temperature_name
                        and room.floor.adjacent_temperature_name in temp_by_name
                    ):
                        current_floor_temp_idx = list(temp_by_name.keys()).index(room.floor.adjacent_temperature_name)

                    updated_floor_temp = st.selectbox(
                        "Angrenzende Temperatur",
                        options=list(temp_by_name.keys()),
                        index=current_floor_temp_idx,
                        format_func=lambda name: f"{name} ({temp_by_name[name].value_celsius:.1f} °C)",
                        key=f"update_floor_adjacent_temp_{room_idx}",
                    )
                else:
                    st.error("Bitte zuerst Temperaturen im Temperaturkatalog anlegen.")
                    updated_floor_temp = None

            # Decken-Sektion
            st.write("**Decke:**")
            col_ceiling_1, col_ceiling_2 = st.columns(2)

            with col_ceiling_1:
                ceiling_options = get_catalog_by_type(ConstructionType.CEILING)
                if ceiling_options:
                    current_ceiling_idx = 0
                    if room.ceiling and room.ceiling.construction_name:
                        ceiling_names = [c.name for c in ceiling_options]
                        if room.ceiling.construction_name in ceiling_names:
                            current_ceiling_idx = ceiling_names.index(room.ceiling.construction_name)

                    updated_ceiling_construction = st.selectbox(
                        "Konstruktion",
                        options=[c.name for c in ceiling_options],
                        index=current_ceiling_idx,
                        key=f"update_room_ceiling_construction_{room_idx}",
                        help="Aufbau des Decke",
                    )
                else:
                    st.error("Im Bauteilkatalog fehlt mindestens eine Decke-Konstruktion.")
                    updated_ceiling_construction = None

            with col_ceiling_2:
                if temp_catalog:
                    current_ceiling_temp_idx = 0
                    if (
                        room.ceiling
                        and room.ceiling.adjacent_temperature_name
                        and room.ceiling.adjacent_temperature_name in temp_by_name
                    ):
                        current_ceiling_temp_idx = list(temp_by_name.keys()).index(
                            room.ceiling.adjacent_temperature_name
                        )

                    updated_ceiling_temp = st.selectbox(
                        "Angrenzende Temperatur",
                        options=list(temp_by_name.keys()),
                        index=current_ceiling_temp_idx,
                        format_func=lambda name: f"{name} ({temp_by_name[name].value_celsius:.1f} °C)",
                        key=f"update_ceiling_adjacent_temp_{room_idx}",
                    )
                else:
                    updated_ceiling_temp = None

        button_cols = st.columns([9, 1])
        with button_cols[1]:
            submit = st.button("💾 Speichern", type="primary", key=f"update_room_submit_{room_idx}")

        if submit:
            if not updated_name or updated_name.strip() == "":
                st.error("Bitte geben Sie einen Raumnamen ein.")
                return

            if not rectangles_payload:
                st.error("Bitte mindestens eine Fläche angeben.")
                return

            for idx, area in enumerate(rectangles_payload, 1):
                if area.length_m <= 0 or area.width_m <= 0:
                    st.error(f"Fläche {idx}: Länge und Breite müssen größer als 0 sein.")
                    return

            if not updated_floor_construction or not updated_ceiling_construction:
                st.error("Bitte Boden und Decke aus dem Katalog auswählen.")
                return

            if not updated_floor_temp or not updated_ceiling_temp:
                st.error("Bitte angrenzende Temperaturen für Boden und Decke auswählen.")
                return

            room.name = updated_name
            room.net_height_m = updated_height
            room.room_temperature_name = updated_temp_name
            room.ventilation.air_change_1_h = updated_air_change
            # Flächen wurden bereits direkt aktualisiert, verwende die aktuellen Werte
            room.areas = rectangles_payload

            # Boden aktualisieren
            if room.floor:
                room.floor.construction_name = updated_floor_construction
                room.floor.adjacent_temperature_name = updated_floor_temp
            else:
                room.floor = Element(
                    type=ElementType.FLOOR,
                    name="Boden",
                    construction_name=updated_floor_construction,
                    adjacent_temperature_name=updated_floor_temp,
                )

            # Decke aktualisieren
            if room.ceiling:
                room.ceiling.construction_name = updated_ceiling_construction
                room.ceiling.adjacent_temperature_name = updated_ceiling_temp
            else:
                room.ceiling = Element(
                    type=ElementType.CEILING,
                    name="Decke",
                    construction_name=updated_ceiling_construction,
                    adjacent_temperature_name=updated_ceiling_temp,
                )

            # Cleanup session state
            if f"areas_to_delete_{room_idx}" in st.session_state:
                del st.session_state[f"areas_to_delete_{room_idx}"]

            st.session_state[f"show_room_update_form_{room_idx}"] = False
            save_building(st.session_state.building)
            st.success(f"Raum '{updated_name}' wurde aktualisiert!")
            st.rerun()
            room.room_temperature_name = updated_temp_name
            room.ventilation.air_change_1_h = updated_air_change

            # Boden aktualisieren
            if room.floor:
                room.floor.construction_name = updated_floor_construction
                room.floor.adjacent_temperature_name = updated_floor_temp
            else:
                room.floor = Element(
                    type=ElementType.FLOOR,
                    name="Boden",
                    construction_name=updated_floor_construction,
                    adjacent_temperature_name=updated_floor_temp,
                )

            # Decke aktualisieren
            if room.ceiling:
                room.ceiling.construction_name = updated_ceiling_construction
                room.ceiling.adjacent_temperature_name = updated_ceiling_temp
            else:
                room.ceiling = Element(
                    type=ElementType.CEILING,
                    name="Decke",
                    construction_name=updated_ceiling_construction,
                    adjacent_temperature_name=updated_ceiling_temp,
                )

            st.session_state[f"show_room_update_form_{room_idx}"] = False
            save_building(st.session_state.building)
            st.success(f"Raum '{updated_name}' wurde aktualisiert!")
            st.rerun()


def render_room_info(room: Room, room_idx: int) -> None:
    """Zeigt Raum-Informationen mit Bearbeiten- und Löschen-Button."""
    # Header mit Buttons
    header_cols = st.columns([10, 1])
    with header_cols[0]:
        st.subheader("Raum")
    with header_cols[1]:
        update_form_key = f"show_room_update_form_{room_idx}"
        show_update = st.session_state.get(update_form_key, False)
        btn_cols = st.columns(2)
        with btn_cols[0]:
            if st.button("✏️" if not show_update else "✖️", key=f"toggle_room_update_{room_idx}"):
                st.session_state[update_form_key] = not show_update
                st.rerun()
        with btn_cols[1]:
            if st.button("🗑️", key=f"delete_room_{room_idx}"):
                st.session_state.building.rooms.pop(room_idx)
                save_building(st.session_state.building)
                st.rerun()

    # Update-Formular oder Info anzeigen
    if st.session_state.get(update_form_key, False):
        render_room_update_form(room, room_idx)
    else:
        col1, col2 = st.columns([2, 2])

        with col1:
            st.write(f"**Fläche:** {room.floor_area_m2:.2f} m²")
            st.write(f"**Volumen:** {room.volume_m3:.2f} m³")
            st.write(f"**Nettohöhe (Innenmaß):** {room.net_height_m:.2f} m")

        with col2:
            room_temp = st.session_state.building.get_temperature_by_name(room.room_temperature_name)
            room_temp_text = format_temperature(room_temp)
            st.write(f"**Raumtemperatur:** {room_temp_text}")
            st.write(f"**Luftwechsel:** {room.ventilation.air_change_1_h} 1/h")
            st.write(f"**Bruttohöhe (Außenmaß):** {room.gross_height_m(st.session_state.building):.2f} m")


# ============================================================================
# Flächen-Editor
# ============================================================================


def render_area_update_form(room: Room, room_idx: int, area_idx: int) -> None:
    """Zeigt Formular zum Aktualisieren einer Fläche."""
    area = room.areas[area_idx]

    with st.form(key=f"update_area_form_{room_idx}_{area_idx}"):
        st.write("**Fläche bearbeiten:**")

        cols = st.columns([2, 2])

        with cols[0]:
            updated_length = st.number_input(
                "Länge (m)",
                min_value=0.1,
                value=area.length_m,
                step=0.1,
                key=f"update_area_length_{room_idx}_{area_idx}",
            )

        with cols[1]:
            updated_width = st.number_input(
                "Breite (m)",
                min_value=0.1,
                value=area.width_m,
                step=0.1,
                key=f"update_area_width_{room_idx}_{area_idx}",
            )

        button_cols = st.columns([9, 1])
        with button_cols[1]:
            submit = st.form_submit_button("💾 Speichern", type="primary")

        if submit:
            area.length_m = updated_length
            area.width_m = updated_width

            st.session_state[f"show_area_update_form_{room_idx}_{area_idx}"] = False
            st.session_state[f"room_{room_idx}_expanded"] = True
            save_building(st.session_state.building)
            st.success(f"Fläche {area_idx + 1} wurde aktualisiert!")
            st.rerun()


# def render_area_info(area: Area, area_idx: int, total_areas: int, room: Room, room_idx: int) -> None:
#     """Zeigt Informationen zu einer Fläche mit Bearbeiten- und Löschen-Button."""
#     net_area = area.area_m2

#     title = f"Fläche {area_idx + 1}" if total_areas > 1 else "Fläche"
#     expander_title = f"📐 {title}: {area.length_m:.2f} m × {area.width_m:.2f} m = {net_area:.2f} m²"

#     with st.expander(expander_title, expanded=False):
#         # Header mit Buttons
#         update_form_key = f"show_area_update_form_{room_idx}_{area_idx}"
#         show_update = st.session_state.get(update_form_key, False)

#         header_cols = st.columns([10, 1])
#         with header_cols[1]:
#             btn_cols = st.columns(2)
#             with btn_cols[0]:
#                 if st.button("✏️" if not show_update else "✖️", key=f"toggle_area_update_{room_idx}_{area_idx}"):
#                     st.session_state[update_form_key] = not show_update
#                     st.rerun()
#             with btn_cols[1]:
#                 if total_areas > 1 and st.button("🗑️", key=f"delete_area_{room_idx}_{area_idx}"):
#                     room.areas.pop(area_idx)
#                     st.session_state[f"room_{room_idx}_expanded"] = True
#                     save_building(st.session_state.building)
#                     st.rerun()

#         # Update-Formular oder Info anzeigen
#         if show_update:
#             render_area_update_form(room, room_idx, area_idx)
#         else:
#             cols = st.columns([2, 2])
#             with cols[0]:
#                 st.write(f"**Länge:** {area.length_m:.2f} m")
#                 st.write(f"**Breite:** {area.width_m:.2f} m")
#             with cols[1]:
#                 st.write(f"**Nettofläche:** {net_area:.2f} m²")


def render_room_areas_editor(room: Room, room_idx: int) -> None:
    """Zeigt den Flächen-Editor für einen Raum."""
    if room.areas is None:
        room.areas = []

    # Header mit Add-Button
    header_cols = st.columns([20, 1])
    with header_cols[0]:
        st.subheader("Flächen")
    with header_cols[1]:
        st.write("")
        if st.button("➕", key=f"add_area_{room_idx}", type="secondary"):
            room.areas.append(Area(length_m=4.0, width_m=3.0))
            st.session_state[f"room_{room_idx}_expanded"] = True
            save_building(st.session_state.building)
            st.rerun()

    # if not room.areas:
    #     st.info("Noch keine Flächen vorhanden.")
    #     return

    # for idx, area in enumerate(room.areas):
    #     render_area_info(area, idx, len(room.areas), room, room_idx)


# ============================================================================
# Wände-Sektion
# ============================================================================


def render_wall_header_and_toggle(room_idx: int) -> bool:
    """Zeigt Header und Toggle-Button für Wände. Gibt zurück ob Formular angezeigt werden soll."""
    form_state_key = f"show_wall_form_{room_idx}"
    show_form = st.session_state.get(form_state_key, False)

    header_cols = st.columns([20, 1])
    with header_cols[0]:
        st.subheader("Wände")
    with header_cols[1]:
        st.write("")
        if st.button("➕" if not show_form else "✖️", key=f"toggle_wall_form_{room_idx}", type="secondary"):
            st.session_state[form_state_key] = not show_form
            st.rerun()

    return show_form


def render_wall_update_form(room_idx: int, wall: Wall, wall_idx: int) -> None:
    """Zeigt Formular zum Aktualisieren einer Wand."""
    with st.form(key=f"update_wall_form_{room_idx}_{wall_idx}"):
        st.write("**Wand bearbeiten:**")

        wall_options = get_wall_catalog()
        wall_by_name = {c.name: c for c in wall_options}

        col1, col2 = st.columns(2)

        with col1:
            updated_orientation = st.text_input(
                "Richtung / Bezeichnung", value=wall.orientation, key=f"update_wall_orientation_{room_idx}_{wall_idx}"
            )

            updated_length = st.number_input(
                "Länge (m)",
                min_value=0.1,
                value=wall.net_length_m,
                step=0.1,
                key=f"update_wall_length_{room_idx}_{wall_idx}",
            )

        with col2:
            current_constr_idx = (
                list(wall_by_name.keys()).index(wall.construction_name) if wall.construction_name in wall_by_name else 0
            )
            updated_construction = st.selectbox(
                "Aufbau",
                options=list(wall_by_name.keys()),
                index=current_constr_idx,
                key=f"update_wall_constr_{room_idx}_{wall_idx}",
            )

            selected_construction = wall_by_name[updated_construction]
            updated_adj_temp = None

            if selected_construction.element_type == ConstructionType.INTERNAL_WALL:
                temp_options = get_temperature_options()
                current_temp_idx = 0
                if wall.adjacent_room_temperature_name and wall.adjacent_room_temperature_name in temp_options:
                    current_temp_idx = list(temp_options.keys()).index(wall.adjacent_room_temperature_name)

                updated_adj_temp = st.selectbox(
                    "Temperatur angrenzender Raum",
                    options=list(temp_options.keys()),
                    index=current_temp_idx,
                    format_func=lambda name: f"{name} ({temp_options[name].value_celsius:.1f} °C)",
                    key=f"update_wall_adj_temp_{room_idx}_{wall_idx}",
                )

        st.write("**Angrenzende Wände:**")
        wall_catalog_names = ["Keine"] + [c.name for c in wall_options]

        neighbor_cols = st.columns(2)
        with neighbor_cols[0]:
            left_idx = wall_catalog_names.index(wall.left_wall_name) if wall.left_wall_name in wall_catalog_names else 0
            updated_left_wall = st.selectbox(
                "Nachbarwand Links",
                options=wall_catalog_names,
                index=left_idx,
                key=f"update_wall_left_{room_idx}_{wall_idx}",
            )

        with neighbor_cols[1]:
            right_idx = (
                wall_catalog_names.index(wall.right_wall_name) if wall.right_wall_name in wall_catalog_names else 0
            )
            updated_right_wall = st.selectbox(
                "Nachbarwand Rechts",
                options=wall_catalog_names,
                index=right_idx,
                key=f"update_wall_right_{room_idx}_{wall_idx}",
            )

        button_cols = st.columns([9, 1])
        with button_cols[1]:
            submit = st.form_submit_button("💾 Speichern", type="primary")

        if submit:
            error = validate_wall_inputs(
                updated_orientation,
                updated_length,
                updated_left_wall,
                updated_right_wall,
                selected_construction,
                updated_adj_temp,
            )

            if error:
                st.error(error)
                return

            wall.orientation = updated_orientation
            wall.net_length_m = updated_length
            wall.construction_name = updated_construction
            wall.left_wall_name = updated_left_wall
            wall.right_wall_name = updated_right_wall
            wall.adjacent_room_temperature_name = updated_adj_temp

            st.session_state[f"show_wall_update_form_{room_idx}_{wall_idx}"] = False
            st.session_state[f"room_{room_idx}_expanded"] = True
            save_building(st.session_state.building)
            st.success(f"Wand '{updated_orientation}' wurde aktualisiert!")
            st.rerun()


def render_wall_item(room: Room, room_idx: int, wall: Wall, wall_idx: int) -> None:
    """Zeigt eine einzelne Wand mit Details."""
    with st.expander(f"🧱 {wall.orientation} ({wall.net_length_m:.2f} m × {room.net_height_m:.2f} m)", expanded=False):
        # Header mit Buttons
        update_form_key = f"show_wall_update_form_{room_idx}_{wall_idx}"
        show_update = st.session_state.get(update_form_key, False)

        header_cols = st.columns([10, 1])
        with header_cols[1]:
            btn_cols = st.columns(2)
            with btn_cols[0]:
                if st.button("✏️" if not show_update else "✖️", key=f"toggle_wall_update_{room_idx}_{wall_idx}"):
                    st.session_state[update_form_key] = not show_update
                    st.rerun()
            with btn_cols[1]:
                if st.button("🗑️", key=f"delete_wall_{room_idx}_{wall_idx}"):
                    room.walls.pop(wall_idx)
                    st.session_state[f"room_{room_idx}_expanded"] = True
                    save_building(st.session_state.building)
                    st.rerun()

        # Update-Formular oder Info anzeigen
        if show_update:
            render_wall_update_form(room_idx, wall, wall_idx)
        else:
            cols = st.columns([2, 2, 1])

            with cols[0]:
                wall_construction = st.session_state.building.get_construction_by_name(wall.construction_name)
                st.write(f"**Konstruktion:** {wall.construction_name}")

                # Zeige Temperatur bei Innenwänden
                if (
                    wall_construction
                    and wall_construction.element_type == ConstructionType.INTERNAL_WALL
                    and wall.adjacent_room_temperature_name
                ):
                    adj_temp = st.session_state.building.get_temperature_by_name(wall.adjacent_room_temperature_name)
                    if adj_temp:
                        st.write(f"**Angrenzender Raum:** {format_temperature(adj_temp)}")

            with cols[1]:
                if wall_construction:
                    st.write(f"**U-Wert:** {wall_construction.u_value_w_m2k:.2f} W/m²K")

            # Längen-Anzeige
            length_cols = st.columns([2, 2, 1])
            with length_cols[0]:
                st.write(f"**Nettolänge (Innenmaß):** {wall.net_length_m:.2f} m")
            with length_cols[1]:
                st.write(f"**Bruttolänge (Außenmaß):** {wall.gross_length_m(st.session_state.building):.2f} m")

            # Nachbarwände
            render_neighbor_walls(wall)

        # Fenster/Türen (immer anzeigen)
        st.divider()
        render_wall_openings(room, room_idx, wall, wall_idx)


def render_neighbor_walls(wall: Wall) -> None:
    """Zeigt angrenzende Wandbauteile."""
    if not wall.left_wall_name and not wall.right_wall_name:
        return

    st.write("**Angrenzende Wandbauteile:**")
    neighbor_cols = st.columns([2, 2, 1])

    with neighbor_cols[0]:
        if wall.left_wall_name:
            left_wall = st.session_state.building.get_construction_by_name(wall.left_wall_name)
            if left_wall:
                wall_thickness_mm = left_wall.thickness_mm or 0.0
                if left_wall.element_type == ConstructionType.INTERNAL_WALL:
                    wall_thickness_mm = wall_thickness_mm / 2
                st.write(f"⬅️ **Links:** {left_wall.name} (Dicke: {wall_thickness_mm:.1f} mm)")

    with neighbor_cols[1]:
        if wall.right_wall_name:
            right_wall = st.session_state.building.get_construction_by_name(wall.right_wall_name)
            if right_wall:
                wall_thickness_mm = right_wall.thickness_mm or 0.0
                if right_wall.element_type == ConstructionType.INTERNAL_WALL:
                    wall_thickness_mm = wall_thickness_mm / 2
                st.write(f"➡️ **Rechts:** {right_wall.name} (Dicke: {wall_thickness_mm:.1f} mm)")


def render_existing_walls(room: Room, room_idx: int) -> None:
    """Zeigt alle existierenden Wände eines Raums."""
    if room.walls:
        st.write("**Vorhandene Wände:**")
        for wall_idx, wall in enumerate(room.walls):
            render_wall_item(room, room_idx, wall, wall_idx)
    else:
        st.info("Noch keine Wände vorhanden.")


def calculate_wall_length_from_areas(room: Room, room_idx: int) -> float:
    """Berechnet die Wandlänge basierend auf Dropdown-Auswahl."""
    areas = room.areas or []
    if not areas:
        return 0.0

    selected_dimensions: list[float] = []

    for rect_idx, area in enumerate(areas, 1):
        selection = st.session_state.get(f"wall_length_rect_{room_idx}_{rect_idx}", "Nicht verwenden")

        if selection.startswith("Länge"):
            selected_dimensions.append(area.length_m)
        elif selection.startswith("Breite"):
            selected_dimensions.append(area.width_m)

    return sum(selected_dimensions) if selected_dimensions else 0.0


def render_wall_length_selector(room: Room, room_idx: int) -> float:
    """Zeigt Auswahl für Wandlänge basierend auf Rechtecken."""
    st.write("**Wandlänge:**")
    areas = room.areas or []
    wall_length_key = f"wall_length_input_{room_idx}"

    if not areas:
        return st.number_input("Länge (m)", min_value=0.1, value=4.0, step=0.1, key=f"wall_length_manual_{room_idx}")

    # Zeige alle Dropdowns in einer Zeile
    num_cols = len(areas) + 1
    cols_dims = st.columns(num_cols)

    # Dropdowns für jedes Rechteck
    for rect_idx, area in enumerate(areas, 1):
        with cols_dims[rect_idx]:
            rect_name = f"Fläche {rect_idx}" if len(areas) > 1 else "Fläche"
            options = ["Nicht verwenden", f"Länge ({area.length_m:.2f} m)", f"Breite ({area.width_m:.2f} m)"]

            st.selectbox(
                rect_name, options=options, key=f"wall_length_rect_{room_idx}_{rect_idx}", label_visibility="visible"
            )

    # Berechne Gesamtlänge
    calculated_length = calculate_wall_length_from_areas(room, room_idx)

    if calculated_length > 0:
        st.session_state[wall_length_key] = calculated_length

    # Eingabefeld ganz links
    with cols_dims[0]:
        return st.number_input(
            "Wandlänge (m) -> aus Länge/Breite der Flächen oder manuell anpassen",
            min_value=0.0,
            step=0.1,
            key=wall_length_key,
        )


def render_wall_neighbor_selectors(room_idx: int, wall_options: list) -> tuple[str, str]:
    """Zeigt Auswahlfelder für Nachbarwände."""
    st.write("**Angrenzende Wände**")
    cols2 = st.columns([2, 2, 2])

    wall_catalog_names = ["Keine"] + [c.name for c in wall_options]

    with cols2[0]:
        left_wall_name = st.selectbox(
            "Aufbau Nachbarwand Links",
            options=wall_catalog_names,
            key=f"wall_left_{room_idx}",
            help="Wählen Sie das Wandbauteil aus dem Katalog, das links angrenzt",
        )

    with cols2[1]:
        right_wall_name = st.selectbox(
            "Aufbau Nachbarwand Rechts",
            options=wall_catalog_names,
            key=f"wall_right_{room_idx}",
            help="Wählen Sie das Wandbauteil aus dem Katalog, das rechts angrenzt",
        )

    return left_wall_name, right_wall_name


def validate_wall_inputs(
    orientation: str, length: float, left_wall: str, right_wall: str, construction, adjacent_temp: str | None
) -> str | None:
    """Validiert Wand-Eingaben. Gibt Fehlermeldung zurück oder None."""
    if not orientation or orientation.strip() == "":
        return "Bitte geben Sie eine Richtung / Bezeichnung für die Wand ein."
        return "Bitte geben Sie eine Richtung / Bezeichnung für die Wand ein."

    if length <= 0:
        return "Bitte geben Sie eine gültige Wandlänge größer als 0 ein."

    if left_wall == "Keine":
        return "Bitte wählen Sie eine Nachbarwand Links aus dem Katalog."

    if right_wall == "Keine":
        return "Bitte wählen Sie eine Nachbarwand Rechts aus dem Katalog."

    if construction.element_type == ConstructionType.INTERNAL_WALL and adjacent_temp is None:
        return "Bitte geben Sie die Temperatur des angrenzenden Raums für die Innenwand ein."

    return None


def render_wall_add_form(room: Room, room_idx: int, wall_options: list) -> None:
    """Zeigt Formular zum Hinzufügen einer neuen Wand."""
    with st.container(border=True):
        wall_by_name = {c.name: c for c in wall_options}

        # Prüfe ob eine Innenwand ausgewählt wurde
        selected_constr_name = st.session_state.get(f"wall_constr_{room_idx}")
        is_internal_wall = False
        if selected_constr_name and selected_constr_name in wall_by_name:
            is_internal_wall = wall_by_name[selected_constr_name].element_type == ConstructionType.INTERNAL_WALL

        st.write("**Aufbau:**")

        # Spalten abhängig von Wandtyp
        cols = st.columns([2, 2, 2]) if is_internal_wall else st.columns([2, 2])

        with cols[0]:
            wall_orientation = st.text_input(
                "Richtung / Bezeichnung",
                value="",
                key=f"wall_orientation_{room_idx}",
                placeholder="z.B. Norden, Osten, Süden 1, Westen 2",
            )

        with cols[1]:
            selected_wall_constr = st.selectbox(
                "Aufbau", options=list(wall_by_name.keys()), key=f"wall_constr_{room_idx}"
            )

        # Temperatur des angrenzenden Raums (nur bei Innenwand)
        adjacent_temp_name = None
        selected_construction = wall_by_name[selected_wall_constr]

        if selected_construction.element_type == ConstructionType.INTERNAL_WALL:
            with cols[2]:
                adjacent_temp_name = render_temperature_selector(
                    f"adjacent_temp_{room_idx}", "Temperatur des angrenzenden Raums"
                )

        # Wandlänge
        wall_length = render_wall_length_selector(room, room_idx)

        # Nachbarwände
        left_wall_name, right_wall_name = render_wall_neighbor_selectors(room_idx, wall_options)

        # Button unten rechts
        button_cols = st.columns([9, 1])
        with button_cols[1]:
            add_wall = st.button("➕ Hinzufügen", type="primary", key=f"add_wall_btn_{room_idx}")

    # Validierung und Hinzufügen
    if add_wall:
        error = validate_wall_inputs(
            wall_orientation, wall_length, left_wall_name, right_wall_name, selected_construction, adjacent_temp_name
        )

        if error:
            st.error(error)
            return

        # Type-Sicherheit: Nach Validierung sind selected_wall_constr garantiert nicht None
        assert selected_wall_constr is not None

        wall = Wall(
            orientation=wall_orientation,
            net_length_m=wall_length,
            construction_name=selected_wall_constr,
            left_wall_name=left_wall_name,
            right_wall_name=right_wall_name,
            adjacent_room_temperature_name=adjacent_temp_name,
        )

        room.walls.append(wall)
        st.session_state[f"show_wall_form_{room_idx}"] = False
        st.session_state[f"room_{room_idx}_expanded"] = True
        save_building(st.session_state.building)
        st.success(f"Wand '{wall_orientation}' hinzugefügt!")
        st.rerun()


def render_walls_section(room: Room, room_idx: int) -> None:
    """Zeigt Wände-Sektion mit Button zum Hinzufügen und Liste."""
    wall_options = get_wall_catalog()

    if not wall_options:
        st.subheader("Wände")
        st.warning("Im Bauteilkatalog fehlen Wand-Konstruktionen. Bitte zuerst im Katalog anlegen.")
        return

    show_form = render_wall_header_and_toggle(room_idx)
    render_existing_walls(room, room_idx)

    if show_form:
        render_wall_add_form(room, room_idx, wall_options)


# ============================================================================
# Fenster & Türen (Wandöffnungen)
# ============================================================================


def render_opening_header_and_toggle(room_idx: int, wall_idx: int) -> bool:
    """Zeigt Header und Toggle für Wandöffnungen."""
    form_state_key = f"show_opening_form_{room_idx}_{wall_idx}"
    show_form = st.session_state.get(form_state_key, False)

    header_cols = st.columns([20, 1])
    with header_cols[0]:
        st.write("**Fenster & Türen**")
    with header_cols[1]:
        if st.button(
            "➕" if not show_form else "✖️", key=f"toggle_opening_form_{room_idx}_{wall_idx}", type="secondary"
        ):
            st.session_state[form_state_key] = not show_form
            st.rerun()

    return show_form


def render_window_update_form(wall: Wall, room_idx: int, wall_idx: int, win_idx: int, window: Element) -> None:
    """Zeigt Formular zum Aktualisieren eines Fensters."""
    with st.form(key=f"update_window_form_{room_idx}_{wall_idx}_{win_idx}"):
        window_options = get_catalog_by_type(ConstructionType.WINDOW)
        window_by_name = {w.name: w for w in window_options}

        cols = st.columns([2, 1.5, 1.5, 2])

        with cols[0]:
            updated_name = st.text_input(
                "Name", value=window.name, key=f"update_window_name_{room_idx}_{wall_idx}_{win_idx}"
            )

        with cols[1]:
            updated_width = st.number_input(
                "Breite (m)",
                min_value=0.1,
                value=window.width_m or 1.2,
                step=0.1,
                key=f"update_window_width_{room_idx}_{wall_idx}_{win_idx}",
            )

        with cols[2]:
            updated_height = st.number_input(
                "Höhe (m)",
                min_value=0.1,
                value=window.height_m or 1.5,
                step=0.1,
                key=f"update_window_height_{room_idx}_{wall_idx}_{win_idx}",
            )

        with cols[3]:
            current_constr_idx = (
                list(window_by_name.keys()).index(window.construction_name)
                if window.construction_name in window_by_name
                else 0
            )
            updated_construction = st.selectbox(
                "Konstruktion",
                options=list(window_by_name.keys()),
                index=current_constr_idx,
                key=f"update_window_constr_{room_idx}_{wall_idx}_{win_idx}",
            )

        button_cols = st.columns([9, 1])
        with button_cols[1]:
            submit = st.form_submit_button("💾", type="primary")

        if submit:
            if not updated_name or updated_name.strip() == "":
                st.error("Bitte geben Sie einen Namen ein.")
                return

            window.name = updated_name
            window.width_m = updated_width
            window.height_m = updated_height
            window.construction_name = updated_construction

            st.session_state[f"show_window_update_form_{room_idx}_{wall_idx}_{win_idx}"] = False
            st.session_state[f"room_{room_idx}_expanded"] = True
            save_building(st.session_state.building)
            st.success(f"Fenster '{updated_name}' wurde aktualisiert!")
            st.rerun()


def render_door_update_form(wall: Wall, room_idx: int, wall_idx: int, door_idx: int, door: Element) -> None:
    """Zeigt Formular zum Aktualisieren einer Tür."""
    with st.form(key=f"update_door_form_{room_idx}_{wall_idx}_{door_idx}"):
        door_options = get_catalog_by_type(ConstructionType.DOOR)
        door_by_name = {d.name: d for d in door_options}

        cols = st.columns([2, 1.5, 1.5, 2])

        with cols[0]:
            updated_name = st.text_input(
                "Name", value=door.name, key=f"update_door_name_{room_idx}_{wall_idx}_{door_idx}"
            )

        with cols[1]:
            updated_width = st.number_input(
                "Breite (m)",
                min_value=0.1,
                value=door.width_m or 0.87,
                step=0.1,
                key=f"update_door_width_{room_idx}_{wall_idx}_{door_idx}",
            )

        with cols[2]:
            updated_height = st.number_input(
                "Höhe (m)",
                min_value=0.1,
                value=door.height_m or 2.1,
                step=0.1,
                key=f"update_door_height_{room_idx}_{wall_idx}_{door_idx}",
            )

        with cols[3]:
            current_constr_idx = (
                list(door_by_name.keys()).index(door.construction_name) if door.construction_name in door_by_name else 0
            )
            updated_construction = st.selectbox(
                "Konstruktion",
                options=list(door_by_name.keys()),
                index=current_constr_idx,
                key=f"update_door_constr_{room_idx}_{wall_idx}_{door_idx}",
            )

        button_cols = st.columns([9, 1])
        with button_cols[1]:
            submit = st.form_submit_button("💾", type="primary")

        if submit:
            if not updated_name or updated_name.strip() == "":
                st.error("Bitte geben Sie einen Namen ein.")
                return

            door.name = updated_name
            door.width_m = updated_width
            door.height_m = updated_height
            door.construction_name = updated_construction

            st.session_state[f"show_door_update_form_{room_idx}_{wall_idx}_{door_idx}"] = False
            st.session_state[f"room_{room_idx}_expanded"] = True
            save_building(st.session_state.building)
            st.success(f"Tür '{updated_name}' wurde aktualisiert!")
            st.rerun()


def render_window_list(wall: Wall, room_idx: int, wall_idx: int) -> None:
    """Zeigt Liste der Fenster mit Update-Funktion."""
    if not wall.windows:
        return

    st.write("*Fenster:*")
    for win_idx, window in enumerate(wall.windows):
        update_form_key = f"show_window_update_form_{room_idx}_{wall_idx}_{win_idx}"
        show_update = st.session_state.get(update_form_key, False)

        if show_update:
            render_window_update_form(wall, room_idx, wall_idx, win_idx, window)
        else:
            cols = st.columns([2, 8, 1])
            with cols[0]:
                st.write(f"{window.name}")
            with cols[1]:
                win_construction = st.session_state.building.get_construction_by_name(window.construction_name)
                u_value_str = f"{win_construction.u_value_w_m2k:.2f}" if win_construction else "N/A"
                st.write(
                    f"{window.width_m:.2f} × {window.height_m:.2f} m = {window.area_m2:.2f} m² | U: {u_value_str} W/m²K"
                )
            with cols[2]:
                btn_cols = st.columns(2)
                with btn_cols[0]:
                    if st.button("✏️", key=f"edit_win_{room_idx}_{wall_idx}_{win_idx}"):
                        st.session_state[update_form_key] = True
                        st.rerun()
                with btn_cols[1]:
                    if st.button("🗑️", key=f"del_win_{room_idx}_{wall_idx}_{win_idx}"):
                        wall.windows.pop(win_idx)
                        st.session_state[f"room_{room_idx}_expanded"] = True
                        save_building(st.session_state.building)
                        st.rerun()


def render_door_list(wall: Wall, room_idx: int, wall_idx: int) -> None:
    """Zeigt Liste der Türen mit Update-Funktion."""
    if not wall.doors:
        return

    st.write("*Türen:*")
    for door_idx, door in enumerate(wall.doors):
        update_form_key = f"show_door_update_form_{room_idx}_{wall_idx}_{door_idx}"
        show_update = st.session_state.get(update_form_key, False)

        if show_update:
            render_door_update_form(wall, room_idx, wall_idx, door_idx, door)
        else:
            cols = st.columns([2, 8, 1])
            with cols[0]:
                st.write(f"{door.name}")
            with cols[1]:
                door_construction = st.session_state.building.get_construction_by_name(door.construction_name)
                u_value_str = f"{door_construction.u_value_w_m2k:.2f}" if door_construction else "N/A"
                st.write(f"{door.width_m:.2f} × {door.height_m:.2f} m = {door.area_m2:.2f} m² | U: {u_value_str} W/m²K")
            with cols[2]:
                btn_cols = st.columns(2)
                with btn_cols[0]:
                    if st.button("✏️", key=f"edit_door_{room_idx}_{wall_idx}_{door_idx}"):
                        st.session_state[update_form_key] = True
                        st.rerun()
                with btn_cols[1]:
                    if st.button("🗑️", key=f"del_door_{room_idx}_{wall_idx}_{door_idx}"):
                        wall.doors.pop(door_idx)
                        st.session_state[f"room_{room_idx}_expanded"] = True
                        save_building(st.session_state.building)
                        st.rerun()


def get_opening_catalog_options() -> tuple[list, dict]:
    """Erstellt kombinierte Liste von Fenster- und Tür-Optionen."""
    window_options = get_catalog_by_type(ConstructionType.WINDOW)
    door_options = get_catalog_by_type(ConstructionType.DOOR)

    combined_options = []
    opening_by_display_name = {}

    for window in window_options:
        display_name = f"🪟 {window.name}"
        combined_options.append(display_name)
        opening_by_display_name[display_name] = window

    for door in door_options:
        display_name = f"🚪 {door.name}"
        combined_options.append(display_name)
        opening_by_display_name[display_name] = door

    return combined_options, opening_by_display_name


def render_opening_add_form(wall: Wall, room_idx: int, wall_idx: int) -> None:
    """Zeigt Formular zum Hinzufügen von Fenstern/Türen."""
    with st.form(key=f"add_opening_form_{room_idx}_{wall_idx}"):
        cols = st.columns([1, 2, 1.5, 1.5, 2])

        with cols[0]:
            opening_type = cast(
                ElementType,
                st.selectbox(
                    "Typ",
                    options=["window", "door"],
                    format_func=lambda x: "Fenster" if x == "window" else "Tür",
                    key=f"opening_type_{room_idx}_{wall_idx}",
                ),
            )

        with cols[1]:
            opening_name = st.text_input(
                "Name",
                value="",
                placeholder=f"z.B. {'Fenster' if opening_type == 'window' else 'Tür'} 1",
                key=f"opening_name_{room_idx}_{wall_idx}",
            )

        with cols[2]:
            opening_width = st.number_input(
                "Breite (m)",
                min_value=0.1,
                value=1.2 if opening_type == "window" else 0.87,
                step=0.1,
                key=f"opening_width_{room_idx}_{wall_idx}",
            )

        with cols[3]:
            opening_height = st.number_input(
                "Höhe (m)",
                min_value=0.1,
                value=1.5 if opening_type == "window" else 2.1,
                step=0.1,
                key=f"opening_height_{room_idx}_{wall_idx}",
            )

        with cols[4]:
            combined_options, opening_by_display_name = get_opening_catalog_options()

            if not combined_options:
                st.error("Keine Fenster- oder Tür-Konstruktionen im Katalog!")
                selected_opening_constr = None
            else:
                selected_opening_display = st.selectbox(
                    "Konstruktion", options=combined_options, key=f"opening_constr_{room_idx}_{wall_idx}"
                )
                selected_opening_constr = selected_opening_display

        # Button rechts ausrichten
        button_cols = st.columns([9, 1])
        with button_cols[1]:
            add_opening = st.form_submit_button("➕ Hinzufügen", type="primary", disabled=not combined_options)

        if add_opening:
            if not opening_name or opening_name.strip() == "":
                st.error("Bitte geben Sie einen Namen ein.")
                return

            if not selected_opening_constr:
                st.error("Bitte wählen Sie eine Konstruktion aus.")
                return

            construction = opening_by_display_name[selected_opening_constr]

            # Validiere Typ und Konstruktion
            if opening_type == "window" and construction.element_type != ConstructionType.WINDOW:
                st.error("Bitte wählen Sie eine Fenster-Konstruktion (🪟) für einen Fenster-Typ.")
                return
            if opening_type == "door" and construction.element_type != ConstructionType.DOOR:
                st.error("Bitte wählen Sie eine Tür-Konstruktion (🚪) für einen Tür-Typ.")
                return

            element = Element(
                type=opening_type,
                name=opening_name,
                construction_name=construction.name,
                width_m=opening_width,
                height_m=opening_height,
            )

            if opening_type == "window":
                wall.windows.append(element)
            else:
                wall.doors.append(element)

            st.session_state[f"show_opening_form_{room_idx}_{wall_idx}"] = False
            st.session_state[f"room_{room_idx}_expanded"] = True
            save_building(st.session_state.building)
            st.success(f"{'Fenster' if opening_type == 'window' else 'Tür'} '{opening_name}' hinzugefügt!")
            st.rerun()


def render_wall_openings(room: Room, room_idx: int, wall: Wall, wall_idx: int) -> None:
    """Zeigt Fenster und Türen einer Wand."""
    show_form = render_opening_header_and_toggle(room_idx, wall_idx)

    render_window_list(wall, room_idx, wall_idx)
    render_door_list(wall, room_idx, wall_idx)

    if not wall.windows and not wall.doors:
        st.info("Keine Fenster oder Türen vorhanden.")

    if show_form:
        render_opening_add_form(wall, room_idx, wall_idx)


# ============================================================================
# Raum-Detail-Ansicht
# ============================================================================


def render_room_detail(room: Room, room_idx: int) -> None:
    """Zeigt Details und Bauteile eines Raums."""
    expander_state_key = f"room_{room_idx}_expanded"
    expanded = bool(st.session_state.get(expander_state_key, False))

    with st.expander(f"📐 {room.name} ({room.volume_m3:.2f} m³)", expanded=expanded):
        render_room_heat_loads(room, room_idx)
        render_room_info(room, room_idx)
        render_room_floor_ceiling_assignment(room)
        render_room_areas_editor(room, room_idx)
        render_walls_section(room, room_idx)


# ============================================================================
# Haupt-Render-Funktion
# ============================================================================


def render_rooms_tab() -> None:
    """Rendert den kompletten Räume-Tab."""
    st.header("Räume")
    render_room_add_form()
    st.divider()

    if not st.session_state.building.rooms:
        st.info("👆 Fügen Sie zuerst einen Raum hinzu, um zu beginnen.")
        return

    for room_idx, room in enumerate(st.session_state.building.rooms):
        render_room_detail(room, room_idx)
