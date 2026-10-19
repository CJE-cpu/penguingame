"""Losslessly package right-sized PNG sources for faster native/web startup."""
from pathlib import Path
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "pygame" / "data"

# These sources are sliced or scaled down at runtime. The target sizes retain
# at least 2x the largest on-screen sprite dimension while greatly reducing
# browser download, PNG decode and per-launch scaling work.
TARGETS = {
    "adult-motion-atlas-v2.png": (720, 665),
    "baby-motion-atlas-v2.png": (720, 576),
    "enemy-motion-atlas-v2.png": (724, 543),
    "fish-motion-atlas-v2.png": (724, 543),
    "adventure-objects-atlas-v2.png": (724, 543),
    "antarctic-ice-shelf-tile-v3.png": (1080, 360),
    "shield-potion.png": (256, 256),
}


def optimize(path: Path, maximum: tuple[int, int]) -> tuple[int, int]:
    image = Image.open(path).convert("RGBA")
    before = path.stat().st_size
    image.thumbnail(maximum, Image.Resampling.LANCZOS)
    image.save(path, "PNG", optimize=True, compress_level=9)
    return before, path.stat().st_size


def main() -> None:
    before_total = after_total = 0
    for name, maximum in TARGETS.items():
        before, after = optimize(DATA / name, maximum)
        before_total += before
        after_total += after
        print(f"{name}: {before // 1024} KB -> {after // 1024} KB")
    # The portfolio collection uses the same shield artwork.
    web_shield = ROOT / "web" / "public" / "assets" / "shield-potion.png"
    web_shield.write_bytes((DATA / "shield-potion.png").read_bytes())
    print(f"Total: {before_total // 1024} KB -> {after_total // 1024} KB")


if __name__ == "__main__":
    main()
