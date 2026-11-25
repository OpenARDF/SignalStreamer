"""Draw a printable component locator using the absolute pad locations exported by KiCad."""
import math
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from itertools import product
from xml.sax.saxutils import escape


def coordinates(element):
    return float(element.get("x")), -float(element.get("y"))


def read_ipc(ipc):
    doc = ET.parse(ipc)
    for element in doc.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
    return doc


def read_pads(doc):
    outline = [coordinates(p) for p in doc.find(".//Profile/Polygon")]
    pads = defaultdict(list)
    for pad in doc.findall(".//LayerFeature[@layerRef='F.Cu']/Set/Pad"):
        ref = pad.find("PinRef")
        if ref is not None:
            pads[ref.get("componentRef")].append((ref.get("pin"), *coordinates(pad.find("Location"))))
    return outline, pads


def locator(doc, variant, fitted, svg_path, pdf_path):
    outline, pads = read_pads(doc)
    sections = [
        ("Capacitors", sorted(r for r in fitted if re.fullmatch(r"C\d+", r))),
        ("Diodes and indicators", sorted(r for r in fitted if re.fullmatch(r"D\d+", r))),
        ("Resistors and sensitivity adjustment", sorted(r for r in fitted if r.startswith("R"))),
        ("Windings, BNC and antenna terminals", ["J101", "J102", "J103", "J104", "J105", "L101", "T101"]),
    ]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 1420 1004">',
           '<rect width="1420" height="1004" fill="white"/><g font-family="Arial,sans-serif" fill="#18313a">']

    def text(x, y, value, size, weight="normal"):
        svg.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}">{escape(value)}</text>')

    def circle(x, y, r, fill, stroke):
        svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="{fill}" stroke="{stroke}"/>')

    text(33, 44, f"SignalStreamer 1.2  /  {variant}", 34, "bold")
    legend = ("L101, T101 and J105 are marked on the front. Other kit markings are on the back." if variant == "THT-Kit"
              else "SMD sites, L101, T101 and J105 are marked on the front.")
    text(34, 76, f"Component side up. The BNC faces right. {legend}", 20)
    for panel, (title, refs) in enumerate(sections):
        left = 34 + (panel % 2) * 700
        top = 123 + (panel // 2) * 407
        text(left, top, title, 24, "bold")

        def at(x, y):
            return left + 53 + (x - 40) * 5.55, top + 47 + (y - 58.5) * 5.55

        points = " ".join("%.2f,%.2f" % at(x, y) for x, y in outline)
        svg.append(f'<polygon points="{points}" fill="#f8faf9" stroke="#68818a" stroke-width="1.6"/>')
        for ref, pins in pads.items():
            for _, x, y in pins:
                u, v = at(x, y)
                circle(u, v, 6 if ref.startswith("MH") else 2, "white", "#b8c4c7")
        seen = []
        centers = {}
        for ref in refs:
            pins = [(n, *at(x, y)) for n, x, y in pads[ref] if n.isdigit()]
            if not pins:
                raise ValueError("No copper pads for " + ref)
            centers[ref] = (sum(p[1] for p in pins)/len(pins), sum(p[2] for p in pins)/len(pins))
            # Join only two-terminal parts. On a coil the separately numbered lands locate winding ends.
            if len(pins) == 2 and panel != 3:
                (_, x, y), (_, u, v) = pins
                svg.append(f'<path d="M{x:.1f},{y:.1f} L{u:.1f},{v:.1f}" stroke="#187078" stroke-width="2.5"/>')
            for n, x, y in pins:
                dark = ref.startswith("D") and n == "1"
                circle(x, y, 4.1, "#153e46" if dark else "#ecf8f6", "#12636a")
                if ref in ("T101", "L101"):
                    text(x + 5, y - 5, ref + "." + n, 13, "bold")
                    seen.append((x-2, y-19, x+67, y+5))
                seen.append((x-5, y-5, x+5, y+5))
        for ref in refs:
            if ref in ("T101", "L101"):
                continue
            x, y = centers[ref]
            choices = []
            length = len(ref)*8.8 + 6
            for radius, angle in product((16, 23, 33, 45, 61, 80), range(0, 360, 30)):
                a = math.radians(angle)
                endx, endy = x + radius*math.cos(a), y + radius*math.sin(a)
                lx = endx if math.cos(a) >= 0 else endx-length
                box = lx-2, endy-9, lx+length+2, endy+9
                if box[0] < left or box[2] > left+675 or box[1] < top+11 or box[3] > top+397:
                    continue
                overlaps = sum(box[0]<q[2] and q[0]<box[2] and box[1]<q[3] and q[1]<box[3] for q in seen)
                choices.append((overlaps, radius, abs(math.sin(a)), lx, endx, endy, box))
            _, _, _, lx, ex, ey, box = min(choices)
            seen.append(box)
            svg.append(f'<path d="M{x:.1f},{y:.1f} L{ex:.1f},{ey:.1f}" stroke="#526b74" stroke-width="1"/>')
            svg.append(f'<rect x="{lx:.1f}" y="{ey-8:.1f}" width="{length:.1f}" height="16" fill="white"/>')
            text(lx+2, ey+5, ref, 14, "bold")
    text(34, 955, "Filled dark pad = cathode (pin 1) of each diode and LED. Numbered winding lands correspond to the schematic.", 18)
    text(34, 982, "J101 vertical element     J102 / J103 / J104 counterpoise wires     J105 coax     T101 transformer     L101 tuning coil", 17)
    svg.append("</g></svg>")
    svg_path.write_text("\n".join(svg) + "\n", encoding="utf-8")
    if converter := shutil.which("rsvg-convert"):
        subprocess.run([converter, "-f", "pdf", "-o", pdf_path, svg_path], check=True)
    elif converter := shutil.which("inkscape"):
        subprocess.run([converter, svg_path, f"--export-filename={pdf_path}"], check=True)
    else:
        raise RuntimeError("Install librsvg or Inkscape to render the assembly drawings.")
