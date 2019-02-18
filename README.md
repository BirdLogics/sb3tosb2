# sb3tosb2
Converter for sb3 files to sb2 files

## Instructions
1. Download SbC3.py and specmap2.json into the same folder.
2. Put the .sb3 file in the same folder and name it 'project.sb3'
3. Run SbC3.py with Python 3. It is possible that it will work with Python 2.
4. It will save to 'project.sb2' provided there is not already a file in that location. 

For more advanced usage, such as with diffrent file names, run 'python SbC.py -h'.

## Limitations
- Limited and buggy support for monitors
- Limited and possibly buggy support for comments
- Maximum depth of 1000 embeded blocks due to usage of python recursion
- Sound rate and samples is corrupted resulting in a higher pitch
- Work in progress, as such may be buggy

## TODO
- [ ] Finish monitor support
- [ ] Finish comment support
- [ ] Find and fix any bugs
- [ ] Cleanup code
