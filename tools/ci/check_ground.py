"""Check connectivity of the actual refilled copper, including individual zone islands."""
from collections import defaultdict

import pcbnew as pcb


def check_ground(board):
    layers = (pcb.F_Cu, pcb.B_Cu)
    shapes = defaultdict(list)
    neighbors = defaultdict(set)
    regions = set()
    stitches = set()
    shield = set()

    for zone in board.Zones():
        if zone.GetIsRuleArea() or zone.GetNetname() != "GND":
            continue
        for layer in layers:
            if not zone.IsOnLayer(layer):
                continue
            filled = pcb.SHAPE_POLY_SET(zone.GetFilledPolysList(layer))
            filled.Unfracture()
            for index in range(filled.OutlineCount()):
                node = (zone.m_Uuid.AsString(), layer, index)
                regions.add(node)
                shapes[layer].append((node, filled.Subset(index, index + 1)))

    for item in [*board.GetTracks(), *board.GetPads()]:
        if item.GetNetname() != "GND":
            continue
        node = item.m_Uuid.AsString()
        if isinstance(item, pcb.PCB_VIA) and item.GetIsFree():
            stitches.add(node)
        if isinstance(item, pcb.PAD):
            if item.GetAttribute() == pcb.PAD_ATTRIB_NPTH:
                continue
            if item.GetParentFootprint().GetReference() == "J105" and item.GetNumber() == "2":
                shield.add(node)
        for layer in layers:
            if item.IsOnLayer(layer):
                land = pcb.SHAPE_POLY_SET()
                item.TransformShapeToPolygon(land, layer, 0, pcb.FromMM(0.005), pcb.ERROR_INSIDE)
                shapes[layer].append((node, land))

    # A plated pad or via uses one node on both layers. Tracks and same-net pads
    # can also carry ground between islands, including through a thermal spoke.
    contacts = defaultdict(set)
    for layer, artwork in shapes.items():
        bounded = [(node, copper, copper.BBox()) for node, copper in artwork]
        for index, (node, copper, bounds) in enumerate(bounded):
            for other, adjacent, box in bounded[:index]:
                if bounds.Intersects(box) and copper.Collide(adjacent):
                    neighbors[node].add(other)
                    neighbors[other].add(node)
                    if node in stitches and other in regions:
                        contacts[node].add(layer)
                    if other in stitches and node in regions:
                        contacts[other].add(layer)

    if not regions or not stitches or not shield:
        raise ValueError("Expected filled GND copper, free GND stitching vias and J105 shield pads")
    for node in stitches:
        if contacts[node] != set(layers):
            raise ValueError(f"GND stitching via {node} does not touch a pour on both faces")
    reached = set(shield)
    pending = list(shield)
    while pending:
        new = neighbors[pending.pop()] - reached
        reached.update(new)
        pending.extend(new)
    missing = regions - reached
    if missing:
        raise ValueError(f"GND regions without a conductive path to the J105 shield: {sorted(missing)}")
    print(f"All {len(regions)} GND regions reach J105; {len(stitches)} free GND vias touch both pours.")
