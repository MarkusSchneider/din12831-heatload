from __future__ import annotations

from dataclasses import dataclass

from .models import Building, Room


@dataclass(frozen=True)
class RoomHeatLoadResult:
    room_name: str
    transmission_w: float
    ventilation_w: float

    @property
    def total_w(self) -> float:
        return self.transmission_w + self.ventilation_w


def calc_room_heat_load(room: Room, outside_temperatur: float) -> RoomHeatLoadResult:
    delta_temp = room.room_temperature - outside_temperatur

    transmission_w = 0.0
    for element in room.elements:
        transmission_w += element.construction.u_value_w_m2k * element.area_m2 * delta_temp

    # Einfache Lüftungsverluste: Qv = 0.34 * n * V * ΔT
    # 0.34 ~= rho_air * cp_air / 3600 (Wh/(m³·K) -> W)
    ventilation_w = 0.34 * room.ventilation.air_change_1_h * room.volume_m3 * delta_temp

    return RoomHeatLoadResult(
        room_name=room.name,
        transmission_w=transmission_w,
        ventilation_w=ventilation_w,
    )


def calc_building_heat_load(building: Building) -> list[RoomHeatLoadResult]:
    return [calc_room_heat_load(room, building.outside_temperatur) for room in building.rooms]
