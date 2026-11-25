# SignalStreamer 1.2 prototype

Both assemblies use the same two-layer, 1.6 mm PCB and the same machined Polycase SL-42PMBR. The detector follows the eleven-capacitor Rev 1.1 schematic. Each detector position has a surface-mount site and a through-hole site connected to the same nets. Select one named variant in KiCad 10. The default view shows all available sites.

## Files for a build

| Recipient | Files | What to do |
| --- | --- | --- |
| PCB fabricator | [Bare board](../Manufacturing/1.2-prototype/SignalStreamer-bare-board.zip) | Use the copper, mask, silkscreen, outline and both drill files for either assembly. |
| PCB assembler | [PCBA BOM](../Manufacturing/1.2-prototype/SMD-PCBA/PCBA-BOM.csv), [placement CSV](../Manufacturing/1.2-prototype/SMD-PCBA/Placement-mm.csv), [top paste](../Manufacturing/1.2-prototype/SMD-PCBA/Front-stencil.gbr), [assembly drawing](../Manufacturing/1.2-prototype/SMD-PCBA/Assembly.pdf) | Place the 28 top-side parts on the common board. The placement file uses KiCad's absolute origin in mm. Verify pin 1 and LED cathodes in the assembler's placement preview. |
| Finisher of the SMD build | [Completion BOM](../Manufacturing/1.2-prototype/SMD-PCBA/Completion-BOM.csv) | Install the BNC, windings, four antenna leads, five light pipes and enclosure hardware. H201 identifies the PCB already included in the PCBA. |
| Hand-kit builder | [Kit BOM](../Manufacturing/1.2-prototype/THT-Kit/Kit-BOM.csv), [assembly drawing](../Manufacturing/1.2-prototype/THT-Kit/Assembly.pdf) | Order quantities for one complete kit. Fit the 200-series detector parts, including RV201. All soldering can be done with a conventional iron. |
| Polycase | [Two-piece machining STEP](../Mechanical/SignalStreamer-machined.step), [dimensioned drawing](../Mechanical/SignalStreamer-machining.pdf) | Machine the stock base and cover as a matched set. The drawing references the previously approved SignalSlinger press-fit and BNC cuts. |

The [kit electronics order](../Manufacturing/1.2-prototype/THT-Kit/Electronics-BOM.csv) contains the manufacturer numbers for the 29 electronic and connector placements. Use the full kit BOM to source the mechanical and winding materials. The kit BOM counts each purchased core once. H203, H206 and H209 make T101. H202, H204 and H206 make L101. Supply solder and the adhesive used to secure the tuning bead and cap. One bag of Polycase SCREWS-MBR-100 supplies 100 individual boss screws. Each board uses four.

## Assembly details

1. Populate the selected detector. The five LEDs are D103/105/107/109/111 on the SMD build and D203/205/207/209/211 on the kit. Both sets of optical centers have a 6.82 mm pitch. The assembly drawings mark the cathode of every diode. On the vertical glass diodes, bend the banded lead down into pad 1 and place the body at pad 2.
2. For the hand kit, form each WP7113ID lead outward by 1.27 mm to obtain a 5.08 mm lead pitch. Hold the leads at the bend to protect the package. Center the lens between its holes. Use an 18.0 mm gauge from the PCB component surface to the lens tip, then tack one lead. Trial-fit the cover before soldering the second lead. The lenses sit behind the five cover apertures. The SMD build uses a VCC LFB063CTP pressed into each aperture from outside the cover.
3. Assemble T101 on the T130-2 core. Wind 54 turns of 24 AWG for the primary and two turns of 22 AWG for the secondary, following the Rev 1.1 winding legend. On the assembly drawing, the outside and inside primary ends go to T101.4 (P) and T101.3 (P′). The outside and inside secondary ends go to T101.1 (S1) and T101.2 (S1′). Secure the toroid with three ties.
4. Assemble L101 using the FB-31-4852 bead and the lipstick tube. Allow the adhesive to cure, wind 17 close-spaced turns of 24 AWG, and solder to L101.1 and L101.2. Position its axis through the center of the case opening and secure it with four ties. Keep the tie heads and trimmed tails clear of the lid, bosses and tuning mechanism. The original manual illustrates the winding and bead assembly. [Winding and deployment instructions](https://docs.google.com/document/d/1ixdft7eyVAQ5lvPSUMsNJx15NzzCWhzimSsPBIRxByI/edit)
5. Solder the Amphenol 31-5431 at J105. Before mounting the board, thread the J104 radial through the lower hole W4 in the base. Route it beneath the PCB, around the inside of the mounting boss nearest J104 and clear of the BNC solder tails. Lay the other two radials in the BNC-end seam openings, J102 at W2 and J103 at W3. For the vertical, feed the board end of the lead through W1 from outside the detached cover. Pass it down through the outer 5.2 mm PCB relief hole, back up through the inner one and solder the stripped end to J101. Leave the cover free to slide along the wire for service. At each radial terminal, pass the insulated lead through its 5.2 mm PCB relief hole and solder the stripped end to the 2.45 mm plated hole. Allow 5.1 m for the vertical and 2.9 m per radial before end preparation. For 14 AWG stranded wire, select insulation up to 4.2 mm OD.
6. Set sensitivity with RV101 on the SMD board or RV201 on the kit. Both are 2 kΩ. The Bourns 3224W surface-mount part has 12 nominal turns and a 0.25 W rating. The PV36W hand-soldered part has 25 nominal turns and a 0.5 W rating. Adjust while observing the indicators.

## Enclosure fit

Open [the editable FreeCAD model](../Mechanical/SignalStreamer-enclosure.FCStd) and change the named cells in its dimensions spreadsheet to edit the machining features. The two machined solids share the stock part orientation. The fit-study group contains the populated boards as separate models. Show one board at a time and enable the light-pipe envelopes for the SMD build. Enable the radial wire group to inspect the example routes for 4.2 mm OD wire from the three PCB relief holes. The separate W1 fit study shows the vertical lead through the cover and both J101 relief holes. The Rev B machining STEP contains the two machined shells.

| Feature | Prototype dimensions and registration |
| --- | --- |
| LED apertures | Five holes Ø0.117 ±0.005 in. Their row is 0.980 in (24.892 mm) from the cover width centerline toward the tuning-tube side. The row is 4.64 mm inboard of the long PCB edge, as on SignalSlinger. The PCB bosses establish the in-plane datum. |
| BNC | Ø0.551 ±0.005 in, midway across the end wall and 0.739 in above the exterior base bottom. Both halves carry part of the cut, as on SignalSlinger. |
| Tuning tube | Ø20.0 ±0.3 mm for a modeled 16.6 mm tube. The bore center follows the mounted tube axis. Nominal radial clearance is 1.7 mm. The machining drawing specifies ±0.25 mm per axis for center location. |
| Antenna wire | Four Ø6.0 ±0.3 mm openings. On the BNC end, W2 and W3 straddle the seam at Z −16.67 and +16.67 mm, halfway between the connector center and each side edge. W4 is centered directly below the BNC at Y −12.70 mm, with its center 6.50 mm above the exterior base bottom. W1 for the vertical is on the LED face, centered across the cover at Z 0, X −45.30 mm. Its center is 8.68 mm from the end opposite the BNC, on the flat rim outside the recessed panel. Each opening gives a 4.2 mm lead 0.9 mm nominal radial clearance. |

The BNC and press-fit dimensions come from Polycase production drawings J-29441AB and J-29441AC, revision 0. Other SignalSlinger panel openings are outside this design. The model uses representative component bodies and nominal wire-free winding forms. Windings, solder, fastener heads, supplier molding variation and tie heads require a physical fit check.

The board retains the direct-coax option for builds outside the chassis. Omit J105, solder the coax center to the separate 2.01 mm feed hole on that footprint and the braid to a connector ground post. Lace the jacket through the two pairs of 3.6 mm tie holes. Both chassis build BOMs specify the BNC.

## Digital verification

Each selected detector has the same 18 nets and pin connections as Rev 1.1 when component references are mapped to their counterparts. KiCad 10.0.8 reported zero ERC and DRC violations, zero unconnected items and zero schematic/PCB parity issues. The two named variants produced identical copper, mask, silkscreen and outline plots. The SMD BOM and position file agree on 28 placements and the stencil has 57 apertures.

FreeCAD reopened the native file and the two-solid machining STEP. The five optical centers coincide with the lid holes for both populated boards. Neither populated board intersects either machined shell at nominal dimensions. All four modeled 4.2 mm leads clear both populated PCBs, the machined shells and one another. The W1 jacket has 0.90 mm nominal clearance at the cover and 0.97 mm below its return bend at the base. Physical results belong in the first-article record below.

## First articles

| Stage | Acceptance check |
| --- | --- |
| Machined sample | Test the actual LFB063CTP retention in each of the five holes. Compare it with an approved SignalSlinger case. Fit the BNC and seat the board on all four bosses before tightening. Inspect the seam, stroke the tuner fully, and pass the selected 14 AWG stock through all four openings. With the actual leads dressed and the board seated, check the lower radial against the BNC solder joints and verify that the upper two jackets clear the closed seam. Check the vertical lead’s return bend beneath the PCB and slide the cover along the lead to confirm access to the board. |
| Optical check | With the lid fitted, compare visibility against SignalSlinger in outdoor light. Light one indicator at a time and check adjacent apertures for spill. The CAD stack leaves 4.37 mm between the SMD LED and pipe input. VCC recommends a maximum 0.51 mm gap for best performance with wide-angle emitters. [VCC LFB series drawing](https://datasheet.datasheetarchive.com/originals/dk/DKDS-23/452587.pdf) The hand-kit lens apex clears the inside lid plane by 0.65 mm nominal. Check height and direct visibility separately. |
| RF comparison | Build one of each assembly. Use the same deployed wires, feed line, power levels and tuning arrangement for both and a working Rev 1.1 reference. Record minimum SWR and tuner travel across 3.5–3.7 MHz. At the manual's 3.55 MHz test point, target SWR below 2.5:1. At peak tuning, check the first LED is fully lit and the second partially lit at 1 W. At 5 W, set four fully lit and the fifth dim. Measure detector voltage, wiper load and trimmer dissipation at maximum operating drive. [Bourns 3224 ratings](https://www.bourns.com/docs/Product-Datasheets/3224.pdf) |
| Release | Record both builds' results, the actual tube and wire diameters, the optical result and Polycase's first-article review before marking the prototype as production hardware. |

## Regenerating the manufacturing files

Open [the KiCad project](../KiCad/SignalStreamer.kicad_pro) with KiCad 10 and its standard symbol, footprint and model libraries installed. The coil, formed LED, BNC and SMD trimmer models travel with the project. The export tool requires Python 3.9 or newer and either librsvg's `rsvg-convert` or Inkscape for the printable assembly maps.

```sh
python3 tools/export_manufacturing.py
```

Use `--kicad-cli PATH` for a KiCad installation outside PATH or `--output DIR` for a separate output directory. The tool runs ERC, DRC and schematic/board parity, compares the manufacturer BOM with the placement coordinates, checks the two STEP populations and checks the stencil aperture count. The stock mounting bosses put the underside of the board at Y −10.16 mm. To refresh a fit study, export the board STEP using the absolute origin, rotate it −90° about X, then translate by (−90.025, −10.16, −88.0349) mm in the supplier coordinate system. Recheck both halves and the five optical axes.
