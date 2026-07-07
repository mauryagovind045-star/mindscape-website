#!/usr/bin/env python3
"""
optimize_images.py — resize + compress property photos for the web.

Processes every .jpg/.jpeg/.png in a folder (in place, overwriting) so each
image is at most MAX_WIDTH wide and saved as progressive JPEG at QUALITY.
Keeps files small and fast-loading for the listing pages.

Usage:
    python3 tools/optimize_images.py assets/properties/<slug>
    python3 tools/optimize_images.py assets/properties/<slug> 1600 82

Requires Pillow:  pip3 install pillow
"""

import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  pip3 install pillow")

MAX_WIDTH = 1600
QUALITY = 82
EXTS = (".jpg", ".jpeg", ".png")


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 tools/optimize_images.py <folder> [max_width] [quality]")
    folder = sys.argv[1]
    max_width = int(sys.argv[2]) if len(sys.argv) > 2 else MAX_WIDTH
    quality = int(sys.argv[3]) if len(sys.argv) > 3 else QUALITY

    if not os.path.isdir(folder):
        sys.exit(f"Not a folder: {folder}")

    files = [f for f in sorted(os.listdir(folder)) if f.lower().endswith(EXTS)]
    if not files:
        print("No images found.")
        return

    for name in files:
        src = os.path.join(folder, name)
        stem = os.path.splitext(name)[0]
        dst = os.path.join(folder, stem + ".jpg")
        im = Image.open(src).convert("RGB")
        if im.width > max_width:
            im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
        im.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)
        if dst != src:            # was a .png/.jpeg — remove the original
            os.remove(src)
        kb = os.path.getsize(dst) // 1024
        print(f"  {stem}.jpg  {im.width}x{im.height}  {kb} KB")

    print(f"Optimized {len(files)} image(s) in {folder}")


if __name__ == "__main__":
    main()
