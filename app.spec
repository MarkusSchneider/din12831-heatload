# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller Spezifikation für DIN 12831 Heizlast App."""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# Streamlit-Daten und Metadaten sammeln
streamlit_data = collect_data_files("streamlit")
streamlit_hidden = collect_submodules("streamlit")
streamlit_metadata = copy_metadata("streamlit")

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        # JSON-Datei mit einpacken
        ('building_data.json', '.'),
        # Streamlit-Assets und Metadaten
        *streamlit_data,
        *streamlit_metadata,
    ],
    hiddenimports=[
        'streamlit',
        'streamlit.runtime.scriptrunner.magic_funcs',
        'pydantic',
        'pydantic.json_schema',
        'pydantic_core',
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
