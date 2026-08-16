"""CIELAB color conversion and tone-palette generation.

No third-party dependencies: pure Python implementations of the sRGB <-> CIELAB
round trip (D65 reference white), plus a helper that builds a perceptually
even "tone" palette (constant hue, stepped lightness) from a single seed color.

CIELAB is useful here because equal steps in L* look evenly spaced to the eye,
and a color's hue/chroma (a*, b*) can be held fixed while only lightness
changes -- which is exactly what "같은 색조, 다른 명도" (same tone, different
lightness) tints/shades require. Plain RGB or HSL interpolation does not have
that property.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# D65 reference white, 0-1 scale (matches the sRGB matrix below).
_WHITE = (0.9504559, 1.0, 1.0890578)

_SRGB_TO_XYZ = (
    (0.4124564, 0.3575761, 0.1804375),
    (0.2126729, 0.7151522, 0.0721750),
    (0.0193339, 0.1191920, 0.9503041),
)

_XYZ_TO_SRGB = (
    (3.2404542, -1.5371385, -0.4985314),
    (-0.9692660, 1.8760108, 0.0415560),
    (0.0556434, -0.2040259, 1.0572252),
)

_EPS = 216 / 24389  # (6/29)**3
_KAPPA = 24389 / 27  # (29/3)**3


@dataclass(frozen=True)
class Lab:
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


def _f(t: float) -> float:
    return t ** (1 / 3) if t > _EPS else (_KAPPA * t + 16) / 116


def _f_inv(t: float) -> float:
    t3 = t ** 3
    return t3 if t3 > _EPS else (116 * t - 16) / _KAPPA


def rgb_to_lab(rgb: tuple[int, int, int]) -> Lab:
    r, g, b = (_srgb_channel_to_linear(c) for c in rgb)
    xr, yr, zr = _SRGB_TO_XYZ
    X = xr[0] * r + xr[1] * g + xr[2] * b
    Y = yr[0] * r + yr[1] * g + yr[2] * b
    Z = zr[0] * r + zr[1] * g + zr[2] * b

    fx = _f(X / _WHITE[0])
    fy = _f(Y / _WHITE[1])
    fz = _f(Z / _WHITE[2])

    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b_ = 200 * (fy - fz)
    return Lab(L, a, b_)


def lab_to_rgb(lab: Lab) -> tuple[int, int, int]:
    fy = (lab.L + 16) / 116
    fx = fy + lab.a / 500
    fz = fy - lab.b / 200

    X = _f_inv(fx) * _WHITE[0]
    Y = _f_inv(fy) * _WHITE[1]
    Z = _f_inv(fz) * _WHITE[2]

    xr, yr, zr = _XYZ_TO_SRGB
    r_lin = xr[0] * X + xr[1] * Y + xr[2] * Z
    g_lin = yr[0] * X + yr[1] * Y + yr[2] * Z
    b_lin = zr[0] * X + zr[1] * Y + zr[2] * Z

    return (
        round(_linear_channel_to_srgb(r_lin)),
        round(_linear_channel_to_srgb(g_lin)),
        round(_linear_channel_to_srgb(b_lin)),
    )


def hex_to_lab(hex_str: str) -> Lab:
    return rgb_to_lab(hex_to_rgb(hex_str))


def lab_to_hex(lab: Lab, *, clamp: bool = True) -> str:
    r, g, b = lab_to_rgb(lab)
    if not clamp and not all(0 <= c <= 255 for c in (r, g, b)):
        raise ValueError(f"Lab{(lab.L, lab.a, lab.b)} is outside the sRGB gamut")
    return rgb_to_hex((r, g, b))


def _in_gamut(lab: Lab) -> bool:
    r, g, b = lab_to_rgb(lab)
    return all(0 <= c <= 255 for c in (r, g, b))


def _lab_from_lch(L: float, C: float, h_deg: float) -> Lab:
    h = math.radians(h_deg)
    return Lab(L, C * math.cos(h), C * math.sin(h))


def gamut_map(L: float, C: float, h_deg: float) -> Lab:
    """Find the largest chroma <= C at (L, h) that stays inside the sRGB gamut."""
    lab = _lab_from_lch(L, C, h_deg)
    if C <= 0 or _in_gamut(lab):
        return lab
    lo, hi = 0.0, C
    for _ in range(24):
        mid = (lo + hi) / 2
        if _in_gamut(_lab_from_lch(L, mid, h_deg)):
            lo = mid
        else:
            hi = mid
    return _lab_from_lch(L, lo, h_deg)


def generate_tone_palette(
    seed_hex: str,
    steps: int = 6,
    l_min: float = 12.0,
    l_max: float = 94.0,
) -> list[dict]:
    """Build a same-hue, stepped-lightness tone palette from a seed color.

    Hue (h) is held fixed at the seed's hue. Chroma is taken from the seed
    but tapered/gamut-mapped near black and white, since very dark or very
    light sRGB colors cannot carry much chroma. Returns a list of dicts
    (darkest -> lightest), each with L*, a*, b*, chroma, hue, and hex.
    """
    if steps < 2:
        raise ValueError("steps must be >= 2")
    seed_lab = hex_to_lab(seed_hex)
    hue = seed_lab.hue
    base_chroma = seed_lab.chroma

    palette = []
    for i in range(steps):
        t = i / (steps - 1)
        L = l_min + t * (l_max - l_min)
        # Taper chroma toward the ends of the lightness range (0 and 100)
        # so tints/shades stay plausible instead of clipping hard.
        taper = math.sin(math.pi * (L / 100.0))
        target_c = base_chroma * taper
        lab = gamut_map(L, target_c, hue)
        palette.append(
            {
                "L": round(lab.L, 2),
                "a": round(lab.a, 2),
                "b": round(lab.b, 2),
                "chroma": round(lab.chroma, 2),
                "hue": round(lab.hue, 2),
                "hex": lab_to_hex(lab),
            }
        )
    return palette
