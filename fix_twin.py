import sys

lines = open('roof_hunter/src/weather_twin/roof_hunter_digital_twin.py').readlines()
with open('roof_hunter/src/weather_twin/roof_hunter_digital_twin.py', 'w') as f:
    skip = False
    for i, line in enumerate(lines):
        if i + 1 == 400: # if best_cell:
            f.write(line)
            skip = True
            continue
        if skip:
            if "if dist < 10:" in line: # End of my messy insert
                 f.write("            " + line.strip() + "\n")
                 skip = False
            continue
        f.write(line)
