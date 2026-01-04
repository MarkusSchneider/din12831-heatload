from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ElementType = Literal["wall", "window", "door", "ceiling", "floor"]


class ConstructionType(str, Enum):
    EXTERNAL_WALL = "external_wall"
    INTERNAL_WALL = "internal_wall"
    CEILING = "ceiling"
    FLOOR = "floor"
    WINDOW = "window"
    DOOR = "door"


class Construction(BaseModel):
    name: str
    element_type: ConstructionType = Field(default=ConstructionType.EXTERNAL_WALL, description="Bauteiltyp")
    u_value_w_m2k: float = Field(gt=0, description="U-Wert in W/(m²·K)")
    thickness_m: float | None = Field(default=None, ge=0, description="Dicke (nur für Wand/Decke/Boden)")


class Temperature(BaseModel):
    """Temperatur-Referenzobjekt für wiederverwendbare Temperaturen."""
    name: str = Field(description="Bezeichnung der Temperatur (z.B. 'Wohnraum', 'Außen', 'Keller')")
    value_celsius: float = Field(description="Temperaturwert in °C")

    def __str__(self) -> str:
        return f"{self.name} ({self.value_celsius:.1f} °C)"


class Element(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: ElementType
    name: str
    construction_name: str = Field(description="Name der Konstruktion aus Katalog")
    width_m: float | None = Field(default=None, gt=0, description="Breite in m")
    height_m: float | None = Field(default=None, gt=0, description="Höhe in m")
    adjacent_temperature_name: str | None = Field(default=None, description="Name der Temperatur des angrenzenden Raums/Bereichs (z.B. für Boden/Decke)")

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
    net_length_m: float = Field(gt=0, description="Netto-Wandlänge (Innenraumlänge) in m")
    construction_name: str = Field(description="Name der Wandkonstruktion aus Katalog")
    windows: list[Element] = Field(default_factory=list, description="Fenster in dieser Wand")
    doors: list[Element] = Field(default_factory=list, description="Türen in dieser Wand")
    left_wall_name: str = Field(description="Name der linken Nachbarwand (Bauteil aus Katalog)")
    right_wall_name: str = Field(description="Name der rechten Nachbarwand (Bauteil aus Katalog)")
    adjacent_room_temperature_name: str | None = Field(default=None, description="Name der Temperatur des angrenzenden Raums (nur für Innenwände)")

    def gross_length_m(self, building: Building) -> float:
        """
        Berechnet die Brutto-Wandlänge (Außenmaß).

        Bruttolänge = Nettolänge + linke Wanddicke + rechte Wanddicke
        - Außenwand: volle Dicke wird addiert
        - Innenwand: halbe Dicke wird addiert
        """
        left_wall = building.get_construction_by_name(self.left_wall_name)
        right_wall = building.get_construction_by_name(self.right_wall_name)

        left_thickness = 0.0
        if left_wall and left_wall.thickness_m is not None:
            left_thickness = (
                left_wall.thickness_m if left_wall.element_type == ConstructionType.EXTERNAL_WALL else left_wall.thickness_m / 2.0
            )

        right_thickness = 0.0
        if right_wall and right_wall.thickness_m is not None:
            right_thickness = (
                right_wall.thickness_m if right_wall.element_type == ConstructionType.EXTERNAL_WALL else right_wall.thickness_m / 2.0
            )

        return self.net_length_m + left_thickness + right_thickness


class Room(BaseModel):
    name: str
    areas: list[Area] | None = Field(
        default=None,
        description="Raumgrundriss als Summe mehrerer Rechtecke (jeweils Länge×Breite).",
    )
    net_height_m: float = Field(gt=0, description="Netto-Raumhöhe (Innenraumhöhe) in m")
    room_temperature_name: str | None = Field(default=None, description="Name der Raumtemperatur aus Katalog")
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

    def gross_height_m(self, building: Building) -> float:
        """Berechnet die Brutto-Raumhöhe (Außenmaß).

        Bruttohöhe = Nettohöhe + Deckendicke
        """
        ceiling_thickness = 0.0
        if self.ceiling and self.ceiling.construction_name:
            ceiling_construction = building.get_construction_by_name(self.ceiling.construction_name)
            if ceiling_construction and ceiling_construction.thickness_m is not None:
                ceiling_thickness = ceiling_construction.thickness_m
        return self.net_height_m + ceiling_thickness

    @property
    def volume_m3(self) -> float:
        return self.floor_area_m2 * self.net_height_m

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
    temperature_catalog: list[Temperature] = Field(default_factory=list, description="Temperaturkatalog")
    outside_temperature_name: str | None = Field(default=None, description="Name der Normaußentemperatur aus Katalog")
    default_room_temperature_name: str | None = Field(default=None, description="Name der Standard-Raumtemperatur aus Katalog")
    construction_catalog: list[Construction] = Field(default_factory=list, description="Bauteilkatalog")
    thermal_bridge_surcharge: float = Field(default=0.05, ge=0, description="Wärmebrückenzuschlag (größer als 0)")
    rooms: list[Room] = Field(default_factory=list)

    def get_temperature_by_name(self, name: str | None) -> Temperature:
        """Holt eine Temperatur aus dem Katalog nach Name."""
        if name is None:
            raise ValueError("Temperature name cannot be None")
        for temp in self.temperature_catalog:
            if temp.name == name:
                return temp
        raise ValueError(f"Temperature '{name}' not found in catalog")

    def get_construction_by_name(self, name: str | None) -> Construction:
        """Holt ein Bauteil aus dem Katalog nach Name."""
        if name is None:
            raise ValueError("Construction name cannot be None")
        for construction in self.construction_catalog:
            if construction.name == name:
                return construction
        raise ValueError(f"Construction '{name}' not found in catalog")

    @property
    def outside_temperature(self) -> Temperature:
        """Gibt die Normaußentemperatur aus dem Katalog zurück."""
        return self.get_temperature_by_name(self.outside_temperature_name)

    @property
    def default_room_temperature(self) -> Temperature:
        """Gibt die Standard-Raumtemperatur aus dem Katalog zurück."""
        return self.get_temperature_by_name(self.default_room_temperature_name)
