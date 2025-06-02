import argparse
import os
import sys
from extract import extractMain
from simulate import simulate

def convert_to_routing_netlist(gds_file, tech_file, output_file):
    # check if input files exist in expected folders
    gds_path = os.path.join("layout", gds_file)
    tech_path = os.path.join("tech", tech_file)
    if not os.path.isfile(gds_path):
        print(f"Error: {gds_file} not found in 'layout/' folder.")
        sys.exit(1)
    if not os.path.isfile(tech_path):
        print(f"Error: {tech_file} not found in 'tech/' folder.")
        sys.exit(1)

    # create output directory if it doesnt exist
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    extractMain(gds_path, tech_path, "output/"+output_file)
    # create empty .cmos file in output/
    #output_path = os.path.join(output_dir, output_file)
    #with open(output_path, "w") as f:
    #    pass
    
    #print(f"Created empty netlist file: {output_path}")

def simulate_netlist(netlist_file):
    # check if .cmos file exists in output/
    netlist_path = os.path.join("output", netlist_file)
    if not os.path.isfile(netlist_path):
        print(f"Error: {netlist_file} not found in 'output/' folder.")
        sys.exit(1)

    # dummy simulation message
    print(f"Simulating netlist {netlist_path} ...")
    simulate(netlist_path)
    print("Simulation complete.")

def main():
    parser = argparse.ArgumentParser(
        description="GDS to CMOS netlist extraction and simulation tool."
    )
    parser.add_argument(
        "-m", "--mode",
        required=True,
        choices=["extract", "simulate"],
        help="Mode of operation: extract or simulate"
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Input files (extract: <layout.gds> <tech.json>, simulate: <netlist.cmos>)"
    )
    parser.add_argument(
        "-o", "--output",
        default="netlist.cmos",
        help="Output netlist file name (only for extract mode) (extract: <layout.gds> <tech.json> -o <example.cmos>)"
    )

    args = parser.parse_args()

    if args.mode == "extract":
        if len(args.inputs) != 2:
            parser.error("extract mode requires two input files: <layout.gds> <tech.json>")
        gds_file, tech_file = args.inputs
        convert_to_routing_netlist(gds_file, tech_file, args.output)

    elif args.mode == "simulate":
        if len(args.inputs) != 1:
            parser.error("simulate mode requires one input file: <netlist.cmos>")
        netlist_file = args.inputs[0]
        simulate_netlist(netlist_file)

if __name__ == "__main__":
    main()
