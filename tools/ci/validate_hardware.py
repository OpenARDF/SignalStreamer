"""Validate SignalStreamer's CAD sources and tracked fabrication files in a scratch copy."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile

import pcbnew as pcb

from check_ground import check_ground

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export_manufacturing import PROJECT, ROOT, VARIANTS, export, plot_bare_board


def comparable(name, data):
    if name.endswith(".gbrjob"):
        job = json.loads(data)
        del job["Header"]["CreationDate"]
        return job
    # Preserve artwork, tool tables, coordinate data and generator versions.
    stamp = rb"\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d(?:Z|[+-]\d\d:\d\d)?"
    lines = data.splitlines()
    prefixes = (b"%TF.CreationDate,", b"; #@! TF.CreationDate,", b"G04 Created by KiCad ", b"; DRILL file KiCad ")
    return [re.sub(stamp, b"<date>", line) if line.startswith(prefixes) else line for line in lines]


def check_files(saved, fresh):
    with ZipFile(saved) as left, ZipFile(fresh) as right:
        if sorted(left.namelist()) != sorted(right.namelist()):
            raise ValueError(f"File list differs between {saved} and the fresh export")
        for name in right.namelist():
            if comparable(name, left.read(name)) != comparable(name, right.read(name)):
                raise ValueError(f"Stale fabrication file: {name}. Regenerate the manufacturing export.")


def check_rule_limits(cli, project, board, work):
    rules = json.loads(project.with_suffix(".kicad_pro").read_text())["board"]["design_settings"]["rules"]
    if rules["min_track_width"] < 0.5:
        raise ValueError("Project minimum track width must be at least 0.50 mm")

    # Exercise effective rules on real objects in the scratch copy, so disabled
    # checks or custom rules that no longer apply are caught as well.
    track = next(item for item in board.GetTracks() if not isinstance(item, pcb.PCB_VIA))
    track.SetWidth(pcb.FromMM(0.49))
    via = next(v for v in board.GetTracks() if isinstance(v, pcb.PCB_VIA) and v.GetIsFree())
    via.SetDrill(pcb.FromMM(0.49))
    via.SetWidth(pcb.FromMM(0.97))
    pcb.SaveBoard(str(project.with_suffix(".kicad_pcb")), board)
    report = work / "via-rule-probe.json"
    print("Control test: DRC must reject the undersized track and via in the scratch copy.", flush=True)
    subprocess.run([cli, "pcb", "drc", "--format", "json", "--units", "mm", "-o", report,
                    project.with_suffix(".kicad_pcb")], check=True, env={**os.environ, "LC_ALL": "C"})
    findings = json.loads(report.read_text())["violations"]
    if not any(v["type"] == "track_width" and any(i["uuid"] == track.m_Uuid.AsString() for i in v["items"])
               for v in findings):
        raise ValueError("KiCad must reject a 0.49 mm track")
    violations = [v for v in findings
                  if any(i["uuid"] == via.m_Uuid.AsString() for i in v["items"])]
    for kind, label, floor in (("annular_width", "annular width", 0.25), ("drill_out_of_range", "hole", 0.50)):
        limits = [float(m[1]) for v in violations if v["type"] == kind
                  for m in re.finditer(rf"min {label} ([0-9.]+) mm", v["description"])]
        if not limits or max(limits) < floor:
            raise ValueError(f"KiCad must enforce a through-via {label} minimum of {floor:.2f} mm")


def validate(cli, output):
    saved = ROOT / "Manufacturing" / "1.2-prototype"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as scratch:
        work = Path(scratch)
        # KiCad resolves project footprints, custom rules and models relative to this directory.
        shutil.copytree(PROJECT.parent, work / "KiCad", ignore=shutil.ignore_patterns("*-backups", "*.lck"))
        project = work / "KiCad" / PROJECT.name
        layout = project.with_suffix(".kicad_pcb")
        subprocess.run([cli, "pcb", "drc", "--refill-zones", "--save-board", "--schematic-parity",
                        "--exit-code-violations", "-o", work / "refilled.rpt", layout], check=True)
        export(cli, output, work, project)
        archive = "SignalStreamer-bare-board.zip"
        check_files(saved / archive, output / archive)
        for variant in VARIANTS:
            plots = work / ("plots-" + variant)
            plot_bare_board(cli, layout, plots, variant)
            for source in (work / "bare").glob("*.gbr"):
                other = plots / source.name
                if comparable(source.name, source.read_bytes()) != comparable(source.name, other.read_bytes()):
                    raise ValueError(f"{variant} changes shared board artwork on {source.name}")
            for source in (output / variant).iterdir():
                target = saved / variant / source.name
                if source.suffix not in (".csv", ".gbr"):
                    continue
                if comparable(source.name, source.read_bytes()) != comparable(source.name, target.read_bytes()):
                    raise ValueError(f"Stale assembly file: {variant}/{source.name}")
        board = pcb.LoadBoard(str(layout))
        check_ground(board)
        check_rule_limits(cli, project, board, work)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new directory for fresh assembly models and fabrication files")
    args = parser.parse_args()
    validate(os.environ.get("KICAD_CLI", "kicad-cli"), args.output)
