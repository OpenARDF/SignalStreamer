"""Export the common bare board and the two KiCad assembly variants.

Run from any directory with KiCad 10 and its standard libraries installed.
"""
import argparse
import csv
import os
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from assembly_map import locator, read_ipc


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "KiCad" / "SignalStreamer"
BOARD = PROJECT.with_suffix(".kicad_pcb")
SCHEMATIC = PROJECT.with_suffix(".kicad_sch")
VARIANTS = ("SMD-PCBA", "THT-Kit")
BOM_FIELDS = "Reference,Value,Manufacturer,Manufacturer PN,Footprint,Assembly,Description,Qty per board,Unit,Link"
BOM_LABELS = "Ref,Value,Manufacturer,MPN,Footprint,Assembly,Description,Amount,Unit,Source"

SMD_TO_THT = {
    f"{kind}{number}": f"{kind}{number + 100}"
    for kind, last in (("C", 111), ("R", 105), ("D", 111))
    for number in range(101, last + 1)
}
SHARED_THT_PINS = {"RV101": {"1", "2", "3"}, "L101": {"1", "2"},
                   "T101": {"1", "2", "3", "4"}, "J105": {"1", "2"}}


def check_footprints(doc):
    # Inspect the common bare board before KiCad filters either assembly variant.
    components = {c.get("refDes"): c for c in doc.findall(".//Component")}
    smd, kit = set(SMD_TO_THT), set(SMD_TO_THT.values())
    expected = smd | kit | set(SHARED_THT_PINS)
    actual = {r for r in components if re.fullmatch(r"(?:C|R|RV|D|L|T)\d+|J105", r)}
    if actual != expected:
        raise ValueError(f"Unexpected or missing board footprints: {actual ^ expected}")

    # Inspect the plotted artwork so hidden fields and F.Fab labels cannot pass as printed ink.
    front_tht = {"L101", "T101", "J105"}
    front_refs = smd | front_tht
    back_refs = kit | (set(SHARED_THT_PINS) - front_tht) | {f"J{i}" for i in range(101, 105)}
    # Include wire reliefs and other through-hole features even when their references are hidden.
    back_artwork = {r for r, c in components.items() if c.get("mountType") == "THMT"} - front_tht
    front_artwork = {r for r, c in components.items() if c.get("mountType") == "SMT"} | front_tht
    for layer, required, forbidden in (("F.Silkscreen", front_refs, back_artwork),
                                       ("B.Silkscreen", back_refs, front_artwork)):
        printed = set()
        for group in doc.findall(f".//LayerFeature[@layerRef='{layer}']/Set"):
            ref = group.get("componentRef")
            label = group.find("NonstandardAttribute[@name='TEXT']")
            if ref in forbidden:
                raise ValueError(f"{ref} has assembly artwork on the wrong layer ({layer})")
            if label is None:
                continue
            value = label.get("value")
            if layer == "F.Silkscreen" and value in ("ANT", "RADIAL"):
                raise ValueError(f"The {value} wire legend belongs on B.Silkscreen")
            if ref and value == ref and group.find("Features/UserSpecial/*") is not None:
                printed.add(ref)
        if required - printed:
            raise ValueError(f"Missing references on {layer}: {sorted(required - printed)}")

    plated = {stack.get("name") for stack in doc.findall(".//PadStackDef")
              if stack.find("PadstackHoleDef[@platingStatus='PLATED']") is not None}
    nets = defaultdict(dict)
    drilled = defaultdict(set)
    # Every through-hole terminal reaches front copper, including each winding end.
    # The extra winding lands on the back have no drill or paste aperture.
    for group in doc.findall(".//LayerFeature[@layerRef='F.Cu']/Set"):
        for pad in group.findall("Pad"):
            terminal = pad.find("PinRef")
            if terminal is None:
                continue
            ref, pin = terminal.get("componentRef"), terminal.get("pin")
            nets[ref][pin] = group.get("net")
            if pad.get("padstackDefRef") in plated:
                drilled[ref].add(pin)

    for ref in sorted(expected):
        if components[ref].get("mountType") != ("SMT" if ref in smd else "THMT"):
            raise ValueError(f"Incorrect mounting technology on {ref}")
        pins = SHARED_THT_PINS.get(ref, {"1", "2"})
        if set(nets[ref]) != pins or not all(nets[ref].values()):
            raise ValueError(f"Missing or unconnected terminals on {ref}: {nets[ref]}")
        if drilled[ref] != (set() if ref in smd else pins):
            raise ValueError(f"Incorrect plated holes on {ref}: {drilled[ref]}")

    for a, b in SMD_TO_THT.items():
        if nets[a] != nets[b] or nets[a]["1"] == nets[a]["2"]:
            raise ValueError(f"Pin-to-net mismatch for {a} / {b}: {nets[a]} / {nets[b]}")


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_order(path, rows):
    # Wound components are assembled from the cores, tube and wire already in the order.
    grouping = defaultdict(list)
    for row in rows:
        if row["Assembly"] != "Wind and install":
            key = tuple(row[field] for field in ("Value", "Manufacturer", "MPN", "Footprint",
                                                 "Assembly", "Description", "Source"))
            grouping[key + (row["Unit"] or "piece",)].append(row)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("References", "Quantity per unit", "Unit", "Value", "Manufacturer",
                         "Manufacturer part number", "Footprint", "Assembly", "Description", "Source"))
        for (*fields, unit), group in grouping.items():
            quantity = sum(Decimal(row["Amount"] or "1") for row in group)
            writer.writerow((", ".join(row["Ref"] for row in group), quantity, unit, *fields))


def export(cli, output, work):
    def run(*args):
        subprocess.run([cli, *args], check=True)

    run("sch", "erc", "--exit-code-violations", "-o", work / "erc.rpt", SCHEMATIC)
    run("pcb", "drc", "--schematic-parity", "--exit-code-violations", "-o", work / "drc.rpt", BOARD)
    gerbers = work / "bare"
    run("pcb", "export", "gerbers", "--layers", "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts",
        "--no-protel-ext", "-o", gerbers, BOARD)
    run("pcb", "export", "drill", "--excellon-units", "mm", "--excellon-separate-th", "-o", gerbers, BOARD)
    if len(list(gerbers.glob("*.gbr"))) != 7 or len(list(gerbers.glob("*.drl"))) != 2:
        raise ValueError("Expected seven Gerber layers and separate plated and unplated drill files")
    with ZipFile(output / "SignalStreamer-bare-board.zip", "w", ZIP_DEFLATED) as archive:
        for path in sorted(gerbers.iterdir()):
            archive.write(path, path.name)

    ipc = work / "board.xml"
    run("pcb", "export", "ipc2581", "--units", "mm", "-o", ipc, BOARD)
    doc = read_ipc(ipc)
    check_footprints(doc)
    populations = {}
    for variant in VARIANTS:
        folder = output / variant
        folder.mkdir()
        native_bom = work / (variant + ".csv")
        run("sch", "export", "bom", "--variant", variant, "--exclude-dnp", "--fields", BOM_FIELDS,
            "--labels", BOM_LABELS, "-o", native_bom, SCHEMATIC)
        rows = read_rows(native_bom)
        by_ref = {row["Ref"]: row for row in rows}
        populations[variant] = set(by_ref)
        if len(by_ref) != len(rows):
            raise ValueError("Expected one KiCad BOM row per reference")
        board_step = folder / (variant + ".step")
        board_step.touch()
        run("pcb", "export", "step", "--force", "--variant", variant, "--no-dnp", "--subst-models",
            "-o", board_step, BOARD)
        modeled = set(re.findall(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\('\d+','([A-Z]+\d+)'", board_step.read_text()))
        expected = {r["Ref"] for r in rows if r["Footprint"]}
        if modeled != expected:
            raise ValueError(f"STEP population mismatch for {variant}: {modeled ^ expected}")
        locator(doc, variant, set(by_ref), work / (variant + ".svg"), folder / "Assembly.pdf")
        if variant == "SMD-PCBA":
            positions = folder / "Placement-mm.csv"
            run("pcb", "export", "pos", "--variant", variant, "--exclude-dnp", "--smd-only", "--format",
                "csv", "--units", "mm", "-o", positions, BOARD)
            machine = [row for row in rows if row["Assembly"] == "Machine placement"]
            fitted = read_rows(positions)
            if ({row["Ref"] for row in fitted} != {row["Ref"] for row in machine}
                    or len(fitted) != len(SMD_TO_THT) or any(row["Side"] != "top" for row in fitted)
                    or any(not row["MPN"] for row in machine)):
                raise ValueError("Machine BOM and front-side positions must describe the same 27 orderable parts")
            write_order(folder / "PCBA-BOM.csv", machine)
            write_order(folder / "Completion-BOM.csv", [row for row in rows if row not in machine])
            stencil = work / "stencil"
            run("pcb", "export", "gerbers", "--variant", variant, "--layers", "F.Paste",
                "--no-protel-ext", "-o", stencil, BOARD)
            paste = next(stencil.glob("*.gbr"))
            if paste.read_text().count("D03*") != 2 * len(SMD_TO_THT):
                raise ValueError("Expected 54 front-side paste apertures for 27 placed parts")
            shutil.copy(paste, folder / "Front-stencil.gbr")
        else:
            write_order(folder / "Kit-BOM.csv", rows)
            electronics = [row for row in rows if row["Assembly"] == "Hand installation"]
            if any(not row["MPN"] for row in electronics):
                raise ValueError("Kit electronics require manufacturer part numbers")
            write_order(folder / "Electronics-BOM.csv", electronics)

    shared = set(SHARED_THT_PINS) | {f"H{i}" for i in range(201, 210)} | {"N201"}
    if (populations["SMD-PCBA"] != shared | set(SMD_TO_THT) | {f"LP{i}" for i in range(1, 6)}
            or populations["THT-Kit"] != shared | set(SMD_TO_THT.values())):
        raise ValueError("Variant population differs from the Rev 1.2 assembly design")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default=os.environ.get("KICAD_CLI", "kicad-cli"))
    parser.add_argument("--output", type=Path, default=ROOT / "Manufacturing" / "1.2-prototype")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        result = work / "output"
        result.mkdir()
        export(args.kicad_cli, result, work)
        # Publish only after both variants and the common manufacturing files pass checks.
        shutil.copytree(result, args.output, dirs_exist_ok=True)


if __name__ == "__main__":
    main()
