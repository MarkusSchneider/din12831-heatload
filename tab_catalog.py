"""Tab für den Bauteilkatalog."""

import streamlit as st
from src.din12831.models import Construction, ConstructionType
from utils import save_building


def render_catalog_add_form() -> None:
    """Zeigt Formular zum Hinzufügen einer neuen Konstruktion."""
    is_empty = len(st.session_state.building.construction_catalog) == 0

    with st.expander("➕ Neue Konstruktion hinzufügen", expanded=is_empty):
        # Reset flag prüfen und Session State leeren
        if st.session_state.get("reset_catalog_form", False):
            for key in ["catalog_element_type", "catalog_name", "catalog_u", "catalog_thickness"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["reset_catalog_form"] = False

        # Alle Eingaben in einer Zeile
        cols = st.columns([1, 2, 1, 1])

        with cols[0]:
            element_type = st.selectbox(
                "Bauteiltyp",
                options=list(ConstructionType),
                format_func=lambda x: {
                    ConstructionType.EXTERNAL_WALL: "Außenwand",
                    ConstructionType.INTERNAL_WALL: "Innenwand",
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
        has_thickness = element_type in [ConstructionType.EXTERNAL_WALL, ConstructionType.INTERNAL_WALL, ConstructionType.CEILING, ConstructionType.FLOOR]
        catalog_thickness = None
        if has_thickness:
            with cols[3]:
                catalog_thickness = st.number_input("Dicke (m)", min_value=0.00, value=0.30, step=0.01, key="catalog_thickness")

        if st.button("Konstruktion hinzufügen", type="primary", key="add_catalog"):
            if not catalog_name:
                st.error("Bitte geben Sie eine Bezeichnung ein.")
                return

            new_construction = Construction(
                name=catalog_name,
                element_type=element_type,
                u_value_w_m2k=catalog_u,
                thickness_m=catalog_thickness,
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

    type_labels = {
        ConstructionType.EXTERNAL_WALL: "Außenwand",
        ConstructionType.INTERNAL_WALL: "Innenwand",
        ConstructionType.CEILING: "Decke",
        ConstructionType.FLOOR: "Boden",
        ConstructionType.WINDOW: "Fenster",
        ConstructionType.DOOR: "Tür"
    }

    for idx, construction in enumerate(catalog):
        cols = st.columns([2, 1, 2, 2, 1])

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
