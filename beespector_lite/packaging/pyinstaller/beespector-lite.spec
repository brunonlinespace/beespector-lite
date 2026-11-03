# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules
project_root=Path(SPECPATH).resolve().parents[2]
program_root=project_root/"beespector_lite"
excludes=["PySide2","PySide6","PyQt5","PyQt6.QtPdf","PyQt6.QtPdfWidgets","PyQt6.QtPrintSupport","PyQt6.QtWebEngineCore","PyQt6.QtWebEngineQuick","PyQt6.QtWebEngineWidgets"]
a=Analysis([str(project_root/"main.py")],pathex=[str(project_root)],binaries=[],datas=[(str(program_root/"assets"),"beespector_lite/assets"),(str(program_root/"docs"),"beespector_lite/docs"),(str(program_root/"LICENSE"),"beespector_lite"),(str(program_root/"identity.json"),"beespector_lite")],hiddenimports=collect_submodules("beespector_lite"),hookspath=[],hooksconfig={},runtime_hooks=[],excludes=excludes,noarchive=False,optimize=1)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name="beespector-lite",debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name="beespector-lite")
