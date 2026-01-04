"""Tab für die Räume - Refaktorierte Version mit kleineren, fokussierten Funktionen."""

import streamlit as st
import pandas as pd
from typing import cast, Optional
from src.models import Room, Element, Ventilation, Area, ConstructionType, Wall, ElementType, Temperature
from src.din12831.calc_heat_load import calc_room_heat_load
from src.utils import save_building, get_catalog_by_type


# ============================================================================
# Helper Funktionen für Temperatur- und Katalog-Handling
# ============================================================================

def format_temperature(temp: Optional[Temperature]) -> str:
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

def render_adjacent_temperature_info(element: Optional[Element], label: str) -> str:
    """Zeigt Informationen zur angrenzenden Temperatur eines Bauteils."""
    if not element or not element.adjacent_temperature_name:
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
    col1, col2, _ = st.columns([2, 2, 1])

    with col1:
        render_floor_info(room)
    with col2:
        render_ceiling_info(room)


# ============================================================================
# Formularkomponenten für neuen Raum
# ============================================================================

def render_temperature_selector(key: str, label: str = "Raumtemperatur") -> Optional[str]:
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
        key=key
    )
    return selected_temp_name


def render_construction_selector(
    construction_type: ConstructionType,
    key: str,
    label: str
) -> Optional[str]:
    """Zeigt einen Konstruktions-Auswahldialog."""
    options = get_catalog_by_type(construction_type)

    if not options:
        type_name = "Boden" if construction_type == ConstructionType.FLOOR else "Decke"
        st.error(f"Im Bauteilkatalog fehlt mindestens eine {type_name}-Konstruktion.")
        return None

    return st.selectbox(
        label,
        options=[c.name for c in options],
        key=key,
        help=f"Aufbau des {label}"
    )


def render_floor_ceiling_selectors() -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Zeigt Auswahldialoge für Boden und Decke."""
    # Boden-Sektion
    st.write("**Boden:**")
    col_floor_1, col_floor_2 = st.columns(2)

    with col_floor_1:
        floor_construction = render_construction_selector(
            ConstructionType.FLOOR,
            "new_room_floor_construction",
            "Konstruktion"
        )

    with col_floor_2:
        floor_temp = render_temperature_selector(
            "new_floor_adjacent_temp",
            "Angrenzende Temperatur"
        )

    # Decken-Sektion
    st.write("**Decke:**")
    col_ceiling_1, col_ceiling_2 = st.columns(2)

    with col_ceiling_1:
        ceiling_construction = render_construction_selector(
            ConstructionType.CEILING,
            "new_room_ceiling_construction",
            "Konstruktion"
        )

    with col_ceiling_2:
        ceiling_temp = render_temperature_selector(
            "new_ceiling_adjacent_temp",
            "Angrenzende Temperatur"
        )

    return floor_construction, floor_temp, ceiling_construction, ceiling_temp


def render_rectangle_editor(rect_id: int, rect_ids: list[int]) -> Area:
    """Zeigt Editor für ein einzelnes Rechteck."""
    wall_catalog = get_wall_catalog()
    wall_catalog_names = ["Keine"] + [c.name for c in wall_catalog]

    # Zeile 1: Oben (Bauteil)
    row1 = st.columns([1, 3, 1])
    with row1[1]:
        top_row = st.columns([1, 1])
        with top_row[0]:
            r_len = st.number_input(
                "Länge (m)",
                min_value=0.0,
                value=0.0,
                step=0.1,
                key=f"new_room_rect_{rect_id}_len",
            )
        with top_row[1]:
            top_wall = st.selectbox(
                "Konstruktion Oben",
                options=wall_catalog_names,
                key=f"new_room_rect_{rect_id}_top",
                help="Aufbau Wand oben vom Rechteck"
            )
    with row1[2]:
        if len(rect_ids) > 1 and st.button("🗑️", key=f"new_room_rect_{rect_id}_del"):
            rect_ids.remove(rect_id)
            st.session_state[f"new_room_rect_ids"] = rect_ids
            st.rerun()

    # Zeile 2: Links - Rechteck-Darstellung - Rechts
    row2 = st.columns([2, 1, 2])
    with row2[0]:
        r_wid = st.number_input(
            "Breite (m)",
            min_value=0.0,
            value=0.0,
            step=0.1,
            key=f"new_room_rect_{rect_id}_wid",
        )
        left_wall = st.selectbox(
            "Konstruktion Links",
            options=wall_catalog_names,
            key=f"new_room_rect_{rect_id}_left",
            help="Aufbau Wand links vom Rechteck"
        )
    with row2[1]:
        st.markdown(
            """
            <div style='text-align: center; padding: 20px; border: 2px solid #ccc; border-radius: 8px; background-color: #f0f2f6; margin-top: 24px;'>
                <p style='margin: 0; font-size: 24px;'>📐</p>
                <p style='margin: 0; font-size: 12px; color: #666;'>Rechteck</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with row2[2]:
        right_wall = st.selectbox(
            "Konstruktion Rechts",
            options=wall_catalog_names,
            key=f"new_room_rect_{rect_id}_right",
            help="Aufbau Wand rechts vom Rechteck"
        )

    # Zeile 3: Unten (Bauteil, zentriert)
    row3 = st.columns([2, 3, 2])
    with row3[1]:
        bottom_wall = st.selectbox(
            "Konstruktion Unten",
            options=wall_catalog_names,
            key=f"new_room_rect_{rect_id}_bottom",
            help="Aufbau Wand unten vom Rechteck"
        )

    st.divider()

    return Area(
        length_m=float(r_len),
        width_m=float(r_wid),
        left_adjacent_name=None if left_wall == "Keine" else left_wall,
        top_adjacent_name=None if top_wall == "Keine" else top_wall,
        right_adjacent_name=None if right_wall == "Keine" else right_wall,
        bottom_adjacent_name=None if bottom_wall == "Keine" else bottom_wall,
    )


def render_rectangles_section() -> list[Area]:
    """Zeigt die Sektion zum Bearbeiten von Rechtecken."""
    rect_ids_key = "new_room_rect_ids"
    if rect_ids_key not in st.session_state:
        st.session_state[rect_ids_key] = [1]

    st.write("**Flächen**")
    rectangles_payload: list[Area] = []
    rect_ids: list[int] = st.session_state[rect_ids_key]

    for idx, rect_id in enumerate(list(rect_ids), 1):
        area = render_rectangle_editor(rect_id, rect_ids)
        rectangles_payload.append(area)

    if st.button("➕ Weitere Fläche hinzufügen", key="add_new_room_rect"):
        max_id = max(rect_ids) if rect_ids else 0
        rect_ids.append(max_id + 1)
        st.session_state[rect_ids_key] = rect_ids
        st.rerun()

    return rectangles_payload


def validate_new_room_inputs(
    room_name: str,
    rectangles: list[Area],
    temp_name: Optional[str],
    floor_constr: Optional[str],
    ceiling_constr: Optional[str]
) -> Optional[str]:
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
    ceiling_temp: str
) -> Room:
    """Erstellt ein neues Room-Objekt."""
    new_room = Room(
        name=name,
        areas=rectangles,
        net_height_m=height,
        room_temperature_name=temp_name,
        ventilation=Ventilation(air_change_1_h=air_change)
    )

    new_room.floor = Element(
        type="floor",
        name="Boden",
        construction_name=floor_constr,
        adjacent_temperature_name=floor_temp,
    )

    new_room.ceiling = Element(
        type="ceiling",
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
            rectangles_payload = render_rectangles_section()

        with col2:
            new_height = st.number_input(
                "Höhe (m)", min_value=0.1, value=2.5, step=0.1, key="new_height")

            selected_temp_name = render_temperature_selector("new_temp")

            new_air_change = st.number_input(
                "Luftwechsel (1/h)",
                min_value=0.0,
                value=0.5,
                step=0.1,
                key="new_air_change",
                help="Anzahl der Luftwechsel pro Stunde. Die Norm empfiehlt mindestens 0.5 1/h für Wohnräume."
            )

            floor_constr, floor_temp, ceiling_constr, ceiling_temp = render_floor_ceiling_selectors()

        if not st.button("Raum hinzufügen", type="primary"):
            return

        # Validierung
        error = validate_new_room_inputs(
            new_room_name,
            rectangles_payload,
            selected_temp_name,
            floor_constr,
            ceiling_constr
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
            ceiling_temp
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
            help="Wärmeverlust durch Bauteile (Wände, Decke, Boden, Fenster, Türen)"
        )
    with heat_col2:
        st.metric(
            "Lüftungswärmeverlust",
            f"{result.ventilation_w:.0f} W",
            help="Wärmeverlust durch Luftwechsel"
        )
    with heat_col3:
        st.metric(
            "Gesamt-Heizlast",
            f"{result.total_w:.0f} W",
            help="Summe aus Transmissions- und Lüftungswärmeverlust"
        )


def render_element_transmission_details(result) -> None:
    """Zeigt Details zu den Transmissionswärmeverlusten der einzelnen Bauteile."""
    if not result.element_transmissions:
        return

    with st.expander("📋 Details nach Bauteilen", expanded=False):
        st.write("**Transmissionswärmeverluste der einzelnen Bauteile:**")

        element_data = []
        for element in result.element_transmissions:
            element_data.append({
                "Bauteil": element.element_name,
                "Fläche [m²]": f"{element.area_m2:.2f}",
                "U-Wert [W/(m²·K)]": f"{element.u_value_w_m2k:.2f}",
                "U-Wert korr. [W/(m²·K)]": f"{element.u_value_corrected_w_m2k:.2f}",
                "ΔT [K]": f"{element.delta_temp_k:.1f}",
                "Wärmeverlust [W]": f"{element.transmission_w:.0f}"
            })

        element_df = pd.DataFrame(element_data)
        st.dataframe(
            element_df,
            width='stretch',
            hide_index=True,
            column_config={
                "U-Wert korr. [W/(m²·K)]": st.column_config.TextColumn(
                    "U-Wert korr. [W/(m²·K)]",
                    help="U-Wert mit Wärmebrückenzuschlag"
                )
            }
        )


def render_room_heat_loads(room: Room, room_idx: int) -> None:
    """Berechnet und zeigt die Heizlasten eines Raums."""
    try:
        result = calc_room_heat_load(
            room,
            st.session_state.building.outside_temperature.value_celsius,
            st.session_state.building
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

def render_room_info(room: Room, room_idx: int) -> None:
    """Zeigt Raum-Informationen und Löschen-Button."""
    st.subheader("Raum")
    col1, col2, col3 = st.columns([2, 2, 1])

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

    with col3:
        if st.button("🗑️ Löschen", key=f"delete_room_{room_idx}"):
            st.session_state.building.rooms.pop(room_idx)
            save_building(st.session_state.building)
            st.rerun()


# ============================================================================
# Flächen-Editor
# ============================================================================

def render_area_info(area: Area, area_idx: int, total_areas: int) -> None:
    """Zeigt Informationen zu einer Fläche."""
    net_area = area.area_m2
    gross_area = area.gross_area_m2(st.session_state.building)

    title = f"Fläche {area_idx + 1}" if total_areas > 1 else "Fläche"
    expander_title = f"📐 {title}: {area.length_m:.2f} m × {area.width_m:.2f} m = {net_area:.2f} m² (Netto) / {gross_area:.2f} m² (Brutto)"

    with st.expander(expander_title, expanded=False):
        cols = st.columns([2, 2])
        with cols[0]:
            st.write(f"**Länge:** {area.length_m:.2f} m")
            st.write(f"**Breite:** {area.width_m:.2f} m")
        with cols[1]:
            st.write(f"**Nettofläche:** {net_area:.2f} m²")
            st.write(f"**Bruttofläche:** {gross_area:.2f} m²")

        # Angrenzende Bauteile
        st.write("**Angrenzende Bauteile:**")
        adjacent_info = []
        if area.left_adjacent_name:
            adjacent_info.append(f"⬅️ Links: {area.left_adjacent_name}")
        if area.top_adjacent_name:
            adjacent_info.append(f"⬆️ Oben: {area.top_adjacent_name}")
        if area.right_adjacent_name:
            adjacent_info.append(f"➡️ Rechts: {area.right_adjacent_name}")
        if area.bottom_adjacent_name:
            adjacent_info.append(f"⬇️ Unten: {area.bottom_adjacent_name}")

        if adjacent_info:
            for info in adjacent_info:
                st.write(f"  {info}")
        else:
            st.info("Keine angrenzenden Bauteile definiert")


def render_room_areas_editor(room: Room, room_idx: int) -> None:
    """Zeigt den Flächen-Editor für einen Raum."""
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
        render_area_info(room.areas[idx], idx, len(room.areas))


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
        if st.button("➕" if not show_form else "✖️",
                     key=f"toggle_wall_form_{room_idx}",
                     type="secondary"):
            st.session_state[form_state_key] = not show_form
            st.rerun()

    return show_form


def render_wall_item(room: Room, room_idx: int, wall: Wall, wall_idx: int) -> None:
    """Zeigt eine einzelne Wand mit Details."""
    with st.expander(f"🧱 {wall.orientation} ({wall.net_length_m:.2f} m × {room.net_height_m:.2f} m)", expanded=False):
        cols = st.columns([2, 2, 1])

        with cols[0]:
            wall_construction = st.session_state.building.get_construction_by_name(wall.construction_name)
            st.write(f"**Konstruktion:** {wall.construction_name}")

            # Zeige Temperatur bei Innenwänden
            if wall_construction and wall_construction.element_type == ConstructionType.INTERNAL_WALL:
                if wall.adjacent_room_temperature_name:
                    adj_temp = st.session_state.building.get_temperature_by_name(wall.adjacent_room_temperature_name)
                    if adj_temp:
                        st.write(f"**Angrenzender Raum:** {format_temperature(adj_temp)}")

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

        # Nachbarwände
        render_neighbor_walls(wall)

        # Fenster/Türen
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
                wall_thickness = left_wall.thickness_m or 0.0
                if left_wall.element_type == ConstructionType.INTERNAL_WALL:
                    wall_thickness = wall_thickness / 2
                st.write(f"⬅️ **Links:** {left_wall.name} (Dicke: {wall_thickness} m)")

    with neighbor_cols[1]:
        if wall.right_wall_name:
            right_wall = st.session_state.building.get_construction_by_name(wall.right_wall_name)
            if right_wall:
                wall_thickness = right_wall.thickness_m or 0.0
                if right_wall.element_type == ConstructionType.INTERNAL_WALL:
                    wall_thickness = wall_thickness / 2
                st.write(f"➡️ **Rechts:** {right_wall.name} (Dicke: {wall_thickness} m)")


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
        return st.number_input(
            "Länge (m)",
            min_value=0.1,
            value=4.0,
            step=0.1,
            key=f"wall_length_manual_{room_idx}"
        )

    # Zeige alle Dropdowns in einer Zeile
    num_cols = len(areas) + 1
    cols_dims = st.columns(num_cols)

    # Dropdowns für jedes Rechteck
    for rect_idx, area in enumerate(areas, 1):
        with cols_dims[rect_idx]:
            rect_name = f"Fläche {rect_idx}" if len(areas) > 1 else "Fläche"
            options = [
                "Nicht verwenden",
                f"Länge ({area.length_m:.2f} m)",
                f"Breite ({area.width_m:.2f} m)"
            ]

            st.selectbox(
                rect_name,
                options=options,
                key=f"wall_length_rect_{room_idx}_{rect_idx}",
                label_visibility="visible"
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
            help="Wählen Sie das Wandbauteil aus dem Katalog, das links angrenzt"
        )

    with cols2[1]:
        right_wall_name = st.selectbox(
            "Aufbau Nachbarwand Rechts",
            options=wall_catalog_names,
            key=f"wall_right_{room_idx}",
            help="Wählen Sie das Wandbauteil aus dem Katalog, das rechts angrenzt"
        )

    return left_wall_name, right_wall_name


def validate_wall_inputs(
    orientation: str,
    length: float,
    left_wall: str,
    right_wall: str,
    construction,
    adjacent_temp: Optional[str]
) -> Optional[str]:
    """Validiert Wand-Eingaben. Gibt Fehlermeldung zurück oder None."""
    if not orientation or orientation.strip() == "":
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
                placeholder="z.B. Norden, Osten, Süden 1, Westen 2"
            )

        with cols[1]:
            selected_wall_constr = st.selectbox(
                "Aufbau",
                options=list(wall_by_name.keys()),
                key=f"wall_constr_{room_idx}"
            )

        # Temperatur des angrenzenden Raums (nur bei Innenwand)
        adjacent_temp_name = None
        selected_construction = wall_by_name[selected_wall_constr]

        if selected_construction.element_type == ConstructionType.INTERNAL_WALL:
            with cols[2]:
                adjacent_temp_name = render_temperature_selector(
                    f"adjacent_temp_{room_idx}",
                    "Temperatur des angrenzenden Raums"
                )

        # Wandlänge
        wall_length = render_wall_length_selector(room, room_idx)

        # Nachbarwände
        left_wall_name, right_wall_name = render_wall_neighbor_selectors(room_idx, wall_options)

        # Button unten rechts
        button_cols = st.columns([6, 1])
        with button_cols[1]:
            add_wall = st.button("➕ Hinzufügen", type="primary", key=f"add_wall_btn_{room_idx}")

    # Validierung und Hinzufügen
    if add_wall:
        error = validate_wall_inputs(
            wall_orientation,
            wall_length,
            left_wall_name,
            right_wall_name,
            selected_construction,
            adjacent_temp_name
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
        if st.button("➕" if not show_form else "✖️",
                     key=f"toggle_opening_form_{room_idx}_{wall_idx}",
                     type="secondary"):
            st.session_state[form_state_key] = not show_form
            st.rerun()

    return show_form


def render_window_list(wall: Wall, room_idx: int, wall_idx: int) -> None:
    """Zeigt Liste der Fenster."""
    if not wall.windows:
        return

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


def render_door_list(wall: Wall, room_idx: int, wall_idx: int) -> None:
    """Zeigt Liste der Türen."""
    if not wall.doors:
        return

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
            combined_options, opening_by_display_name = get_opening_catalog_options()

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
            add_opening = st.form_submit_button(
                "➕ Hinzufügen",
                type="primary",
                disabled=not combined_options
            )

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
