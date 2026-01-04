from __future__ import annotations

from dataclasses import dataclass

from .models import Building, Room, ConstructionType


@dataclass(frozen=True)
class ElementHeatLoad:
    """Wärmeverlust eines einzelnen Bauteils."""
    element_name: str
    u_value_w_m2k: float
    u_value_corrected_w_m2k: float
    area_m2: float
    delta_temp_k: float
    transmission_w: float


@dataclass(frozen=True)
class RoomHeatLoadResult:
    room_name: str
    element_transmissions: list[ElementHeatLoad]
    ventilation_w: float

    @property
    def transmission_w(self) -> float:
        """Gesamte Transmissionswärmeverluste."""
        return sum(element.transmission_w for element in self.element_transmissions)

    @property
    def total_w(self) -> float:
        """Gesamte Heizlast (Transmission + Lüftung)."""
        return self.transmission_w + self.ventilation_w


def calc_element_transmission(building: Building, element_name: str, construction_name: str, area_m2: float, delta_temp: float, deduction_area_m2: float = 0.0) -> ElementHeatLoad:
    """Berechnet den Transmissionswärmeverlust eines Bauteils.

    Args:
        building: Building-Objekt für Zugriff auf Konstruktionskatalog
        element_name: Name des Elements für die Ausgabe
        construction_name: Name der Konstruktion aus dem Katalog
        area_m2: Bruttofläche des Bauteils in m²
        delta_temp: Temperaturdifferenz in K
        deduction_area_m2: Abzugsfläche für Fenster und Türen in m² (Standard: 0.0)

    Returns:
        ElementHeatLoad mit Name, U-Wert, Fläche, Temperaturdifferenz und Transmissionswärmeverlust in W
    """
    construction = building.get_construction_by_name(construction_name)
    u_value_w_m2k = construction.u_value_w_m2k
    u_value_corrected_w_m2k = u_value_w_m2k + building.thermal_bridge_surcharge
    net_area_m2 = area_m2 - deduction_area_m2
    transmission_w = u_value_corrected_w_m2k * net_area_m2 * delta_temp

    return ElementHeatLoad(
        element_name=element_name,
        u_value_w_m2k=u_value_w_m2k,
        u_value_corrected_w_m2k=u_value_corrected_w_m2k,
        area_m2=net_area_m2,
        delta_temp_k=delta_temp,
        transmission_w=transmission_w
    )


def calc_floor_ceiling_heat_load(room: Room, room_temp: float, outside_temperatur: float, building: Building) -> list[ElementHeatLoad]:
    """Berechnet die Transmissionswärmeverluste für Boden und Decke."""
    elements_list: list[ElementHeatLoad] = []

    # Boden berechnen
    if room.floor:
        floor_area = room.floor_area_m2

        # Temperaturdifferenz für Boden
        if room.floor.adjacent_temperature_name:
            adj_temp = building.get_temperature_by_name(room.floor.adjacent_temperature_name)
            delta_temp_floor = room_temp - adj_temp.value_celsius
        else:
            delta_temp_floor = room_temp - outside_temperatur

        elements_list.append(calc_element_transmission(
            building,
            room.floor.name,
            room.floor.construction_name,
            floor_area,
            delta_temp_floor,
        ))

    # Decke berechnen
    if room.ceiling:
        ceiling_area = room.floor_area_m2

        # Temperaturdifferenz für Decke
        if room.ceiling.adjacent_temperature_name:
            adj_temp = building.get_temperature_by_name(room.ceiling.adjacent_temperature_name)
            delta_temp_ceiling = room_temp - adj_temp.value_celsius
        else:
            delta_temp_ceiling = room_temp - outside_temperatur

        elements_list.append(calc_element_transmission(
            building,
            room.ceiling.name,
            room.ceiling.construction_name,
            ceiling_area,
            delta_temp_ceiling,
        ))

    return elements_list


def calc_walls_heat_load(room: Room, room_temp: float, outside_temperatur: float, building: Building) -> list[ElementHeatLoad]:
    """Berechnet die Transmissionswärmeverluste für Wände (berücksichtigt Innenwände, Fenster und Türen)."""
    walls_list: list[ElementHeatLoad] = []

    for wall in room.walls:
        # Hole Wall-Construction aus Katalog
        wall_construction = building.get_construction_by_name(wall.construction_name)

        # Berechne Bruttowandfläche
        wall_area_m2 = wall.gross_length_m(building) * room.gross_height_m(building)

        # Berechne Abzugsfläche für Fenster und Türen
        deduction_area = sum(window.area_m2 for window in wall.windows) + sum(door.area_m2 for door in wall.doors)

        # Bestimme Temperaturdifferenz basierend auf Wandtyp
        if wall_construction.element_type == ConstructionType.INTERNAL_WALL:
            # Bei Innenwänden: Verwende Temperatur des angrenzenden Raums dynamisch aus Katalog
            adjacent_room_temperature = building.get_temperature_by_name(wall.adjacent_room_temperature_name)
            delta_temp = room_temp - adjacent_room_temperature.value_celsius
        else:
            # Bei Außenwänden: Verwende Außentemperatur
            delta_temp = room_temp - outside_temperatur

        walls_list.append(calc_element_transmission(
            building,
            wall.orientation,
            wall.construction_name,
            wall_area_m2,
            delta_temp,
            deduction_area,
        ))

        # Fenster in dieser Wand
        for window in wall.windows:
            walls_list.append(calc_element_transmission(
                building,
                f"{window.name} ({wall.orientation})",
                window.construction_name,
                window.area_m2,
                delta_temp,
            ))

        # Türen in dieser Wand
        for door in wall.doors:
            walls_list.append(calc_element_transmission(
                building,
                f"{door.name} ({wall.orientation})",
                door.construction_name,
                door.area_m2,
                delta_temp,
            ))

    return walls_list


def calc_transmission_heat_load(room: Room, room_temp: float, outside_temperatur: float, building: Building) -> float:
    """Berechnet die Transmissionswärmeverluste eines Raums."""
    floor_ceiling_list = calc_floor_ceiling_heat_load(room, room_temp, outside_temperatur, building)
    walls_list = calc_walls_heat_load(room, room_temp, outside_temperatur, building)
    floor_ceiling_heat_load = sum(e.transmission_w for e in floor_ceiling_list)
    walls_heat_load = sum(w.transmission_w for w in walls_list)
    return floor_ceiling_heat_load + walls_heat_load


def calc_ventilation_heat_load(room: Room, room_temp: float, outside_temperatur: float) -> float:
    """Berechnet die Lüftungswärmeverluste eines Raums.

    Einfache Lüftungsverluste: Qv = 0.34 * n * V * ΔT
    0.34 ~= rho_air * cp_air / 3600 (Wh/(m³·K) -> W)
    """
    delta_temp_ventilation = room_temp - outside_temperatur
    ventilation_w = 0.34 * room.ventilation.air_change_1_h * room.volume_m3 * delta_temp_ventilation
    return ventilation_w


def calc_room_heat_load(room: Room, outside_temperatur: float, building: Building) -> RoomHeatLoadResult:
    """Berechnet die gesamte Heizlast eines Raums (Transmission + Lüftung) mit Details pro Bauteil."""
    # Hole Raumtemperatur dynamisch aus Katalog
    room_temp = building.get_temperature_by_name(room.room_temperature_name).value_celsius

    # Lüftungswärmeverluste
    ventilation_w = calc_ventilation_heat_load(room, room_temp, outside_temperatur)

    # Liste für alle Bauteile
    element_transmissions_w: list[ElementHeatLoad] = []

    # Wände, Fenster und Türen
    element_transmissions_w.extend(calc_walls_heat_load(room, room_temp, outside_temperatur, building))

    # Boden und Decke
    element_transmissions_w.extend(calc_floor_ceiling_heat_load(room, room_temp, outside_temperatur, building))

    return RoomHeatLoadResult(
        room_name=room.name,
        element_transmissions=element_transmissions_w,
        ventilation_w=ventilation_w,
    )


def calc_building_heat_load(building: Building) -> list[RoomHeatLoadResult]:
    return [calc_room_heat_load(room, building.outside_temperature.value_celsius, building) for room in building.rooms]
