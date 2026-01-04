from __future__ import annotations

from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

# =============================================================================
# Enumerations
# =============================================================================


class ConstructionType(str, Enum):
    """Bauteiltypen für Konstruktionen im Katalog."""

    EXTERNAL_WALL = "external_wall"
    INTERNAL_WALL = "internal_wall"
    CEILING = "ceiling"
    FLOOR = "floor"
    WINDOW = "window"
    DOOR = "door"


class ElementType(str, Enum):
    """Elementtypen für konkrete Bauelemente in Räumen."""

    WINDOW = "window"
    DOOR = "door"
    CEILING = "ceiling"
    FLOOR = "floor"


# =============================================================================
# Hilfsklassen
# =============================================================================


class Temperature(BaseModel):
    """Temperatur-Referenzobjekt für wiederverwendbare Temperaturen."""

    name: str = Field(description="Bezeichnung der Temperatur (z.B. 'Wohnraum', 'Außen', 'Keller')")
    value_celsius: float = Field(description="Temperaturwert in °C")


class Ventilation(BaseModel):
    """
    Lüftungsparameter für einen Raum.

    Definiert die Luftwechselrate für die Berechnung von Lüftungswärmeverlusten nach DIN 12831.
    """

    air_change_1_h: float = Field(default=0.5, ge=0.0, description="Luftwechsel n in 1/h")


class Area(BaseModel):
    """
    Rechteckige Teilfläche eines Raums (Boden/Decke).

    Repräsentiert ein Rechteck mit Netto-Abmessungen (Länge × Breite).
    Wird verwendet für Räume mit komplexen Grundrissen (L-Form, etc.).
    Die Brutto-Fläche wird aus den Wänden des Raums berechnet.
    """

    length_m: float = Field(ge=0)
    width_m: float = Field(ge=0)

    @property
    def area_m2(self) -> float:
        """Berechnet die Netto-Fläche (Länge × Breite)."""
        return self.length_m * self.width_m


# =============================================================================
# Fachliche Klassen
# =============================================================================


class Construction(BaseModel):
    """
    Bauteilkonstruktion mit U-Wert und optionaler Dicke.

    Repräsentiert verschiedene Bauteile wie Außenwände, Innenwände, Fenster, Türen, Böden und Decken.
    Enthält thermische Eigenschaften und Validierung für dickenabhängige Berechnungen.
    """

    name: str
    element_type: ConstructionType = Field(default=ConstructionType.EXTERNAL_WALL, description="Bauteiltyp")
    u_value_w_m2k: float = Field(gt=0, description="U-Wert in W/(m²·K)")
    thickness_m: float | None = Field(default=None, ge=0, description="Dicke (nur für Wand/Decke/Boden)")

    _TYPES_REQUIRING_THICKNESS: ClassVar[set[ConstructionType]] = {
        ConstructionType.EXTERNAL_WALL,
        ConstructionType.INTERNAL_WALL,
        ConstructionType.FLOOR,
        ConstructionType.CEILING,
    }

    @model_validator(mode="after")
    def validate_thickness(self):
        """Validiere, dass Wände, Böden und Decken eine Dicke haben."""
        if self.element_type in Construction._TYPES_REQUIRING_THICKNESS and self.thickness_m is None:
            raise ValueError(f"Construction type '{self.element_type.value}' requires thickness_m to be set")
        return self

    def get_adjacent_thickness(self) -> float:
        """Berechnet die Dicke für angrenzende Bauteil-Berechnungen.

        - Außenwand: volle Dicke
        - Innenwand/Boden/Decke: halbe Dicke

        Returns:
            Dicke des Bauteils in Metern für angrenzende Berechnungen

        Raises:
            ValueError: Wenn Bauteiltyp keine Dickenberechnung unterstützt oder keine Dicke definiert ist
        """
        if self.element_type not in Construction._TYPES_REQUIRING_THICKNESS:
            raise ValueError(
                f"Invalid construction type '{self.element_type.value}' for '{self.name}'. "
                f"Only walls, floors, and ceilings have adjacent thickness."
            )

        if self.thickness_m is None:
            raise ValueError(f"Construction '{self.name}' has no thickness defined")

        if self.element_type == ConstructionType.EXTERNAL_WALL:
            return self.thickness_m
        else:
            return self.thickness_m / 2.0


class Element(BaseModel):
    """
    Einzelnes Bauelement wie Fenster, Tür, Boden oder Decke.

    Repräsentiert ein konkretes Bauteil in einem Raum mit Abmessungen und Verknüpfung zum Konstruktionskatalog.
    Fenster und Türen benötigen Breite und Höhe.
    """

    model_config = ConfigDict(from_attributes=True)

    type: ElementType
    name: str
    construction_name: str = Field(description="Name der Konstruktion aus Katalog")
    width_m: float | None = Field(default=None, gt=0, description="Breite in m")
    height_m: float | None = Field(default=None, gt=0, description="Höhe in m")
    adjacent_temperature_name: str | None = Field(
        default=None, description="Name der Temperatur des angrenzenden Raums/Bereichs (z.B. für Boden/Decke)"
    )

    _TYPES_REQUIRING_DIMENSIONS: ClassVar[set[ElementType]] = {ElementType.WINDOW, ElementType.DOOR}

    @model_validator(mode="after")
    def validate_dimensions(self):
        """Validiere, dass für Fenster und Türen Breite und Höhe angegeben sind."""
        if self.type in Element._TYPES_REQUIRING_DIMENSIONS and (self.width_m is None or self.height_m is None):
            raise ValueError(f"{self.type} benötigt 'width_m' und 'height_m'")
        return self

    @property
    def area_m2(self) -> float:
        """Berechnet die Fläche aus Breite × Höhe."""
        if self.width_m is not None and self.height_m is not None:
            return self.width_m * self.height_m
        return 0.0


class Wall(BaseModel):
    """Wand eines Raums mit Fenstern und Türen.

    Repräsentiert eine Außen- oder Innenwand mit Netto-Abmessungen, Fenstern, Türen
    und Verknüpfungen zu angrenzenden Wänden für Brutto-Längenberechnungen.
    """

    model_config = ConfigDict(from_attributes=True)

    orientation: str = Field(description="Richtung/Bezeichnung (z.B. Nord, Ost, Süd 1, West 2)")
    net_length_m: float = Field(gt=0, description="Netto-Wandlänge (Innenraumlänge) in m")
    construction_name: str = Field(description="Name der Wandkonstruktion aus Katalog")
    windows: list[Element] = Field(default_factory=list, description="Fenster in dieser Wand")
    doors: list[Element] = Field(default_factory=list, description="Türen in dieser Wand")
    left_wall_name: str = Field(description="Name der linken Nachbarwand (Bauteil aus Katalog)")
    right_wall_name: str = Field(description="Name der rechten Nachbarwand (Bauteil aus Katalog)")
    adjacent_room_temperature_name: str | None = Field(
        default=None, description="Name der Temperatur des angrenzenden Raums (nur für Innenwände)"
    )

    def gross_length_m(self, building: Building) -> float:
        """
        Berechnet die Brutto-Wandlänge (Außenmaß).

        Bruttolänge = Nettolänge + linke Wanddicke + rechte Wanddicke
        - Außenwand: volle Dicke wird addiert
        - Innenwand: halbe Dicke wird addiert
        """
        left_thickness = get_adjacent_thickness(building, self.left_wall_name)
        right_thickness = get_adjacent_thickness(building, self.right_wall_name)

        return self.net_length_m + left_thickness + right_thickness

    def gross_area_m2(self, building: Building, gross_height_m: float) -> float:
        """
        Berechnet die Brutto-Wandfläche (Außenmaß).

        Bruttofläche = Bruttolänge × Bruttohöhe
        Die Bruttohöhe sollte von room.gross_height_m(building) übergeben werden.
        """
        gross_length = self.gross_length_m(building)
        return gross_length * gross_height_m


class Room(BaseModel):
    """
    Raum mit allen Bauelementen für Heizlastberechnung.

    Repräsentiert einen Raum mit Grundflächen (Areas), Wänden, Boden, Decke und Lüftungsparametern.
    Berechnet Netto- und Bruttoflächen/-volumina für die Wärmeverlustberechnung nach DIN 12831.
    """

    name: str
    areas: list[Area] = Field(
        default=[],
        description="Raumgrundriss als Summe mehrerer Rechtecke (jeweils Länge×Breite).",
    )
    net_height_m: float = Field(gt=0, description="Netto-Raumhöhe (Innenraumhöhe) in m")
    room_temperature_name: str | None = Field(default=None, description="Name der Raumtemperatur aus Katalog")
    walls: list[Wall] = Field(default_factory=list, description="Wände des Raums")
    floor: Element | None = Field(default=None, description="Bodenkonstruktion")
    ceiling: Element | None = Field(default=None, description="Deckenkonstruktion")
    ventilation: Ventilation = Field(default_factory=Ventilation)

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

    def _get_neighbor_thickness(self, building: Building, wall_name: str | None) -> float:
        """Berechnet die Dicke einer Nachbarwand für Flächenstreifen-Berechnung.

        Innenwände tragen nur mit halber Dicke bei (da sie zwischen zwei Räumen liegen).
        Außenwände tragen mit voller Dicke bei.

        Args:
            building: Building-Objekt für Zugriff auf Konstruktionskatalog
            wall_name: Name der Nachbarwand

        Returns:
            Halbe oder volle Wanddicke in Metern (0.0 wenn wall_name None)
        """
        if not wall_name:
            return 0.0

        construction = building.get_construction_by_name(wall_name)
        if not construction or construction.thickness_m is None:
            return 0.0

        thickness = construction.thickness_m
        if construction.element_type == ConstructionType.INTERNAL_WALL:
            return thickness / 2
        return thickness

    def _calculate_gross_area_m2(self, building: Building) -> float:
        """Berechnet die Brutto-Grundfläche mit Option C Formel.

        Bruttofläche = Nettofläche + Σ (Nettolänge + Dicke_links/2 + Dicke_rechts/2) × Wanddicke

        Für jede Wand wird ein Flächenstreifen berechnet, der die halben Nachbarwanddicken
        einbezieht. So werden Ecken automatisch korrekt erfasst (jede Ecke von zwei Wänden
        je zur Hälfte).

        Die Bruttofläche ist für Boden und Decke identisch, da sie nur von den Wanddicken
        abhängt, nicht von der Dicke des Bodens oder der Decke selbst.

        Args:
            building: Building-Objekt für Zugriff auf Konstruktionskatalog

        Returns:
            Brutto-Grundfläche in m²
        """
        if not self.areas:
            return 0.0

        # Nettofläche als Basis
        net_area = self.floor_area_m2

        # Addiere Flächenstreifen für jede Wand
        for wall in self.walls:
            wall_construction = building.get_construction_by_name(wall.construction_name)
            if not wall_construction or wall_construction.thickness_m is None:
                continue

            thickness = wall_construction.thickness_m

            # Berechne Dicken der Nachbarwände (halbe Dicke bei Innenwänden)
            left_thickness = self._get_neighbor_thickness(building, wall.left_wall_name)
            right_thickness = self._get_neighbor_thickness(building, wall.right_wall_name)

            # Flächenstreifen: (Nettolänge + halbe Nachbardicken) × Wanddicke
            strip_length = wall.net_length_m + left_thickness + right_thickness
            strip_area = strip_length * thickness
            net_area += strip_area

        return net_area

    def gross_floor_area_m2(self, building: Building) -> float:
        """Berechnet die Brutto-Grundfläche des Bodens mit Option C Formel."""
        if not self.floor:
            return 0.0
        return self._calculate_gross_area_m2(building)

    def gross_ceiling_area_m2(self, building: Building) -> float:
        """Berechnet die Brutto-Grundfläche der Decke mit Option C Formel."""
        if not self.ceiling:
            return 0.0
        return self._calculate_gross_area_m2(building)

    @property
    def volume_m3(self) -> float:
        return self.floor_area_m2 * self.net_height_m


class Building(BaseModel):
    """Gebäude mit Katalogen und Räumen.

    Zentrales Objekt für die Heizlastberechnung nach DIN 12831.
    Enthält Temperatur- und Konstruktionskataloge sowie alle Räume des Gebäudes.
    Verwaltet globale Parameter wie Wärmebrückenzuschlag.
    """

    name: str
    temperature_catalog: list[Temperature] = Field(default_factory=list, description="Temperaturkatalog")
    outside_temperature_name: str | None = Field(default=None, description="Name der Normaußentemperatur aus Katalog")
    default_room_temperature_name: str | None = Field(
        default=None, description="Name der Standard-Raumtemperatur aus Katalog"
    )
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


# =============================================================================
# Hilfsfunktionen
# =============================================================================


def get_adjacent_thickness(building: Building, adjacent_name: str) -> float:
    """
    Hilfsfunktion: Berechnet die Dicke eines angrenzenden Bauteils nach Name.
    Diese Funktion kombiniert Katalog-Lookup und Dickenberechnung.

    Args:
        building: Building-Objekt für Zugriff auf Konstruktionskatalog
        adjacent_name: Name des angrenzenden Bauteils (required)

    Returns:
        Dicke des Bauteils in Metern

    Raises:
        ValueError: Wenn Bauteil nicht im Katalog gefunden wird oder Dickenberechnung fehlschlägt
    """
    assert adjacent_name is not None, "adjacent_name cannot be None"

    construction = building.get_construction_by_name(adjacent_name)
    return construction.get_adjacent_thickness()
