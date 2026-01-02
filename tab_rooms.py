"""Tab für die Räume."""

import streamlit as st
from typing import cast
from src.din12831.models import Room, Element, Ventilation, Area, ConstructionType, Wall, ElementType
from utils import save_building, get_catalog_by_type


def render_room_floor_ceiling_assignment(room: Room) -> None:
    current_floor = room.floor.construction.name if room.floor else "Nicht zugewiesen"
    current_ceiling = room.ceiling.construction.name if room.ceiling else "Nicht zugewiesen"

    col1, col2, _ = st.columns([2, 2, 1])
    with col1:
        st.write(f"**Boden:** {current_floor}")
    with col2:
        st.write(f"**Decke:** {current_ceiling}")


def render_room_add_form() -> None:
    """Zeigt Formular zum Hinzufügen eines neuen Raums."""
    is_empty = len(st.session_state.building.rooms) == 0

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
            new_temp = st.number_input(
                "Raumtemperatur (°C)", min_value=15.0, max_value=25.0, value=20.0, step=0.5, key="new_temp")
            new_air_change = st.number_input(
                "Luftwechsel (1/h)", min_value=0.0, value=0.5, step=0.1, key="new_air_change")

            floor_options = get_catalog_by_type(ConstructionType.FLOOR)
            ceiling_options = get_catalog_by_type(ConstructionType.CEILING)

            if floor_options:
                st.selectbox(
                    "Boden (aus Katalog)",
                    options=[c.name for c in floor_options],
                    key="new_room_floor_construction",
                )
            else:
                st.error("Im Bauteilkatalog fehlt mindestens eine Boden-Konstruktion.")

            if ceiling_options:
                st.selectbox(
                    "Decke (aus Katalog)",
                    options=[c.name for c in ceiling_options],
                    key="new_room_ceiling_construction",
                )
            else:
                st.error("Im Bauteilkatalog fehlt mindestens eine Decken-Konstruktion.")

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
            height_m=new_height,
            room_temperature=new_temp,
            ventilation=Ventilation(air_change_1_h=new_air_change)
        )

        # Boden/Decke als direkte Felder (Fläche = Raumfläche)
        new_room.floor = Element(
            type="floor",
            name="Boden",
            construction=floor_by_name[floor_selected],
        )
        new_room.ceiling = Element(
            type="ceiling",
            name="Decke",
            construction=ceiling_by_name[ceiling_selected],
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


def render_room_info(room: Room, room_idx: int) -> None:
    """Zeigt Raum-Informationen und Löschen-Button."""
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        st.write(f"**Fläche:** {room.floor_area_m2:.2f} m²")
        st.write(f"**Volumen:** {room.volume_m3:.2f} m³")
    with col2:
        st.write(f"**Raumtemperatur:** {room.room_temperature}°C")
        st.write(f"**Luftwechsel:** {room.ventilation.air_change_1_h} 1/h")
    with col3:
        if st.button("🗑️ Löschen", key=f"delete_room_{room_idx}"):
            st.session_state.building.rooms.pop(room_idx)
            save_building(st.session_state.building)
            st.rerun()


def render_room_areas_editor(room: Room, room_idx: int) -> None:
    if room.areas is None:
        room.areas = []

    expander_state_key = f"room_{room_idx}_expanded"

    rect_ids_key = f"room_{room_idx}_rect_ids"
    if rect_ids_key not in st.session_state or len(st.session_state[rect_ids_key]) != len(room.areas):
        st.session_state[rect_ids_key] = list(range(1, len(room.areas) + 1)) or [1]
        if not room.areas:
            room.areas = [Area(length_m=4.0, width_m=3.0)]

    rect_ids: list[int] = st.session_state[rect_ids_key]

    st.subheader("Flächen")
    for idx, rect_id in enumerate(list(rect_ids)):
        rect = room.areas[idx]
        cols = st.columns([2, 2, 1])
        with cols[0]:
            st.write(f"**Länge:** {rect.length_m} m")
        with cols[1]:
            st.write(f"**Breite:** {rect.width_m} m")


def render_walls_section(room: Room, room_idx: int) -> None:
    """Zeigt Wände-Sektion mit Button zum Hinzufügen und Liste."""
    wall_options = get_catalog_by_type(ConstructionType.WALL)

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
            with st.expander(f"🧱 {wall.orientation} ({wall.length_m:.2f} m × {room.height_m:.2f} m)", expanded=False):
                cols = st.columns([2, 2, 1])

                with cols[0]:
                    st.write(f"**Konstruktion:** {wall.construction.name}")
                with cols[1]:
                    st.write(f"**U-Wert:** {wall.construction.u_value_w_m2k:.2f} W/m²K")
                with cols[2]:
                    if st.button("🗑️", key=f"delete_wall_{room_idx}_{wall_idx}"):
                        room.walls.pop(wall_idx)
                        st.session_state[f"room_{room_idx}_expanded"] = True
                        save_building(st.session_state.building)
                        st.rerun()

                # Nachbarwände (Bauteile aus Katalog) anzeigen
                if wall.left_wall or wall.right_wall:
                    st.write("**Angrenzende Wandbauteile:**")
                    neighbor_cols = st.columns([2, 2, 1])
                    with neighbor_cols[0]:
                        if wall.left_wall:
                            st.write(f"⬅️ **Links:** {wall.left_wall.name} (U: {wall.left_wall.u_value_w_m2k:.2f} W/m²K)")
                    with neighbor_cols[1]:
                        if wall.right_wall:
                            st.write(f"➡️ **Rechts:** {wall.right_wall.name} (U: {wall.right_wall.u_value_w_m2k:.2f} W/m²K)")

                # Fenster/Türen-Sektion
                st.divider()
                render_wall_openings(room, room_idx, wall, wall_idx)
    else:
        st.info("Noch keine Wände vorhanden.")

    # Formular nur anzeigen wenn aktiviert
    if show_form:
        with st.form(key=f"add_wall_form_{room_idx}"):
            cols = st.columns([2, 2, 2])

            with cols[0]:
                wall_orientation = st.text_input(
                    "Richtung / Bezeichnung",
                    value="",
                    key=f"wall_orientation_{room_idx}",
                    placeholder="z.B. Norden, Osten, Süden 1, Westen 2"
                )

            with cols[1]:
                wall_length = st.number_input(
                    "Länge (m)", min_value=0.1, value=4.0, step=0.1, key=f"wall_length_{room_idx}")

            with cols[2]:
                wall_by_name = {c.name: c for c in wall_options}
                selected_wall_constr = st.selectbox(
                    "Aufbau",
                    options=list(wall_by_name.keys()),
                    key=f"wall_constr_{room_idx}"
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
                add_wall = st.form_submit_button("➕ Hinzufügen", type="primary", use_container_width=True)

            if not add_wall:
                return

            # Validierung der Pflichtfelder
            if not wall_orientation or wall_orientation.strip() == "":
                st.error("Bitte geben Sie eine Richtung / Bezeichnung für die Wand ein.")
                return

            if wall_length <= 0:
                st.error("Bitte geben Sie eine gültige Wandlänge größer als 0 ein.")
                return

            if left_wall_name == "Keine":
                st.error("Bitte wählen Sie eine Nachbarwand Links aus dem Katalog.")
                return

            if right_wall_name == "Keine":
                st.error("Bitte wählen Sie eine Nachbarwand Rechts aus dem Katalog.")
                return

            wall = Wall(
                orientation=wall_orientation,
                length_m=wall_length,
                construction=wall_by_name[selected_wall_constr],
                left_wall=wall_by_name[left_wall_name],
                right_wall=wall_by_name[right_wall_name],
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
            cols = st.columns([3, 2, 1])
            with cols[0]:
                st.write(f"• {window.name}")
            with cols[1]:
                st.write(f"U: {window.construction.u_value_w_m2k:.2f} W/m²K")
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
            cols = st.columns([3, 2, 1])
            with cols[0]:
                st.write(f"• {door.name}")
            with cols[1]:
                st.write(f"U: {door.construction.u_value_w_m2k:.2f} W/m²K")
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
            cols = st.columns([1, 2, 2, 2])

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
                opening_area = st.number_input(
                    "Fläche (m²)",
                    min_value=0.1,
                    value=2.0 if opening_type == "window" else 2.5,
                    step=0.1,
                    key=f"opening_area_{room_idx}_{wall_idx}"
                )

            with cols[3]:
                # Konstruktionen aus Katalog
                opening_constr_type = ConstructionType.WINDOW if opening_type == "window" else ConstructionType.DOOR
                opening_options = get_catalog_by_type(opening_constr_type)

                if not opening_options:
                    st.error(f"Keine {'Fenster' if opening_type == 'window' else 'Tür'}-Konstruktionen im Katalog!")
                    opening_by_name = {}
                    selected_opening_constr = None
                else:
                    opening_by_name = {c.name: c for c in opening_options}
                    selected_opening_constr = st.selectbox(
                        "Konstruktion",
                        options=list(opening_by_name.keys()),
                        key=f"opening_constr_{room_idx}_{wall_idx}"
                    )

            # Button rechts ausrichten
            button_cols = st.columns([6, 1])
            with button_cols[1]:
                add_opening = st.form_submit_button("➕ Hinzufügen", type="primary", use_container_width=True, disabled=not opening_options)

            if add_opening:
                if not opening_name or opening_name.strip() == "":
                    st.error("Bitte geben Sie einen Namen ein.")
                    return

                if not selected_opening_constr:
                    st.error("Bitte wählen Sie eine Konstruktion aus.")
                    return

                element = Element(
                    type=opening_type,
                    name=opening_name,
                    construction=opening_by_name[selected_opening_constr],
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
        st.subheader("Raum")
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
