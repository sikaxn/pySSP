# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files

pedalboard_datas, pedalboard_binaries, pedalboard_hiddenimports = collect_all('pedalboard')
pedalboard_native_datas, pedalboard_native_binaries, pedalboard_native_hiddenimports = collect_all('pedalboard_native')

datas = [('pyssp\\assets', 'pyssp\\assets'), ('docs\\build\\html', 'docs\\build\\html'), ('.build_meta\\version.json', '.')]
datas += collect_data_files('imageio_ffmpeg')
datas += pedalboard_datas + pedalboard_native_datas
binaries = pedalboard_binaries + pedalboard_native_binaries
hiddenimports = pedalboard_hiddenimports + pedalboard_native_hiddenimports


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='pySSP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
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
    name='pySSP',
)
