"""CLI for building an OKLab tone palette and applying it to a PowerPoint file.

Subcommands:
  palette   Print a tone palette (OKLab + hex) computed from one seed color.
  theme     Write the palette into a .pptx theme color scheme (dk1/lt1/dk2/lt2/
            accent1-6/hlink/folHlink), so every slide that follows the theme
            picks it up.
  swatches  Generate a small demo .pptx with the palette drawn as labeled
            rectangles, so you can see the tones without touching theme colors.
  gradient  Fill an existing shape (matched by name) with a linear gradient
            built from the tone palette.

If --color2 is given, the palette interpolates straight from --color to
--color2 through OKLab (a "color A to color B" gradient, hue included).
Otherwise it builds a same-hue tints/shades ramp from --color alone.
"""

from __future__ import annotations

import argparse
import sys

from color_oklab import generate_tone_palette, interpolate_tone_palette

_ROLE_ORDER = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6"]


def _build_palette(args: argparse.Namespace) -> list[dict]:
    if args.color2:
        return interpolate_tone_palette(args.color, args.color2, steps=args.steps)
    return generate_tone_palette(args.color, steps=args.steps, l_min=args.l_min, l_max=args.l_max)


def _print_palette(palette: list[dict]) -> None:
    print(f"{'role':<8} {'hex':<8} {'L':>7} {'a':>7} {'b':>7} {'C':>7} {'h(deg)':>7}")
    for i, c in enumerate(palette):
        role = _ROLE_ORDER[i] if i < len(_ROLE_ORDER) else f"tone{i}"
        print(f"{role:<8} #{c['hex']:<7} {c['L']:>7.3f} {c['a']:>7.3f} {c['b']:>7.3f} {c['chroma']:>7.3f} {c['hue']:>7}")


def cmd_palette(args: argparse.Namespace) -> None:
    _print_palette(_build_palette(args))


def cmd_theme(args: argparse.Namespace) -> None:
    from lxml import etree
    from pptx import Presentation
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    from pptx.oxml.ns import qn

    palette = _build_palette(args)
    hexes = [c["hex"] for c in palette]

    prs = Presentation(args.template) if args.template else Presentation()
    master_part = prs.slide_masters[0].part
    theme_part = master_part.part_related_by(RT.THEME)

    # The theme part is a generic (non-XML-aware) opc Part in python-pptx, so
    # we parse/edit/reserialize its blob directly rather than going through
    # an `.element` property.
    theme_root = etree.fromstring(theme_part.blob)
    clr_scheme = theme_root.find(f".//{qn('a:themeElements')}/{qn('a:clrScheme')}")
    if clr_scheme is None:
        raise SystemExit("could not find a:clrScheme in the theme part")

    role_tags = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6",
                 "hlink", "folHlink"]
    # Assign darkest tones to dk1/dk2, lightest to lt1/lt2, remaining spread
    # across accents (cycling if there are fewer palette steps than accents),
    # and mid-tones to the hyperlink colors.
    role_hex = {}
    role_hex["dk1"] = hexes[0]
    role_hex["lt1"] = hexes[-1]
    role_hex["dk2"] = hexes[min(1, len(hexes) - 1)]
    role_hex["lt2"] = hexes[max(len(hexes) - 2, 0)]
    accent_slots = ["accent1", "accent2", "accent3", "accent4", "accent5", "accent6"]
    for i, slot in enumerate(accent_slots):
        role_hex[slot] = hexes[i % len(hexes)]
    mid = hexes[len(hexes) // 2]
    role_hex["hlink"] = mid
    role_hex["folHlink"] = hexes[max(len(hexes) // 2 - 1, 0)]

    for tag in role_tags:
        node = clr_scheme.find(qn(f"a:{tag}"))
        if node is None:
            continue
        for child in list(node):
            node.remove(child)
        srgb = node.makeelement(qn("a:srgbClr"), {"val": role_hex[tag]})
        node.append(srgb)

    theme_part.blob = etree.tostring(theme_root, xml_declaration=True, encoding="UTF-8", standalone=True)

    prs.save(args.out)
    print(f"wrote theme with tone palette from #{args.color.lstrip('#').upper()} -> {args.out}")
    for tag in role_tags:
        print(f"  {tag:<9} #{role_hex[tag]}")


_FILL_TAGS = ["noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill"]
_SPPR_PRE_FILL_TAGS = ["xfrm", "custGeom", "prstGeom"]


def _set_gradient_fill(sp_element, hexes: list[str], angle_deg: float) -> None:
    """Replace a <p:sp>'s fill with a linear a:gradFill built from `hexes`."""
    from pptx.oxml.ns import qn

    sp_pr = sp_element.find(qn("p:spPr"))
    if sp_pr is None:
        raise ValueError("shape has no spPr element")

    for tag in _FILL_TAGS:
        existing = sp_pr.find(qn(f"a:{tag}"))
        if existing is not None:
            sp_pr.remove(existing)

    grad_fill = sp_pr.makeelement(qn("a:gradFill"), {"flip": "none", "rotWithShape": "1"})
    gs_lst = grad_fill.makeelement(qn("a:gsLst"), {})
    grad_fill.append(gs_lst)
    n = len(hexes)
    for i, hex_val in enumerate(hexes):
        pos = round(i / (n - 1) * 100000)
        gs = gs_lst.makeelement(qn("a:gs"), {"pos": str(pos)})
        srgb = gs.makeelement(qn("a:srgbClr"), {"val": hex_val})
        gs.append(srgb)
        gs_lst.append(gs)
    lin = grad_fill.makeelement(qn("a:lin"), {"ang": str(round(angle_deg * 60000)), "scaled": "1"})
    grad_fill.append(lin)

    insert_at = 0
    for i, child in enumerate(sp_pr):
        if etree_localname(child) in _SPPR_PRE_FILL_TAGS:
            insert_at = i + 1
    sp_pr.insert(insert_at, grad_fill)


def etree_localname(element) -> str:
    from lxml import etree

    return etree.QName(element.tag).localname


def cmd_gradient(args: argparse.Namespace) -> None:
    from pptx import Presentation

    palette = _build_palette(args)
    hexes = [c["hex"] for c in palette]

    prs = Presentation(args.template)
    matches = []
    for slide_index, slide in enumerate(prs.slides):
        if args.slide is not None and slide_index != args.slide:
            continue
        for shape in slide.shapes:
            if shape.name == args.shape:
                matches.append((slide_index, shape))

    if not matches:
        raise SystemExit(f"no shape named {args.shape!r} found" + ("" if args.slide is None else f" on slide {args.slide}"))

    for slide_index, shape in matches:
        _set_gradient_fill(shape._element, hexes, args.angle)
        print(f"slide {slide_index}: applied gradient to {shape.name!r}")

    prs.save(args.out)
    src = f"#{args.color.lstrip('#').upper()}"
    if args.color2:
        src += f" -> #{args.color2.lstrip('#').upper()}"
    print(f"wrote gradient from {src} ({args.steps} steps, {args.angle} deg) -> {args.out}")
    _print_palette(palette)


def cmd_swatches(args: argparse.Namespace) -> None:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    palette = _build_palette(args)

    prs = Presentation(args.template) if args.template else Presentation()
    blank_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]
    slide = prs.slides.add_slide(blank_layout)

    title_src = f"#{args.color.lstrip('#').upper()}"
    if args.color2:
        title_src += f" -> #{args.color2.lstrip('#').upper()}"
    title_box = slide.shapes.add_textbox(Inches(0.4), Inches(0.3), Inches(9.2), Inches(0.6))
    tf = title_box.text_frame
    tf.text = f"OKLab tone palette from {title_src}"
    tf.paragraphs[0].font.size = Pt(24)
    tf.paragraphs[0].font.bold = True

    n = len(palette)
    margin = Inches(0.4)
    top = Inches(1.2)
    height = Inches(4.2)
    total_width = Inches(9.2)
    gap = Inches(0.12)
    box_width = (total_width - gap * (n - 1)) / n

    for i, c in enumerate(palette):
        left = margin + i * (box_width + gap)
        rect = slide.shapes.add_shape(1, left, top, box_width, height)  # 1 = MSO_SHAPE.RECTANGLE
        rect.fill.solid()
        rect.fill.fore_color.rgb = RGBColor.from_string(c["hex"])
        rect.line.color.rgb = RGBColor.from_string("000000")
        rect.line.width = Pt(0.5)

        label_box = slide.shapes.add_textbox(left, top + height + Inches(0.05), box_width, Inches(0.8))
        ltf = label_box.text_frame
        ltf.word_wrap = True
        p0 = ltf.paragraphs[0]
        p0.text = f"#{c['hex']}"
        p0.alignment = PP_ALIGN.CENTER
        p0.font.size = Pt(12)
        p0.font.bold = True
        p1 = ltf.add_paragraph()
        p1.text = f"L{c['L']:.2f} a{c['a']:.2f} b{c['b']:.2f}"
        p1.alignment = PP_ALIGN.CENTER
        p1.font.size = Pt(10)

    prs.save(args.out)
    print(f"wrote {n}-step swatch deck -> {args.out}")
    _print_palette(palette)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("color", help="seed color as a hex string, e.g. #2E86AB")
        p.add_argument(
            "--color2",
            default=None,
            help="if set, interpolate straight through OKLab from `color` to `color2` "
            "(e.g. red to yellow) instead of building a same-hue tints/shades ramp; "
            "--l-min/--l-max are ignored in this mode",
        )
        p.add_argument("--steps", type=int, default=6, help="number of tone steps (default: 6)")
        p.add_argument("--l-min", type=float, default=0.12, help="minimum OKLab L, 0-1, single-color mode only (default: 0.12)")
        p.add_argument("--l-max", type=float, default=0.94, help="maximum OKLab L, 0-1, single-color mode only (default: 0.94)")

    p_palette = sub.add_parser("palette", help="print a tone palette")
    add_common(p_palette)
    p_palette.set_defaults(func=cmd_palette)

    p_theme = sub.add_parser("theme", help="apply the palette to a .pptx theme color scheme")
    add_common(p_theme)
    p_theme.add_argument("--template", help="existing .pptx to start from (default: blank presentation)")
    p_theme.add_argument("--out", required=True, help="output .pptx path")
    p_theme.set_defaults(func=cmd_theme)

    p_swatches = sub.add_parser("swatches", help="generate a demo .pptx showing the palette as swatches")
    add_common(p_swatches)
    p_swatches.add_argument("--template", help="existing .pptx to add the swatch slide to")
    p_swatches.add_argument("--out", required=True, help="output .pptx path")
    p_swatches.set_defaults(func=cmd_swatches)

    p_gradient = sub.add_parser("gradient", help="fill an existing shape with a tone-palette gradient")
    add_common(p_gradient)
    p_gradient.add_argument("--template", required=True, help="existing .pptx containing the shape to recolor")
    p_gradient.add_argument("--shape", required=True, help="exact shape name to fill, e.g. '직사각형 2'")
    p_gradient.add_argument("--slide", type=int, default=None, help="0-based slide index (default: all slides)")
    p_gradient.add_argument("--angle", type=float, default=45.0, help="gradient angle in degrees (default: 45)")
    p_gradient.add_argument("--out", required=True, help="output .pptx path")
    p_gradient.set_defaults(func=cmd_gradient)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
