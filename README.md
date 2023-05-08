# MIDI Soundfont Testing Program
This program is designed to be run in a Bash terminal and requires the fluidsynth and lame packages to be installed on your system. It supports playing MIDI files with different SoundFonts and provides basic controls for switching between tracks and SoundFonts. Additionally, it allows for MP3 export via lame. The program is particularly useful for testing .sf2 soundfonts, but can also be used as a general media player for your MIDI files. Optionally, the program can display interesting facts and trivia as you listen.  

<img src="https://user-images.githubusercontent.com/38471159/236817091-e4550aa2-7ecb-4dd3-8378-435185aa818e.png" width="500" height="400">

## Prerequisites
Before using this program, you'll need at least one MIDI file and a .sf2 soundfont. You must also have the following installed:

```
fluidsynth
timidity
pulseaudio
lame (for conversion to .mp3)
find (usually included in most Linux distributions)
shuf (usually included in most Linux distributions)
pgrep (usually included in most Linux distributions)
midicsv (optional to handle metadata)
trivia.txt (optional - place in the working directory of the script)
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

If the program detects `trivia.txt` in the working directory it will display various interesting facts during playback. 

The program will find the first MIDI file in the shuffled list and start playing it using the default SoundFont.
Use the following keys to control the program:

`s` : Switch to the next SoundFont.

`,` : Switch to the previous track.

`.` : Switch to the next track.

`o` : Output current track to MP3 using current soundfont (saved to `/Output/*.mp3`). 

`q` : Quit the program.

## Additional
If the `debug` string is set to `true` the program will also convert the MIDI file to .csv and store them in newly created `tmp/*` folders, which you can view during playback. At this time, this feature is purely for debugging. All temporary folders are deleted on exit.

## Bugs/Other
The program checks for instances of fluidsynth using pgrep. If no psid is found it will skip to the next track and begin playback. This means that if fluidsynth is already running, or if it does not close properly, the automatic playback function will stop working. To fix this use `pgrep fluidsynth` to determine the psid, and kill the process manually before re-running the script.  

## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation.
