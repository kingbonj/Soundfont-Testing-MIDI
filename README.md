# MIDI Soundfont Testing Program
This is a Bash script that allows you to test a shuffled list of MIDI files with different SoundFonts. The program uses the fluidsynth command to play the MIDI files using the selected SoundFont and provides basic controls for switching between tracks and SoundFonts.

![screenshot](https://user-images.githubusercontent.com/38471159/234487823-ca5a4607-19d1-4a57-8936-eab800aab94b.png)

## Prerequisites
Before using this program, you'll need to have the following installed:

```
fluidsynth
timidity
lame (for conversion and output not yet implemented)
find (usually included in most Linux distributions)
shuf (usually included in most Linux distributions)
```


## Usage
1. Clone the repository or download the `midi_soundfont_test.sh` script.
2. Open a terminal and navigate to the directory where the script is located.
3. Run the script with the following command:

```
./midi_soundfont_test.sh [midi_dir]
```

By default, the program will look for MIDI files in the `~/MIDI/` directory. You can specify a different directory by passing its path as an argument to the script. It will also search for soundfonts in the `/usr/share/sounds/sf2/` directory.

The program will display the metadata for the first MIDI file in the shuffled list and start playing it using the default SoundFont.
Use the following keys to control the program:

s: Switch to the next SoundFont.
,: Switch to the previous track.
.: Switch to the next track.
q: Quit the program.

## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation.
