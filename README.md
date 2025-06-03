# SimGDS
**SimGDS** is A recreation of a fundamental part of the Layer vs. Schematic process created in Python w/ the Gdstk library  
made for the AP Computer Science A Final Project.

## The Goal
An Electronic Design Automation (EDA) tool with the following capabilities:
- Command Line Interface (CLI)
- Parse and extract data from a GDS layout file
- Convert GDS -> Netlist
- Output netlist as a custom designed .cmos file
- Simulate .cmos files as digital logic

## Project Structure
📁simgds/  
├── 🐍simgds.py - Handles the CLI  
├── 🐍extract.py - Parses and extracts layout data to a .cmos netlist  
├── 🐍simulate.py - Contains logic for simulating .cmos netlists  
├── 📁layout/  - Stores .gds layout files  
│   ├── 🏠inverter.gds  
│   └── ...  
├── 📁tech/ - Stores .json technology files  
│   ├── 🧪process.json  
│   └── ...  
├── 📁output/ - Stores .cmos netlist files  
│   ├── ⚙fulladder.cmos  
│   └── ...  
├── 🧾poetry.lock - Project dependecies managed by Poetry  
└── 🧾pyproject.toml   

## Installation
1. Ensure you have Python 3.8 or higher installed
2. Clone the repository
   ```bash
   git clone https://github.com/evanliu-at-icstudents/simgds.git
   cd simgds
   ```
3. Install dependencies using poetry
   ```bash
   poetry install
   ```
   
## Usage
Make sure you have .gds and .json files in the correct folders

### Help command
```bash
poetry run python simgds.py -h
```
this will output
```yaml
usage: simgds.py [-h] -m {extract,simulate} [-o OUTPUT] inputs [inputs ...]

GDS to CMOS netlist extraction and simulation tool.

positional arguments:
  inputs                Input files
                        extract: <layout.gds> <tech.json>
                        simulate: <netlist.cmos>

options:
  -h, --help            Show this help message and exit
  -m, --mode {extract,simulate}
                        Mode of operation: extract or simulate
  -o, --output OUTPUT   Output netlist file name (only for extract mode)
                        (default: netlist.cmos)
```

### Extraction
**Purpose**: Convert a GDS file into a CMOS netlist
**Inputs**:
- A GDS layout file located in the layout/ directory
- A technology description .json file located in the tech/ directory

**Output**:
- A CMOS netlist file saved in the output/ directory (defaults to netlist.cmos)

**Example**:
```bash
poetry run python simgds.py -m extract example.gds tech.json -o mynetlist.cmos
```
This will read layout/example.gds and tech/tech.json, and create output/mynetlist.cmos.

### Simulation
**Purpose**: Simulate a CMOS netlist
**Inputs**:
- A CMOS netlist file located in the output/ directory

**Output**:
- Digital logic output via truth table or user input

**Example**:
```bash
poetry run python simgds.py -m simulate mynetlist.cmos
```
This will simulate output/mynetlist.cmos and print simulation results to the console.


