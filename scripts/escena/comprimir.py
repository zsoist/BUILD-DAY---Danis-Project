#!/usr/bin/env python3
"""Paleta de 96 colores + alfa binaria + WebP sin pérdida: el pixel art queda
nítido y pesa ~3 veces menos.  uv run python scripts/escena/comprimir.py <archivos...>"""
import sys
from PIL import Image

for f in sys.argv[1:]:
    im = Image.open(f).convert("RGBA")
    a = im.getchannel("A").point(lambda v: 255 if v > 127 else 0)
    q = im.convert("RGB").quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
    q.putalpha(a)
    q.save(f, "WEBP", lossless=True, method=6)
