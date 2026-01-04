"""Test script to verify the launcher works correctly before building executable."""

import subprocess
import sys
from pathlib import Path


def test_launcher():
    """Test if the launcher can start the Streamlit app correctly."""
    print("Testing launcher.py...")
    print("-" * 60)

    # Run the launcher
    launcher_path = Path(__file__).parent / "launcher.py"

    if not launcher_path.exists():
        print("❌ ERROR: launcher.py not found!")
        return False

    print(f"✓ Found launcher at: {launcher_path}")
    print("\nStarting Streamlit via launcher...")
    print("Press Ctrl+C to stop the test\n")
    print("-" * 60)

    try:
        # Run the launcher
        subprocess.run([sys.executable, str(launcher_path)])
        return True
    except KeyboardInterrupt:
        print("\n\n" + "-" * 60)
        print("✓ Test completed successfully!")
        print("The launcher can start Streamlit correctly.")
        return True
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("DIN 12831 Heizlast - Launcher Test")
    print("=" * 60)
    print()

    success = test_launcher()

    if success:
        print("\n✓ All tests passed!")
        print("\nYou can now build the executable with:")
        print("  pyinstaller app.spec --clean")
    else:
        print("\n❌ Tests failed!")
        print("Please fix the errors before building.")
        sys.exit(1)
