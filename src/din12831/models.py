from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


ElementType = Literal["wall", "window", "door", "ceiling", "floor"]


class ConstructionType(str, Enum):
    WALL = "wall"
    CEILING = "ceiling"
    FLOOR = "floor"
    WINDOW = "window"
    DOOR = "door"


class Construction(BaseModel):
    name: str
    element_type: ConstructionType = Field(
        default=ConstructionType.WALL, description="Bauteiltyp")
    u_value_w_m2k: float = Field(gt=0, description="U-Wert in W/(m²·K)")
    thickness_m: float | None = Field(
        default=None, gt=0, description="Dicke (nur für Wand/Decke/Boden)")
    is_external: bool | None = Field(
        default=None, description="Außenwand (nur für Wand)")


class Element(BaseModel):
    type: ElementType
    name: str
    area_m2: float = Field(gt=0)
    construction: Construction


class Ventilation(BaseModel):
    air_change_1_h: float = Field(
        default=0.5, ge=0.0, description="Luftwechsel n in 1/h")


class Area(BaseModel):
    model_config = {"frozen": True}

    length_m: float = Field(gt=0)
    width_m: float = Field(gt=0)

    @property
    def area_m2(self) -> float:
        return self.length_m * self.width_m


class Wall(BaseModel):
    orientation: str = Field(description="Richtung/Bezeichnung (z.B. Nord, Ost, Süd 1, West 2)")
    length_m: float = Field(gt=0, description="Wandlänge in m")
    construction: Construction = Field(description="Wandkonstruktion aus Katalog")
    windows: list[Element] = Field(default_factory=list, description="Fenster in dieser Wand")
    doors: list[Element] = Field(default_factory=list, description="Türen in dieser Wand")
    left_wall: str | None = Field(default=None, description="Linke Nachbarwand (Orientierung/Bezeichnung)")
    right_wall: str | None = Field(default=None, description="Rechte Nachbarwand (Orientierung/Bezeichnung)")


class Room(BaseModel):
    name: str
    areas: list[Area] | None = Field(
        default=None,
        description="Raumgrundriss als Summe mehrerer Rechtecke (jeweils Länge×Breite).",
    )
    height_m: float = Field(gt=0)
    room_temperature: float = Field(
        default=20.0, description="Raumtemperatur in °C")
    walls: list[Wall] = Field(default_factory=list, description="Wände des Raums")
    floor: Element | None = Field(default=None, description="Bodenkonstruktion")
    ceiling: Element | None = Field(default=None, description="Deckenkonstruktion")
    ventilation: Ventilation = Field(default_factory=Ventilation)

    @property
    def floor_area_m2(self) -> float:
        if not self.areas:
            return 0.0
        return sum(r.area_m2 for r in self.areas)

    @property
    def volume_m3(self) -> float:
        return self.floor_area_m2 * self.height_m


class Building(BaseModel):
    name: str
    outside_temperatur: float = Field(
        default=-10.0, description="Normaußentemperatur in °C")
    construction_catalog: list[Construction] = Field(
        default_factory=list, description="Bauteilkatalog")
    rooms: list[Room] = Field(default_factory=list)
