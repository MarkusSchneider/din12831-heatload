from __future__ import annotations

from dataclasses import dataclass

from .models import Building, Room, ConstructionType


@dataclass(frozen=True)
class RoomHeatLoadResult:
    room_name: str
    transmission_w: float
    ventilation_w: float

    @property
    def total_w(self) -> float:
        return self.transmission_w + self.ventilation_w


def calc_elements_heat_load(room: Room, room_temp: float, outside_temperatur: float, building: Building) -> float:
    """Berechnet die Transmissionswärmeverluste für Bauelemente (Boden, Decke, Fenster, Türen)."""
    elements_heat_load = 0.0

    for element in room.elements:
        # Hole Construction aus Katalog
        construction = building.get_construction_by_name(element.construction_name)

        delta_temp = room_temp - outside_temperatur
        elements_heat_load += construction.u_value_w_m2k * element.area_m2 * delta_temp

    return elements_heat_load


def calc_walls_heat_load(room: Room, room_temp: float, outside_temperatur: float, building: Building) -> float:
    """Berechnet die Transmissionswärmeverluste für Wände (berücksichtige Innenwände)."""
    walls_heat_load = 0.0

    for wall in room.walls:
        # Hole Wall-Construction aus Katalog
        wall_construction = building.get_construction_by_name(wall.construction_name)

        # Berechne Bruttowandfläche
        wall_area_m2 = wall.gross_length_m(building) * room.gross_height_m(building)

        # Subtrahiere Fenster- und Türflächen
        for window in wall.windows:
            wall_area_m2 -= window.area_m2

        for door in wall.doors:
            wall_area_m2 -= door.area_m2

        # Bestimme Temperaturdifferenz basierend auf Wandtyp
        if wall_construction.element_type == ConstructionType.INTERNAL_WALL:
            # Bei Innenwänden: Verwende Temperatur des angrenzenden Raums dynamisch aus Katalog
            adj_temp_obj = building.get_temperature_by_name(wall.adjacent_room_temperature_name)
            delta_temp = room_temp - adj_temp_obj.value_celsius
        else:
            # Bei Außenwänden: Verwende Außentemperatur
            delta_temp = room_temp - outside_temperatur

        walls_heat_load += wall_construction.u_value_w_m2k * wall_area_m2 * delta_temp

    return walls_heat_load


def calc_transmission_heat_load(room: Room, room_temp: float, outside_temperatur: float, building: Building) -> float:
    """Berechnet die Transmissionswärmeverluste eines Raums."""
    elements_heat_load = calc_elements_heat_load(room, room_temp, outside_temperatur, building)
    walls_heat_load = calc_walls_heat_load(room, room_temp, outside_temperatur, building)
    return elements_heat_load + walls_heat_load


def calc_ventilation_heat_load(room: Room, room_temp: float, outside_temperatur: float) -> float:
    """Berechnet die Lüftungswärmeverluste eines Raums.

    Einfache Lüftungsverluste: Qv = 0.34 * n * V * ΔT
    0.34 ~= rho_air * cp_air / 3600 (Wh/(m³·K) -> W)
    """
    delta_temp_ventilation = room_temp - outside_temperatur
    ventilation_w = 0.34 * room.ventilation.air_change_1_h * room.volume_m3 * delta_temp_ventilation
    return ventilation_w


def calc_room_heat_load(room: Room, outside_temperatur: float, building: Building) -> RoomHeatLoadResult:
    """Berechnet die gesamte Heizlast eines Raums (Transmission + Lüftung)."""
    # Hole Raumtemperatur dynamisch aus Katalog
    room_temp = building.get_temperature_by_name(room.room_temperature_name).value_celsius

    ventilation_w = calc_ventilation_heat_load(room, room_temp, outside_temperatur)
    transmission_w = calc_transmission_heat_load(room, room_temp, outside_temperatur, building)

    return RoomHeatLoadResult(
        room_name=room.name,
        transmission_w=transmission_w,
        ventilation_w=ventilation_w,
    )


def calc_building_heat_load(building: Building) -> list[RoomHeatLoadResult]:
    return [calc_room_heat_load(room, building.outside_temperature.value_celsius, building) for room in building.rooms]
