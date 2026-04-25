# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

pedalboard_datas, pedalboard_binaries, pedalboard_hiddenimports = collect_all("pedalboard")
pedalboard_native_datas, pedalboard_native_binaries, pedalboard_native_hiddenimports = collect_all("pedalboard_native")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=pedalboard_binaries + pedalboard_native_binaries,
    datas=[('pyssp\\assets', 'pyssp\\assets'), ('docs\\build\\html', 'docs\\build\\html')] + pedalboard_datas + pedalboard_native_datas,
    hiddenimports=pedalboard_hiddenimports + pedalboard_native_hiddenimports + ['pedalboard_native'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pySSP_debug',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['pyssp\\assets\\app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pySSP_debug',
)
