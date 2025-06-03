import gdstk
import os
import json

def is_valid_polygon(poly):
    try:
        pts = poly.points
        return pts is not None and len(pts) >= 3 and hasattr(pts, "shape") and len(pts.shape) == 2 and pts.shape[1] == 2
    except Exception:
        return False

def find_transistors_by_bounding_box(library, tech):
    with open(tech, "r") as f:
        jsonTech = json.load(f)

    POLY_LAYER, POLY_DATATYPE = jsonTech["ls"]["POLY"]["layer"], jsonTech["ls"]["POLY"]["datatype"]
    DIFF_LAYER, DIFF_DATATYPE = jsonTech["ls"]["DIFF"]["layer"], jsonTech["ls"]["DIFF"]["datatype"]
    NWELL_LAYER, NWELL_DATATYPE = jsonTech["ls"]["NWELL"]["layer"], jsonTech["ls"]["NWELL"]["datatype"]
    CONTACT_LAYER, CONTACT_DATATYPE = jsonTech["ls"]["CONTACT"]["layer"], jsonTech["ls"]["CONTACT"]["datatype"]

    nmos_transistors = []
    pmos_transistors = []
    nmos_id = 1
    pmos_id = 1

    for cell in library.cells:
        print(f"\nProcessing cell: {cell.name}")
        all_polygons = cell.get_polygons()

        poly_polys = [p for p in all_polygons if p.layer == POLY_LAYER and p.datatype == POLY_DATATYPE and is_valid_polygon(p)]
        diff_polys = [p for p in all_polygons if p.layer == DIFF_LAYER and p.datatype == DIFF_DATATYPE and is_valid_polygon(p)]
        nwell_polys = [p for p in all_polygons if p.layer == NWELL_LAYER and p.datatype == NWELL_DATATYPE and is_valid_polygon(p)]
        contact_polys = [p for p in all_polygons if p.layer == CONTACT_LAYER and p.datatype == CONTACT_DATATYPE and is_valid_polygon(p)]

        if not poly_polys or not diff_polys:
            print("  Skipping: no poly or diffusion polygons found.")
            continue

        transistor_candidates = []
        for poly in poly_polys:
            for diff in diff_polys:
                try:
                    channel = gdstk.boolean([poly], [diff], "and")
                    if channel and all(is_valid_polygon(c) for c in channel):
                        transistor_candidates.append((cell.name, poly, diff, channel))
                except Exception:
                    continue

        if not transistor_candidates:
            continue

        for cell_name, poly, diff, channel in transistor_candidates:
            try:
                channel_bbox = channel[0].bounding_box()
            except Exception:
                continue

            is_in_nwell = False
            for nwell in nwell_polys:
                try:
                    well_bbox = nwell.bounding_box()
                    if (
                        channel_bbox[0][0] >= well_bbox[0][0] and
                        channel_bbox[0][1] >= well_bbox[0][1] and
                        channel_bbox[1][0] <= well_bbox[1][0] and
                        channel_bbox[1][1] <= well_bbox[1][1]
                    ):
                        is_in_nwell = True
                        break
                except Exception:
                    continue

            contacts_in_diff = []
            for contact in contact_polys:
                try:
                    if gdstk.boolean([contact], [diff], "and"):
                        contacts_in_diff.append(contact)
                except Exception:
                    continue

            diff_bbox = diff.bounding_box()
            left_x = diff_bbox[0][0]
            right_x = diff_bbox[1][0]
            diff_width = right_x - left_x

            contacts_positions = sorted(
                [(c, (c.bounding_box()[0][0] + c.bounding_box()[1][0]) / 2) for c in contacts_in_diff],
                key=lambda x: x[1]
            )

            left_threshold = left_x + diff_width * 0.4
            right_threshold = left_x + diff_width * 0.6

            left_contacts = [c for c, x in contacts_positions if x <= left_threshold]
            right_contacts = [c for c, x in contacts_positions if x >= right_threshold]
            middle_contacts = [c for c, x in contacts_positions if left_threshold < x < right_threshold]

            if len(left_contacts) == 2 and len(right_contacts) == 2:
                source_contacts, drain_contacts = left_contacts, right_contacts
            elif len(contacts_in_diff) == 3 and len(middle_contacts) == 1:
                source_contacts = left_contacts + right_contacts
                drain_contacts = middle_contacts
            else:
                half = len(contacts_positions) // 2
                source_contacts = [c for c, _ in contacts_positions[:half]]
                drain_contacts = [c for c, _ in contacts_positions[half:]]

            transistor_record = {
                "id": None,
                "cell_name": cell_name,
                "poly": poly,
                "diff": diff,
                "channel": channel,
                "contacts": contacts_in_diff,
                "source_contacts": source_contacts,
                "drain_contacts": drain_contacts,
                "is_in_nwell": is_in_nwell,
            }

            if is_in_nwell:
                transistor_record["id"] = f"PMOS_{pmos_id}"
                pmos_transistors.append(transistor_record)
                pmos_id += 1
            else:
                transistor_record["id"] = f"NMOS_{nmos_id}"
                nmos_transistors.append(transistor_record)
                nmos_id += 1

    return nmos_transistors, pmos_transistors

def find_transistor_pairs(transistors):
    def contacts_overlap(c_list1, c_list2):
        for c1 in c_list1:
            bb1 = c1.bounding_box()
            for c2 in c_list2:
                bb2 = c2.bounding_box()
                if not (bb1[1][0] < bb2[0][0] or bb1[0][0] > bb2[1][0] or bb1[1][1] < bb2[0][1] or bb1[0][1] > bb2[1][1]):
                    return True
        return False

    nmos_transistors = [t for t in transistors if not t["is_in_nwell"]]
    pmos_transistors = [t for t in transistors if t["is_in_nwell"]]

    def find_pairs_for_type(transistor_list, prefix):
        parallel_pairs = []
        series_pairs = []
        used_pairs = set()
        parallel_id = 1
        series_id = 1

        for i, t1 in enumerate(transistor_list):
            for j, t2 in enumerate(transistor_list):
                if j <= i:
                    continue

                source_overlap = contacts_overlap(t1["source_contacts"], t2["source_contacts"])
                drain_overlap = contacts_overlap(t1["drain_contacts"], t2["drain_contacts"])

                if source_overlap or drain_overlap:
                    pair_key = tuple(sorted([t1["id"], t2["id"]]))
                    if pair_key in used_pairs:
                        continue
                    used_pairs.add(pair_key)

                    combined_contacts = list(set(t1["contacts"] + t2["contacts"]))
                    contacts_positions = sorted(set(
                        (c.bounding_box()[0][0] + c.bounding_box()[1][0]) / 2 for c in combined_contacts
                    ))

                    if len(contacts_positions) == 2:
                        series_pairs.append({
                            "id": f"{prefix}SERIES_PAIR_{series_id}",
                            "pair": (t1["id"], t2["id"]),
                            "transistors": (t1, t2),
                        })
                        series_id += 1
                    elif len(contacts_positions) == 3:
                        parallel_pairs.append({
                            "id": f"{prefix}PARALLEL_PAIR_{parallel_id}",
                            "pair": (t1["id"], t2["id"]),
                            "transistors": (t1, t2),
                        })
                        parallel_id += 1

        return parallel_pairs, series_pairs

    nmos_parallel, nmos_series = find_pairs_for_type(nmos_transistors, "NMOS_")
    pmos_parallel, pmos_series = find_pairs_for_type(pmos_transistors, "PMOS_")

    return nmos_parallel + pmos_parallel, nmos_series + pmos_series

def find_connected_port(polygon, tech):
    for port_type in ("in", "out"):
        for name, info in tech[port_type].items():
            if polygon.layer == info["layer"] and polygon.datatype == info["datatype"]:
                return name
    return "N/A"

def find_connected_port_group(polygons, tech):
    for p in polygons:
        port = find_connected_port(p, tech)
        if port != "N/A":
            return port
    return "N/A"

def transpile_to_netlist_and_save(extraction_result, tech_path, output_filename):
    if not extraction_result:
        print("No extraction result to transpile.")
        return

    try:
        with open(tech_path, "r") as f:
            tech = json.load(f)

        port_lines = []
        for direction, ports in tech.items():
            if direction in ("in", "out"):
                for name in ports:
                    port_lines.append(f"PORT {direction.upper()} {name}")

        netlist_lines = sorted(port_lines)

        for t in extraction_result["pmos_transistors"]:
            gate = find_connected_port(t["poly"], tech)
            source = find_connected_port_group(t["source_contacts"], tech)
            drain = find_connected_port_group(t["drain_contacts"], tech)
            netlist_lines.append(f"PMOS {t['id']} {gate} {source} {drain}")

        for t in extraction_result["nmos_transistors"]:
            gate = find_connected_port(t["poly"], tech)
            source = find_connected_port_group(t["source_contacts"], tech)
            drain = find_connected_port_group(t["drain_contacts"], tech)
            netlist_lines.append(f"NMOS {t['id']} {gate} {source} {drain}")

        with open(output_filename, "w") as out_file:
            out_file.write("\n".join(netlist_lines))
            print(f"Netlist written to {output_filename}")

    except Exception as e:
        print(f"Error transpiling to netlist: {e}")

def write_cmos_netlist(net_connections, transistors, tech, output_path):
    netid_to_ports = {}
    for net_id, conn in net_connections.items():
        if conn["ports"]:
            netid_to_ports[net_id] = list(conn["ports"])[0]
        else:
            netid_to_ports[net_id] = net_id

    port_lines = []
    for direction in ("in", "out"):
        if direction in tech:
            for port_name in tech[direction]:
                port_lines.append(f"PORT {direction.upper()} {port_name}")

    transistor_port_map = {}
    for net_id, conn in net_connections.items():
        for t_id, parts in conn["transistors"].items():
            for part in parts:
                if t_id not in transistor_port_map:
                    transistor_port_map[t_id] = {}
                transistor_port_map[t_id][part] = netid_to_ports[net_id]

    transistor_lines = []
    for t in transistors:
        t_id = t["id"]
        transistor_type = "PMOS" if t["is_in_nwell"] else "NMOS"
        gate = transistor_port_map.get(t_id, {}).get("gate", "N/A")
        source = transistor_port_map.get(t_id, {}).get("source", "N/A")
        drain = transistor_port_map.get(t_id, {}).get("drain", "N/A")

        line = f"{transistor_type} {t_id} {gate} {source} {drain}"
        transistor_lines.append(line)

    dir_path = os.path.dirname(output_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    with open(output_path, "w") as f:
        f.write("\n".join(sorted(port_lines) + transistor_lines))
        f.write("\n")

    print(f"Netlist written to {output_path}")

def find_net_object_connections(metal_nets, transistors, tech, all_polygons):
    net_connections = {}

    tech_ports = {**tech.get("in", {}), **tech.get("out", {})}

    port_polygons_by_name = {port_name: [] for port_name in tech_ports}
    for poly in all_polygons:
        for port_name, port_info in tech_ports.items():
            if poly.layer == port_info["layer"] and poly.datatype == port_info["datatype"]:
                port_polygons_by_name[port_name].append(poly)

    def polygon_belongs_to_net(poly, net_polys):
        try:
            return any(gdstk.boolean([poly], [net_poly], "and") for net_poly in net_polys)
        except Exception:
            return False

    for net in metal_nets:
        net_id = net["net_id"]
        net_polys = net["polygons"]

        net_connections[net_id] = {
            "transistors": {},
            "ports": set()
        }

        for t in transistors:
            for part_name in ["poly", "source_contacts", "drain_contacts"]:
                elems = t[part_name] if isinstance(t[part_name], list) else [t[part_name]]
                for elem in elems:
                    if polygon_belongs_to_net(elem, net_polys):
                        if t["id"] not in net_connections[net_id]["transistors"]:
                            net_connections[net_id]["transistors"][t["id"]] = set()
                        part = "gate" if part_name == "poly" else part_name.replace("_contacts", "")
                        net_connections[net_id]["transistors"][t["id"]].add(part)

        for port_name, port_polys in port_polygons_by_name.items():
            for port_poly in port_polys:
                if polygon_belongs_to_net(port_poly, net_polys):
                    net_connections[net_id]["ports"].add(port_name)
                    break

    return net_connections

def find_connected_metal_nets(polygons, metal_layer_info):
    from collections import defaultdict

    met1_polygons = [
        p for p in polygons
        if p.layer == metal_layer_info["layer"] and p.datatype == metal_layer_info["datatype"]
    ]

    parent = {id(p): p for p in met1_polygons}

    def find(p_id):
        while id(parent[p_id]) != id(parent[id(parent[p_id])]):
            parent[p_id] = parent[id(parent[p_id])]
        return id(parent[p_id])

    def union(p1, p2):
        root1 = find(id(p1))
        root2 = find(id(p2))
        if root1 != root2:
            parent[root2] = parent[root1]

    for i, p1 in enumerate(met1_polygons):
        for j in range(i + 1, len(met1_polygons)):
            p2 = met1_polygons[j]
            try:
                overlap = gdstk.boolean([p1], [p2], "and")
                if overlap:
                    union(p1, p2)
            except Exception:
                continue

    net_groups = defaultdict(list)
    for p in met1_polygons:
        root = find(id(p))
        net_groups[root].append(p)

    connected_nets = []
    for i, group in enumerate(net_groups.values(), start=1):
        connected_nets.append({
            "net_id": f"NET{i}",
            "polygons": group
        })

    return connected_nets

def extract(gds_path, tech_path, output_path):
    if not os.path.exists(gds_path):
        print(f"Error: GDSII file not found at '{gds_path}'.")
        return

    try:
        lib = gdstk.read_gds(gds_path)
        print(f"Loaded GDSII file: {gds_path}")
        nmos_transistors, pmos_transistors = find_transistors_by_bounding_box(lib, tech_path)
        all_transistors = nmos_transistors + pmos_transistors

        parallel_pairs, series_pairs = find_transistor_pairs(all_transistors)

        paired_ids = {tid for p in parallel_pairs + series_pairs for tid in p["pair"]}
        singles = [t for t in all_transistors if t["id"] not in paired_ids]

        print("\nSingle transistors (not in any pair):")
        for t in singles:
            print(f" {t['id']} in {t['cell_name']}")

        print("\nParallel Pairs:")
        for pair in parallel_pairs:
            print(f" {pair['id']}: {pair['pair']}")

        print("\nSeries Pairs:")
        for pair in series_pairs:
            print(f" {pair['id']}: {pair['pair']}")

        result = {
            "nmos_transistors": nmos_transistors,
            "pmos_transistors": pmos_transistors,
            "parallel_pairs": parallel_pairs,
            "series_pairs": series_pairs,
        }
        transpile_to_netlist_and_save(result, tech_path, output_path)
        return result
    except Exception as e:
        print(f"Error processing GDS: {e}")
        return None

def extractMain(gds_path, tech_path, output_path):
    gds_file = gds_path
    tech_file = tech_path
    netlist_output = output_path
    print(gds_file, tech_file, netlist_output)
    lib = gdstk.read_gds(gds_file)
    with open(tech_file, "r") as f:
        tech = json.load(f)

    met1_info = tech["ls"]["MET1"]

    all_polygons = []
    for cell in lib.cells:
        all_polygons.extend(cell.get_polygons()) #type: ignore

    metal_nets = find_connected_metal_nets(all_polygons, met1_info)

    extraction_result = extract(gds_file, tech_file, netlist_output)

    if extraction_result is None:
        print("Extraction failed or no transistors found.")
    else:
        all_transistors = extraction_result["nmos_transistors"] + extraction_result["pmos_transistors"]

        metal_net_connections = find_net_object_connections(metal_nets, all_transistors, tech, all_polygons)

        print("\nConnected MET1 Nets with transistor parts connected:")
        for net_id, conn in metal_net_connections.items():
            print(f"{net_id}:")
            for tid, parts in conn["transistors"].items():
                print(f"  Transistor {tid} connected at: {', '.join(parts)}")
            if conn["ports"]:
                print(f"  Ports: {', '.join(conn['ports'])}")
            else:
                print("  Ports: None")
        write_cmos_netlist(metal_net_connections, all_transistors, tech, netlist_output)