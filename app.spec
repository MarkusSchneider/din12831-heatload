# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller Spezifikation für DIN 12831 Heizlast App."""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# Streamlit-Daten und Metadaten sammeln
streamlit_data = collect_data_files("streamlit")
streamlit_hidden = collect_submodules("streamlit")
streamlit_metadata = copy_metadata("streamlit")

# Zusätzliche Metadaten für andere Packages
try:
    altair_metadata = copy_metadata("altair")
except Exception:
    altair_metadata = []

try:
    click_metadata = copy_metadata("click")
except Exception:
    click_metadata = []

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Main app script
        ('app.py', '.'),
        # Source package
        ('src/', 'src/'),
        # Streamlit-Assets und Metadaten
        *streamlit_data,
        *streamlit_metadata,
        *altair_metadata,
        *click_metadata,
    ],
    hiddenimports=[
        'streamlit',
        'streamlit.web.cli',
        'streamlit.runtime.scriptrunner.magic_funcs',
        'pydantic',
        'pydantic.json_schema',
        'pydantic_core',
        'click',
        'validators',
        *streamlit_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'PIL',
        'tkinter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='din12831-heatload',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
