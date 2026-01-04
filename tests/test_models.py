"""Tests for models.py"""

import pytest
from pydantic import ValidationError
from src.models import (
    Construction,
    ConstructionType,
    Temperature,
    Element,
    Ventilation,
    Area,
    Wall,
    Room,
    Building,
)


class TestConstructionType:
    """Tests for ConstructionType enum."""

    def test_construction_types_exist(self):
        assert ConstructionType.EXTERNAL_WALL == "external_wall"
        assert ConstructionType.INTERNAL_WALL == "internal_wall"
        assert ConstructionType.CEILING == "ceiling"
        assert ConstructionType.FLOOR == "floor"
        assert ConstructionType.WINDOW == "window"
        assert ConstructionType.DOOR == "door"


class TestConstruction:
    """Tests for Construction model."""

    def test_construction_creation(self):
        construction = Construction(
            name="External Wall 1",
            element_type=ConstructionType.EXTERNAL_WALL,
            u_value_w_m2k=0.24,
            thickness_m=0.36,
        )
        assert construction.name == "External Wall 1"
        assert construction.element_type == ConstructionType.EXTERNAL_WALL
        assert construction.u_value_w_m2k == 0.24
        assert construction.thickness_m == 0.36

    def test_construction_default_type(self):
        construction = Construction(name="Test", u_value_w_m2k=0.5)
        assert construction.element_type == ConstructionType.EXTERNAL_WALL

    def test_construction_no_thickness(self):
        construction = Construction(name="Window 1", u_value_w_m2k=1.2)
        assert construction.thickness_m is None

    def test_construction_invalid_u_value(self):
        with pytest.raises(ValidationError):
            Construction(name="Bad", u_value_w_m2k=0)  # Must be > 0

    def test_construction_negative_thickness(self):
        with pytest.raises(ValidationError):
            Construction(name="Bad", u_value_w_m2k=0.5, thickness_m=-0.1)


class TestTemperature:
    """Tests for Temperature model."""

    def test_temperature_creation(self):
        temp = Temperature(name="Living Room", value_celsius=20.0)
        assert temp.name == "Living Room"
        assert temp.value_celsius == 20.0

    def test_temperature_string_representation(self):
        temp = Temperature(name="Outside", value_celsius=-10.5)
        assert str(temp) == "Outside (-10.5 °C)"

    def test_temperature_negative_values(self):
        temp = Temperature(name="Cold", value_celsius=-20.0)
        assert temp.value_celsius == -20.0


class TestElement:
    """Tests for Element model."""

    def test_element_window_with_dimensions(self):
        element = Element(
            type="window",
            name="Window 1",
            construction_name="Window Type A",
            width_m=1.2,
            height_m=1.5,
        )
        assert element.type == "window"
        assert element.area_m2 == pytest.approx(1.8)

    def test_element_window_without_dimensions_fails(self):
        with pytest.raises(ValidationError):
            Element(
                type="window",
                name="Bad Window",
                construction_name="Window Type A",
            )

    def test_element_door_with_dimensions(self):
        element = Element(
            type="door",
            name="Door 1",
            construction_name="Door Type A",
            width_m=0.9,
            height_m=2.1,
        )
        assert element.type == "door"
        assert element.area_m2 == pytest.approx(1.89)

    def test_element_door_without_height_fails(self):
        with pytest.raises(ValidationError):
            Element(
                type="door",
                name="Bad Door",
                construction_name="Door Type A",
                width_m=0.9,
            )

    def test_element_wall_without_dimensions(self):
        element = Element(
            type="wall",
            name="Wall 1",
            construction_name="External Wall",
        )
        assert element.area_m2 == 0.0

    def test_element_floor_with_adjacent_temperature(self):
        element = Element(
            type="floor",
            name="Floor 1",
            construction_name="Floor Type A",
            adjacent_temperature_name="Basement",
        )
        assert element.adjacent_temperature_name == "Basement"


class TestVentilation:
    """Tests for Ventilation model."""

    def test_ventilation_default(self):
        vent = Ventilation()
        assert vent.air_change_1_h == 0.5

    def test_ventilation_custom(self):
        vent = Ventilation(air_change_1_h=1.5)
        assert vent.air_change_1_h == 1.5

    def test_ventilation_negative_fails(self):
        with pytest.raises(ValidationError):
            Ventilation(air_change_1_h=-0.5)


class TestArea:
    """Tests for Area model."""

    def test_area_simple(self):
        area = Area(length_m=5.0, width_m=4.0)
        assert area.area_m2 == 20.0

    def test_area_with_adjacents(self):
        area = Area(
            length_m=5.0,
            width_m=4.0,
            left_adjacent_name="Wall Left",
            right_adjacent_name="Wall Right",
        )
        assert area.left_adjacent_name == "Wall Left"
        assert area.right_adjacent_name == "Wall Right"

    def test_area_gross_calculation_no_building(self):
        """Test that gross_area_m2 needs a building parameter."""
        area = Area(length_m=5.0, width_m=4.0)
        # This test just ensures the method exists and requires a building
        building = Building(name="Test Building")
        gross_area = area.gross_area_m2(building)
        assert gross_area == 20.0  # No adjacent walls, so same as net


class TestWall:
    """Tests for Wall model."""

    def test_wall_creation(self):
        wall = Wall(
            orientation="North",
            net_length_m=5.0,
            construction_name="External Wall 1",
            left_wall_name="Left Wall",
            right_wall_name="Right Wall",
        )
        assert wall.orientation == "North"
        assert wall.net_length_m == 5.0
        assert len(wall.windows) == 0
        assert len(wall.doors) == 0

    def test_wall_with_windows_and_doors(self):
        window = Element(
            type="window",
            name="Window 1",
            construction_name="Window Type A",
            width_m=1.2,
            height_m=1.5,
        )
        door = Element(
            type="door",
            name="Door 1",
            construction_name="Door Type A",
            width_m=0.9,
            height_m=2.1,
        )
        wall = Wall(
            orientation="South",
            net_length_m=6.0,
            construction_name="External Wall 1",
            left_wall_name="Left Wall",
            right_wall_name="Right Wall",
            windows=[window],
            doors=[door],
        )
        assert len(wall.windows) == 1
        assert len(wall.doors) == 1

    def test_wall_with_adjacent_room(self):
        wall = Wall(
            orientation="East",
            net_length_m=4.0,
            construction_name="Internal Wall 1",
            left_wall_name="Left Wall",
            right_wall_name="Right Wall",
            adjacent_room_temperature_name="Corridor",
        )
        assert wall.adjacent_room_temperature_name == "Corridor"


class TestRoom:
    """Tests for Room model."""

    def test_room_creation(self):
        area = Area(length_m=5.0, width_m=4.0)
        room = Room(
            name="Living Room",
            areas=[area],
            net_height_m=2.5,
        )
        assert room.name == "Living Room"
        assert room.net_height_m == 2.5
        assert room.floor_area_m2 == 20.0
        assert room.volume_m3 == 50.0

    def test_room_multiple_areas(self):
        area1 = Area(length_m=5.0, width_m=4.0)
        area2 = Area(length_m=2.0, width_m=3.0)
        room = Room(
            name="L-Shaped Room",
            areas=[area1, area2],
            net_height_m=2.5,
        )
        assert room.floor_area_m2 == 26.0
        assert room.volume_m3 == 65.0

    def test_room_no_areas(self):
        room = Room(name="Empty Room", net_height_m=2.5)
        assert room.floor_area_m2 == 0.0
        assert room.volume_m3 == 0.0

    def test_room_with_ventilation(self):
        room = Room(
            name="Room with Vent",
            net_height_m=2.5,
            ventilation=Ventilation(air_change_1_h=1.0),
        )
        assert room.ventilation.air_change_1_h == 1.0

    def test_room_elements_property(self):
        window = Element(
            type="window",
            name="Window 1",
            construction_name="Window Type A",
            width_m=1.2,
            height_m=1.5,
        )
        door = Element(
            type="door",
            name="Door 1",
            construction_name="Door Type A",
            width_m=0.9,
            height_m=2.1,
        )
        floor = Element(
            type="floor",
            name="Floor 1",
            construction_name="Floor Type A",
        )
        ceiling = Element(
            type="ceiling",
            name="Ceiling 1",
            construction_name="Ceiling Type A",
        )
        wall = Wall(
            orientation="North",
            net_length_m=5.0,
            construction_name="External Wall 1",
            left_wall_name="Left Wall",
            right_wall_name="Right Wall",
            windows=[window],
            doors=[door],
        )
        room = Room(
            name="Complete Room",
            net_height_m=2.5,
            walls=[wall],
            floor=floor,
            ceiling=ceiling,
        )
        elements = room.elements
        assert len(elements) == 4  # window, door, floor, ceiling


class TestBuilding:
    """Tests for Building model."""

    def test_building_creation(self):
        building = Building(name="My Building")
        assert building.name == "My Building"
        assert len(building.temperature_catalog) == 0
        assert len(building.construction_catalog) == 0
        assert len(building.rooms) == 0
        assert building.thermal_bridge_surcharge == 0.05

    def test_building_with_temperature_catalog(self):
        temp1 = Temperature(name="Living Room", value_celsius=20.0)
        temp2 = Temperature(name="Outside", value_celsius=-10.0)
        building = Building(
            name="Test Building",
            temperature_catalog=[temp1, temp2],
        )
        assert len(building.temperature_catalog) == 2

    def test_building_get_temperature_by_name(self):
        temp1 = Temperature(name="Living Room", value_celsius=20.0)
        temp2 = Temperature(name="Outside", value_celsius=-10.0)
        building = Building(
            name="Test Building",
            temperature_catalog=[temp1, temp2],
        )
        found_temp = building.get_temperature_by_name("Living Room")
        assert found_temp.value_celsius == 20.0

    def test_building_get_temperature_not_found(self):
        building = Building(name="Test Building")
        with pytest.raises(ValueError, match="Temperature 'Unknown' not found"):
            building.get_temperature_by_name("Unknown")

    def test_building_get_temperature_none(self):
        building = Building(name="Test Building")
        with pytest.raises(ValueError, match="Temperature name cannot be None"):
            building.get_temperature_by_name(None)

    def test_building_with_construction_catalog(self):
        const1 = Construction(
            name="External Wall 1",
            element_type=ConstructionType.EXTERNAL_WALL,
            u_value_w_m2k=0.24,
            thickness_m=0.36,
        )
        const2 = Construction(
            name="Window 1",
            element_type=ConstructionType.WINDOW,
            u_value_w_m2k=1.2,
        )
        building = Building(
            name="Test Building",
            construction_catalog=[const1, const2],
        )
        assert len(building.construction_catalog) == 2

    def test_building_get_construction_by_name(self):
        const1 = Construction(
            name="External Wall 1",
            element_type=ConstructionType.EXTERNAL_WALL,
            u_value_w_m2k=0.24,
            thickness_m=0.36,
        )
        building = Building(
            name="Test Building",
            construction_catalog=[const1],
        )
        found_const = building.get_construction_by_name("External Wall 1")
        assert found_const.u_value_w_m2k == 0.24

    def test_building_get_construction_not_found(self):
        building = Building(name="Test Building")
        with pytest.raises(ValueError, match="Construction 'Unknown' not found"):
            building.get_construction_by_name("Unknown")

    def test_building_get_construction_none(self):
        building = Building(name="Test Building")
        with pytest.raises(ValueError, match="Construction name cannot be None"):
            building.get_construction_by_name(None)

    def test_building_outside_temperature_property(self):
        temp_outside = Temperature(name="Outside", value_celsius=-10.0)
        building = Building(
            name="Test Building",
            temperature_catalog=[temp_outside],
            outside_temperature_name="Outside",
        )
        assert building.outside_temperature.value_celsius == -10.0

    def test_building_default_room_temperature_property(self):
        temp_room = Temperature(name="Default Room", value_celsius=20.0)
        building = Building(
            name="Test Building",
            temperature_catalog=[temp_room],
            default_room_temperature_name="Default Room",
        )
        assert building.default_room_temperature.value_celsius == 20.0

    def test_building_with_rooms(self):
        area = Area(length_m=5.0, width_m=4.0)
        room = Room(name="Living Room", areas=[area], net_height_m=2.5)
        building = Building(name="Test Building", rooms=[room])
        assert len(building.rooms) == 1
        assert building.rooms[0].name == "Living Room"

    def test_building_thermal_bridge_surcharge_custom(self):
        building = Building(name="Test Building", thermal_bridge_surcharge=0.1)
        assert building.thermal_bridge_surcharge == 0.1

    def test_building_thermal_bridge_surcharge_negative_fails(self):
        with pytest.raises(ValidationError):
            Building(name="Bad Building", thermal_bridge_surcharge=-0.05)


class TestIntegration:
    """Integration tests for complex scenarios."""

    def test_complete_building_setup(self):
        # Create temperature catalog
        temp_outside = Temperature(name="Outside", value_celsius=-10.0)
        temp_room = Temperature(name="Living Room", value_celsius=20.0)
        temp_basement = Temperature(name="Basement", value_celsius=10.0)

        # Create construction catalog
        ext_wall = Construction(
            name="External Wall",
            element_type=ConstructionType.EXTERNAL_WALL,
            u_value_w_m2k=0.24,
            thickness_m=0.36,
        )
        int_wall = Construction(
            name="Internal Wall",
            element_type=ConstructionType.INTERNAL_WALL,
            u_value_w_m2k=0.5,
            thickness_m=0.12,
        )
        window = Construction(
            name="Window",
            element_type=ConstructionType.WINDOW,
            u_value_w_m2k=1.2,
        )
        floor_const = Construction(
            name="Floor",
            element_type=ConstructionType.FLOOR,
            u_value_w_m2k=0.3,
            thickness_m=0.25,
        )
        ceiling_const = Construction(
            name="Ceiling",
            element_type=ConstructionType.CEILING,
            u_value_w_m2k=0.2,
            thickness_m=0.20,
        )

        # Create building
        building = Building(
            name="Test House",
            temperature_catalog=[temp_outside, temp_room, temp_basement],
            outside_temperature_name="Outside",
            default_room_temperature_name="Living Room",
            construction_catalog=[ext_wall, int_wall, window, floor_const, ceiling_const],
            thermal_bridge_surcharge=0.05,
        )

        # Create room with elements
        window_elem = Element(
            type="window",
            name="Window 1",
            construction_name="Window",
            width_m=1.2,
            height_m=1.5,
        )
        floor_elem = Element(
            type="floor",
            name="Floor",
            construction_name="Floor",
            adjacent_temperature_name="Basement",
        )
        ceiling_elem = Element(
            type="ceiling",
            name="Ceiling",
            construction_name="Ceiling",
        )

        wall = Wall(
            orientation="North",
            net_length_m=5.0,
            construction_name="External Wall",
            left_wall_name="Internal Wall",
            right_wall_name="Internal Wall",
            windows=[window_elem],
        )

        area = Area(
            length_m=5.0,
            width_m=4.0,
            left_adjacent_name="External Wall",
            right_adjacent_name="External Wall",
            top_adjacent_name="Internal Wall",
            bottom_adjacent_name="Internal Wall",
        )

        room = Room(
            name="Living Room",
            areas=[area],
            net_height_m=2.5,
            room_temperature_name="Living Room",
            walls=[wall],
            floor=floor_elem,
            ceiling=ceiling_elem,
            ventilation=Ventilation(air_change_1_h=0.5),
        )

        building.rooms.append(room)

        # Verify the complete setup
        assert building.name == "Test House"
        assert len(building.temperature_catalog) == 3
        assert len(building.construction_catalog) == 5
        assert len(building.rooms) == 1
        assert building.rooms[0].floor_area_m2 == 20.0
        assert building.rooms[0].volume_m3 == 50.0
        assert len(building.rooms[0].elements) == 3  # window, floor, ceiling

        # Test catalog lookups
        assert building.outside_temperature.value_celsius == -10.0
        assert building.default_room_temperature.value_celsius == 20.0
        assert building.get_construction_by_name("External Wall").u_value_w_m2k == 0.24

        # Test gross calculations
        gross_floor = room.gross_floor_area_m2(building)
        assert gross_floor > 20.0  # Should be larger due to wall thickness

        gross_ceiling = room.gross_ceiling_area_m2(building)
        assert gross_ceiling > 20.0  # Should be larger due to wall thickness

        gross_height = room.gross_height_m(building)
        assert gross_height > 2.5  # Should be larger due to ceiling thickness
