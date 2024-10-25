# MIDI Soundfont Testing Program
This program is designed to be run in a Bash terminal and requires the fluidsynth and lame packages to be installed on your system. It supports playing MIDI files with different SoundFonts and provides basic controls for switching between tracks and SoundFonts. Additionally, it allows for MP3 export via lame. The program is particularly useful for testing .sf2 soundfonts, but can also be used as a general media player for your MIDI files. Additionally, the program will also attempt to extract and display embedded metadata from each file that is played.   

<img src="https://github.com/user-attachments/assets/a29dbbaf-25dd-4dea-a085-85b1576b840b" width="500" height="400">


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
trivia.txt (optional and no longer used as of v1.4 - place in the working directory of the script)
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

## Usage
<img src="https://user-images.githubusercontent.com/38471159/236703573-3f424a06-1703-40fe-ac5e-98d45266d16e.png" width="500" height="150">

1. Clone the repository or download the `midi_soundfont_test.sh` script.
2. Open a terminal and navigate to the directory where the script is located.
3. Run the script with the following command:

```
./midi_soundfont_test.sh [midi_dir]
```

By default, the program will look for MIDI files in the `~/MIDI/` directory. You can specify a different directory by passing its path as an argument to the script. It will also search for soundfonts in the `/usr/share/sounds/sf2/` directory.

~~If the program detects `trivia.txt` in the working directory it will display various interesting facts during playback.~~ 

The program will find the first MIDI file in the shuffled list and start playing it using the default SoundFont.
Use the following keys to control the program:

`s` : Switch to the next SoundFont.

`,` : Switch to the previous track.

`.` : Switch to the next track.

`o` : Output current track to MP3 using current soundfont (saved to `/Output/*.mp3`). 

`q` : Quit the program.

## Additional
The program will also convert the MIDI file to .csv and store them in newly created `tmp/*` folders, which you can view during playback. All temporary folders are deleted on exit.

## Bugs/Other
Please report any unexpected bugs!

## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation.
