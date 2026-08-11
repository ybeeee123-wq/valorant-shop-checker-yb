from pathlib import Path
import sys

ROOT = Path(SPECPATH)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "backend"))
from version import __version__

parts = tuple(int(value) for value in __version__.split(".")) + (0,) * (4 - len(__version__.split(".")))
version_file = ROOT / "build_version_info.txt"
version_file.write_text(f"""VSVersionInfo(ffi=FixedFileInfo(filevers={parts}, prodvers={parts}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0,0)), kids=[StringFileInfo([StringTable('040904B0',[StringStruct('CompanyName','VALSHOP'),StringStruct('FileDescription','VALSHOP Windows Companion'),StringStruct('FileVersion','{__version__}'),StringStruct('InternalName','VALSHOP'),StringStruct('OriginalFilename','VALSHOP.exe'),StringStruct('ProductName','VALSHOP'),StringStruct('ProductVersion','{__version__}')])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])""", encoding="utf-8")

a = Analysis(
    [str(ROOT / "launcher.py")],
    pathex=[str(ROOT), str(ROOT.parent / "backend")],
    binaries=[],
    datas=[
        (str(ROOT / "assets" / "valshop.ico"), "assets"),
        (str(ROOT / "release_config.json"), "."),
    ],
    hiddenimports=["keyring.backends.Windows", "sqlalchemy.dialects.sqlite", "PySide6.QtSvg"],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=["tkinter"], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="VALSHOP", debug=False,
    bootloader_ignore_signals=False, strip=False, upx=True, console=False,
    icon=str(ROOT / "assets" / "valshop.ico"), version=str(version_file),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="VALSHOP")
