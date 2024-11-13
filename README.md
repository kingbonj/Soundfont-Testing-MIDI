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
<img src="https://github.com/user-attachments/assets/ab5af1a0-a722-4707-826d-a28347b0b9f5" width="700" height="350">

The Python version provides a graphical interface for testing MIDI files with SoundFonts. To run the Python version, use the following command:

```
python3 soundfontTest.py
```

Ensure that the following dependencies are installed:

```
Python 3
PyGObject (to provide GTK support)
fluidsynth, timidity, lame, midicsv, shuf, and other system tools as required in the Bash version)
```

Key Features of the Python Version:

- Graphical User Interface (GUI) : The Python version provides a GTK-based GUI for selecting and playing MIDI files.
- SoundFont and Track Switching : Switch between SoundFonts and MIDI tracks using the GUI controls.
- Dark Mode and Shuffle : Options to enable dark mode and shuffle mode for MIDI tracks.
![Screenshot 2024-11-13 18 15 52]()

## Additional
The program will also convert the MIDI file to .csv and store them in newly created `tmp/*` folders, which you can view during playback. All temporary folders are deleted on exit.

## Bugs/Other
Format and content of metadata output results will vary depending on the tags provided, unfortunately there is nothing that can be done to elimenate instruments with uncommon or custom names. Please report any other unexpected bugs!

## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License v3.0 as published by
the Free Software Foundation.
