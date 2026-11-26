"""Test freshly populated PCB models in the Rev 1.2 enclosure using FreeCAD Python."""
import math
import os
from pathlib import Path
import re
import sys

if os.environ.get("FREECAD_LIB"):
    sys.path.append(os.environ["FREECAD_LIB"])
import FreeCAD as App
import Part


MECHANICAL = Path(__file__).resolve().parents[2] / "Mechanical"
# The mounting bosses define this PCB-to-Polycase coordinate transform.
MOUNT = App.Placement(App.Vector(-90.025, -10.16, -88.0349), App.Rotation(App.Vector(1, 0, 0), -90))


def aligned_cylinder(surface, direction):
    return isinstance(surface, Part.Cylinder) and abs(surface.Axis.dot(direction)) > 0.99999


def check_model(step, enclosure, kit):
    board = Part.read(str(step))
    board.Placement = MOUNT.multiply(board.Placement)
    # KiCad's top-level STEP occurrences follow the immediate compound children.
    refs = re.findall(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\('\d+','([^']*)','',#5,", step.read_text())
    children = board.childShapes()
    if len(refs) != len(children) or len(set(refs)) != len(refs) or not board.isValid():
        raise ValueError(f"Could not identify the parts in {step.name}")
    parts = dict(zip(refs, children))
    for shell in (enclosure.MachinedBase, enclosure.MachinedCover):
        if board.common(shell.Shape).Volume > 1e-6:
            raise ValueError(f"{step.name} intersects {shell.Name}")

    for i in range(5):
        ref = f"D{(203 if kit else 103) + 2*i}"
        led = parts[ref]
        pipe = enclosure.getObject(f"LFB063CTP{i+1}").Placement.Base
        hole = enclosure.getObject(f"PipeHole{i+1}").Placement.Base
        if kit:
            # The lead frame makes the THT body's bounding box asymmetric.
            centers = [f.Surface.Center for f in led.Faces
                       if aligned_cylinder(f.Surface, App.Vector(0, 1, 0)) and 2.4 < f.Surface.Radius < 2.6]
        else:
            centers = [led.BoundBox.Center]
        if not centers or min(math.hypot(c.x - pipe.x, c.z - pipe.z) for c in centers) > 0.03:
            raise ValueError(f"{ref} optical axis misses its light pipe")
        if math.hypot(pipe.x - hole.x, pipe.z - hole.z) > 0.03:
            raise ValueError(f"Light pipe {i+1} misses its cover bore")

    bnc = parts["J105"]
    bore = enclosure.BNC
    axis = bore.Placement.Rotation.multVec(App.Vector(0, 0, 1))
    barrels = [face.Surface for face in bnc.Faces
               if aligned_cylinder(face.Surface, axis) and abs(face.Surface.Radius - 6.35) < 0.01]
    if (not any((s.Center - bore.Placement.Base).cross(axis).Length <= 0.10 for s in barrels)
            or bnc.BoundBox.XMax <= enclosure.MachinedBase.Shape.BoundBox.XMax
            or bnc.common(bore.Shape).Volume < 1):
        raise ValueError(f"{step.name}: J105 barrel does not register with the BNC opening")

    straps = enclosure.L101TieStraps.Shape
    if len(straps.Solids) != 4:
        raise ValueError("Expected four L101 tie straps in the enclosure fit study")
    for strap in straps.Solids:
        coil = parts["L101"]
        if strap.distToShape(coil)[0] > 0.01 or strap.common(coil).Volume > 1e-6:
            raise ValueError(f"{step.name}: a strap misses or intersects the L101 tube")
    # Nominal measured minima rounded to 0.01 mm in the assembly guide.
    for body, minimum, label in ((parts["RV101"], 3.88, "RV101"), (enclosure.MachinedCover.Shape, 0.65, "cover")):
        gap = body.distToShape(straps)[0]
        if gap < minimum - 0.005:
            raise ValueError(f"{step.name}: strap-to-{label} clearance is {gap:.3f} mm")
    print(f"{step.name}: enclosure, five optical axes, BNC and four L101 straps pass", flush=True)


def validate(output):
    doc = App.openDocument(str(MECHANICAL / "SignalStreamer-enclosure.FCStd"))
    try:
        doc.recompute()
        if any("Invalid" in item.State for item in doc.Objects):
            raise ValueError("Invalid feature in FreeCAD enclosure")
        # Confirm the actual machining deliverable contains both modeled cuts.
        shells = Part.read(str(MECHANICAL / "SignalStreamer-machined.step")).Solids
        if len(shells) != 2:
            raise ValueError("Machining STEP must contain a base and a cover")
        for native, exported in zip(sorted([doc.MachinedBase.Shape, doc.MachinedCover.Shape], key=lambda s: s.Volume),
                                    sorted(shells, key=lambda s: s.Volume)):
            overlap = native.common(exported).Volume
            if native.Volume + exported.Volume - 2 * overlap > native.Volume * 2e-6:
                raise ValueError("Machining STEP differs from the native enclosure")
        for variant in ("SMD-PCBA", "THT-Kit"):
            check_model(output / variant / (variant + ".step"), doc, variant == "THT-Kit")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    validate(Path(sys.argv[1]).resolve())
