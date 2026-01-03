"""Tab für die Räume."""

import streamlit as st
from typing import cast
from src.din12831.models import Room, Element, Ventilation, Area, ConstructionType, Wall, ElementType, Temperature
from src.din12831.calc_heat_load import calc_room_heat_load
from utils import save_building, get_catalog_by_type


def render_room_floor_ceiling_assignment(room: Room) -> None:
    current_floor = room.floor.construction_name if room.floor else "Nicht zugewiesen"
    current_ceiling = room.ceiling.construction_name if room.ceiling else "Nicht zugewiesen"

    col1, col2, _ = st.columns([2, 2, 1])
    with col1:
        adj_temp_str = ""
        if room.floor and room.floor.adjacent_temperature_name:
            adj_temp = st.session_state.building.get_temperature_by_name(room.floor.adjacent_temperature_name)
            if adj_temp:
                adj_temp_str = f"*Angrenzende Temperatur:* {adj_temp.name} ({adj_temp.value_celsius:.1f} °C)"
        st.write(f"**Boden:** {current_floor} - {adj_temp_str}")
    with col2:
        if room.ceiling and room.ceiling.adjacent_temperature_name:
            adj_temp = st.session_state.building.get_temperature_by_name(room.ceiling.adjacent_temperature_name)
            if adj_temp:
                adj_temp_str = f"*Angrenzende Temperatur:* {adj_temp.name} ({adj_temp.value_celsius:.1f} °C)"
        st.write(f"**Decke:** {current_ceiling} - {adj_temp_str}")


def render_room_add_form() -> None:
    """Zeigt Formular zum Hinzufügen eines neuen Raums."""
    is_empty = len(st.session_state.building.rooms) == 0

    # Bestimme den vorausgewählten Index basierend auf der Standard-Raumtemperatur
    temp_catalog: list[Temperature] = st.session_state.building.temperature_catalog
    temp_by_name: dict[str, Temperature] = {t.name: t for t in temp_catalog}

    default_index = 0
    default_temp_name = st.session_state.building.default_room_temperature_name
    if default_temp_name and default_temp_name in temp_by_name:
        default_index = list(temp_by_name.keys()).index(default_temp_name)

    with st.expander("➕ Neuen Raum hinzufügen", expanded=is_empty):
        col1, col2 = st.columns(2)

        rect_ids_key = "new_room_rect_ids"
        if rect_ids_key not in st.session_state:
            st.session_state[rect_ids_key] = [1]

        with col1:
            new_room_name = st.text_input("Raumname", key="new_room_name")
            st.write("**Flächen**")
            rectangles_payload: list[Area] = []

            rect_ids: list[int] = st.session_state[rect_ids_key]
            for _, rect_id in enumerate(list(rect_ids)):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    r_len = st.number_input(
                        f"Länge (m)",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                        key=f"new_room_rect_{rect_id}_len",
                    )
                with c2:
                    r_wid = st.number_input(
                        f"Breite (m)",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                        key=f"new_room_rect_{rect_id}_wid",
                    )
                with c3:
                    if len(rect_ids) > 1 and st.button("🗑️", key=f"new_room_rect_{rect_id}_del"):
                        rect_ids.remove(rect_id)
                        st.session_state[rect_ids_key] = rect_ids
                        st.rerun()

                rectangles_payload.append(Area(length_m=float(r_len), width_m=float(r_wid)))

            if st.button("➕ Weitere Fläche hinzufügen", key="add_new_room_rect"):
                max_id = max(rect_ids) if rect_ids else 0
                rect_ids.append(max_id + 1)
                st.session_state[rect_ids_key] = rect_ids
                st.rerun()

        with col2:
            new_height = st.number_input(
                "Höhe (m)", min_value=0.1, value=2.5, step=0.1, key="new_height")

            # Raumtemperatur aus Katalog auswählen
            if temp_catalog:
                selected_temp_name = st.selectbox(
                    "Raumtemperatur",
                    options=list(temp_by_name.keys()),
                    index=default_index,
                    format_func=lambda name: f"{name} ({temp_by_name[name].value_celsius:.1f} °C)",
                    key="new_temp"
                )
            else:
                st.error("Bitte zuerst Temperaturen im Temperaturkatalog anlegen.")
                selected_temp_name = None

            new_air_change = st.number_input(
                "Luftwechsel (1/h)", min_value=0.0, value=0.5, step=0.1, key="new_air_change")

            floor_options = get_catalog_by_type(ConstructionType.FLOOR)
            ceiling_options = get_catalog_by_type(ConstructionType.CEILING)

            # Boden-Sektion
            st.write("**Boden:**")
            col_floor_1, col_floor_2 = st.columns(2)
            with col_floor_1:
                if floor_options:
                    st.selectbox(
                        "Konstruktion",
                        options=[c.name for c in floor_options],
                        key="new_room_floor_construction",
                    )
                else:
                    st.error("Im Bauteilkatalog fehlt mindestens eine Boden-Konstruktion.")

            with col_floor_2:
                if temp_catalog:
                    temp_by_name = {t.name: t for t in temp_catalog}
                    st.selectbox(
                        "Angrenzende Temperatur",
                        options=list(temp_by_name.keys()),
                        index=default_index,
                        format_func=lambda name: f"{name} ({temp_by_name[name].value_celsius:.1f} °C)",
                        key="new_floor_adjacent_temp",
                        help="Temperatur des Raums/Bereichs unterhalb des Bodens"
                    )

            # Decken-Sektion
            st.write("**Decke:**")
            col_ceiling_1, col_ceiling_2 = st.columns(2)
            with col_ceiling_1:
                if ceiling_options:
                    st.selectbox(
                        "Konstruktion",
                        options=[c.name for c in ceiling_options],
                        key="new_room_ceiling_construction",
                    )
                else:
                    st.error("Im Bauteilkatalog fehlt mindestens eine Decken-Konstruktion.")

            with col_ceiling_2:
                if temp_catalog:
                    temp_by_name = {t.name: t for t in temp_catalog}
                    st.selectbox(
                        "Angrenzende Temperatur",
                        options=list(temp_by_name.keys()),
                        index=default_index,
                        format_func=lambda name: f"{name} ({temp_by_name[name].value_celsius:.1f} °C)",
                        key="new_ceiling_adjacent_temp",
                        help="Temperatur des Raums/Bereichs oberhalb der Decke"
                    )

        if not st.button("Raum hinzufügen", type="primary"):
            return

        if not new_room_name:
            st.error("Bitte geben Sie einen Raumnamen ein.")
            return

        if not rectangles_payload:
            st.error("Bitte mindestens eine Fläche angeben.")
            return

        # Validierung: Länge und Breite müssen größer als 0 sein
        for idx, area in enumerate(rectangles_payload, 1):
            if area.length_m <= 0 or area.width_m <= 0:
                st.error(f"Fläche {idx}: Länge und Breite müssen größer als 0 sein.")
                return

        # Validierung: Temperatur ausgewählt
        if not selected_temp_name:
            st.error("Bitte wählen Sie eine Raumtemperatur aus dem Katalog.")
            return

        floor_options = get_catalog_by_type(ConstructionType.FLOOR)
        ceiling_options = get_catalog_by_type(ConstructionType.CEILING)
        if not floor_options or not ceiling_options:
            st.error(
                "Bitte zuerst im Bauteilkatalog mindestens eine 'Boden'- und eine 'Decke'-Konstruktion anlegen."
            )
            return

        floor_by_name = {c.name: c for c in floor_options}
        ceiling_by_name = {c.name: c for c in ceiling_options}
        floor_selected = cast(str, st.session_state.get("new_room_floor_construction"))
        ceiling_selected = cast(str, st.session_state.get("new_room_ceiling_construction"))

        if floor_selected not in floor_by_name or ceiling_selected not in ceiling_by_name:
            st.error("Bitte Boden und Decke aus dem Katalog auswählen.")
            return

        new_room = Room(
            name=new_room_name,
            areas=rectangles_payload,
            net_height_m=new_height,
            room_temperature_name=selected_temp_name,
            ventilation=Ventilation(air_change_1_h=new_air_change)
        )

        # Boden/Decke als direkte Felder (Fläche = Raumfläche)
        floor_adjacent_temp = cast(str, st.session_state.get("new_floor_adjacent_temp"))
        ceiling_adjacent_temp = cast(str, st.session_state.get("new_ceiling_adjacent_temp"))

        new_room.floor = Element(
            type="floor",
            name="Boden",
            construction_name=floor_selected,
            adjacent_temperature_name=floor_adjacent_temp,
        )
        new_room.ceiling = Element(
            type="ceiling",
            name="Decke",
            construction_name=ceiling_selected,
            adjacent_temperature_name=ceiling_adjacent_temp,
        )
        st.session_state.building.rooms.append(new_room)

        # Eingabe zurücksetzen
        st.session_state[rect_ids_key] = [1]
        for key in list(st.session_state.keys()):
            if isinstance(key, str) and key.startswith("new_room_rect_"):
                del st.session_state[key]

        save_building(st.session_state.building)
        st.success(f"Raum '{new_room_name}' wurde hinzugefügt!")
        st.rerun()


def render_room_heat_loads(room: Room, room_idx: int) -> None:
    """Berechnet und zeigt die Heizlasten eines Raums."""
    try:
        result = calc_room_heat_load(room, st.session_state.building.outside_temperature.value_celsius, st.session_state.building)

        st.subheader("🔥 Heizlasten")
        heat_col1, heat_col2, heat_col3 = st.columns(3)

        with heat_col1:
            st.metric("Transmissionswärmeverlust", f"{result.transmission_w:.0f} W", help="Wärmeverlust durch Bauteile (Wände, Decke, Boden, Fenster, Türen)")
        with heat_col2:
            st.metric("Lüftungswärmeverlust", f"{result.ventilation_w:.0f} W", help="Wärmeverlust durch Luftwechsel")
        with heat_col3:
            st.metric("Gesamt-Heizlast", f"{result.total_w:.0f} W", help="Summe aus Transmissions- und Lüftungswärmeverlust")

        # Details zu den einzelnen Bauteilen
        if result.element_transmissions:
            with st.expander("📋 Details nach Bauteilen", expanded=False):
                st.write("**Transmissionswärmeverluste der einzelnen Bauteile:**")

                # Überschriftenzeile
                header_cols = st.columns([3, 1, 1, 1, 1.5])
                with header_cols[0]:
                    st.write("**Bauteil**")
                with header_cols[1]:
                    st.write("**Fläche [m²]**")
                with header_cols[2]:
                    st.write("**U-Wert [W/m²K]**")
                with header_cols[3]:
                    st.write("**ΔT [K]**")
                with header_cols[4]:
                    st.write("**Wärmeverlust [W]**")

                # Erstelle eine Tabelle mit den Wärmeverlusten
                for element in result.element_transmissions:
                    cols = st.columns([3, 1, 1, 1, 1.5])
                    with cols[0]:
                        st.write(f"• {element.element_name}")
                    with cols[1]:
                        st.write(f"{element.area_m2:.2f}")
                    with cols[2]:
                        st.write(f"{element.u_value_w_m2k:.2f}")
                    with cols[3]:
                        st.write(f"{element.delta_temp_k:.1f}")
                    with cols[4]:
                        st.write(f"**{element.transmission_w:.0f}**")

                st.divider()
                st.write(f"**Summe Transmission:** {result.transmission_w:.0f} W")

        st.divider()

    except Exception as e:
        st.warning(f"Heizlast konnte nicht berechnet werden: {str(e)}")


def render_room_info(room: Room, room_idx: int) -> None:
    """Zeigt Raum-Informationen und Löschen-Button."""
    st.subheader("Raum")
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        st.write(f"**Fläche:** {room.floor_area_m2:.2f} m²")
        st.write(f"**Volumen:** {room.volume_m3:.2f} m³")
        st.write(f"**Nettohöhe (Innenmaß):** {room.net_height_m:.2f} m")
    with col2:
        # Lade Temperatur dynamisch aus Katalog
        room_temp = st.session_state.building.get_temperature_by_name(room.room_temperature_name)
        room_temp_text = f"{room_temp.name} ({room_temp.value_celsius:.1f}°C)" if room_temp else "Nicht zugewiesen"
        st.write(f"**Raumtemperatur:** {room_temp_text}")
        st.write(f"**Luftwechsel:** {room.ventilation.air_change_1_h} 1/h")
        st.write(f"**Bruttohöhe (Außenmaß):** {room.gross_height_m(st.session_state.building):.2f} m")
    with col3:
        if st.button("🗑️ Löschen", key=f"delete_room_{room_idx}"):
            st.session_state.building.rooms.pop(room_idx)
            save_building(st.session_state.building)
            st.rerun()


def render_room_areas_editor(room: Room, room_idx: int) -> None:
    if room.areas is None:
        room.areas = []

    rect_ids_key = f"room_{room_idx}_rect_ids"
    if rect_ids_key not in st.session_state or len(st.session_state[rect_ids_key]) != len(room.areas):
        st.session_state[rect_ids_key] = list(range(1, len(room.areas) + 1)) or [1]
        if not room.areas:
            room.areas = [Area(length_m=4.0, width_m=3.0)]

    rect_ids: list[int] = st.session_state[rect_ids_key]

    st.subheader("Flächen")
    for idx, _ in enumerate(list(rect_ids)):
        rect = room.areas[idx]
        cols = st.columns([2, 2, 1])
        with cols[0]:
            st.write(f"**Länge:** {rect.length_m} m")
        with cols[1]:
            st.write(f"**Breite:** {rect.width_m} m")


def render_walls_section(room: Room, room_idx: int) -> None:
    """Zeigt Wände-Sektion mit Button zum Hinzufügen und Liste."""
    # Hole beide Wandtypen aus dem Katalog
    external_walls = get_catalog_by_type(ConstructionType.EXTERNAL_WALL)
    internal_walls = get_catalog_by_type(ConstructionType.INTERNAL_WALL)
    wall_options = external_walls + internal_walls

    if not wall_options:
        st.subheader("Wände")
        st.warning("Im Bauteilkatalog fehlen Wand-Konstruktionen. Bitte zuerst im Katalog anlegen.")
        return

    # Header und Button in derselben Zeile
    form_state_key = f"show_wall_form_{room_idx}"
    show_form = st.session_state.get(form_state_key, False)

    header_cols = st.columns([20, 1])
    with header_cols[0]:
        st.subheader("Wände")
    with header_cols[1]:
        st.write("")
        if st.button("➕" if not show_form else "✖️",
                     key=f"toggle_wall_form_{room_idx}",
                     type="secondary",
                     use_container_width=True):
            st.session_state[form_state_key] = not show_form
            st.rerun()

    # Liste der vorhandenen Wände
    if room.walls:
        st.write("**Vorhandene Wände:**")
        for wall_idx, wall in enumerate(room.walls):
            with st.expander(f"🧱 {wall.orientation} ({wall.net_length_m:.2f} m × {room.net_height_m:.2f} m)", expanded=False):
                cols = st.columns([2, 2, 1])

                with cols[0]:
                    wall_construction = st.session_state.building.get_construction_by_name(wall.construction_name)
                    st.write(f"**Konstruktion:** {wall.construction_name}")
                    # Zeige Temperatur bei Innenwänden - lade dynamisch aus Katalog
                    if wall_construction and wall_construction.element_type == ConstructionType.INTERNAL_WALL and wall.adjacent_room_temperature_name is not None:
                        adj_temp = st.session_state.building.get_temperature_by_name(wall.adjacent_room_temperature_name)
                        if adj_temp:
                            st.write(f"**Angrenzender Raum:** {adj_temp.name} ({adj_temp.value_celsius:.1f} °C)")
                with cols[1]:
                    if wall_construction:
                        st.write(f"**U-Wert:** {wall_construction.u_value_w_m2k:.2f} W/m²K")
                with cols[2]:
                    if st.button("🗑️", key=f"delete_wall_{room_idx}_{wall_idx}"):
                        room.walls.pop(wall_idx)
                        st.session_state[f"room_{room_idx}_expanded"] = True
                        save_building(st.session_state.building)
                        st.rerun()

                # Längen-Anzeige
                length_cols = st.columns([2, 2, 1])
                with length_cols[0]:
                    st.write(f"**Nettolänge (Innenmaß):** {wall.net_length_m:.2f} m")
                with length_cols[1]:
                    st.write(f"**Bruttolänge (Außenmaß):** {wall.gross_length_m(st.session_state.building):.2f} m")

                # Nachbarwände (Bauteile aus Katalog) anzeigen
                if wall.left_wall_name or wall.right_wall_name:
                    st.write("**Angrenzende Wandbauteile:**")
                    neighbor_cols = st.columns([2, 2, 1])
                    with neighbor_cols[0]:
                        if wall.left_wall_name:
                            left_wall = st.session_state.building.get_construction_by_name(wall.left_wall_name)
                            if left_wall:
                                wall_thickness = left_wall.thickness_m or 0.0
                                wall_thickness = wall_thickness / 2 if left_wall.element_type == ConstructionType.INTERNAL_WALL else wall_thickness
                                st.write(f"⬅️ **Links:** {left_wall.name} (Dicke: {wall_thickness} m)")
                    with neighbor_cols[1]:
                        if wall.right_wall_name:
                            right_wall = st.session_state.building.get_construction_by_name(wall.right_wall_name)
                            if right_wall:
                                wall_thickness = right_wall.thickness_m or 0.0
                                wall_thickness = wall_thickness / 2 if right_wall.element_type == ConstructionType.INTERNAL_WALL else wall_thickness
                                st.write(f"➡️ **Rechts:** {right_wall.name} (Dicke: {wall_thickness} m)")

                # Fenster/Türen-Sektion
                st.divider()
                render_wall_openings(room, room_idx, wall, wall_idx)
    else:
        st.info("Noch keine Wände vorhanden.")

    # Formular nur anzeigen wenn aktiviert
    if show_form:
        # Container mit Rahmen anstatt st.form
        with st.container(border=True):
            # Restliche Eingaben
            st.write("**Aufbau:**")

            # Bestimme zuerst die ausgewählte Konstruktion
            wall_by_name = {c.name: c for c in wall_options}

            # Prüfe ob eine Innenwand ausgewählt wurde für dynamische Spaltenanzahl
            selected_constr_name = st.session_state.get(f"wall_constr_{room_idx}")
            is_internal_wall = False
            if selected_constr_name and selected_constr_name in wall_by_name:
                is_internal_wall = wall_by_name[selected_constr_name].element_type == ConstructionType.INTERNAL_WALL

            # Spalten abhängig von Wandtyp
            if is_internal_wall:
                cols = st.columns([2, 2, 2])
            else:
                cols = st.columns([2, 2])

            with cols[0]:
                wall_orientation = st.text_input(
                    "Richtung / Bezeichnung",
                    value="",
                    key=f"wall_orientation_{room_idx}",
                    placeholder="z.B. Norden, Osten, Süden 1, Westen 2"
                )

            with cols[1]:
                selected_wall_constr = st.selectbox(
                    "Aufbau",
                    options=list(wall_by_name.keys()),
                    key=f"wall_constr_{room_idx}"
                )

            # Temperatur des angrenzenden Raums (nur bei Innenwand) - neben Aufbau
            adjacent_temp_name = None
            selected_construction = wall_by_name[selected_wall_constr]
            if selected_construction.element_type == ConstructionType.INTERNAL_WALL:
                with cols[2]:
                    temp_catalog = st.session_state.building.temperature_catalog
                    if temp_catalog:
                        temp_by_name = {t.name: t for t in temp_catalog}

                        # Bestimme Standardindex basierend auf default_room_temperature_name
                        default_adj_index = 0
                        default_temp_name = st.session_state.building.default_room_temperature_name
                        if default_temp_name and default_temp_name in temp_by_name:
                            default_adj_index = list(temp_by_name.keys()).index(default_temp_name)

                        selected_adj_temp_name = st.selectbox(
                            "Temperatur des angrenzenden Raums",
                            options=list(temp_by_name.keys()),
                            index=default_adj_index,
                            format_func=lambda name: f"{name} ({temp_by_name[name].value_celsius:.1f} °C)",
                            key=f"adjacent_temp_{room_idx}",
                            help="Wählen Sie die Temperatur des Raums, der an diese Innenwand angrenzt"
                        )
                        adjacent_temp_name = selected_adj_temp_name
                    else:
                        st.error("Keine Temperaturen im Katalog")

            # Berechne die Gesamtlänge aus den Dropdowns
            st.write("**Wandlänge:**")
            areas = room.areas or []
            selected_dimensions: list[float] = []

            if areas:
                # Zeige alle Dropdowns in einer Zeile
                num_cols = len(areas) + 1  # +1 für das Eingabefeld
                cols_dims = st.columns(num_cols)

                # Session-State-Key für den aktuellen Wert
                wall_length_key = f"wall_length_input_{room_idx}"

                # Für jedes Rechteck ein Dropdown
                for rect_idx, area in enumerate(areas, 1):
                    with cols_dims[rect_idx]:  # +1 Offset wegen Eingabefeld ganz links
                        rect_name = f"Fläche {rect_idx}" if len(areas) > 1 else "Fläche"
                        options = [
                            "Nicht verwenden",
                            f"Länge ({area.length_m:.2f} m)",
                            f"Breite ({area.width_m:.2f} m)"
                        ]

                        selection = st.selectbox(
                            rect_name,
                            options=options,
                            key=f"wall_length_rect_{room_idx}_{rect_idx}",
                            label_visibility="visible"
                        )

                        # Wert extrahieren wenn ausgewählt
                        if selection.startswith("Länge"):
                            selected_dimensions.append(area.length_m)
                        elif selection.startswith("Breite"):
                            selected_dimensions.append(area.width_m)

                # Berechne Gesamtlänge aus Dropdowns
                calculated_length = sum(selected_dimensions) if selected_dimensions else 0.0

                # Wenn sich die berechnete Länge geändert hat, aktualisiere das Eingabefeld
                if calculated_length > 0:
                    st.session_state[wall_length_key] = calculated_length

                # Eingabefeld für Wandlänge GANZ LINKS (erste Spalte)
                with cols_dims[0]:
                    wall_length = st.number_input(
                        "Wandlänge (m) -> aus Länge/Breite der Flächen oder manuell anpassen",
                        min_value=0.0,
                        step=0.1,
                        key=wall_length_key,
                    )
            else:
                # Fallback: Nur manuelle Eingabe wenn keine Rechtecke vorhanden
                wall_length = st.number_input(
                    "Länge (m)",
                    min_value=0.1,
                    value=4.0,
                    step=0.1,
                    key=f"wall_length_manual_{room_idx}"
                )

            # Nachbarwände aus Katalog auswählen
            st.write("**Angrenzende Wände**")
            cols2 = st.columns([2, 2, 2])

            # Liste der Wandbauteile aus dem Katalog mit "Keine" Option
            wall_catalog_names = ["Keine"] + [c.name for c in wall_options]

            with cols2[0]:
                left_wall_name = st.selectbox(
                    "Aufbau Nachbarwand Links",
                    options=wall_catalog_names,
                    key=f"wall_left_{room_idx}",
                    help="Wählen Sie das Wandbauteil aus dem Katalog, das links angrenzt"
                )

            with cols2[1]:
                right_wall_name = st.selectbox(
                    "Aufbau Nachbarwand Rechts",
                    options=wall_catalog_names,
                    key=f"wall_right_{room_idx}",
                    help="Wählen Sie das Wandbauteil aus dem Katalog, das rechts angrenzt"
                )

            # Button unten rechts ausrichten
            button_cols = st.columns([6, 1])
            with button_cols[1]:
                add_wall = st.button("➕ Hinzufügen", type="primary", use_container_width=True, key=f"add_wall_btn_{room_idx}")

        # Validierung und Hinzufügen außerhalb des Containers (nach Button-Click)
        if add_wall:
            # Validierung der Pflichtfelder
            if not wall_orientation or wall_orientation.strip() == "":
                st.error("Bitte geben Sie eine Richtung / Bezeichnung für die Wand ein.")
            elif wall_length <= 0:
                st.error("Bitte geben Sie eine gültige Wandlänge größer als 0 ein.")
            elif left_wall_name == "Keine":
                st.error("Bitte wählen Sie eine Nachbarwand Links aus dem Katalog.")
            elif right_wall_name == "Keine":
                st.error("Bitte wählen Sie eine Nachbarwand Rechts aus dem Katalog.")
            elif selected_construction.element_type == ConstructionType.INTERNAL_WALL and adjacent_temp_name is None:
                st.error("Bitte geben Sie die Temperatur des angrenzenden Raums für die Innenwand ein.")
            else:
                wall = Wall(
                    orientation=wall_orientation,
                    net_length_m=wall_length,
                    construction_name=selected_wall_constr,
                    left_wall_name=left_wall_name,
                    right_wall_name=right_wall_name,
                    adjacent_room_temperature_name=adjacent_temp_name,
                )

                room.walls.append(wall)
                # Formular ausblenden und State zurücksetzen
                st.session_state[form_state_key] = False
                st.session_state[f"room_{room_idx}_expanded"] = True
                save_building(st.session_state.building)
                st.success(f"Wand '{wall_orientation}' hinzugefügt!")
                st.rerun()


def render_wall_openings(room: Room, room_idx: int, wall: Wall, wall_idx: int) -> None:
    """Zeigt Fenster und Türen einer Wand."""
    # Header und Button in derselben Zeile
    form_state_key = f"show_opening_form_{room_idx}_{wall_idx}"
    show_form = st.session_state.get(form_state_key, False)

    header_cols = st.columns([20, 1])
    with header_cols[0]:
        st.write("**Fenster & Türen**")
    with header_cols[1]:
        if st.button("➕" if not show_form else "✖️",
                     key=f"toggle_opening_form_{room_idx}_{wall_idx}",
                     type="secondary",
                     use_container_width=True):
            st.session_state[form_state_key] = not show_form
            st.rerun()

    # Fenster anzeigen
    if wall.windows:
        st.write("*Fenster:*")
        for win_idx, window in enumerate(wall.windows):
            cols = st.columns([3, 3, 1])
            with cols[0]:
                st.write(f"• {window.name}")
            with cols[1]:
                win_construction = st.session_state.building.get_construction_by_name(window.construction_name)
                u_value_str = f"{win_construction.u_value_w_m2k:.2f}" if win_construction else "N/A"
                st.write(f"{window.width_m:.2f} × {window.height_m:.2f} m = {window.area_m2:.2f} m² | U: {u_value_str} W/m²K")
            with cols[2]:
                if st.button("🗑️", key=f"del_win_{room_idx}_{wall_idx}_{win_idx}"):
                    wall.windows.pop(win_idx)
                    st.session_state[f"room_{room_idx}_expanded"] = True
                    save_building(st.session_state.building)
                    st.rerun()

    # Türen anzeigen
    if wall.doors:
        st.write("*Türen:*")
        for door_idx, door in enumerate(wall.doors):
            cols = st.columns([3, 3, 1])
            with cols[0]:
                st.write(f"• {door.name}")
            with cols[1]:
                door_construction = st.session_state.building.get_construction_by_name(door.construction_name)
                u_value_str = f"{door_construction.u_value_w_m2k:.2f}" if door_construction else "N/A"
                st.write(f"{door.width_m:.2f} × {door.height_m:.2f} m = {door.area_m2:.2f} m² | U: {u_value_str} W/m²K")
            with cols[2]:
                if st.button("🗑️", key=f"del_door_{room_idx}_{wall_idx}_{door_idx}"):
                    wall.doors.pop(door_idx)
                    st.session_state[f"room_{room_idx}_expanded"] = True
                    save_building(st.session_state.building)
                    st.rerun()

    # Info-Text wenn noch keine Öffnungen vorhanden
    if not wall.windows and not wall.doors:
        st.info("Keine Fenster oder Türen vorhanden.")

    # Hinzufügen-Formular nur anzeigen wenn aktiviert
    if show_form:
        with st.form(key=f"add_opening_form_{room_idx}_{wall_idx}"):
            cols = st.columns([1, 2, 1.5, 1.5, 2])

            with cols[0]:
                opening_type = cast(ElementType, st.selectbox(
                    "Typ",
                    options=["window", "door"],
                    format_func=lambda x: "Fenster" if x == "window" else "Tür",
                    key=f"opening_type_{room_idx}_{wall_idx}"
                ))

            with cols[1]:
                opening_name = st.text_input(
                    "Name",
                    value="",
                    placeholder=f"z.B. {'Fenster' if opening_type == 'window' else 'Tür'} 1",
                    key=f"opening_name_{room_idx}_{wall_idx}"
                )

            with cols[2]:
                opening_width = st.number_input(
                    "Breite (m)",
                    min_value=0.1,
                    value=1.2 if opening_type == "window" else 0.87,
                    step=0.1,
                    key=f"opening_width_{room_idx}_{wall_idx}"
                )

            with cols[3]:
                opening_height = st.number_input(
                    "Höhe (m)",
                    min_value=0.1,
                    value=1.5 if opening_type == "window" else 2.1,
                    step=0.1,
                    key=f"opening_height_{room_idx}_{wall_idx}"
                )

            with cols[4]:
                # Konstruktionen aus Katalog - zeige beide Typen mit Label
                window_options = get_catalog_by_type(ConstructionType.WINDOW)
                door_options = get_catalog_by_type(ConstructionType.DOOR)

                # Erstelle eine kombinierte Liste mit Typ-Präfix
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

                if not combined_options:
                    st.error("Keine Fenster- oder Tür-Konstruktionen im Katalog!")
                    selected_opening_constr = None
                else:
                    selected_opening_display = st.selectbox(
                        "Konstruktion",
                        options=combined_options,
                        key=f"opening_constr_{room_idx}_{wall_idx}"
                    )
                    selected_opening_constr = selected_opening_display

            # Button rechts ausrichten
            button_cols = st.columns([6, 1])
            with button_cols[1]:
                add_opening = st.form_submit_button("➕ Hinzufügen", type="primary", use_container_width=True, disabled=not combined_options)

            if add_opening:
                if not opening_name or opening_name.strip() == "":
                    st.error("Bitte geben Sie einen Namen ein.")
                    return

                if not selected_opening_constr:
                    st.error("Bitte wählen Sie eine Konstruktion aus.")
                    return

                # Hole die tatsächliche Konstruktion
                construction = opening_by_display_name[selected_opening_constr]

                # Validiere, dass Typ und Konstruktion zusammenpassen
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

                # Formular ausblenden und State zurücksetzen
                st.session_state[form_state_key] = False
                st.session_state[f"room_{room_idx}_expanded"] = True
                save_building(st.session_state.building)
                st.success(f"{'Fenster' if opening_type == 'window' else 'Tür'} '{opening_name}' hinzugefügt!")
                st.rerun()


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
