# MIDI Soundfont Testing Program
This program is designed to be run in a Bash terminal and requires the fluidsynth and lame packages to be installed on your system. It supports playing MIDI files with different SoundFonts and provides basic controls for switching between tracks and SoundFonts. Additionally, it allows for MP3 export via lame. The program is particularly useful for testing .sf2 soundfonts, but can also be used as a general media player for your MIDI files. Additionally, the program will also attempt to extract and display embedded metadata from each file that is played.   

<img src="https://github.com/user-attachments/assets/40482a18-39b7-4219-9a13-dec6b62b6063" width="500" height="400">

## Prerequisites
Before using this program, you'll need at least one MIDI file and a .sf2 soundfont. You must also have the following installed:

```
fluidsynth
timidity
pulseaudio
libnotify-bin (for desktop notifications)
lame (for conversion to .mp3)
find (usually included in most Linux distributions)
shuf (usually included in most Linux distributions)
pgrep (usually included in most Linux distributions)
midicsv (optional to handle metadata)
binutils (required for strings to function correctly)
```

Additionally, the following system packages _may_ need to be installed:

```
libasound2-dev
libasound2-data
libasound2-plugins
libfluidsynth1
libglib2.0-dev
libjack-dev
libpulse-dev
```

The script looks for MIDI files in the ~/MIDI/ directory by default, and it searches for .sf2 SoundFonts in the /usr/share/sounds/sf2/ directory.

## Usage
### Bash Version
<img src="https://github.com/user-attachments/assets/46b5ff33-af2b-4892-9aef-2d0a69c08c8a" width="500" height="350">

1. Clone the repository or download the `midi_soundfont_test.sh` script.
2. Open a terminal and navigate to the directory where the script is located.
3. Run the script with the following command:

```
./midi_soundfont_test.sh [midi_dir]
```

By default, the program will look for MIDI files in the `~/MIDI/` directory. You can specify a different directory by passing its path as an argument to the script. It will also search for soundfonts in the `/usr/share/sounds/sf2/` directory.

The program will find the first MIDI file in the shuffled list and start playing it using the default SoundFont.
Use the following keys to control the program:

`s` : Switch to the next SoundFont.

`,` : Switch to the previous track.

`.` : Switch to the next track.

`o` : Output current track to MP3 using current soundfont (saved to `/Output/*.mp3`). 

`q` : Quit the program.

### Python Version
<img src="https://github.com/user-attachments/assets/a9b2a34a-bb01-4f91-a1aa-cca0607f4c6f" width="700" height="350">

The Python version provides a graphical interface for testing MIDI files with SoundFonts, and also supports .mod files via xmp (full list of supported filetypes scroll down). To run the Python version, use the following command:


```
python3 soundfontTest.py
```

To fully utilise the script you provided, the following Python dependencies and system requirements are necessary:

### Python Libraries
```
os - Built-in; no installation required.
subprocess - Built-in; no installation required.
threading - Built-in; no installation required.
random - Built-in; no installation required.
signal - Built-in; no installation required.
sys - Built-in; no installation required.
shutil - Built-in; no installation required.
tempfile - Built-in; no installation required.
time - Built-in; no installation required.
requests - Install using pip install requests.
re - Built-in; no installation required.
webbrowser - Built-in; no installation required.
gi (PyGObject) - Install via your package manager (e.g., sudo apt install python3-gi gir1.2-gtk-3.0) or via pip (pip install PyGObject).
Pillow (PIL) - Install using pip install Pillow.
base64 - Built-in; no installation required.
traceback - Built-in; no installation required.
selenium - Install using pip install selenium.
io - Built-in; no installation required.
```

## PyGObject Modules
Ensure these libraries are available, typically through your system's package manager:

`Gtk 3.0 (gi.require_version('Gtk', '3.0'))`
`GdkPixbuf 2.0 (gi.require_version('GdkPixbuf', '2.0'))`
`GObject Introspection`
`GLib`

### External Dependencies

The script depends on several command-line tools and libraries:

`fluidsynth` - Install via your system's package manager (e.g., `sudo apt install fluidsynth`).
`timidity` - Install via your system's package manager.
`strings` (from binutils) - Typically available by default or via `sudo apt install binutils`.
`lame` - Install via your system's package manager (e.g., `sudo apt install lame`).
`find` - Usually pre-installed on Linux.
`shuf` - Provided by the coreutils package (standard on Linux).
`pgrep` - Usually pre-installed.
`midicsv` - Install via your package manager.
`xmp` - Install using sudo apt install xmp.
`openmpt123` - Install via sudo apt install openmpt123.
`mplayer` - Install via your system's package manager (e.g., sudo apt install mplayer).
`chromedriver` - Download from ChromeDriver's official site.

### Notes
Ensure the `chromedriver` version matches your installed Google Chrome version.
Use a modern Linux distribution with access to the required tools.
Some components, like `fluidsynth` and `lame`, require appropriate configurations or paths.

Place `soundfontpy.png` in the root folder. 
Place `image.jpg` (fallback art placeholder) in the root folder. 

Key Features of the Python Version:

- Graphical User Interface (GUI) : The Python version provides a GTK-based GUI for selecting and playing MIDI and MOD packed files.
- SoundFont and Track Switching : Switch between SoundFonts and MIDI tracks using the GUI controls.
- Dark Mode and Shuffle : Options to enable dark mode and shuffle mode for MIDI tracks.
- Image Scraping : (will use image.jpg placed in the media directory if present), will download an image based on the name of the containing folder and save as `image.jpg`. It is best therefore to organise your files into `~/MIDI/{title}/{song}.*` to mitigate random images being displayed.

### Installation Summary
Run the following to install most Python dependencies:

`pip install requests Pillow selenium PyGObject`

Use your system's package manager to install external tools:

`sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-gdkpixbuf-2.0 fluidsynth timidity binutils lame midicsv xmp openmpt123 mplayer`

## Additional
The program will also convert the MIDI file to .csv and store them in newly created `tmp/*` folders, which you can view during playback. All temporary folders are deleted on exit.

## Supported Filetypes

The program will scan `~/`, `~/MIDI`, and `~/MOD` for matching filetypes:
```
.mid, .midi, .mod, .xm, .it, .s3m, .stm, .imf, .ptm, .mdl, .ult, .liq, .masi, .j2b, .amf, .med, .rts, .digi, .sym, .dbm, .qc, .okt, .sfx, .far, .umx, .hmn, .slt, .coco, .ims, .669, .abk, .uni, .gmc
```

## Bugs/Other
Format and content of metadata output results will vary depending on the tags provided, unfortunately there is nothing that can be done to elimenate instruments with uncommon or custom names. Please report any other unexpected bugs!

## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License v3.0 as published by
the Free Software Foundation.
