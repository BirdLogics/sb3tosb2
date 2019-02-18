# Sb3 to Sb2 Converter 
# Version 0.1.1

import argparse
import json
import zipfile

def main(sb3_path, sb2_path, specmap_path="./specmap2.json", overwrite=False, debug=False):
    """Automatically converts a sb3 file and saves it in sb2 format.
    
    sb3_path -- the path to the .sb3 file
    sb2_path -- the save path for the .sb2 file
    specmap_path -- change the load path for the sb3 to sb2 specmap
    overwrite -- allow overwriting existing files'
    debug -- save a debug to project.json if overwrite is enabled"""

    # Load the sb3 to sb2 specmap
    specmap2 = loadSpecmap(specmap_path)

    # Load the sb3 json
    sb3 = loadProject(sb3_path)

    # Make sure everything loaded correctly
    if sb3 and specmap2:
        # Convert the project
        project = Converter(sb3, specmap2)
        sb2, filemap = project.convert()

        # Save the project
        saveProject(sb2, filemap, sb2_path, sb3_path, overwrite, debug)
    else:
        print("Failed to load necessary files.")

def loadSpecmap(spec_path="./specmap2.json"):
    """Loads the sb3 to sb2 specmap json and parse it."""
    specmap2_file = None
    try:
        specmap2_file = open(spec_path, "r")
        specmap2 = json.load(specmap2_file)
        return specmap2
    except FileNotFoundError:
        print("Specmap file '%s' not found." % spec_path)
        return False
    except json.decoder.JSONDecodeError:
        print("Ffile '%s' is not a valid json file." % spec_path)
        return False
    except:
        print("Unkown error opening '%s'." % spec_path)
        raise
    finally:
        if specmap2_file: specmap2_file.close()

def loadProject(sb3_path):
    """Load a sb3 project and return the parsed project json."""
    sb3_file = None
    try:
        sb3_file = zipfile.ZipFile(sb3_path, "r")
        sb3_json = sb3_file.read("project.json")
        sb3 = json.loads(sb3_json)
        return sb3
    except FileNotFoundError:
        print("Project file '%s' not found." % sb3_path)
        return False
    except zipfile.BadZipFile:
        print("File '%s' is not a valid zip file.")
        return False
    except json.decoder.JSONDecodeError:
        print("File '%s/project.json' is not a valid json file." % sb3_path)
        return False
    except:
        print("Unkown error opening '%s'." % sb3_path)
        raise
    finally:
        if sb3_file: sb3_file.close()
    return False

def saveProject(sb2, filemap, sb2_path, sb3_path, overwrite=False, debug=False):
    """Create and save a sb2 zip from the converted project and sb3 zip."""
    sb2_file = None
    sb2_jfile = None
    sb3_file = None

    # Save the results
    try:
        # Get the sb2 json string
        sb2_json = json.dumps(sb2, indent=4, separators=(',', ': '))

        if overwrite:
            # Open and overwrite existing files
            sb2_file = zipfile.ZipFile(sb2_path, "w")

            if debug:
                # Save a copy of the json
                sb2_jfile = open("project.json", "w")
                sb2_jfile.write(sb2_json)
                print("Saved debug to 'project.json'.")
        else:
            # Will throw an error if a file already exists
            sb2_file = zipfile.ZipFile(sb2_path, "x")
        
        # Save the sb2 json
        sb2_file.writestr("project.json", sb2_json)

        # Open the .sb3 to get its assets
        sb3_file = zipfile.ZipFile(sb3_path, "r")

        for group in filemap:
            for i in range(0, len(group)):
                # Get the file names
                fileName3 = group[i]
                fileName2 = str(i) + "." + fileName3.split(".")[-1]

                f = sb3_file.read(fileName3)
                sb2_file.writestr(fileName2, f)

        print("Saved to '%s'" % sb2_path)
        return True
    except FileExistsError:
        print("File '%s' already exists. Delete or rename it and try again." % sb2_path)
        return False
    except FileNotFoundError:
        print("File '%s' not found." % sb3_path)
        return False
    except:
        print("Unkown error saving to '%s' or reading from '%s'." % (sb2_path, sb3_path))
        raise
    finally:
        if sb2_file: sb2_file.close()
        if sb2_jfile: sb2_jfile.close()
        elif debug: print("Did not save debug json to 'project.json'.")
        if sb3_file: sb3_file.close()

class Converter:
    """Class for converting a sb3 project json to the sb2 format"""

    sb3 = {} # The sb3 project json
    sb2 = {} # The sb2 project json
    specmap2 = {} # A specmap for sb3 to sb2
    filemap = [[],[]] # List of the sb3 files and their sb2 names

    rotationStyles = {"all around": "normal", "left-right":"leftRight", 
                    "don't rotate": "none"} # A key for sb3 rotation styles to sb2

    sprites = [] # Holds the children of the stage
    monitors = {} # Holds monitors and their positions

    blocks = {} # Holds blockIds for connecting comments
    blockCount = 0 # Count for comments

    staticFields = ["sensing_current", # Some fields are all caps for some reason with these
        "looks_changeeffectby", "looks_seteffectto"]

    def __init__(self, project, specmap2):
        """Sets the sb3 project and specmap for the convertor."""
        self.sb3 = project
        self.specmap2 = specmap2
    
    def convert(self):
        """Convert the loaded sb3 project to sb2 format"""
        # Get the monitors for use with lists
        for monitor in self.sb3["monitors"]:
            if monitor["opcode"] == "data_variable":
                self.monitors[monitor["id"]] = {
                    "target": "",
                    "cmd": "getVar:",
                    "param": monitor["params"]["VARIABLE"],
                    "color": 15629590,
                    "label": "",
                    "mode": 1, # TODO Monitor modes
                    #"sliderMin": monitor["min"],
                    #"sliderMax": monitor["max"],
                    "isDiscrete": True, # TODO Is this in 3.0? (Only ints)
                    "x": monitor["x"],
                    "y": monitor["y"],
                    "visible": monitor["visible"]
                }
            elif monitor["opcode"] == "data_listcontents":
              self.monitors[monitor["id"]] = {
                    "listName": monitor["params"]["LIST"],
                    "contents": [],
                    "isPersistent": False,
                    "x": monitor["x"],
                    "y": monitor["y"],
                    "width": monitor["width"],
                    "height": monitor["height"],
                    "visible": monitor["visible"]
                }
            else:
                pass # TODO Monitors for sound volume, etc.

        # Parse each target(sprite)
        for target in self.sb3["targets"]:
            object = self.parseTarget(target)
            if object["objName"] == "Stage":
                self.sb2 = object
            else:
                self.sprites.append(object)

        # Add the sprites and monitors to the stage
        monitors = list(self.monitors.values())
        self.sb2["children"] = self.sprites + monitors

        # Add info about this converter
        self.sb2["info"] = {
                "userAgent": "sb3 to sb2 imfh v0.0.3",
                "flashVersion": "",
                "scriptCount": 0, # TODO Script count
                "videoOn": False,
                "spriteCount": len(self.sprites),
                "swfVersion": ""
        }
    
        return self.sb2, self.filemap

    def parseTarget(self, target):
        """Parses a sb3 target into a sb2 sprite"""
        # Holds the empty target
        sprite = {"objName": target["name"]}

        # Get variables
        variables = []
        for id in target["variables"]:
            var = target["variables"][id]
            isCloud = False
            if len(var) == 3 and var[2]:
                isCloud = True
            variables.append({
                "name": var[0],
                "value": var[1],
                "isPersistent": isCloud
                })
            if id in self.monitors:
                self.monitors[id]["target"] = target["name"]
        if variables:
            sprite["variables"] = variables
        # TODO Variable monitors

        # Get lists
        lists = []
        for id in target["lists"]:
            if id in self.monitors:
                l = target["lists"][id]
                #self.monitors[id]["listName"] = l[0]
                self.monitors[id]["contents"] = l[1] # TODO Is this repeated?
                lists.append(self.monitors[id])
            else:
                l = target["lists"][id]
                lists.append({
                    "listName": l[0],
                    "contents": l[1],
                    "isPersistent": False,
                    "x": 5,
                    "y": 5,
                    "width": 105,
                    "height": 179,
                    "visible": False
                })
        if lists:
            sprite["lists"] = lists

        # Reset the blockId list
        self.blocks = {}
        self.blockCount = 0

        # Get scripts
        scripts = []
        for id in target["blocks"]:
            block = target["blocks"][id]
            if type(block) == dict:
                if block["topLevel"]:
                    script = self.parseScript(id, target["blocks"])
                    scripts.append(script)
            elif type(block) == list:
                script = []
                script.append(round(block[3] / 1.5))
                script.append(round(block[4] / 2.2))
                script.append([])

                # Handle reporters not in a block
                if block[0] == 12:
                    # Get the variable
                    script[2].append(["readVariable", block[1]])
                elif block[0] == 13:
                    # Get the list
                    script[2].append(["contentsOfList:", block[1]])
                scripts.append(script)
                
        if scripts:
            sprite["scripts"] = scripts

        # Get script comments
        comments = []
        for id in target["comments"]:
            comment = target["comments"][id]
            #if comment["blockId"] in self.blocks:
                #blockIndex = self.blocks[comment["blockId"]
            #else:
            blockIndex = -1 # TODO Connected comments
            if comment["x"] == None:
                comment["x"] = 0
            if comment["y"] == None:
                comment["y"] = 0
            comments.append([
                round(comment["x"] / 1.5),
                round(comment["y"] / 2.2),
                round(comment["width"] / 1.5),
                round(comment["height"] / 2.2),
                not comment["minimized"],
                blockIndex,
                comment["text"]
            ])
        if comments:
            sprite["scriptComments"] = comments

        # Get sounds
        sounds = []
        for sound in target["sounds"]:
            if not sound["md5ext"] in self.filemap[0]:
                self.filemap[0].append(sound["md5ext"])
            sounds.append({
                "soundName": sound["name"],
                "soundID": self.filemap[0].index(sound["md5ext"]),
                "md5": sound["md5ext"],
                "sampleCount": sound["sampleCount"], # TODO These are messed up, sound is high pitched
                "rate": sound["rate"],
                "format": "" # TODO Sound format?
            })
        if sounds:
            sprite["sounds"] = sounds

        # Get costumes
        costumes = []
        for costume in target["costumes"]:
            if not costume["md5ext"] in self.filemap[1]:
                self.filemap[1].append(costume["md5ext"])
            if "bitmapResolution" in costume:
                costumes.append({
                    "costumeName": costume["name"],
                    "baseLayerID": self.filemap[1].index(costume["md5ext"]),
                    "BaseLayerMD5": costume["md5ext"],
                    "bitmapResolution": costume["bitmapResolution"],
                    "rotationCenterX": costume["rotationCenterX"],
                    "rotationCenterY": costume["rotationCenterY"]
                })
            else:
                costumes.append({
                    "costumeName": costume["name"],
                    "baseLayerID": self.filemap[1].index(costume["md5ext"]),
                    "baseLayerMD5": costume["md5ext"],
                    "rotationCenterX": costume["rotationCenterX"],
                    "rotationCenterY": costume["rotationCenterY"]
                })
        sprite["costumes"] = costumes

        # Get other attributes
        sprite["currentCostumeIndex"] = target["currentCostume"]
        
        if not target["isStage"]:
            sprite["scratchX"] = target["x"]
            sprite["scratchY"] = target["y"]
            sprite["scale"] = round(target["size"] / 100)
            sprite["direction"] = target["direction"]
            if target["rotationStyle"] in self.rotationStyles:
                sprite["rotationStyle"] = self.rotationStyles[target["rotationStyle"]]
            else:
                sprite["rotationStyle"] = target["rotationStyle"]
            sprite["isDraggable"] = target["draggable"]
            sprite["indexInLibrary"] = len(self.sprites) + 1
            sprite["visible"] = target["visible"]
            sprite["spriteInfo"] = {} # Always blank
        else:
            sprite["penLayerMD5"] = "" # TODO Is there a pen MD5 in sb3?
            sprite["penLayerID"] = target["layerOrder"]
            sprite["tempoBPM"] = target["tempo"]
            sprite["videoAlpha"] = round((100 - target["videoTransparency"]) / 100, 2)

        return sprite

    def parseScript(self, id, blocks):
        """Converts a sb3 script to a sb2 script."""

        # Holds the parsed script
        script = []

        # The parsed blocks
        blocks2 = []

        # The current block being parsed
        block = blocks[id]

        # A list of blocks for connected comments
        blockIds = []

        # Check if the block is top level
        if block["topLevel"]:
            # Get the position of the script
            script.append(round(block["x"] / 1.5))
            script.append(round(block["y"] / 2.2))
            topLevel = True
            self.blocks[id] = self.blockCount
            self.blockCount += 1
        else:
            topLevel = False

        while block:
            # Holds the parsed block
            block2 = []

            # Get the 3.0 opcode
            opcode = block["opcode"]

            # Get the specmap for the block, handle custom blocks
            argmap = None
            if opcode == "procedures_definition":
                # Handle custom block definition
                value = block["inputs"]["custom_block"][1]
                value = blocks[value]["mutation"]
                block2.append("procDef")
                block2.append(value["proccode"])
                block2.append(json.loads(value["argumentnames"]))
                block2.append(json.loads(value["argumentdefaults"]))
                block2.append(value["warp"])
            elif opcode == "procedures_call":
                # Handle custom block call
                value = block["mutation"]
                block2.append("call")
                block2.append(value["proccode"])

                # Create a custom argument map
                argmap = []
                for arg in json.loads(value["argumentids"]):
                    argmap.append(["input",arg])
            elif opcode == "argument_reporter_string_number":
                # Handle custom block string/number reporter
                block2.append("getParam")
                block2.append(block["fields"]["VALUE"][0])
                block2.append("r")
            elif opcode == "argument_reporter_boolean":
                # Handle custom block boolean reporter
                block2.append("getParam")
                block2.append(block["fields"]["VALUE"][0])
                block2.append("b")
            # Handle some sb3 exclusive workarounds
            elif opcode == "looks_gotofrontback":
                # Handle the new front/back argument
                if block["fields"]["FRONT_BACK"][0] == "back":
                    block2.append("goBackByLayers:")
                    block2.append(999)
                else:
                    block2.append("comeToFront")
            elif opcode == "looks_goforwardbackwardlayers":
                # Handle the new fowards/back argument
                block2.append("goBackByLayers:")
                try:
                    if block["fields"]["FORWARD_BACKWARD"][0] == "foward":
                        block2.append(int(block["inputs"]["NUM"][1][1]) * -1)
                    else:
                        block2.append(block["inputs"]["NUM"][1][1])
                except:
                    block2.append(block["inputs"]["NUM"][1][1])
            elif opcode == "looks_costumenumbername":
                if block["fields"]["NUMBER_NAME"][0] == "name":
                    block2.append("costumeName") # Undefined block
                else:
                    block2.append("costumeIndex")
            elif opcode == "looks_backdropnumbername":
                if block["fields"]["NUMBER_NAME"][0] == "number":
                    block2.append("backgroundIndex")
                else:
                    block2.append("sceneName")
            elif opcode in self.specmap2:
                # Get the sb2 block id
                block2.append(self.specmap2[opcode][0])

                # Get the block's argmap
                argmap = self.specmap2[opcode][1]
            else:
                # It's probably a Scratch 3 block that this can't convert
                block2.append(opcode)

                # Make a custom argmap for it
                argmap = []
                for field in block["fields"]:
                    argmap.append(["field",field])
                for input in block["inputs"]:
                    argmap.append(["input",input])

            if argmap != None:
                # Loop through each parameter and parse it
                for arg in argmap:
                    if arg[0] == "field":
                        # Get the sb3 field argument
                        value = block["fields"][arg[1]][0]

                        # Some fields are all caps for some reason
                        if opcode in self.staticFields:
                            value = value.lower()
                    elif arg[0] == "input":
                        # Get the sb3 input argument
                        value = block["inputs"][arg[1]]

                        # Parse the input
                        value = value[1]
                        if type(value) == list:
                            if value[0] == 1:
                                if value[1] == None:
                                    value = False
                                else:
                                    value = value[1]
                            if value[0] == 9:
                                # Convert the hex color to decimal
                                value = int(value[1].strip("#"), 16)
                            elif value[0] == 12:
                                # Get the variable
                                value = ["readVariable", value[1]]
                            elif value[0] == 13:
                                # Get the list
                                value = ["contentsOfList:", value[1]]
                            else:
                                value = value[1]
                        elif value in blocks:
                            if blocks[value]["shadow"]:
                                # It is probably a menu TODO Menu testing
                                value = blocks[value]["fields"][arg[1]][0]
                            else:
                                if arg[1] in ["SUBSTACK", "SUBSTACK2"]:
                                    self.blockCount += 1
                                    value = self.parseScript(value, blocks)
                                else:
                                    value = self.parseScript(value, blocks)
                                    value = value[0] # TODO Always works?
                        elif not arg[1] in ["SUBSTACK", "SUBSTACK2"] and value == None:
                            # Blank value in bool input is null in sb3 but false in sb2
                            value = False
                        else:
                            pass
                    else:
                        raise Exception("Invalid argmap")

                    # Add the parsed parameter to the block
                    block2.append(value)

            # Add the block to the script
            blocks2.append(block2)

            # Get the next block
            if block["next"]:
                block = blocks[block["next"]]
            else:
                block = False

        if topLevel:
            # Add the blocks to the script
            script.append(blocks2)
        else:
            # This was called recursively
            script = blocks2

        return script

# Run the program if not imported as a module
if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("sb3_path", help="path to the .sb3 projet, defaults to './project.sb3'", nargs="?", default="./project.sb3")
    parser.add_argument("sb2_path", help="path to the .sb2 projet, default gotten from sb3_path", nargs="?", default=None)
    parser.add_argument("specmap", help="path to the specmap json, defaults to './specmap2.json'", nargs="?", default="./specmap2.json")
    parser.add_argument("-s", "--specmap", help="alternate to specmap_path")
    parser.add_argument("-o", "--overwrite", help="overwrite existing files at the sb2 destination", action="store_true")
    parser.add_argument("-d", "--debug", help="save a debug json to './project.json' if overwrite is enabled", action="store_true")
    args = parser.parse_args()
    
    # A bit more parsing
    sb3_path = args.sb3_path
    if args.sb2_path:
        sb2_path = args.sb2_path
    else:
        sb2_path = sb3_path.split(".")
        sb2_path[-1] = "sb2"
        sb2_path = '.'.join(sb2_path)
    specmap_path = args.specmap
    overwrite = args.overwrite
    debug = args.debug

    # Run the converter with these arguments
    main(sb3_path, sb2_path, specmap_path, overwrite, debug)