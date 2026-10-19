"""Build the current Pygame source into release/AntarcticPenguin.exe."""

from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / "pygame"
BUILD = ROOT / "build" / "desktop"
RELEASE = ROOT / "release"


def main() -> None:
    try:
        import PyInstaller.__main__
    except ImportError as error:
        raise SystemExit(
            "PyInstaller가 필요합니다. "
            "python -m pip install -r requirements-build.txt 를 먼저 실행하세요."
        ) from error

    shutil.rmtree(BUILD, ignore_errors=True)
    RELEASE.mkdir(exist_ok=True)
    executable = RELEASE / "AntarcticPenguin.exe"
    executable.unlink(missing_ok=True)
    separator = ";" if sys.platform == "win32" else ":"
    PyInstaller.__main__.run([
        str(GAME / "main.py"),
        "--name=AntarcticPenguin",
        "--onefile",
        "--windowed",
        "--clean",
        f"--distpath={RELEASE}",
        f"--workpath={BUILD / 'work'}",
        f"--specpath={BUILD}",
        f"--paths={GAME}",
        f"--add-data={GAME / 'data'}{separator}data",
    ])
    if not executable.exists():
        raise RuntimeError("실행 파일 생성에 실패했습니다.")
    print(f"Desktop game written to {executable}")


if __name__ == "__main__":
    main()
