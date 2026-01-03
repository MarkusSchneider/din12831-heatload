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


def calc_transmission_heat_load(room: Room, room_temp: float, outside_temperatur: float, building: Building) -> float:
    """Berechnet die Transmissionswärmeverluste eines Raums."""
    transmission_w = 0.0

    # Berechne Transmissionsverluste für Bauelemente (Boden, Decke, Fenster, Türen)
    for element in room.elements:
        # Hole Construction aus Katalog
        construction = building.get_construction_by_name(element.construction_name)
        if construction is None:
            continue  # Überspringe, wenn Konstruktion nicht gefunden

        delta_temp = room_temp - outside_temperatur
        transmission_w += construction.u_value_w_m2k * element.area_m2 * delta_temp

    # Berechne Transmissionsverluste für Wände (berücksichtige Innenwände)
    for wall in room.walls:
        # Hole Wall-Construction aus Katalog
        wall_construction = building.get_construction_by_name(wall.construction_name)
        if wall_construction is None:
            continue  # Überspringe, wenn Konstruktion nicht gefunden

        # Berechne Wandfläche
        wall_area_m2 = wall.net_length_m * room.net_height_m

        # Subtrahiere Fenster- und Türflächen
        for window in wall.windows:
            wall_area_m2 -= window.area_m2
        for door in wall.doors:
            wall_area_m2 -= door.area_m2

        # Bestimme Temperaturdifferenz basierend auf Wandtyp
        if wall_construction.element_type == ConstructionType.INTERNAL_WALL:
            # Bei Innenwänden: Verwende Temperatur des angrenzenden Raums dynamisch aus Katalog
            adj_temp_obj = building.get_temperature_by_name(wall.adjacent_room_temperature_name)
            if adj_temp_obj is not None:
                delta_temp = room_temp - adj_temp_obj.value_celsius
            else:
                # Fallback: keine Temperaturdifferenz wenn nicht angegeben
                delta_temp = 0.0
        else:
            # Bei Außenwänden: Verwende Außentemperatur
            delta_temp = room_temp - outside_temperatur

        transmission_w += wall_construction.u_value_w_m2k * wall_area_m2 * delta_temp

    return transmission_w


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
    room_temp_obj = building.get_temperature_by_name(room.room_temperature_name)
    room_temp = room_temp_obj.value_celsius if room_temp_obj else 20.0

    transmission_w = calc_transmission_heat_load(room, room_temp, outside_temperatur, building)
    ventilation_w = calc_ventilation_heat_load(room, room_temp, outside_temperatur)

    return RoomHeatLoadResult(
        room_name=room.name,
        transmission_w=transmission_w,
        ventilation_w=ventilation_w,
    )


def calc_building_heat_load(building: Building) -> list[RoomHeatLoadResult]:
    return [calc_room_heat_load(room, building.outside_temperature.value_celsius, building) for room in building.rooms]
