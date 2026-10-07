# FC26

Standalone Windows desktop utility for bulk editing player PlayStyles in FC26 roster exports.

## What it does

- Imports CSV rosters and JSON player lists (`[{...}]` or `{"players": [{...}]}`).
- Adds or replaces base PlayStyles and PlayStyle+ selections for every player record.
- Keeps other JSON properties and CSV columns, previews the first six players, and exports to a new file by default.
- Supports custom style names. The built-in library is a convenience list, not an authoritative FC26 database.
- Creates a `.bak` file before an explicitly confirmed overwrite of the source.

The interchange fields are `playstyles` and `playstyles_plus`. JSON stores each as an array of style-name strings. CSV stores each as a semicolon-separated string. Existing string fields may also use semicolons or pipes.

**Native game files are not edited.** FC26 squad, database, and career-save formats are not interchangeable with this roster format. Export a compatible CSV/JSON roster from your modding workflow, edit it here, then use the appropriate game/mod tool to import it. This app does not patch the game executable or inject changes into a running game.

## Run from source

Requires Python 3 with Tkinter.

```sh
python playstyle_tool.py
```

## Build the Windows app

On Windows, install Python 3 and run `build_windows.bat` from this folder. It installs PyInstaller and creates the standalone `dist\FC26PlaystyleEditor.exe`; Python is not needed on the target PC. The build script must be run on Windows to produce a Windows executable.

## Tests

```sh
python -m unittest -v test_playstyle_tool.py
```
