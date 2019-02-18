import json

# Load the sb2 to sb3 specmap file
specmap_file = None
try:
    specmap_file = open("./specmap.json", "r")
    specmap = json.load(specmap_file)
except:
    print("Failed to load './specmap.json'.")
    raise
finally:
    if specmap_file: specmap_file.close()


# Holds the converted specmap
specmap2 = {}

# Convert the specmap
for key in specmap:
    # Get the 3.0 argument names
    args = []
    for arg in specmap[key]["argMap"]:
        argType = arg["type"]
        args.append([argType, arg[argType + "Name"]])
    
    # Add the argument list to specmap2
    specmap2[specmap[key]["opcode"]] = [key, args]

# Add missing blocks
specmap2["event_whengreaterthan"] = [
    "whenSensorGreaterThan", [["field", "WHENGREATERTHANMENU"], ["input", "VALUE"]]
]

# Save the sb3 to sb2 specmap file
specmap2_file = None
try:
    specmap2_file = open("./specmap2.json", "w")
    json.dump(specmap2, specmap2_file, indent=4, separators=(',', ': '))
    print("Saved to './specmap2.json'.")
except:
    print("Failed to save './specmap2.json'.")
    raise
finally:
    if specmap2_file: specmap2_file.close()