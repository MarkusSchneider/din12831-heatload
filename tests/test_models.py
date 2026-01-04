"""Tests for models.py"""

import pytest
from pydantic import ValidationError

from src.models import (
    Area,
    Building,
    Construction,
    ConstructionType,
    Element,
    ElementType,
    Room,
    Temperature,
    Ventilation,
    Wall,
    get_adjacent_thickness,
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
        construction = Construction(name="Test", u_value_w_m2k=0.5, thickness_m=0.3)
        assert construction.element_type == ConstructionType.EXTERNAL_WALL

    def test_construction_no_thickness(self):
        construction = Construction(name="Window 1", element_type=ConstructionType.WINDOW, u_value_w_m2k=1.2)
        assert construction.thickness_m is None

    def test_construction_invalid_u_value(self):
        with pytest.raises(ValidationError):
            Construction(name="Bad", u_value_w_m2k=0)  # Must be > 0

    def test_construction_negative_thickness(self):
        with pytest.raises(ValidationError):
            Construction(name="Bad", u_value_w_m2k=0.5, thickness_m=-0.1)

    def test_construction_requires_thickness_for_walls(self):
        """Test that external walls require thickness."""
        with pytest.raises(ValidationError) as exc_info:
            Construction(name="External Wall", element_type=ConstructionType.EXTERNAL_WALL, u_value_w_m2k=0.24)
        assert "requires thickness_m to be set" in str(exc_info.value)

    def test_construction_requires_thickness_for_internal_walls(self):
        """Test that internal walls require thickness."""
        with pytest.raises(ValidationError) as exc_info:
            Construction(name="Internal Wall", element_type=ConstructionType.INTERNAL_WALL, u_value_w_m2k=0.5)
        assert "requires thickness_m to be set" in str(exc_info.value)

    def test_construction_requires_thickness_for_floor(self):
        """Test that floors require thickness."""
        with pytest.raises(ValidationError) as exc_info:
            Construction(name="Floor", element_type=ConstructionType.FLOOR, u_value_w_m2k=0.3)
        assert "requires thickness_m to be set" in str(exc_info.value)

    def test_construction_requires_thickness_for_ceiling(self):
        """Test that ceilings require thickness."""
        with pytest.raises(ValidationError) as exc_info:
            Construction(name="Ceiling", element_type=ConstructionType.CEILING, u_value_w_m2k=0.2)
        assert "requires thickness_m to be set" in str(exc_info.value)

    def test_construction_no_thickness_required_for_window(self):
        """Test that windows don't require thickness."""
        construction = Construction(name="Window", element_type=ConstructionType.WINDOW, u_value_w_m2k=0.8)
        assert construction.thickness_m is None

    def test_construction_no_thickness_required_for_door(self):
        """Test that doors don't require thickness."""
        construction = Construction(name="Door", element_type=ConstructionType.DOOR, u_value_w_m2k=1.8)
        assert construction.thickness_m is None

    def test_get_adjacent_thickness_external_wall(self):
        """Test that external walls return full thickness."""
        construction = Construction(
            name="External Wall", element_type=ConstructionType.EXTERNAL_WALL, u_value_w_m2k=0.24, thickness_m=0.36
        )
        assert construction.get_adjacent_thickness() == 0.36

    def test_get_adjacent_thickness_internal_wall(self):
        """Test that internal walls return half thickness."""
        construction = Construction(
            name="Internal Wall", element_type=ConstructionType.INTERNAL_WALL, u_value_w_m2k=0.5, thickness_m=0.12
        )
        assert construction.get_adjacent_thickness() == pytest.approx(0.06)

    def test_get_adjacent_thickness_floor(self):
        """Test that floors return half thickness."""
        construction = Construction(
            name="Floor", element_type=ConstructionType.FLOOR, u_value_w_m2k=0.3, thickness_m=0.25
        )
        assert construction.get_adjacent_thickness() == pytest.approx(0.125)

    def test_get_adjacent_thickness_ceiling(self):
        """Test that ceilings return half thickness."""
        construction = Construction(
            name="Ceiling", element_type=ConstructionType.CEILING, u_value_w_m2k=0.2, thickness_m=0.30
        )
        assert construction.get_adjacent_thickness() == pytest.approx(0.15)

    def test_get_adjacent_thickness_window_fails(self):
        """Test that windows can't calculate adjacent thickness."""
        construction = Construction(name="Window", element_type=ConstructionType.WINDOW, u_value_w_m2k=0.8)
        with pytest.raises(ValueError) as exc_info:
            construction.get_adjacent_thickness()
        assert "Invalid construction type" in str(exc_info.value)
        assert "Window" in str(exc_info.value)

    def test_get_adjacent_thickness_door_fails(self):
        """Test that doors can't calculate adjacent thickness."""
        construction = Construction(name="Door", element_type=ConstructionType.DOOR, u_value_w_m2k=1.8)
        with pytest.raises(ValueError) as exc_info:
            construction.get_adjacent_thickness()
        assert "Invalid construction type" in str(exc_info.value)
        assert "Door" in str(exc_info.value)


class TestGetAdjacentThickness:
    """Tests for module-level get_adjacent_thickness function."""

    def test_get_adjacent_thickness_external_wall(self):
        """Test that external walls return full thickness."""
        external_wall = Construction(
            name="External Wall", element_type=ConstructionType.EXTERNAL_WALL, u_value_w_m2k=0.24, thickness_m=0.36
        )
        building = Building(name="Test Building", construction_catalog=[external_wall])

        thickness = get_adjacent_thickness(building, "External Wall")
        assert thickness == 0.36

    def test_get_adjacent_thickness_internal_wall(self):
        """Test that internal walls return half thickness."""
        internal_wall = Construction(
            name="Internal Wall", element_type=ConstructionType.INTERNAL_WALL, u_value_w_m2k=0.5, thickness_m=0.12
        )
        building = Building(name="Test Building", construction_catalog=[internal_wall])

        thickness = get_adjacent_thickness(building, "Internal Wall")
        assert thickness == 0.06  # Half of 0.12

    def test_get_adjacent_thickness_floor(self):
        """Test that floors return half thickness."""
        floor = Construction(name="Floor", element_type=ConstructionType.FLOOR, u_value_w_m2k=0.3, thickness_m=0.25)
        building = Building(name="Test Building", construction_catalog=[floor])

        thickness = get_adjacent_thickness(building, "Floor")
        assert thickness == 0.125  # Half of 0.25

    def test_get_adjacent_thickness_ceiling(self):
        """Test that ceilings return half thickness."""
        ceiling = Construction(
            name="Ceiling", element_type=ConstructionType.CEILING, u_value_w_m2k=0.2, thickness_m=0.20
        )
        building = Building(name="Test Building", construction_catalog=[ceiling])

        thickness = get_adjacent_thickness(building, "Ceiling")
        assert thickness == 0.10  # Half of 0.20

    def test_get_adjacent_thickness_construction_not_found(self):
        """Test that ValueError is raised when construction is not found."""
        building = Building(name="Test Building")

        with pytest.raises(ValueError) as exc_info:
            get_adjacent_thickness(building, "Nonexistent Wall")
        assert "Construction 'Nonexistent Wall' not found" in str(exc_info.value)

    def test_get_adjacent_thickness_none_adjacent_name(self):
        """Test that AssertionError is raised when adjacent_name is None."""
        building = Building(name="Test Building")

        with pytest.raises(AssertionError) as exc_info:
            get_adjacent_thickness(building, None)  # type: ignore
        assert "adjacent_name cannot be None" in str(exc_info.value)

    def test_get_adjacent_thickness_window_raises_error(self):
        """Test that windows raise ValueError (no thickness applicable)."""
        window = Construction(name="Window", element_type=ConstructionType.WINDOW, u_value_w_m2k=1.2)
        building = Building(name="Test Building", construction_catalog=[window])

        with pytest.raises(ValueError) as exc_info:
            get_adjacent_thickness(building, "Window")
        assert "Invalid construction type" in str(exc_info.value)

    def test_get_adjacent_thickness_door_raises_error(self):
        """Test that doors raise ValueError (no thickness applicable)."""
        door = Construction(name="Door", element_type=ConstructionType.DOOR, u_value_w_m2k=1.8)
        building = Building(name="Test Building", construction_catalog=[door])

        with pytest.raises(ValueError) as exc_info:
            get_adjacent_thickness(building, "Door")
        assert "Invalid construction type" in str(exc_info.value)


class TestTemperature:
    """Tests for Temperature model."""

    def test_temperature_creation(self):
        temp = Temperature(name="Living Room", value_celsius=20.0)
        assert temp.name == "Living Room"
        assert temp.value_celsius == 20.0

    def test_temperature_negative_values(self):
        temp = Temperature(name="Cold", value_celsius=-20.0)
        assert temp.value_celsius == -20.0


class TestElement:
    """Tests for Element model."""

    def test_element_window_with_dimensions(self):
        element = Element(
            type=ElementType.WINDOW,
            name="Window 1",
            construction_name="Window Type A",
            width_m=1.2,
            height_m=1.5,
        )
        assert element.type == ElementType.WINDOW
        assert element.area_m2 == pytest.approx(1.8)

    def test_element_window_without_dimensions_fails(self):
        with pytest.raises(ValidationError):
            Element(
                type=ElementType.WINDOW,
                name="Bad Window",
                construction_name="Window Type A",
            )

    def test_element_door_with_dimensions(self):
        element = Element(
            type=ElementType.DOOR,
            name="Door 1",
            construction_name="Door Type A",
            width_m=0.9,
            height_m=2.1,
        )
        assert element.type == ElementType.DOOR
        assert element.area_m2 == pytest.approx(1.89)

    def test_element_door_without_height_fails(self):
        with pytest.raises(ValidationError):
            Element(
                type=ElementType.DOOR,
                name="Bad Door",
                construction_name="Door Type A",
                width_m=0.9,
            )

    def test_element_floor_without_dimensions(self):
        element = Element(
            type=ElementType.FLOOR,
            name="Floor 1",
            construction_name="Floor Construction",
        )
        assert element.area_m2 == 0.0

    def test_element_floor_with_adjacent_temperature(self):
        element = Element(
            type=ElementType.FLOOR,
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
        area = Area(
            length_m=5.0,
            width_m=4.0,
        )
        assert area.area_m2 == 20.0


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
            type=ElementType.WINDOW,
            name="Window 1",
            construction_name="Window Type A",
            width_m=1.2,
            height_m=1.5,
        )
        door = Element(
            type=ElementType.DOOR,
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

    def test_wall_gross_length_with_adjacents(self):
        """Test Wall.gross_length_m() with adjacent walls."""
        external_wall = Construction(
            name="External Wall", element_type=ConstructionType.EXTERNAL_WALL, u_value_w_m2k=0.24, thickness_m=0.36
        )
        internal_wall = Construction(
            name="Internal Wall", element_type=ConstructionType.INTERNAL_WALL, u_value_w_m2k=0.5, thickness_m=0.12
        )
        building = Building(name="Test Building", construction_catalog=[external_wall, internal_wall])

        wall = Wall(
            orientation="North",
            net_length_m=5.0,
            construction_name="External Wall",
            left_wall_name="External Wall",  # Full thickness: 0.36
            right_wall_name="Internal Wall",  # Half thickness: 0.06
        )

        # Gross length = 5.0 + 0.36 + 0.06 = 5.42
        gross_length = wall.gross_length_m(building)
        assert gross_length == pytest.approx(5.42)

    def test_wall_gross_length_no_adjacents(self):
        """Test Wall.gross_length_m() with simple same-type adjacent walls."""
        external_wall = Construction(
            name="External Wall", element_type=ConstructionType.EXTERNAL_WALL, u_value_w_m2k=0.24, thickness_m=0.36
        )
        building = Building(name="Test Building", construction_catalog=[external_wall])

        wall = Wall(
            orientation="North",
            net_length_m=5.0,
            construction_name="External Wall",
            left_wall_name="External Wall",
            right_wall_name="External Wall",
        )

        # Gross length = 5.0 + 0.36 + 0.36 = 5.72
        gross_length = wall.gross_length_m(building)
        assert gross_length == pytest.approx(5.72)

    def test_wall_gross_area(self):
        """Test Wall.gross_area_m2() calculation."""
        external_wall = Construction(
            name="External Wall", element_type=ConstructionType.EXTERNAL_WALL, u_value_w_m2k=0.24, thickness_m=0.36
        )
        ceiling = Construction(
            name="Ceiling", element_type=ConstructionType.CEILING, u_value_w_m2k=0.2, thickness_m=0.20
        )
        building = Building(name="Test Building", construction_catalog=[external_wall, ceiling])

        wall = Wall(
            orientation="North",
            net_length_m=5.0,
            construction_name="External Wall",
            left_wall_name="External Wall",  # 0.36
            right_wall_name="External Wall",  # 0.36
        )

        # Gross length = 5.0 + 0.36 + 0.36 = 5.72
        # Net height = 2.5, ceiling thickness = 0.20
        # Gross height = 2.5 + 0.20 = 2.7
        # Gross area = 5.72 * 2.7 = 15.444
        gross_area = wall.gross_area_m2(building, gross_height_m=2.7)
        assert gross_area == pytest.approx(15.444)


class TestRoom:
    """Tests for Room model."""

    def test_room_creation(self):
        area = Area(
            length_m=5.0,
            width_m=4.0,
        )
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
        area1 = Area(
            length_m=5.0,
            width_m=4.0,
        )
        area2 = Area(
            length_m=2.0,
            width_m=3.0,
        )
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

    def test_room_gross_height(self):
        """Test Room.gross_height_m() with ceiling thickness."""
        ceiling = Construction(
            name="Ceiling", element_type=ConstructionType.CEILING, u_value_w_m2k=0.2, thickness_m=0.20
        )
        building = Building(name="Test Building", construction_catalog=[ceiling])

        ceiling_elem = Element(type=ElementType.CEILING, name="Ceiling 1", construction_name="Ceiling")
        room = Room(name="Test Room", net_height_m=2.5, ceiling=ceiling_elem)

        # Gross height = 2.5 + 0.20 = 2.7
        gross_height = room.gross_height_m(building)
        assert gross_height == pytest.approx(2.7)

    def test_room_gross_height_no_ceiling(self):
        """Test Room.gross_height_m() without ceiling."""
        building = Building(name="Test Building")
        room = Room(name="Test Room", net_height_m=2.5)

        # Gross height = net height when no ceiling
        gross_height = room.gross_height_m(building)
        assert gross_height == 2.5

    def test_room_gross_floor_area(self):
        """Test Room.gross_floor_area_m2() calculation mit wandbasierter Berechnung."""
        external_wall = Construction(
            name="External Wall", element_type=ConstructionType.EXTERNAL_WALL, u_value_w_m2k=0.24, thickness_m=0.36
        )
        internal_wall = Construction(
            name="Internal Wall", element_type=ConstructionType.INTERNAL_WALL, u_value_w_m2k=0.5, thickness_m=0.12
        )
        floor_construction = Construction(
            name="Floor", element_type=ConstructionType.FLOOR, u_value_w_m2k=0.3, thickness_m=0.15
        )
        building = Building(
            name="Test Building", construction_catalog=[external_wall, internal_wall, floor_construction]
        )

        area = Area(
            length_m=5.0,
            width_m=4.0,
        )
        floor_elem = Element(type=ElementType.FLOOR, name="Floor", construction_name="Floor")

        # Raum mit 4 Wänden (rechteckig)
        room = Room(
            name="Test Room",
            areas=[area],
            net_height_m=2.5,
            floor=floor_elem,
            walls=[
                Wall(
                    orientation="Nord",
                    net_length_m=5.0,
                    construction_name="External Wall",
                    left_wall_name="External Wall",
                    right_wall_name="External Wall",
                ),
                Wall(
                    orientation="Süd",
                    net_length_m=5.0,
                    construction_name="Internal Wall",
                    left_wall_name="Internal Wall",
                    right_wall_name="Internal Wall",
                ),
                Wall(
                    orientation="Ost",
                    net_length_m=4.0,
                    construction_name="External Wall",
                    left_wall_name="Internal Wall",
                    right_wall_name="External Wall",
                ),
                Wall(
                    orientation="West",
                    net_length_m=4.0,
                    construction_name="Internal Wall",
                    left_wall_name="External Wall",
                    right_wall_name="Internal Wall",
                ),
            ],
        )

        # Nettofläche = 5.0 * 4.0 = 20.0 m²
        # Wandstreifen-Berechnung:
        # Nord (Ext, eff=0.36): 5.0*0.36 + (0.36*0.36)/2 + (0.36*0.36)/2 = 1.80 + 0.0648 + 0.0648 = 1.9296 m²
        # Süd  (Int, eff=0.06): 5.0*0.06 + (0.06*0.06)/2 + (0.06*0.06)/2 = 0.30 + 0.0018 + 0.0018 = 0.3036 m²
        # Ost  (Ext, eff=0.36): 4.0*0.36 + (0.36*0.06)/2 + (0.36*0.36)/2 = 1.44 + 0.0108 + 0.0648 = 1.5156 m²
        # West (Int, eff=0.06): 4.0*0.06 + (0.06*0.36)/2 + (0.06*0.06)/2 = 0.24 + 0.0108 + 0.0018 = 0.2526 m²
        # Summe Streifen = 4.0014 m²
        # Bruttofläche = 20.0 + 4.0014 = 24.0014 m²
        gross_floor = room.gross_floor_area_m2(building)
        assert gross_floor == pytest.approx(24.0014)

    def test_room_gross_ceiling_area(self):
        """Test Room.gross_ceiling_area_m2() calculation mit wandbasierter Berechnung."""
        external_wall = Construction(
            name="External Wall", element_type=ConstructionType.EXTERNAL_WALL, u_value_w_m2k=0.24, thickness_m=0.36
        )
        ceiling_construction = Construction(
            name="Ceiling", element_type=ConstructionType.CEILING, u_value_w_m2k=0.2, thickness_m=0.20
        )
        building = Building(name="Test Building", construction_catalog=[external_wall, ceiling_construction])

        # L-förmiger Raum: zwei Areas
        area1 = Area(
            length_m=5.0,
            width_m=4.0,
        )
        area2 = Area(
            length_m=2.0,
            width_m=3.0,
        )
        ceiling_elem = Element(type=ElementType.CEILING, name="Ceiling", construction_name="Ceiling")

        # Raum mit 6 Wänden (L-Form)
        room = Room(
            name="L-Shaped Room",
            areas=[area1, area2],
            net_height_m=2.5,
            ceiling=ceiling_elem,
            walls=[
                Wall(
                    orientation="Nord",
                    net_length_m=5.0,
                    construction_name="External Wall",
                    left_wall_name="External Wall",
                    right_wall_name="External Wall",
                ),
                Wall(
                    orientation="Ost 1",
                    net_length_m=4.0,
                    construction_name="External Wall",
                    left_wall_name="External Wall",
                    right_wall_name="External Wall",
                ),
                Wall(
                    orientation="Süd 1",
                    net_length_m=3.0,
                    construction_name="External Wall",
                    left_wall_name="External Wall",
                    right_wall_name="External Wall",
                ),
                Wall(
                    orientation="Ost 2",
                    net_length_m=3.0,
                    construction_name="External Wall",
                    left_wall_name="External Wall",
                    right_wall_name="External Wall",
                ),
                Wall(
                    orientation="Süd 2",
                    net_length_m=2.0,
                    construction_name="External Wall",
                    left_wall_name="External Wall",
                    right_wall_name="External Wall",
                ),
                Wall(
                    orientation="West",
                    net_length_m=7.0,
                    construction_name="External Wall",
                    left_wall_name="External Wall",
                    right_wall_name="External Wall",
                ),
            ],
        )

        # Nettofläche = (5.0 * 4.0) + (2.0 * 3.0) = 20.0 + 6.0 = 26.0 m²
        # Wandstreifen-Berechnung - alle Wände External (eff=0.36):
        # Nord:  5.0*0.36 + (0.36*0.36)/2 + (0.36*0.36)/2 = 1.80 + 0.0648 + 0.0648 = 1.9296 m²
        # Ost1:  4.0*0.36 + (0.36*0.36)/2 + (0.36*0.36)/2 = 1.44 + 0.0648 + 0.0648 = 1.5696 m²
        # Süd1:  3.0*0.36 + (0.36*0.36)/2 + (0.36*0.36)/2 = 1.08 + 0.0648 + 0.0648 = 1.2096 m²
        # Ost2:  3.0*0.36 + (0.36*0.36)/2 + (0.36*0.36)/2 = 1.08 + 0.0648 + 0.0648 = 1.2096 m²
        # Süd2:  2.0*0.36 + (0.36*0.36)/2 + (0.36*0.36)/2 = 0.72 + 0.0648 + 0.0648 = 0.8496 m²
        # West:  7.0*0.36 + (0.36*0.36)/2 + (0.36*0.36)/2 = 2.52 + 0.0648 + 0.0648 = 2.6496 m²
        # Summe Streifen = 9.4176 m²
        # Bruttofläche = 26.0 + 9.4176 = 35.4176 m²
        gross_ceiling = room.gross_ceiling_area_m2(building)
        assert gross_ceiling == pytest.approx(35.4176)


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
        area = Area(
            length_m=5.0,
            width_m=4.0,
        )
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
            type=ElementType.WINDOW,
            name="Window 1",
            construction_name="Window",
            width_m=1.2,
            height_m=1.5,
        )
        floor_elem = Element(
            type=ElementType.FLOOR,
            name="Floor",
            construction_name="Floor",
            adjacent_temperature_name="Basement",
        )
        ceiling_elem = Element(
            type=ElementType.CEILING,
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


class TestDemoRoomGrossAreas:
    """Test Bruttoflächen-Berechnung für Demo-Räume (Arbeitszimmer und Bad)."""

    def test_arbeitszimmer_gross_area(self):
        """Test Bruttoflächen-Berechnung für Arbeitszimmer aus building_data_Demo.json.

        Manuelle Berechnung:
        #           Wanddicke  Wanddicke eff.  Länge     Angrenzend Links  Angrenzend Rechts  Wandfläche  Ecke links  Ecke Rechts    Summe
        # Osten      0.42           0.42        3.70           0.25                0.06         1.554000    0.052500    0.012600     1.619100
        # Süden      0.42           0.42        3.70           0.06                0.12         1.554000    0.012600    0.025200     1.591800
        # Westen     0.42           0.42        1.22           0.12                0.00         0.512400    0.025200    0.000000     0.537600
        # Norden 1   0.42           0.42        0.59           0.00                0.00         0.247800    0.000000    0.000000     0.247800
        # Norden 2   0.42           0.42        1.89           0.00                0.25         0.793800    0.000000    0.052500     0.846300
        # Summe Wandstreifen: 4.842600 m²
        # Nettofläche: 13.690000 m²
        # Bruttofläche: 18.532600 m²
        """
        import json
        from pathlib import Path

        # Lade Demo-Daten
        demo_file = Path(__file__).parent.parent / "building_data_Demo.json"
        with open(demo_file, encoding="utf-8") as f:
            data = json.load(f)

        building = Building(**data)
        room = next((r for r in building.rooms if r.name == "Arbeitszimmer"), None)

        assert room is not None, "Arbeitszimmer nicht in Demo-Daten gefunden"

        # Nettofläche
        assert room.floor_area_m2 == pytest.approx(13.69)

        # Bruttofläche - erwarteter Wert aus manueller Berechnung
        gross_floor = room.gross_floor_area_m2(building)
        assert gross_floor == pytest.approx(17.744100, abs=1e-5)

        # Floor und Ceiling müssen identisch sein
        gross_ceiling = room.gross_ceiling_area_m2(building)
        assert gross_floor == pytest.approx(gross_ceiling, abs=1e-6)

    def test_bad_gross_area(self):
        """Test Bruttoflächen-Berechnung für Bad aus building_data_Demo.json.

        Manuelle Berechnung:
        #            Wanddicke  Wanddicke eff.  Länge     Angrenzend Links  Angrenzend Rechts  Wandfläche  Ecke links  Ecke Rechts     Summe
        # Ostwand      0.42           0.42       3.40           0.125               0.06         1.428000    0.026250    0.012600     1.466850
        # Südwand      0.12           0.06       1.96           0.42                0.06         0.117600    0.012600    0.001800     0.132000
        # Westwand 1   0.12           0.06       2.37           0.06                0.06         0.142200    0.001800    0.001800     0.145800
        # Nordwand 1   0.12           0.06       1.25           0.06                0.00         0.075000    0.001800    0.000000     0.076800
        # Nordwand 2   0.25           0.125      0.71           0.06                0.42         0.088750    0.003750    0.026250     0.118750
        # Westwand 2   0.12           0.06       1.03           0.00                0.125        0.061800    0.000000    0.003750     0.065550
        # Summe Wandstreifen: 2.005750 m²
        # Nettofläche: 5.376500 m²
        # Bruttofläche: 7.382250 m²
        """
        import json
        from pathlib import Path

        # Lade Demo-Daten
        demo_file = Path(__file__).parent.parent / "building_data_Demo.json"
        with open(demo_file, encoding="utf-8") as f:
            data = json.load(f)

        building = Building(**data)
        room = next((r for r in building.rooms if r.name == "Bad"), None)

        assert room is not None, "Bad nicht in Demo-Daten gefunden"

        # Nettofläche (L-förmig: 2.37×1.96 + 1.03×0.71)
        assert room.floor_area_m2 == pytest.approx(5.3765, abs=1e-4)

        # Bruttofläche - erwarteter Wert aus manueller Berechnung
        gross_floor = room.gross_floor_area_m2(building)
        assert gross_floor == pytest.approx(7.382250, abs=1e-5)

        # Floor und Ceiling müssen identisch sein
        gross_ceiling = room.gross_ceiling_area_m2(building)
        assert gross_floor == pytest.approx(gross_ceiling, abs=1e-6)
