"""Testet die neuen Element-Dimensionen (nur Breite × Höhe, keine direkte Flächeneingabe)"""

from src.din12831.models import Element, Construction, ConstructionType

# Erstelle eine Fenster-Konstruktion
window_construction = Construction(
    name="Test-Fenster",
    element_type=ConstructionType.WINDOW,
    u_value_w_m2k=1.3
)

# Test 1: Fenster mit Breite und Höhe
print("Test 1: Fenster mit Breite × Höhe")
window1 = Element(
    type="window",
    name="Fenster 1",
    construction=window_construction,
    width_m=1.2,
    height_m=1.5
)
print(f"  Breite: {window1.width_m} m")
print(f"  Höhe: {window1.height_m} m")
print(f"  Berechnete Fläche: {window1.area_m2:.2f} m²")
print(f"  ✓ Test erfolgreich!\n")

# Test 2: Tür mit Breite und Höhe
door_construction = Construction(
    name="Test-Tür",
    element_type=ConstructionType.DOOR,
    u_value_w_m2k=1.4
)

print("Test 2: Tür mit Breite × Höhe")
door1 = Element(
    type="door",
    name="Tür 1",
    construction=door_construction,
    width_m=1.0,
    height_m=2.1
)
print(f"  Breite: {door1.width_m} m")
print(f"  Höhe: {door1.height_m} m")
print(f"  Berechnete Fläche: {door1.area_m2:.2f} m²")
print(f"  ✓ Test erfolgreich!\n")

# Test 3: Boden/Decke ohne Dimensionen (erlaubt)
floor_construction = Construction(
    name="Test-Boden",
    element_type=ConstructionType.FLOOR,
    u_value_w_m2k=1.0
)

print("Test 3: Boden ohne Dimensionen (erlaubt für floor/ceiling)")
floor1 = Element(
    type="floor",
    name="Boden 1",
    construction=floor_construction
)
print(f"  Fläche: {floor1.area_m2:.2f} m² (0.0 ist OK für Boden/Decke)")
print(f"  ✓ Test erfolgreich!\n")

# Test 4: Fehler bei fehlenden Dimensionen für Fenster
print("Test 4: Validierung - Fenster ohne Dimensionen sollte fehlschlagen")
try:
    window_invalid = Element(
        type="window",
        name="Ungültiges Fenster",
        construction=window_construction
    )
    print("  ✗ Test fehlgeschlagen - Validierung hat nicht gegriffen!")
except ValueError as e:
    print(f"  ✓ Erwarteter Fehler: {e}\n")

# Test 5: Fehler bei nur einer Dimension
print("Test 5: Validierung - Fenster mit nur Breite sollte fehlschlagen")
try:
    window_invalid2 = Element(
        type="window",
        name="Ungültiges Fenster 2",
        construction=window_construction,
        width_m=1.2
    )
    print("  ✗ Test fehlgeschlagen - Validierung hat nicht gegriffen!")
except ValueError as e:
    print(f"  ✓ Erwarteter Fehler: {e}\n")

print("Alle Tests abgeschlossen!")
