"""Tests für calc_heat_load Modul."""

import pytest
from src.din12831.calc_heat_load import (
    ElementHeatLoad,
    RoomHeatLoadResult,
    calc_element_transmission,
    calc_floor_ceiling_heat_load,
    calc_walls_heat_load,
    calc_ventilation_heat_load,
    calc_room_heat_load,
    calc_building_heat_load,
)
from src.models import (
    Building,
    Room,
    Construction,
    ConstructionType,
    Temperature,
    Element,
    ElementType,
    Ventilation,
    Area,
    Wall,
)


@pytest.fixture
def sample_constructions():
    """Erstellt Beispielkonstruktionen für Tests."""
    return [
        Construction(
            name="Außenwand Standard",
            element_type=ConstructionType.EXTERNAL_WALL,
            u_value_w_m2k=0.24,
            thickness_m=0.36,
        ),
        Construction(
            name="Innenwand Standard",
            element_type=ConstructionType.INTERNAL_WALL,
            u_value_w_m2k=0.5,
            thickness_m=0.12,
        ),
        Construction(
            name="Fenster Dreifach",
            element_type=ConstructionType.WINDOW,
            u_value_w_m2k=0.8,
        ),
        Construction(
            name="Haustür",
            element_type=ConstructionType.DOOR,
            u_value_w_m2k=1.8,
        ),
        Construction(
            name="Bodenplatte",
            element_type=ConstructionType.FLOOR,
            u_value_w_m2k=0.3,
            thickness_m=0.25,
        ),
        Construction(
            name="Decke Standard",
            element_type=ConstructionType.CEILING,
            u_value_w_m2k=0.2,
            thickness_m=0.30,
        ),
    ]


@pytest.fixture
def sample_temperatures():
    """Erstellt Beispieltemperaturen für Tests."""
    return [
        Temperature(name="Außen", value_celsius=-12.0),
        Temperature(name="Wohnraum", value_celsius=20.0),
        Temperature(name="Keller", value_celsius=10.0),
        Temperature(name="Dachboden", value_celsius=5.0),
    ]


@pytest.fixture
def sample_building(sample_constructions, sample_temperatures):
    """Erstellt ein Beispielgebäude für Tests."""
    return Building(
        name="Testgebäude",
        construction_catalog=sample_constructions,
        temperature_catalog=sample_temperatures,
        outside_temperature_name="Außen",
        default_room_temperature_name="Wohnraum",
    )


@pytest.fixture
def simple_room(sample_building):
    """Erstellt einen einfachen Testraum."""
    # Add no_wall construction for internal boundaries
    no_wall = Construction(
        name="No Wall",
        element_type=ConstructionType.INTERNAL_WALL,
        u_value_w_m2k=0.5,
        thickness_m=0.0
    )
    sample_building.construction_catalog.append(no_wall)

    room = Room(
        name="Wohnzimmer",
        areas=[Area(
            length_m=5.0,
            width_m=4.0,
            left_adjacent_name="No Wall",
            right_adjacent_name="No Wall",
            top_adjacent_name="No Wall",
            bottom_adjacent_name="No Wall"
        )],
        net_height_m=2.5,
        room_temperature_name="Wohnraum",
        ventilation=Ventilation(air_change_1_h=0.5),
    )

    # Boden
    room.floor = Element(
        type=ElementType.FLOOR,
        name="Boden",
        construction_name="Bodenplatte",
        adjacent_temperature_name="Keller",
    )

    # Decke
    room.ceiling = Element(
        type=ElementType.CEILING,
        name="Decke",
        construction_name="Decke Standard",
        adjacent_temperature_name="Dachboden",
    )

    # Wand mit Fenster
    wall = Wall(
        orientation="Nord",
        net_length_m=5.0,
        construction_name="Außenwand Standard",
        left_wall_name="Außenwand Standard",
        right_wall_name="Außenwand Standard",
        windows=[
            Element(
                type=ElementType.WINDOW,
                name="Fenster 1",
                construction_name="Fenster Dreifach",
                width_m=1.2,
                height_m=1.5,
            )
        ],
        doors=[],
    )
    room.walls.append(wall)

    return room


class TestElementHeatLoad:
    """Tests für ElementHeatLoad Dataclass."""

    def test_create_element_heat_load(self):
        """Test der Erstellung eines ElementHeatLoad Objekts."""
        element = ElementHeatLoad(
            element_name="Testwand",
            u_value_w_m2k=0.24,
            u_value_corrected_w_m2k=0.29,
            area_m2=10.0,
            delta_temp_k=32.0,
            transmission_w=500.0,
        )
        assert element.element_name == "Testwand"
        assert element.u_value_w_m2k == 0.24
        assert element.area_m2 == 10.0
        assert element.delta_temp_k == 32.0
        assert element.transmission_w == 500.0


class TestRoomHeatLoadResult:
    """Tests für RoomHeatLoadResult Dataclass."""

    def test_transmission_w_property(self):
        """Test der transmission_w Property."""
        elements = [
            ElementHeatLoad("Element 1", 0.24, 0.29, 10.0, 32.0, 100.0),
            ElementHeatLoad("Element 2", 0.30, 0.35, 15.0, 32.0, 200.0),
            ElementHeatLoad("Element 3", 0.20, 0.25, 20.0, 32.0, 150.0),
        ]
        result = RoomHeatLoadResult(
            room_name="Test Raum",
            element_transmissions=elements,
            ventilation_w=50.0,
        )
        assert result.transmission_w == 450.0

    def test_total_w_property(self):
        """Test der total_w Property."""
        elements = [
            ElementHeatLoad("Element 1", 0.24, 0.29, 10.0, 32.0, 100.0),
            ElementHeatLoad("Element 2", 0.30, 0.35, 15.0, 32.0, 200.0),
        ]
        result = RoomHeatLoadResult(
            room_name="Test Raum",
            element_transmissions=elements,
            ventilation_w=50.0,
        )
        assert result.total_w == 350.0


class TestCalcElementTransmission:
    """Tests für calc_element_transmission Funktion."""

    def test_basic_calculation(self, sample_building):
        """Test einer einfachen Transmissionsberechnung."""
        result = calc_element_transmission(
            building=sample_building,
            element_name="Testwand",
            construction_name="Außenwand Standard",
            area_m2=10.0,
            delta_temp=32.0,  # 20°C - (-12°C)
        )

        assert result.element_name == "Testwand"
        assert result.u_value_w_m2k == 0.24
        assert result.area_m2 == 10.0
        assert result.delta_temp_k == 32.0
        # (0.24 + 0.05 thermal bridge) W/(m²K) * 10 m² * 32 K = 92.8 W
        assert pytest.approx(result.transmission_w, 0.01) == 92.8

    def test_with_deduction_area(self, sample_building):
        """Test mit Abzugsfläche."""
        result = calc_element_transmission(
            building=sample_building,
            element_name="Wand mit Fenster",
            construction_name="Außenwand Standard",
            area_m2=10.0,
            delta_temp=32.0,
            deduction_area_m2=2.0,
        )

        assert result.area_m2 == 8.0  # Nettofläche: 10 - 2
        assert result.delta_temp_k == 32.0
        # (0.24 + 0.05 thermal bridge) W/(m²K) * (10 - 2) m² * 32 K = 74.24 W
        assert pytest.approx(result.transmission_w, 0.01) == 74.24

    def test_default_deduction_area(self, sample_building):
        """Test mit Standard-Abzugsfläche (0.0)."""
        result = calc_element_transmission(
            building=sample_building,
            element_name="Boden",
            construction_name="Bodenplatte",
            area_m2=20.0,
            delta_temp=10.0,
        )

        assert result.u_value_w_m2k == 0.3
        assert result.area_m2 == 20.0
        assert result.delta_temp_k == 10.0
        # (0.3 + 0.05 thermal bridge) W/(m²K) * 20 m² * 10 K = 70.0 W
        assert pytest.approx(result.transmission_w, 0.01) == 70.0


class TestCalcVentilationHeatLoad:
    """Tests für calc_ventilation_heat_load Funktion."""

    def test_ventilation_calculation(self, simple_room):
        """Test der Lüftungswärmeverlustberechnung."""
        room_temp = 20.0
        outside_temp = -12.0

        result = calc_ventilation_heat_load(simple_room, room_temp, outside_temp)

        # V = 5 * 4 * 2.5 = 50 m³
        # Qv = 0.34 * 0.5 * 50 * 32 = 272 W
        assert pytest.approx(result, 0.01) == 272.0

    def test_zero_air_change(self, simple_room):
        """Test mit Luftwechsel = 0."""
        simple_room.ventilation.air_change_1_h = 0.0

        result = calc_ventilation_heat_load(simple_room, 20.0, -12.0)

        assert result == 0.0


class TestCalcFloorCeilingHeatLoad:
    """Tests für calc_floor_ceiling_heat_load Funktion."""

    def test_floor_and_ceiling(self, sample_building, simple_room):
        """Test der Boden- und Deckenberechnung."""
        room_temp = 20.0
        outside_temp = -12.0

        result = calc_floor_ceiling_heat_load(simple_room, room_temp, outside_temp, sample_building)

        assert len(result) == 2

        # Boden: (0.3 + 0.05 thermal bridge) W/(m²K) * 20 m² * (20 - 10) K = 70.0 W
        floor_result = next(e for e in result if e.element_name == "Boden")
        assert floor_result.u_value_w_m2k == 0.3
        assert floor_result.area_m2 == 20.0
        assert floor_result.delta_temp_k == 10.0
        assert pytest.approx(floor_result.transmission_w, 0.01) == 70.0

        # Decke: (0.2 + 0.05 thermal bridge) W/(m²K) * 20 m² * (20 - 5) K = 75.0 W
        ceiling_result = next(e for e in result if e.element_name == "Decke")
        assert ceiling_result.u_value_w_m2k == 0.2
        assert ceiling_result.area_m2 == 20.0
        assert ceiling_result.delta_temp_k == 15.0
        assert pytest.approx(ceiling_result.transmission_w, 0.01) == 75.0


class TestCalcWallsHeatLoad:
    """Tests für calc_walls_heat_load Funktion."""

    def test_wall_with_window(self, sample_building, simple_room):
        """Test einer Wand mit Fenster."""
        room_temp = 20.0
        outside_temp = -12.0

        result = calc_walls_heat_load(simple_room, room_temp, outside_temp, sample_building)

        # Erwarte 2 Elemente: Wand und Fenster
        assert len(result) == 2

        # Fenster: (0.8 + 0.05 thermal bridge) W/(m²K) * 1.8 m² * 32 K = 48.96 W
        window_result = next(e for e in result if "Fenster" in e.element_name)
        assert window_result.u_value_w_m2k == 0.8
        assert pytest.approx(window_result.area_m2, 0.01) == 1.8
        assert window_result.delta_temp_k == 32.0
        assert pytest.approx(window_result.transmission_w, 0.01) == 48.96


class TestCalcRoomHeatLoad:
    """Tests für calc_room_heat_load Funktion."""

    def test_complete_room_calculation(self, sample_building, simple_room):
        """Test der kompletten Raumberechnung."""
        result = calc_room_heat_load(simple_room, -12.0, sample_building)

        assert result.room_name == "Wohnzimmer"
        assert result.ventilation_w > 0
        assert result.transmission_w > 0
        assert result.total_w == result.transmission_w + result.ventilation_w

        # Prüfe dass alle Elemente vorhanden sind
        element_names = [e.element_name for e in result.element_transmissions]
        assert "Boden" in element_names
        assert "Decke" in element_names
        assert "Nord" in element_names


class TestCalcBuildingHeatLoad:
    """Tests für calc_building_heat_load Funktion."""

    def test_building_with_multiple_rooms(self, sample_building, simple_room):
        """Test der Gebäudeberechnung mit mehreren Räumen."""
        # Füge zwei Räume hinzu
        sample_building.rooms = [simple_room]

        result = calc_building_heat_load(sample_building)

        assert len(result) == 1
        assert result[0].room_name == "Wohnzimmer"
        assert result[0].total_w > 0
