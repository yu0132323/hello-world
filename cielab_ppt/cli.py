"""CLI for building a CIELAB tone palette and applying it to a PowerPoint file.

Subcommands:
  palette   Print a tone palette (Lab + hex) computed from one seed color.
  theme     Write the palette into a .pptx theme color scheme (dk1/lt1/dk2/lt2/
            accent1-6/hlink/folHlink), so every slide that follows the theme
            picks it up.
  swatches  Generate a small demo .pptx with the palette drawn as labeled
            rectangles, so you can see the tones without touching theme colors.
"""

from __future__ import annotations

import argparse
import sys

from color_lab import generate_tone_palette

_ROLE_ORDER = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6"]


def _print_palette(palette: list[dict]) -> None:
    print(f"{'role':<8} {'hex':<8} {'L*':>7} {'a*':>7} {'b*':>7} {'C*':>7} {'h(deg)':>7}")
    for i, c in enumerate(palette):
        role = _ROLE_ORDER[i] if i < len(_ROLE_ORDER) else f"tone{i}"
        print(f"{role:<8} #{c['hex']:<7} {c['L']:>7} {c['a']:>7} {c['b']:>7} {c['chroma']:>7} {c['hue']:>7}")


def cmd_palette(args: argparse.Namespace) -> None:
    palette = generate_tone_palette(args.color, steps=args.steps, l_min=args.l_min, l_max=args.l_max)
    _print_palette(palette)


def cmd_theme(args: argparse.Namespace) -> None:
    from lxml import etree
    from pptx import Presentation
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    from pptx.oxml.ns import qn

    palette = generate_tone_palette(args.color, steps=args.steps, l_min=args.l_min, l_max=args.l_max)
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


def cmd_swatches(args: argparse.Namespace) -> None:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    palette = generate_tone_palette(args.color, steps=args.steps, l_min=args.l_min, l_max=args.l_max)

    prs = Presentation(args.template) if args.template else Presentation()
    blank_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]
    slide = prs.slides.add_slide(blank_layout)

    title_box = slide.shapes.add_textbox(Inches(0.4), Inches(0.3), Inches(9.2), Inches(0.6))
    tf = title_box.text_frame
    tf.text = f"CIELAB tone palette from #{args.color.lstrip('#').upper()}"
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
        p1.text = f"L*{c['L']:.0f} a*{c['a']:.0f} b*{c['b']:.0f}"
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
        p.add_argument("--steps", type=int, default=6, help="number of tone steps, darkest to lightest (default: 6)")
        p.add_argument("--l-min", type=float, default=12.0, help="minimum L* (default: 12)")
        p.add_argument("--l-max", type=float, default=94.0, help="maximum L* (default: 94)")

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

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
