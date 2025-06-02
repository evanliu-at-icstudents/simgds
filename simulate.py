from itertools import product
import os

def grabinputs(filename):
    result = []
    with open(filename+".cmos", 'r') as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                result.append(stripped.split())
    result.sort(key=lambda x: x[0])
    port = list(filter(lambda x: x[0] == 'PORT', result))
    portinputs = [x[2] for x in port if x[1] == 'IN' and x[2] not in ('VDD', 'GND')]
    return portinputs

def graboutputs(filename):
    result = []
    with open(filename+".cmos", 'r') as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                result.append(stripped.split())
    result.sort(key=lambda x: x[0])
    port = list(filter(lambda x: x[0] == 'PORT', result))
    portoutputs = [x[2] for x in port if x[1] == 'OUT']
    return portoutputs

def simulate_circuit(filename, inputs):
    result = []

    with open(filename+".cmos", 'r') as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                result.append(stripped.split())
    result.sort(key=lambda x: x[0])

    # seperate io ports and wires
    port = list(filter(lambda x: x[0] == 'PORT', result))
    portinputs = [x[2] for x in port if x[1] == 'IN' and x[2] not in ('VDD', 'GND')]
    portoutputs = [x[2] for x in port if x[1] == 'OUT']
    wire = list(portinputs + portoutputs) + ['VDD', 'GND']

    # sep cmos logic and instances
    queue = [x for x in result if x[0] == "NMOS" or x[0] == "PMOS" or x[0] == "INST"]
    correct = []

    # topological sort to resolve dependencies
    while len(queue) > 0:
        if queue[0][0] != "INST":
            if queue[0][2] in wire and queue[0][3] in wire:
                wire.append(queue[0][4])
                correct.append(queue[0])
                queue.pop(0)
            else:
                queue.append(queue.pop(0))
        else:
            instinputs = len(grabinputs("output/"+queue[0][1]))
            instoutputs = len(graboutputs("output/"+queue[0][1]))
            if all(queue[0][i+3] in wire for i in range(instinputs)):
                for i in range(instoutputs):
                    wire.append(queue[0][i+3+instinputs])
                correct.append(queue[0])
                queue.pop(0)
            else:
                queue.append(queue.pop(0))

    # init wires
    simulatedinputs = {each: 0 for each in wire}
    simulatedinputs['VDD'] = 1
    simulatedinputs['GND'] = 0

    # set input values
    for pin in portinputs:
        if pin in inputs:
            simulatedinputs[pin] = inputs[pin]

    # simulate circuit
    for each in correct:
        if each[0] == "NMOS" and simulatedinputs[each[2]] == 1:
            simulatedinputs[each[4]] = simulatedinputs[each[3]]
        if each[0] == "PMOS" and simulatedinputs[each[2]] == 0:
            simulatedinputs[each[4]] = simulatedinputs[each[3]]
        if each[0] == "INST":
            numinputs = len(grabinputs("output/"+each[1]))
            outputs = len(graboutputs("output/"+each[1]))
            input_values = {}

            # get the input names for this instance
            sub_inputs = grabinputs("output/"+each[1])
            # map the instance inputs to the actual values
            for i in range(numinputs):
                input_values[sub_inputs[i]] = simulatedinputs[each[i+3]]

            # recursively simulate the subcircuit
            simulatedoutputs = simulate_circuit("output/"+each[1], input_values)

            # set the outputs
            for i in range(outputs):
                simulatedinputs[each[i+3+numinputs]] = simulatedoutputs[i]

    # return output values
    return [simulatedinputs[pin] for pin in portoutputs]

def readfile(filename, generateTruth):
    # get port information
    portinputs = grabinputs(filename)
    portoutputs = graboutputs(filename)

    # print header
    print(filename)
    print(" ".join(portinputs + portoutputs))

    if generateTruth:
        # generate truth table
        if len(portinputs) > 6:
            print("error: too many inputs to generate truth table")
        else:
            for values in product([0, 1], repeat=len(portinputs)):
                input_dict = {pin: val for pin, val in zip(portinputs, values)}
                output_values = simulate_circuit(filename, input_dict)
                print(" ".join(map(str, values + tuple(output_values))))
    else:
        # get single input case from user
        while True:
            try:
                input_str = input(f"enter values for {', '.join(portinputs)} (sep with spaces 0/1): ")
                input_values = list(map(int, input_str.split()))
                if len(input_values) != len(portinputs):
                    print(f"error: expected {len(portinputs)} inputs")
                    continue
                if any(v not in (0, 1) for v in input_values):
                    print("error: all inputs must be 0 or 1")
                    continue
                break
            except ValueError:
                print("error: please enter numbers only")

        input_dict = {pin: val for pin, val in zip(portinputs, input_values)}
        output_values = simulate_circuit(filename, input_dict)
        print(" ".join(portoutputs))
        print(" ".join(map(str, output_values)))


def simulate(fileName):
    readfile(os.path.splitext(fileName)[0], input("Generate truth table? (y/n): ") == 'y')