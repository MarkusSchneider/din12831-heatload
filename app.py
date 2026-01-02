import streamlit as st
from typing import cast
import json
from pathlib import Path
from src.din12831.models import Building, Room, Element, Construction, Ventilation, ElementType, Area, ConstructionType, Wall

st.set_page_config(page_title="DIN EN 12831 Heizlast", layout="wide")

DATA_FILE = Path("building_data.json")


# ============================================================================
# Datei-Operationen
# ============================================================================

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


def _get_catalog_by_type(construction_type: ConstructionType) -> list[Construction]:
    return [
        c
        for c in st.session_state.building.construction_catalog
        if c.element_type == construction_type
    ]


def _set_room_floor_ceiling(
    room: Room,
    floor_construction: Construction,
    ceiling_construction: Construction,
) -> None:
    """Setzt Boden und Decke eines Raums."""
    area = room.floor_area_m2
    room.floor = Element(
        type="floor",
        name="Boden",
        area_m2=area,
        construction=floor_construction,
    )
    room.ceiling = Element(
        type="ceiling",
        name="Decke",
        area_m2=area,
        construction=ceiling_construction,
    )


def _sync_fixed_surface_areas(room: Room) -> None:
    """Synchronisiert Boden/Decken-Flächen mit Raumfläche."""
    area = room.floor_area_m2
    if room.floor:
        room.floor.area_m2 = area
    if room.ceiling:
        room.ceiling.area_m2 = area


def render_room_floor_ceiling_assignment(room: Room, room_idx: int) -> None:
    floor_options = _get_catalog_by_type(ConstructionType.FLOOR)
    ceiling_options = _get_catalog_by_type(ConstructionType.CEILING)

    if not floor_options or not ceiling_options:
        st.error(
            "Ein Raum muss eine Boden- und eine Decken-Konstruktion aus dem Bauteilkatalog zugewiesen bekommen. "
            "Bitte im Katalog mindestens eine 'Boden'- und eine 'Decke'-Konstruktion anlegen."
        )
        return

    floor_by_name = {c.name: c for c in floor_options}
    ceiling_by_name = {c.name: c for c in ceiling_options}

    current_floor = room.floor.construction.name if room.floor else None
    current_ceiling = room.ceiling.construction.name if room.ceiling else None

    floor_names = list(floor_by_name.keys())
    ceiling_names = list(ceiling_by_name.keys())

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        selected_floor = st.selectbox(
            "Boden (aus Katalog)",
            options=floor_names,
            index=(floor_names.index(current_floor) if current_floor in floor_by_name else 0),
            key=f"room_{room_idx}_floor_construction",
        )
    with col2:
        selected_ceiling = st.selectbox(
            "Decke (aus Katalog)",
            options=ceiling_names,
            index=(ceiling_names.index(current_ceiling) if current_ceiling in ceiling_by_name else 0),
            key=f"room_{room_idx}_ceiling_construction",
        )
    with col3:
        if st.button("💾", key=f"room_{room_idx}_save_floor_ceiling"):
            st.session_state[f"room_{room_idx}_expanded"] = True
            _set_room_floor_ceiling(
                room,
                floor_construction=floor_by_name[selected_floor],
                ceiling_construction=ceiling_by_name[selected_ceiling],
            )
            save_building(st.session_state.building)
            st.success("Boden/Decke zugewiesen.")
            st.rerun()


# ============================================================================
# UI-Komponenten: Bauteilkatalog
# ============================================================================

def render_catalog_add_form() -> None:
    """Zeigt Formular zum Hinzufügen einer neuen Konstruktion."""
    is_empty = len(st.session_state.building.construction_catalog) == 0

    with st.expander("➕ Neue Konstruktion hinzufügen", expanded=is_empty):
        from src.din12831.models import ConstructionType

        # Reset flag prüfen und Session State leeren
        if st.session_state.get("reset_catalog_form", False):
            for key in ["catalog_element_type", "catalog_name", "catalog_u", "catalog_thickness", "catalog_is_external"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["reset_catalog_form"] = False

        # Alle Eingaben in einer Zeile
        cols = st.columns([1, 2, 1, 1, 1])

        with cols[0]:
            element_type = st.selectbox(
                "Bauteiltyp",
                options=list(ConstructionType),
                format_func=lambda x: {
                    ConstructionType.WALL: "Wand",
                    ConstructionType.CEILING: "Decke",
                    ConstructionType.FLOOR: "Boden",
                    ConstructionType.WINDOW: "Fenster",
                    ConstructionType.DOOR: "Tür",
                }[x],
                key="catalog_element_type",
            )

        with cols[1]:
            catalog_name = st.text_input("Bezeichnung", placeholder="z.B. Außenwand gedämmt", key="catalog_name")

        with cols[2]:
            catalog_u = st.number_input("U-Wert (W/m²K)", min_value=0.01, value=0.24, step=0.01, key="catalog_u")

        # Dicke nur für Wand, Decke, Boden anzeigen
        has_thickness = element_type in [ConstructionType.WALL, ConstructionType.CEILING, ConstructionType.FLOOR]
        catalog_thickness = None
        if has_thickness:
            with cols[3]:
                catalog_thickness = st.number_input("Dicke (m)", min_value=0.01, value=0.30, step=0.01, key="catalog_thickness")

        # Wandtyp nur für Wand anzeigen
        is_wall = element_type == ConstructionType.WALL
        is_external = None
        if is_wall:
            with cols[4]:
                is_external = st.selectbox(
                    "Wandtyp",
                    options=[True, False],
                    format_func=lambda x: "Außenwand" if x else "Innenwand",
                    index=0,
                    key="catalog_is_external",
                )

        if st.button("Konstruktion hinzufügen", type="primary", key="add_catalog"):
            if not catalog_name:
                st.error("Bitte geben Sie eine Bezeichnung ein.")
                return

            new_construction = Construction(
                name=catalog_name,
                element_type=element_type,
                u_value_w_m2k=catalog_u,
                thickness_m=catalog_thickness,
                is_external=is_external,
            )
            st.session_state.building.construction_catalog.append(new_construction)
            save_building(st.session_state.building)

            st.success(f"Konstruktion '{catalog_name}' wurde hinzugefügt!")
            st.rerun()


def render_catalog_list() -> None:
    """Zeigt Liste aller Konstruktionen im Katalog."""
    catalog = st.session_state.building.construction_catalog

    if not catalog:
        st.info(
            "👆 Fügen Sie Konstruktionen zu Ihrem Katalog hinzu, um sie bei der Raumplanung wiederzuverwenden.")
        return

    st.subheader(f"Vorhandene Konstruktionen ({len(catalog)})")

    from src.din12831.models import ConstructionType
    type_labels = {
        ConstructionType.WALL: "Wand",
        ConstructionType.CEILING: "Decke",
        ConstructionType.FLOOR: "Boden",
        ConstructionType.WINDOW: "Fenster",
        ConstructionType.DOOR: "Tür"
    }

    for idx, construction in enumerate(catalog):
        cols = st.columns([2, 1, 2, 2, 2, 1])

        with cols[0]:
            st.write(f"**{construction.name}**")
        with cols[1]:
            st.write(f"{type_labels[construction.element_type]}")
        with cols[2]:
            st.write(f"U: {construction.u_value_w_m2k:.3f} W/m²K")
        with cols[3]:
            thickness_text = f"{construction.thickness_m:.3f} m" if construction.thickness_m else "—"
            st.write(f"Dicke: {thickness_text}")
        with cols[4]:
            if construction.is_external is not None:
                wall_type = "Außenwand" if construction.is_external else "Innenwand"
                st.write(wall_type)
            else:
                st.write("—")
        with cols[5]:
            if st.button("🗑️", key=f"delete_catalog_{idx}"):
                catalog.pop(idx)
                save_building(st.session_state.building)
                st.rerun()


def render_catalog_tab() -> None:
    """Rendert den kompletten Bauteilkatalog-Tab."""
    st.header("Bauteilkatalog")
    st.caption(
        "Verwalten Sie wiederverwendbare Konstruktionen für Wände, Fenster, Türen, etc.")

    render_catalog_add_form()
    st.divider()
    render_catalog_list()


# ============================================================================
# UI-Komponenten: Räume
# ============================================================================

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
            st.write("**Flächen (Rechtecke)**")
            rectangles_payload: list[Area] = []

            rect_ids: list[int] = st.session_state[rect_ids_key]
            for _, rect_id in enumerate(list(rect_ids)):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    r_len = st.number_input(
                        f"Länge (m)",
                        min_value=0.1,
                        value=4.0,
                        step=0.1,
                        key=f"new_room_rect_{rect_id}_len",
                    )
                with c2:
                    r_wid = st.number_input(
                        f"Breite (m)",
                        min_value=0.1,
                        value=3.0,
                        step=0.1,
                        key=f"new_room_rect_{rect_id}_wid",
                    )
                with c3:
                    if len(rect_ids) > 1 and st.button("🗑️", key=f"new_room_rect_{rect_id}_del"):
                        rect_ids.remove(rect_id)
                        st.session_state[rect_ids_key] = rect_ids
                        st.rerun()

                rectangles_payload.append(Area(length_m=float(r_len), width_m=float(r_wid)))

            if st.button("➕ Fläche hinzufügen", key="new_room_add_rect"):
                next_id = (max(rect_ids) + 1) if rect_ids else 1
                rect_ids.append(next_id)
                st.session_state[rect_ids_key] = rect_ids
                st.rerun()

        with col2:
            new_height = st.number_input(
                "Höhe (m)", min_value=0.1, value=2.5, step=0.1, key="new_height")
            new_temp = st.number_input(
                "Raumtemperatur (°C)", min_value=15.0, max_value=25.0, value=20.0, step=0.5, key="new_temp")
            new_air_change = st.number_input(
                "Luftwechsel (1/h)", min_value=0.0, value=0.5, step=0.1, key="new_air_change")

            floor_options = _get_catalog_by_type(ConstructionType.FLOOR)
            ceiling_options = _get_catalog_by_type(ConstructionType.CEILING)

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
            st.error("Bitte mindestens ein Rechteck angeben.")
            return

        floor_options = _get_catalog_by_type(ConstructionType.FLOOR)
        ceiling_options = _get_catalog_by_type(ConstructionType.CEILING)
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
        area = new_room.floor_area_m2
        new_room.floor = Element(
            type="floor",
            name="Boden",
            area_m2=area,
            construction=floor_by_name[floor_selected],
        )
        new_room.ceiling = Element(
            type="ceiling",
            name="Decke",
            area_m2=area,
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


def render_room_rectangles_editor(room: Room, room_idx: int) -> None:
    if room.areas is None:
        room.areas = []

    expander_state_key = f"room_{room_idx}_expanded"

    rect_ids_key = f"room_{room_idx}_rect_ids"
    if rect_ids_key not in st.session_state or len(st.session_state[rect_ids_key]) != len(room.areas):
        st.session_state[rect_ids_key] = list(range(1, len(room.areas) + 1)) or [1]
        if not room.areas:
            room.areas = [Area(length_m=4.0, width_m=3.0)]

    rect_ids: list[int] = st.session_state[rect_ids_key]

    st.write("**Flächen (Rechtecke)**")
    for idx, rect_id in enumerate(list(rect_ids)):
        rect = room.areas[idx]
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            st.number_input(
                f"Länge (m)",
                min_value=0.1,
                value=float(rect.length_m),
                step=0.1,
                key=f"room_{room_idx}_rect_{rect_id}_len",
            )
        with c2:
            st.number_input(
                f"Breite (m)",
                min_value=0.1,
                value=float(rect.width_m),
                step=0.1,
                key=f"room_{room_idx}_rect_{rect_id}_wid",
            )
        with c3:
            if len(rect_ids) > 1 and st.button("🗑️", key=f"room_{room_idx}_rect_{rect_id}_del"):
                room.areas.pop(idx)
                rect_ids.remove(rect_id)
                st.session_state[rect_ids_key] = rect_ids
                st.session_state[expander_state_key] = True
                _sync_fixed_surface_areas(room)
                save_building(st.session_state.building)
                st.rerun()

    c_add, _ = st.columns([1, 1])
    with c_add:
        if st.button("➕ Fläche hinzufügen", key=f"room_{room_idx}_add_rect"):
            room.areas.append(Area(length_m=1.0, width_m=1.0))
            next_id = (max(rect_ids) + 1) if rect_ids else 1
            rect_ids.append(next_id)
            st.session_state[rect_ids_key] = rect_ids
            st.session_state[expander_state_key] = True
            _sync_fixed_surface_areas(room)
            save_building(st.session_state.building)
            st.rerun()


def render_wall_add_form(room: Room, room_idx: int) -> None:
    """Zeigt Formular zum Hinzufügen einer neuen Wand."""
    wall_options = _get_catalog_by_type(ConstructionType.WALL)

    if not wall_options:
        st.warning("Im Bauteilkatalog fehlen Wand-Konstruktionen. Bitte zuerst im Katalog anlegen.")
        return

    with st.form(key=f"add_wall_form_{room_idx}"):
        st.write("**Neue Wand hinzufügen**")
        cols = st.columns([2, 2, 2, 1])

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

        with cols[3]:
            st.write("")  # Spacer
            st.write("")  # Spacer
            add_wall = st.form_submit_button(
                "➕ Wand hinzufügen", type="primary")

        if not add_wall:
            return

        wall = Wall(
            orientation=wall_orientation,
            length_m=wall_length,
            construction=wall_by_name[selected_wall_constr],
        )

        room.walls.append(wall)
        st.session_state[f"room_{room_idx}_expanded"] = True
        save_building(st.session_state.building)
        st.success(f"Wand '{wall_orientation}' hinzugefügt!")
        st.rerun()


def render_wall_list(room: Room, room_idx: int) -> None:
    """Zeigt Liste aller Wände eines Raums."""
    if not room.walls:
        st.info("Noch keine Wände vorhanden. Fügen Sie die erste Wand hinzu.")
        return

    st.write("**Vorhandene Wände:**")
    for wall_idx, wall in enumerate(room.walls):
        wall_area = wall.length_m * room.height_m
        with st.expander(f"🧱 {wall.orientation} ({wall.length_m:.2f} m × {room.height_m:.2f} m = {wall_area:.2f} m²)", expanded=False):
            cols = st.columns([2, 2, 2, 1])

            with cols[0]:
                st.write(f"**Konstruktion:** {wall.construction.name}")
            with cols[1]:
                st.write(f"**U-Wert:** {wall.construction.u_value_w_m2k:.2f} W/m²K")
            with cols[2]:
                openings_area = sum(w.area_m2 for w in wall.windows) + sum(d.area_m2 for d in wall.doors)
                net_area = max(0.0, wall_area - openings_area)
                st.write(f"**Nettofläche:** {net_area:.2f} m²")
            with cols[3]:
                if st.button("🗑️", key=f"delete_wall_{room_idx}_{wall_idx}"):
                    room.walls.pop(wall_idx)
                    st.session_state[f"room_{room_idx}_expanded"] = True
                    save_building(st.session_state.building)
                    st.rerun()

            # Fenster/Türen-Sektion
            st.divider()
            render_wall_openings(room, room_idx, wall, wall_idx)


def render_wall_openings(room: Room, room_idx: int, wall: Wall, wall_idx: int) -> None:
    """Zeigt Fenster und Türen einer Wand."""
    st.write("**Fenster & Türen**")

    # Fenster anzeigen
    if wall.windows:
        st.write("*Fenster:*")
        for win_idx, window in enumerate(wall.windows):
            cols = st.columns([3, 2, 2, 1])
            with cols[0]:
                st.write(f"• {window.name}")
            with cols[1]:
                st.write(f"{window.area_m2:.2f} m²")
            with cols[2]:
                st.write(f"U: {window.construction.u_value_w_m2k:.2f} W/m²K")
            with cols[3]:
                if st.button("🗑️", key=f"del_win_{room_idx}_{wall_idx}_{win_idx}"):
                    wall.windows.pop(win_idx)
                    st.session_state[f"room_{room_idx}_expanded"] = True
                    save_building(st.session_state.building)
                    st.rerun()

    # Türen anzeigen
    if wall.doors:
        st.write("*Türen:*")
        for door_idx, door in enumerate(wall.doors):
            cols = st.columns([3, 2, 2, 1])
            with cols[0]:
                st.write(f"• {door.name}")
            with cols[1]:
                st.write(f"{door.area_m2:.2f} m²")
            with cols[2]:
                st.write(f"U: {door.construction.u_value_w_m2k:.2f} W/m²K")
            with cols[3]:
                if st.button("🗑️", key=f"del_door_{room_idx}_{wall_idx}_{door_idx}"):
                    wall.doors.pop(door_idx)
                    st.session_state[f"room_{room_idx}_expanded"] = True
                    save_building(st.session_state.building)
                    st.rerun()

    # Hinzufügen-Formular
    with st.form(key=f"add_opening_form_{room_idx}_{wall_idx}"):
        cols = st.columns([1, 2, 2, 2, 1])

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
                value=f"{'Fenster' if opening_type == 'window' else 'Tür'} 1",
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
            opening_options = _get_catalog_by_type(opening_constr_type)

            if not opening_options:
                st.error(f"Keine {'Fenster' if opening_type == 'window' else 'Tür'}-Konstruktionen im Katalog!")
                add_opening = st.form_submit_button("➕ Hinzufügen", disabled=True)
            else:
                opening_by_name = {c.name: c for c in opening_options}
                selected_opening_constr = st.selectbox(
                    "Konstruktion",
                    options=list(opening_by_name.keys()),
                    key=f"opening_constr_{room_idx}_{wall_idx}"
                )

                with cols[4]:
                    st.write("")
                    st.write("")
                    add_opening = st.form_submit_button("➕")

                if add_opening:
                    element = Element(
                        type=opening_type,
                        name=opening_name,
                        area_m2=opening_area,
                        construction=opening_by_name[selected_opening_constr],
                    )

                    if opening_type == "window":
                        wall.windows.append(element)
                    else:
                        wall.doors.append(element)

                    st.session_state[f"room_{room_idx}_expanded"] = True
                    save_building(st.session_state.building)
                    st.success(f"{'Fenster' if opening_type == 'window' else 'Tür'} hinzugefügt!")
                    st.rerun()


def render_room_detail(room: Room, room_idx: int) -> None:
    """Zeigt Details und Bauteile eines Raums."""
    expander_state_key = f"room_{room_idx}_expanded"
    expanded = bool(st.session_state.get(expander_state_key, False))
    with st.expander(f"📐 {room.name} ({room.volume_m3:.2f} m³)", expanded=expanded):
        render_room_info(room, room_idx)
        render_room_floor_ceiling_assignment(room, room_idx)
        render_room_rectangles_editor(room, room_idx)
        st.subheader("Wände")
        render_wall_add_form(room, room_idx)
        render_wall_list(room, room_idx)


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


# ============================================================================
# UI-Komponenten: Sidebar
# ============================================================================

def render_sidebar() -> None:
    """Rendert die Sidebar mit Gebäude-Einstellungen und Speicher-Optionen."""
    with st.sidebar:
        st.header("Gebäude-Einstellungen")

        building_name = st.text_input(
            "Gebäudename", value=st.session_state.building.name)
        outside_temp = st.number_input(
            "Normaußentemperatur (°C)",
            value=st.session_state.building.outside_temperatur,
            min_value=-30.0,
            max_value=20.0,
            step=1.0
        )

        st.session_state.building.name = building_name
        st.session_state.building.outside_temperatur = outside_temp

        st.divider()
        st.subheader("Gebäudeübersicht")
        st.metric("Anzahl Räume", len(st.session_state.building.rooms))
        st.metric("Konstruktionen im Katalog", len(
            st.session_state.building.construction_catalog))


# ============================================================================
# Hauptanwendung
# ============================================================================

def initialize_session_state() -> None:
    """Initialisiert den Session State."""
    if 'building' not in st.session_state:
        st.session_state.building = load_building()


def main() -> None:
    """Hauptfunktion der Streamlit-App."""
    initialize_session_state()

    st.title("🏠 DIN EN 12831 Heizlastberechnung")
    st.caption("Gebäude mit Räumen und Bauteilen definieren")

    render_sidebar()

    tab1, tab2, tab3 = st.tabs(["🏗️ Bauteilkatalog", "📐 Räume", "🔍 Debug"])

    with tab1:
        render_catalog_tab()

    with tab2:
        render_rooms_tab()

    with tab3:
        st.header("Debug-Informationen")
        st.json(st.session_state.building.model_dump())


if __name__ == "__main__":
    main()
