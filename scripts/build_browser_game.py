"""Build the Pygame project for the website without packaging local environments."""

from pathlib import Path
import os
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / "pygame"
STAGE = ROOT / "build" / "browser-game"
OUTPUT = ROOT / "web" / "public" / "game"


def main() -> None:
    shutil.rmtree(STAGE, ignore_errors=True)
    shutil.rmtree(OUTPUT, ignore_errors=True)
    STAGE.mkdir(parents=True)

    for source in GAME.glob("*.py"):
        if source.name != "test_game.py":
            shutil.copy2(source, STAGE / source.name)
    shutil.copytree(GAME / "data", STAGE / "data")
    # Browser builds use the current atlases and PNG assets. Documentation,
    # duplicate GIF exports and superseded atlases only increase download and
    # unzip time.
    for unused in (STAGE / "data").glob("*.gif"):
        unused.unlink()
    for unused in (STAGE / "data").glob("*.md"):
        unused.unlink()
    for name in ("adventure-objects-atlas.png", "antarctic-enemy-variety-atlas.png",
                 "penguin-animation-atlas.png", "penguin-walk-eight-frames-atlas.png",
                 "penguin-fish-ice-sprite-atlas.png"):
        (STAGE / "data" / name).unlink(missing_ok=True)

    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pygbag",
            "--build",
            "--ume_block",
            "0",
            "--title",
            "남극 펭귄의 모험",
            STAGE.name,
        ],
        cwd=STAGE.parent,
        env=env,
        check=True,
    )
    shutil.copytree(STAGE / "build" / "web", OUTPUT)
    # Use the ZIP-based APK in browsers. Some static hosts mark .tar.gz files
    # with Content-Encoding: gzip, causing fetch() to transparently decompress
    # them before Python's tarfile module sees the data.
    for archive in OUTPUT.glob("*.tar.gz"):
        archive.unlink()
    index = OUTPUT / "index.html"
    html = index.read_text(encoding="utf-8")
    build_version = str(max(int(path.stat().st_mtime) for path in GAME.rglob("*") if path.is_file()))
    archive_name = f"browser-game-{build_version}.apk"
    (OUTPUT / "browser-game.apk").rename(OUTPUT / archive_name)
    html = html.replace('data-os="vtx,snd,gui"', 'data-os="gui"')
    html = html.replace(
        "if not platform.window.MM.UME:",
        "if platform.window.config.ume_block and not platform.window.MM.UME:",
    )
    html = html.replace(
        "https://pygame-web.github.io/cdn/0.9.3//browserfs.min.js",
        "https://pygame-web.github.io/archives/0.9/browserfs.min.js",
    )
    # Pygbag's default template uses a 16:9 framebuffer. The game is rendered
    # at 800x600, so that default created a roughly 604px square backing canvas
    # which the browser then stretched, causing blur and extra scaling work.
    html = html.replace('fb_ar   :  1.77', 'fb_ar   :  1.333333')
    html = html.replace('fb_width : "1280"', 'fb_width : "800"')
    html = html.replace('fb_height : "720"', 'fb_height : "600"')
    # The template resizes SDL once more after main.py has already created the
    # 800x600 display. Inside an iframe that late resize chooses the shorter
    # viewport edge and turns the framebuffer into a 596x596 square.
    html = html.replace('    platform.window.window_resize()\n', '    # Keep the native 800x600 SDL framebuffer.\n')
    html = html.replace('            width: 100%;\n            height: 100%;',
                        '            width: 100% !important;\n            height: 100% !important;')
    old_unpack = '''    if platform.window.location.host.find('.itch.zone')>0:
        import zipfile
        async with platform.fopen("browser-game.apk", "rb") as archive:
            with zipfile.ZipFile(archive) as zip_ref:
                zip_ref.extractall(appdir.as_posix())
    else:
        import tarfile
        async with platform.fopen("browser-game.tar.gz", "rb") as archive:
            tar = tarfile.open(fileobj=archive, mode="r:gz")
            tar.extractall(path=appdir.as_posix(), filter='tar')
            tar.close()
'''
    new_unpack = '''    import zipfile
    async with platform.fopen("browser-game.apk", "rb") as archive:
        with zipfile.ZipFile(archive) as zip_ref:
            zip_ref.extractall(appdir.as_posix())
'''
    if old_unpack not in html:
        raise RuntimeError("Pygbag archive loader template changed")
    html = html.replace(old_unpack, new_unpack)
    html = html.replace('"browser-game.apk"', f'"{archive_name}"')
    index.write_text(html, encoding="utf-8")
    print(f"Browser game written to {OUTPUT}")


if __name__ == "__main__":
    main()
