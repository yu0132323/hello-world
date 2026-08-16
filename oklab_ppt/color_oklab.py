"""OKLab color conversion and tone-palette generation.

No third-party dependencies: pure Python implementation of the sRGB <-> OKLab
round trip (Björn Ottosson, 2020), plus a helper that builds a perceptually
even "tone" palette (constant hue, stepped lightness) from a single seed color.

OKLab is used here instead of CIELAB because it keeps hue noticeably more
constant while lightness changes -- CIELAB is known to visibly shift hue
(especially blues drifting toward purple) as L* moves, which shows up as a
palette that doesn't quite "match" at the light/dark ends. OKLab's L also
lines up much better with perceived lightness for saturated colors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_LMS_FROM_LINEAR_SRGB = (
    (0.4122214708, 0.5363325363, 0.0514459929),
    (0.2119034982, 0.6806995451, 0.1073969566),
    (0.0883024619, 0.2817188376, 0.6299787005),
)

_OKLAB_FROM_LMS_ = (
    (0.2104542553, 0.7936177850, -0.0040720468),
    (1.9779984951, -2.4285922050, 0.4505937099),
    (0.0259040371, 0.7827717662, -0.8086757660),
)

_LMS_FROM_OKLAB_ = (
    (1.0, 0.3963377774, 0.2158037573),
    (1.0, -0.1055613458, -0.0638541728),
    (1.0, -0.0894841775, -1.2914855480),
)

_LINEAR_SRGB_FROM_LMS = (
    (4.0767416621, -3.3077115913, 0.2309699292),
    (-1.2684380046, 2.6097574011, -0.3413193965),
    (-0.0041960863, -0.7034186147, 1.7076147010),
)


@dataclass(frozen=True)
class Oklab:
    L: float
    a: float
    b: float

    @property
    def chroma(self) -> float:
        return math.hypot(self.a, self.b)

    @property
    def hue(self) -> float:
        """Hue angle in degrees, 0-360."""
        return math.degrees(math.atan2(self.b, self.a)) % 360


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    s = hex_str.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        raise ValueError(f"invalid hex color: {hex_str!r}")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    r, g, b = (max(0, min(255, round(c))) for c in rgb)
    return f"{r:02X}{g:02X}{b:02X}"


def _srgb_channel_to_linear(c: float) -> float:
    c /= 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _linear_channel_to_srgb(c: float) -> float:
    if c <= 0.0031308:
        v = 12.92 * c
    else:
        v = 1.055 * (max(c, 0.0) ** (1 / 2.4)) - 0.055
    return v * 255.0


def _cbrt(x: float) -> float:
    return math.copysign(abs(x) ** (1 / 3), x)


def rgb_to_oklab(rgb: tuple[int, int, int]) -> Oklab:
    r, g, b = (_srgb_channel_to_linear(c) for c in rgb)

    lm = _LMS_FROM_LINEAR_SRGB
    l = lm[0][0] * r + lm[0][1] * g + lm[0][2] * b
    m = lm[1][0] * r + lm[1][1] * g + lm[1][2] * b
    s = lm[2][0] * r + lm[2][1] * g + lm[2][2] * b

    l_, m_, s_ = _cbrt(l), _cbrt(m), _cbrt(s)

    ok = _OKLAB_FROM_LMS_
    L = ok[0][0] * l_ + ok[0][1] * m_ + ok[0][2] * s_
    a = ok[1][0] * l_ + ok[1][1] * m_ + ok[1][2] * s_
    b_ = ok[2][0] * l_ + ok[2][1] * m_ + ok[2][2] * s_
    return Oklab(L, a, b_)


def oklab_to_rgb(lab: Oklab) -> tuple[int, int, int]:
    lm = _LMS_FROM_OKLAB_
    l_ = lm[0][0] * lab.L + lm[0][1] * lab.a + lm[0][2] * lab.b
    m_ = lm[1][0] * lab.L + lm[1][1] * lab.a + lm[1][2] * lab.b
    s_ = lm[2][0] * lab.L + lm[2][1] * lab.a + lm[2][2] * lab.b

    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3

    rg = _LINEAR_SRGB_FROM_LMS
    r_lin = rg[0][0] * l + rg[0][1] * m + rg[0][2] * s
    g_lin = rg[1][0] * l + rg[1][1] * m + rg[1][2] * s
    b_lin = rg[2][0] * l + rg[2][1] * m + rg[2][2] * s

    return (
        round(_linear_channel_to_srgb(r_lin)),
        round(_linear_channel_to_srgb(g_lin)),
        round(_linear_channel_to_srgb(b_lin)),
    )


def hex_to_oklab(hex_str: str) -> Oklab:
    return rgb_to_oklab(hex_to_rgb(hex_str))


def oklab_to_hex(lab: Oklab, *, clamp: bool = True) -> str:
    r, g, b = oklab_to_rgb(lab)
    if not clamp and not all(0 <= c <= 255 for c in (r, g, b)):
        raise ValueError(f"Oklab{(lab.L, lab.a, lab.b)} is outside the sRGB gamut")
    return rgb_to_hex((r, g, b))


def _in_gamut(lab: Oklab) -> bool:
    r, g, b = oklab_to_rgb(lab)
    return all(0 <= c <= 255 for c in (r, g, b))


def _oklab_from_lch(L: float, C: float, h_deg: float) -> Oklab:
    h = math.radians(h_deg)
    return Oklab(L, C * math.cos(h), C * math.sin(h))


def gamut_map(L: float, C: float, h_deg: float) -> Oklab:
    """Find the largest chroma <= C at (L, h) that stays inside the sRGB gamut."""
    lab = _oklab_from_lch(L, C, h_deg)
    if C <= 0 or _in_gamut(lab):
        return lab
    lo, hi = 0.0, C
    for _ in range(24):
        mid = (lo + hi) / 2
        if _in_gamut(_oklab_from_lch(L, mid, h_deg)):
            lo = mid
        else:
            hi = mid
    return _oklab_from_lch(L, lo, h_deg)


def generate_tone_palette(
    seed_hex: str,
    steps: int = 6,
    l_min: float = 0.12,
    l_max: float = 0.94,
) -> list[dict]:
    """Build a same-hue, stepped-lightness tone palette from a seed color.

    Hue (h) is held fixed at the seed's hue. Chroma is taken from the seed
    but tapered/gamut-mapped near black and white, since very dark or very
    light sRGB colors cannot carry much chroma. Returns a list of dicts
    (darkest -> lightest), each with OKLab L, a, b, chroma, hue, and hex.

    L ranges 0-1 in OKLab (0 = black, 1 = white), unlike CIELAB's 0-100 scale.
    """
    if steps < 2:
        raise ValueError("steps must be >= 2")
    seed_lab = hex_to_oklab(seed_hex)
    hue = seed_lab.hue
    base_chroma = seed_lab.chroma

    palette = []
    for i in range(steps):
        t = i / (steps - 1)
        L = l_min + t * (l_max - l_min)
        # Taper chroma toward the ends of the lightness range (0 and 1)
        # so tints/shades stay plausible instead of clipping hard.
        taper = math.sin(math.pi * L)
        target_c = base_chroma * taper
        lab = gamut_map(L, target_c, hue)
        palette.append(
            {
                "L": round(lab.L, 4),
                "a": round(lab.a, 4),
                "b": round(lab.b, 4),
                "chroma": round(lab.chroma, 4),
                "hue": round(lab.hue, 2),
                "hex": oklab_to_hex(lab),
            }
        )
    return palette


def interpolate_tone_palette(hex1: str, hex2: str, steps: int = 6) -> list[dict]:
    """Build a palette by interpolating straight through OKLab between two colors.

    Unlike `generate_tone_palette`, hue is not held fixed -- this is what you
    want for a "color A to color B" gradient (e.g. red to yellow) rather than
    a tints/shades ramp of one color. Interpolating in OKLab (instead of RGB
    or CIELAB) avoids the dull, muddy midpoint that a straight RGB blend of
    two saturated hues tends to produce.
    """
    if steps < 2:
        raise ValueError("steps must be >= 2")
    lab1 = hex_to_oklab(hex1)
    lab2 = hex_to_oklab(hex2)

    palette = []
    for i in range(steps):
        t = i / (steps - 1)
        L = lab1.L + t * (lab2.L - lab1.L)
        a = lab1.a + t * (lab2.a - lab1.a)
        b = lab1.b + t * (lab2.b - lab1.b)
        lab = Oklab(L, a, b)
        if not _in_gamut(lab):
            lab = gamut_map(L, lab.chroma, lab.hue)
        palette.append(
            {
                "L": round(lab.L, 4),
                "a": round(lab.a, 4),
                "b": round(lab.b, 4),
                "chroma": round(lab.chroma, 4),
                "hue": round(lab.hue, 2),
                "hex": oklab_to_hex(lab),
            }
        )
    return palette
