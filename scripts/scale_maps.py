"""Scale map images to 1.5x resolution."""

from pathlib import Path

from PIL import Image

SCALE_FACTOR = 1.5
MAPS_DIR = Path(__file__).parent.parent / "src" / "maps"

# Border art relies on hard colour boundaries, so it must not be interpolated.
TASKS = (
    ("map-border.png", "map-border-1.5x.png", Image.Resampling.NEAREST),
    ("map-terrain.png", "map-terrain-1.5x.png", Image.Resampling.LANCZOS),
)


def scale_images() -> None:
    for source_name, target_name, resample in TASKS:
        source = MAPS_DIR / source_name
        target = MAPS_DIR / target_name

        with Image.open(source) as image:
            new_size = (
                round(image.width * SCALE_FACTOR),
                round(image.height * SCALE_FACTOR),
            )
            image.resize(new_size, resample).save(target)

        print(
            f"{source_name} {image.width}x{image.height} -> "
            f"{target_name} {new_size[0]}x{new_size[1]} ({resample.name})"
        )

if __name__ == "__main__":
    scale_images()
