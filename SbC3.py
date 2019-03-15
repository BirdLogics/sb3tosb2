# Sb3 to Sb2 Converter 
# Version 0.2.0

import argparse
import hashlib
import json
import logging
import zipfile

# Configure the logger for the converter
logging.basicConfig(format="%(levelname)s: %(message)s", level=30)
log = logging.getLogger()

def main(sb3_path, sb2_path, specmap_path="./specmap2.json", overwrite=False, optimize=False, debug=False):
    """Automatically converts a sb3 file and saves it in sb2 format.
    
    sb3_path -- the path to the .sb3 file
    sb2_path -- the save path for the .sb2 file
    specmap_path -- change the load path for the sb3 to sb2 specmap
    overwrite -- allow overwriting existing files
    debug -- save a debug to project.json if overwrite is enabled
    optimize -- try to convert strings to numbers"""

    # Load the sb3 to sb2 specmap
    specmap2 = loadSpecmap(specmap_path)

    # Load the sb3 json
    sb3 = loadProject(sb3_path)

    # Make sure everything loaded correctly
    if sb3 and specmap2:
        # Get the convertor object
        project = Converter(sb3, specmap2)

        # Set optimizations
        project.numberOpt = optimize
        project.spaceOpt = optimize

        # Convert the project
        sb2, filemap = project.convert()

        # Save the project
        saveProject(sb2, filemap, sb2_path, sb3_path, overwrite, debug)
    else:
        log.critical("Failed to load necessary files.")

def loadSpecmap(spec_path="./specmap2.json"):
    """Loads the sb3 to sb2 specmap json and parse it."""
    specmap2_file = None
    try:
        specmap2_file = open(spec_path, "r")
        specmap2 = json.load(specmap2_file)
        return specmap2
    except FileNotFoundError:
        log.warning("Specmap file '%s' not found." % spec_path)
        return False
    except json.decoder.JSONDecodeError:
        log.warning("Ffile '%s' is not a valid json file." % spec_path)
        return False
    except:
        log.error("Unkown error opening '%s'." % spec_path, exc_info=True)
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
        log.warning("Project file '%s' not found." % sb3_path)
        return False
    except zipfile.BadZipFile:
        log.warning("File '%s' is not a valid zip file.")
        return False
    except json.decoder.JSONDecodeError:
        log.warning("File '%s/project.json' is not a valid json file." % sb3_path)
        return False
    except:
        log.error("Unkown error opening '%s'." % sb3_path, exc_info=True)
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

        for i in range(0, 1):
            numId = 0
            for id in filemap[i]:
                # Get the sb3 asset
                asset = filemap[i][id]
                assetId = asset[0]["assetId"]
                name = asset[0]["name"]
                format = asset[0]["dataFormat"]
                md5ext = asset[0]["md5ext"]

                # Load the sb3 asset
                assetFile = sb3_file.read(md5ext)

                # Check the format
                if format == "wav":
                    pass # TODO wav sound resampling
                elif format == "mp3":
                    log.warning("Sound conversion for mp3 '%s' not supported.")
                    continue
                elif format == "png":
                    pass
                elif format == "svg":
                    pass # TODO svg repair
                else:
                    log.warning("Unrecognized file format '%s'" % format)

                # Check the file md5
                md5 = hashlib.md5(assetFile).hexdigest()
                if md5 != assetId:
                    if assetId == group[id][0]["assetId"]:
                        log.warning("The md5 for %s '%s' is invalid.", format, name)
                    else:
                        log.error("The md5 for asset '%s' is invalid.", group[id][0]["assetId"])
                
                # Save sb2 assetId info
                if i == 0: # Sound
                    asset[1]["soundID"] = numId
                    asset[1]["md5"] = assetId + "." + format
                elif i == 1: # Costume
                    asset[1]["baseLayerID"] = numId
                    asset[1]["baseLayerMD5"] = assetId + "." + format
                numId += 1

                # Save the sb2 asset
                fileName2 = str(numId) + "." + format
                sb2_file.writestr(fileName2, assetFile)

        print("Saved to '%s'" % sb2_path)
        return True
    except FileExistsError:
        log.warning("File '%s' already exists. Delete or rename it and try again." % sb2_path)
        return False
    except FileNotFoundError:
        log.warning("File '%s' not found." % sb3_path)
        return False
    except:
        log.error("Unkown error saving to '%s' or reading from '%s'." % (sb2_path, sb3_path), exc_info=True)
        return False
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
    filemap = [{}, {}] # List of sb3 files and their sb2 names

    sprites = [] # Holds the children of the stage
    blockIds = [] # Temporarily holds blockIds for anchoring comments

    # TODO Make space adjustable based on version made in
    spaceX = 1.5 # Size adjustment factor
    spaceY = 2.2 # Works best for projects spaced in sb2

    # TODO Create more optimizations
    numberOpt = False # Try to convert all strings to numbers
    spaceOpt = False # TODO Remove contents of hidden list monitors?

    staticFields = ["sensing_current", # Some fields are all caps for some reason
        "looks_changeeffectby", "looks_seteffectto"] # TODO Add more

    rotationStyles = {"all around": "normal", "left-right":"leftRight", 
                "don't rotate": "none"} # A key for sb3 rotation styles to sb2

    monitorModes = {"default": 1, "large": 2, "slider": 3}

    monitorOpcodes = {
        "sensing_answer": "answer",
        "motion_direction": "heading",
        "looks_size": "scale",
        "sensing_loudness": "soundLevel",
        "music_getTempo": "tempo", 
        "sensing_current": "timeAndDate",
        "sensing_timer": "timer",
        "sound_volume": "volume",
        "motion_xposition": "xpos", 
        "motion_yposition": "ypos"
    }

    monitorColors = {
        "motion": 4877524, "looks": 9065943,
        "sound": 12272323, "music": 12272323,
        "data": 15629590, "sensing": 2926050
    }

    extensions = { # Holds conversion data for extensions
        "wedo2": {"extensionName": "LEGO WeDo 2.0"}
    }

    def __init__(self, project, specmap2):
        """Sets the sb3 project and specmap for the convertor."""
        self.sb3 = project
        self.specmap2 = specmap2
    
    def convert(self):
        """Convert the loaded sb3 project to sb2 format"""
        # Parse all monitors which go with sprites
        self.monitors = []
        for monitor in self.sb3["monitors"]:
            self.monitors.append(self.parseMonitor(monitor))

        # Parse each target(sprite)
        for target in self.sb3["targets"]:
            object = self.parseTarget(target)
            if object["objName"] == "Stage":
                self.sb2 = object
            else:
                self.sprites.append(object)

        # Add the sprites and monitors to the stage
        self.sb2["children"] = self.sprites + self.monitors

        # Add info about this converter and project
        self.sb2["info"] = {
                "userAgent": "sb3tosb2 imfh",
                "flashVersion": "",
                "scriptCount": 0, # TODO Script count
                "videoOn": False,
                "spriteCount": len(self.sprites),
                "swfVersion": ""
        }

        # Add extension information
        extensions = []
        for e in self.sb3["extensions"]:
            if e in self.extensions:
                extensions.append(self.extensions[e])
        if extensions:
            self.sb2["info"]["savedExtensions"] = extensions
    
        return self.sb2, self.filemap

    def parseTarget(self, target):
        """Parses a sb3 target into a sb2 sprite"""
        # Holds the empty target
        sprite = {"objName": target["name"]}

        # Get variables
        variables = []
        for id in target["variables"]:
            var = target["variables"][id]

            if len(var) == 3 and var[2]:
                isCloud = True
            else:
                isCloud = False

            value = var[1]
            value = self.specialNumber(value, self.numberOpt)
            
            variables.append({
                "name": var[0],
                "value": value,
                "isPersistent": isCloud
            })
        if variables:
            sprite["variables"] = variables

        # Get lists
        lists = []
        for id in target["lists"]:
            l = target["lists"][id]

            # Get the monitor related to this list
            if id in self.monitors:
                monitor = self.monitors[id]
            else:
                monitor = None

            # Convert special values and possibly optimize all numbers
            for i in range(0, len(l[1])):
                l[1][i] = self.specialNumber(l[1][i], self.numberOpt)

            lists.append({
                "listName": l[0],
                "contents": l[1],
                "isPersistent": False,
                "x": monitor and monitor["x"] or 5,
                "y": monitor and monitor["y"] or 5,
                "width": monitor and monitor["width"] or 104,
                "height": monitor and monitor["height"] or 204,
                "visible": monitor and monitor["visible"] or False
            })
        if lists:
            sprite["lists"] = lists

        # Get scripts
        self.blockIds = [] # Holds blocks for comment anchoring
        scripts = []
        for id in target["blocks"]:
            block = target["blocks"][id]
            if type(block) == dict:
                if block["topLevel"]:
                    script = self.parseScript(id, target["blocks"])
                    scripts.append(script)
            elif type(block) == list:
                # Handle reporter values not in a block
                script = [
                    round(block[3] / self.spaceX),
                    round(block[4] / self.spaceY),
                    []
                ]

                if block[0] == 12: # Variable reporter
                    script[2].append(["readVariable", block[1]]) # TODO check for hacked blocks
                elif block[0] == 13: # List reporter
                    script[2].append(["contentsOfList:", block[1]])
                
                scripts.append(script)
                self.blockIds.append(id)
                
        if scripts:
            sprite["scripts"] = scripts

        # Get script comments
        comments = []
        for id in target["comments"]:
            comment = target["comments"][id]
            if comment["blockId"] in self.blockIds:
                blockIndex = self.blockIds.index(comment["blockId"])
            else:
                blockIndex = -1
            if comment["x"] == None:
                comment["x"] = 0
            if comment["y"] == None:
                comment["y"] = 0
            comments.append([
                round(comment["x"] / self.spaceX),
                round(comment["y"] / self.spaceY),
                round(comment["width"] / self.spaceX),
                round(comment["height"] / self.spaceY),
                not comment["minimized"],
                blockIndex,
                comment["text"]
            ])
        if comments:
            sprite["scriptComments"] = comments

        # Get sounds
        sounds = []
        for sound in target["sounds"]:
            if sound["assetId"] in self.filemap[0]:
                sound2 = self.filemap[0][sound["assetId"]][1]
            else:
                sound2 = {
                    "soundName": sound["name"],
                    "soundID": len(self.filemap[0]),
                    "md5": sound["md5ext"],
                    "sampleCount": sound["sampleCount"], # TODO These are messed up, sound is high pitched
                    "rate": sound["rate"],
                    "format": "" # TODO Sound format
                }
                self.filemap[0][sound["assetId"]] = [sound, sound2]
            sounds.append(sound2)
        if sounds:
            sprite["sounds"] = sounds

        # Get costumes
        costumes = []
        for costume in target["costumes"]:
            if costume["assetId"] in self.filemap[1]:
                costume2 = self.filemap[1][costume["assetId"]][1]
            else:
                costume2 = {
                    "costumeName": costume["name"],
                    "baseLayerID": len(self.filemap[1]),
                    "BaseLayerMD5": costume["md5ext"],
                    "bitmapResolution": costume["bitmapResolution"],
                    "rotationCenterX": costume["rotationCenterX"],
                    "rotationCenterY": costume["rotationCenterY"]
                }
                self.filemap[1][costume["assetId"]] = [costume, costume2]
            costumes.append(costume2)
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
        
        log.info("Parsed sprite '%s'" %target["name"])

        return sprite

    def parseScript(self, id, blocks):
        """Converts a sb3 script to a sb2 script."""

        # The parsed script to be returned
        script = []
        
        # Holds the sb2 block being parsed
        current = []
        
        # Holds the list which parsed blocks are added to
        chain = []
        
        # Initialize the queue
        self.queue = [[id, chain, True]]

        # Get the position of the script
        script.append(round(blocks[id]["x"] / self.spaceX))
        script.append(round(blocks[id]["y"] / self.spaceY))
        
        # Add the chain to the script
        script.append(chain)

        while self.queue:
            # Get the next block to be parsed
            next = self.queue.pop(0)
            blockId = next[0]
            if next[2]:
                # It's a stack
                current = []
                chain = next[1]
            else:
                # It's just a block
                current = next[1]
                chain = False


            # Save the id for comment anchoring
            self.blockIds.append(blockId)

            # Get the sb3 block
            block3 = blocks[blockId]

            # Get the 3.0 opcode
            opcode = block3["opcode"]

            # Get the specmap for the block, handle custom blocks
            argmap = None
            if opcode == "procedures_definition":
                # Handle custom block definition
                value = block3["inputs"]["custom_block"][1]
                value = blocks[value]["mutation"]
                current.append("procDef")
                current.append(value["proccode"])
                current.append(json.loads(value["argumentnames"]))
                current.append(json.loads(value["argumentdefaults"]))
                if value["warp"] == "true" or value["warp"] == True:
                    current.append(True)
                elif value["warp"] == "false" or value["warp"] == False:
                    current.append(False)
            elif opcode == "procedures_call":
                # Handle custom block call
                value = block3["mutation"]
                current.append("call")
                current.append(value["proccode"])

                # Create a custom argument map
                argmap = []
                for arg in json.loads(value["argumentids"]):
                    argmap.append(["input",arg])
            elif opcode == "argument_reporter_string_number":
                # Handle custom block string/number reporter
                current.append("getParam")
                current.append(block3["fields"]["VALUE"][0])
                current.append("r")
            elif opcode == "argument_reporter_boolean":
                # Handle custom block boolean reporter
                current.append("getParam")
                current.append(block3["fields"]["VALUE"][0])
                current.append("b")
            # Handle some sb3 exclusive workarounds
            elif opcode == "looks_gotofrontback":
                # Handle the new front/back argument
                if block3["fields"]["FRONT_BACK"][0] == "back":
                    current.append("goBackByLayers:")
                    current.append(999)
                else:
                    current.append("comeToFront")
            elif opcode == "looks_goforwardbackwardlayers":
                # Handle the new fowards/back argument
                current.append("goBackByLayers:")
                try:
                    if block3["fields"]["FORWARD_BACKWARD"][0] == "foward":
                        current.append(int(block3["inputs"]["NUM"][1][1]) * -1)
                    else:
                        current.append(block3["inputs"]["NUM"][1][1])
                except:
                    current.append(block3["inputs"]["NUM"][1][1])
            elif opcode == "looks_costumenumbername":
                if block3["fields"]["NUMBER_NAME"][0] == "name":
                    current.append("costumeName") # Undefined block
                else:
                    current.append("costumeIndex")
            elif opcode == "looks_backdropnumbername":
                if block3["fields"]["NUMBER_NAME"][0] == "number":
                    current.append("backgroundIndex")
                else:
                    current.append("sceneName")
            elif opcode == "data_deletealloflist":
                current.append("deleteLine:ofList:")
                current.append("all")
                current.append(block3["fields"]["LIST"][0])
            elif opcode in self.specmap2:
                # Get the sb2 block id
                current.append(self.specmap2[opcode][0])

                # Get the block's argmap
                argmap = self.specmap2[opcode][1]
            else:
                # It's probably a Scratch 3 block that this can't convert
                current.append(opcode)

                # Make a custom argmap for it
                argmap = []
                for field in block3["fields"]:
                    argmap.append(["field",field])
                for input in block3["inputs"]:
                    argmap.append(["input",input])

            if argmap != None:
                # Arguments in the queue counter
                self.q = 0

                # Parse each parameter
                for arg in argmap:
                    if arg[0] == "field":
                        # Get the sb3 field argument
                        value = block3["fields"][arg[1]][0]

                        # Some fields are all caps for some reason
                        if opcode in self.staticFields:
                            value = value.lower()
                    elif arg[0] == "input":
                        if arg[1] in block3["inputs"]:
                            try:
                                # Get the sb3 input argument
                                value = self.parseInput(block3, arg[1], blocks)
                            except:
                                log.error("Argument parsing problem.", exc_info=True)
                                value = block3["inputs"][arg[1]]
                        else:
                            value = None # Empty substacks not always stored?

                    # Add the parsed parameter to the block
                    current.append(value)
            
            # Add the block to the script
            if chain != False:
                chain.append(current)
            
            # Add the next block to the queue
            if block3["next"]:
                self.queue.append([block3["next"], chain, True])
        
        return script

    def parseInput(self, block, inp, blocks):
        # Get the input from the block
        value = block["inputs"][inp]

        # Handle possible block input
        if value[0] == 1: # Wrapper; block or value
            if type(value[1]) == list:
                value = value[1]
            else:
                value = [2, value[1]]
        elif value[0] == 3: # Block covering a value
            value = [2, value[1]]
        if value[0] == 2: # Block
            value = value[1]

            if type(value) != list: # Make sure it's not a variable
                if value in blocks:
                    id = value
                    if blocks[id]["shadow"] and inp in blocks[id]["fields"]:
                        # It's probably be a menu
                        value = blocks[id]["fields"][inp][0]
                    elif inp in ["SUBSTACK", "SUBSTACK2"]:
                        value = []
                        self.queue.insert(self.q, [id, value, True])
                        self.q += 1
                    else:
                        value = []
                        self.queue.insert(self.q, [id, value, False])
                        self.q += 1
                elif value == None:
                    # Blank value in bool input is null in sb3 but false in sb2
                    if not inp in ["SUBSTACK", "SUBSTACK2"]:
                        value = False
                else:
                    log.warning("Invalid block id: 's'" %value)

                return value

        # Handle number values
        if value[0] == 4: # Float value
            value = value[1]
        elif value[0] == 5: # UFloat value
            value = value[1]
        elif value[0] == 6: # UInteger value
            value = value[1]
        elif value[0] == 7: # Integer value
            value = value[1]
        elif value[0] == 8: # Float angle value
            value = value[1]
        elif value[0] == 9: # Hex color value
            try:
                value = int(value[1].strip("#"), 16)
            except ValueError:
                log.warning("Unable to convert hex: '%s'" %value[1])
                value = value[1]
        else:
            # Handle other values
            if value[0] == 10: # String value
                value = value[1]
            elif value[0] == 11: # Broadcast value
                value = value[1]
            elif value[0] == 12: # Variable reporter
                self.blockIds.append(None) # TODO Calculate variable block id
                value = ["readVariable", value[1]]
            elif value[0] == 13: # List reporter
                self.blockIds.append(None)
                value = ["contentsOfList:", value[1]]
            else:
                log.warning("Invalid value type: '%s'" %value[1])

            return value
        
        # It's a number, try to convert it to one
        value = self.specialNumber(value, True)

        return value

    def specialNumber(self, value, toNumber=True):
        """Converts special strings to numbers."""
        if value == "Infinity":
            value = float("Inf")
        elif value == "-Infinity":
            value = float("-Inf")
        elif value == "NaN":
            value = float("NaN")
        elif toNumber:
            try:
                value = float(value)
                if value == int(value):
                    value = int(value)
            except ValueError:
                pass # Normal
        return value

    def parseMonitor(self, monitor):
        """Parse a sb3 monitor into an sb2 monitor."""
        cmd = ""
        param = ""
        if monitor["opcode"] == "data_variable":
            cmd = "getVar:"
            param = monitor["params"]["VARIABLE"]
            color = self.monitorColors["data"]
        elif monitor["opcode"] == "data_listcontents":
            return {
                "listName": monitor["params"]["LIST"],
                "contents": ("value" in monitor and monitor["value"] or []),
                "isPersistent": False,
                "x": monitor["x"],
                "y": monitor["y"],
                "width": monitor["width"],
                "height": monitor["height"],
                "visible": monitor["visible"]
            }
        elif monitor["opcode"] == "looks_costumenumbername":
            if monitor["params"]["NUMBER_NAME"] == "number":
                cmd = "costumeIndex"
                color = self.monitorColors["looks"]
            elif monitor["params"]["NUMBER_NAME"] == "name":
                log.warning("Monitor costume name not supported.")
        elif monitor["opcode"] == "looks_backdropnumbername":
            if monitor["params"]["NUMBER_NAME"] == "number":
                cmd = "backgroundIndex"
            elif monitor["params"]["NUMBER_NAME"] == "name":
                cmd = "sceneName"
            color = self.monitorColors["looks"]
        elif monitor["opcode"] == "sensing_current":
            cmd = "timeAndDate"
            param = monitor["params"]["CURRENTMENU"].lower()
            color = self.monitorColors["sensing"]
        elif monitor["opcode"] in self.monitorOpcodes:
            cmd = self.monitorOpcodes[monitor["opcode"]]
            color = self.monitorColors[monitor["opcode"].split("_")[0]]
        else:
            log.warning("Unkown monitor '%s'" % monitor["opcode"])
            return None # TODO Here

# Run the program if not imported as a module
if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("sb3_path", help="path to the .sb3 projet, defaults to './project.sb3'", nargs="?", default="./project.sb3")
    parser.add_argument("sb2_path", help="path to the .sb2 projet, default gotten from sb3_path", nargs="?", default=None)
    parser.add_argument("specmap", help="path to the specmap json, defaults to './specmap2.json'", nargs="?", default="./specmap2.json")
    parser.add_argument("-s", "--specmap", help="alternate to specmap_path")
    parser.add_argument("-w", "--overwrite", help="overwrite existing files at the sb2 destination", action="store_true")
    parser.add_argument("-d", "--debug", help="save a debug json to './project.json' if overwrite is enabled", action="store_true")
    parser.add_argument("-v", "--verbosity", help="controls printed verbosity", action="count", default=0)
    parser.add_argument("-o", "--optimize", help="try to convert all strings to numbers", action="store_true")
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
    verbosity = args.verbosity
    optimize = args.optimize

    # Get the verbosity level
    if verbosity == 0:
        verbosity = 30
    elif verbosity == 1:
        verbosity = 20
    elif verbosity == 2:
        verbosity = 10
    elif verbosity >= 3:
        verbosity = 0

    # Configure the logger verbosity
    log.level = verbosity

    # Run the converter with these arguments
    main(sb3_path, sb2_path, specmap_path, overwrite, optimize, debug)
