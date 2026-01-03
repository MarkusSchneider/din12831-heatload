from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ElementType = Literal["wall", "window", "door", "ceiling", "floor"]


class ConstructionType(str, Enum):
    WALL = "wall"
    CEILING = "ceiling"
    FLOOR = "floor"
    WINDOW = "window"
    DOOR = "door"


class Construction(BaseModel):
    name: str
    element_type: ConstructionType = Field(default=ConstructionType.WALL, description="Bauteiltyp")
    u_value_w_m2k: float = Field(gt=0, description="U-Wert in W/(m²·K)")
    thickness_m: float | None = Field(default=None, gt=0, description="Dicke (nur für Wand/Decke/Boden)")
    is_external: bool | None = Field(default=None, description="Außenwand (nur für Wand)")


class Element(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: ElementType
    name: str
    construction: Construction
    width_m: float | None = Field(default=None, gt=0, description="Breite in m")
    height_m: float | None = Field(default=None, gt=0, description="Höhe in m")

    @model_validator(mode='after')
    def validate_dimensions(self):
        """Validiere, dass für Fenster und Türen Breite und Höhe angegeben sind."""
        if self.type in ["window", "door"]:
            if self.width_m is None or self.height_m is None:
                raise ValueError(
                    f"{self.type} benötigt 'width_m' und 'height_m'"
                )
        return self

    @property
    def area_m2(self) -> float:
        """Berechnet die Fläche aus Breite × Höhe."""
        if self.width_m is not None and self.height_m is not None:
            return self.width_m * self.height_m
        return 0.0


class Ventilation(BaseModel):
    air_change_1_h: float = Field(default=0.5, ge=0.0, description="Luftwechsel n in 1/h")


class Area(BaseModel):
    model_config = {"frozen": True}

    length_m: float = Field(ge=0)
    width_m: float = Field(ge=0)

    @property
    def area_m2(self) -> float:
        return self.length_m * self.width_m


class Wall(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    orientation: str = Field(description="Richtung/Bezeichnung (z.B. Nord, Ost, Süd 1, West 2)")
    length_m: float = Field(gt=0, description="Wandlänge in m")
    construction: Construction = Field(description="Wandkonstruktion aus Katalog")
    windows: list[Element] = Field(default_factory=list, description="Fenster in dieser Wand")
    doors: list[Element] = Field(default_factory=list, description="Türen in dieser Wand")
    left_wall: Construction = Field(description="Linke Nachbarwand (Bauteil aus Katalog)")
    right_wall: Construction = Field(description="Rechte Nachbarwand (Bauteil aus Katalog)")


class Room(BaseModel):
    name: str
    areas: list[Area] | None = Field(
        default=None,
        description="Raumgrundriss als Summe mehrerer Rechtecke (jeweils Länge×Breite).",
    )
    height_m: float = Field(gt=0)
    room_temperature: float = Field(default=20.0, description="Raumtemperatur in °C")
    walls: list[Wall] = Field(default_factory=list, description="Wände des Raums")
    floor: Element | None = Field(default=None, description="Bodenkonstruktion")
    ceiling: Element | None = Field(default=None, description="Deckenkonstruktion")
    ventilation: Ventilation = Field(default_factory=Ventilation)
    floor_plan_image: str | None = Field(default=None, description="Base64-kodiertes Grundrissbild")

    @property
    def floor_area_m2(self) -> float:
        if not self.areas:
            return 0.0
        return sum(r.area_m2 for r in self.areas)

    @property
    def volume_m3(self) -> float:
        return self.floor_area_m2 * self.height_m

    @property
    def elements(self) -> list[Element]:
        """Gibt alle Bauelemente (Wände, Fenster, Türen, Boden, Decke) des Raums zurück."""
        result: list[Element] = []

        # Sammle alle Fenster und Türen aus allen Wänden
        for wall in self.walls:
            result.extend(wall.windows)
            result.extend(wall.doors)

        # Füge Boden und Decke hinzu, falls vorhanden
        if self.floor is not None:
            result.append(self.floor)
        if self.ceiling is not None:
            result.append(self.ceiling)

        return result


class Building(BaseModel):
    name: str
    outside_temperatur: float = Field(default=-10.0, description="Normaußentemperatur in °C")
    construction_catalog: list[Construction] = Field(default_factory=list, description="Bauteilkatalog")
    rooms: list[Room] = Field(default_factory=list)
