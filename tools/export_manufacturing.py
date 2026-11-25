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

from assembly_map import locator


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "KiCad" / "SignalStreamer"
BOARD = PROJECT.with_suffix(".kicad_pcb")
SCHEMATIC = PROJECT.with_suffix(".kicad_sch")
VARIANTS = ("SMD-PCBA", "THT-Kit")
BOM_FIELDS = "Reference,Value,Manufacturer,Manufacturer PN,Footprint,Assembly,Description,Qty per board,Unit,Link"
BOM_LABELS = "Ref,Value,Manufacturer,MPN,Footprint,Assembly,Description,Amount,Unit,Source"


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
        locator(ipc, variant, set(by_ref), work / (variant + ".svg"), folder / "Assembly.pdf")
        if variant == "SMD-PCBA":
            positions = folder / "Placement-mm.csv"
            run("pcb", "export", "pos", "--variant", variant, "--exclude-dnp", "--smd-only", "--format",
                "csv", "--units", "mm", "-o", positions, BOARD)
            machine = [row for row in rows if row["Assembly"] == "Machine placement"]
            fitted = read_rows(positions)
            if ({row["Ref"] for row in fitted} != {row["Ref"] for row in machine}
                    or len(fitted) != 28 or any(row["Side"] != "top" for row in fitted)
                    or any(not row["MPN"] for row in machine)):
                raise ValueError("Machine BOM and front-side positions must describe the same 28 orderable parts")
            write_order(folder / "PCBA-BOM.csv", machine)
            write_order(folder / "Completion-BOM.csv", [row for row in rows if row not in machine])
            stencil = work / "stencil"
            run("pcb", "export", "gerbers", "--variant", variant, "--layers", "F.Paste",
                "--no-protel-ext", "-o", stencil, BOARD)
            paste = next(stencil.glob("*.gbr"))
            if paste.read_text().count("D03*") != 57:
                raise ValueError("Expected 57 front-side paste apertures for 28 placed parts")
            shutil.copy(paste, folder / "Front-stencil.gbr")
        else:
            write_order(folder / "Kit-BOM.csv", rows)
            electronics = [row for row in rows if row["Assembly"] == "Hand installation"]
            if any(not row["MPN"] for row in electronics):
                raise ValueError("Kit electronics require manufacturer part numbers")
            write_order(folder / "Electronics-BOM.csv", electronics)

    shared = {f"H{i}" for i in range(201, 210)} | {"J105", "L101", "T101", "N201"}
    smd = {f"{part}{i}" for part, end in (("C", 112), ("D", 112), ("R", 106)) for i in range(101, end)}
    kit = {ref[0] + str(int(ref[1:]) + 100) for ref in smd}
    if (populations["SMD-PCBA"] != shared | smd | {"RV101"} | {f"LP{i}" for i in range(1, 6)}
            or populations["THT-Kit"] != shared | kit | {"RV201"}):
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
