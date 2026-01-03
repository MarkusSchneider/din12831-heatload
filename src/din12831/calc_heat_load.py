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


def calc_room_heat_load(room: Room, outside_temperatur: float, building: Building) -> RoomHeatLoadResult:
    transmission_w = 0.0

    # Hole Raumtemperatur dynamisch aus Katalog
    room_temp_obj = building.get_temperature_by_name(room.room_temperature_name)
    room_temp = room_temp_obj.value_celsius if room_temp_obj else 20.0

    # Berechne Transmissionsverluste für Bauelemente (Boden, Decke, Fenster, Türen)
    for element in room.elements:
        delta_temp = room_temp - outside_temperatur
        transmission_w += element.construction.u_value_w_m2k * element.area_m2 * delta_temp

    # Berechne Transmissionsverluste für Wände (berücksichtige Innenwände)
    for wall in room.walls:
        # Berechne Wandfläche
        wall_area_m2 = wall.length_m * room.height_m

        # Subtrahiere Fenster- und Türflächen
        for window in wall.windows:
            wall_area_m2 -= window.area_m2
        for door in wall.doors:
            wall_area_m2 -= door.area_m2

        # Bestimme Temperaturdifferenz basierend auf Wandtyp
        if wall.construction.element_type == ConstructionType.INTERNAL_WALL:
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

        transmission_w += wall.construction.u_value_w_m2k * wall_area_m2 * delta_temp

    # Einfache Lüftungsverluste: Qv = 0.34 * n * V * ΔT
    # 0.34 ~= rho_air * cp_air / 3600 (Wh/(m³·K) -> W)
    delta_temp_ventilation = room_temp - outside_temperatur
    ventilation_w = 0.34 * room.ventilation.air_change_1_h * room.volume_m3 * delta_temp_ventilation

    return RoomHeatLoadResult(
        room_name=room.name,
        transmission_w=transmission_w,
        ventilation_w=ventilation_w,
    )


def calc_building_heat_load(building: Building) -> list[RoomHeatLoadResult]:
    return [calc_room_heat_load(room, building.outside_temperatur, building) for room in building.rooms]
