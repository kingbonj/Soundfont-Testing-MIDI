# MIDI Soundfont Testing Program
This program is designed to be run in a Bash terminal and requires the fluidsynth and lame packages to be installed on your system. It supports playing MIDI files with different SoundFonts and provides basic controls for switching between tracks and SoundFonts. Additionally, it allows for MP3 export via lame. The program is particularly useful for testing .sf2 soundfonts, but can also be used as a general media player for your MIDI files. Optionally, the program can display interesting facts and trivia as you listen.  

![Screenshot 2023-05-07 22 30 54](https://user-images.githubusercontent.com/38471159/236703500-fe44802b-1469-4476-b8dc-ae6841e0b899.png)

## Prerequisites
Before using this program, you'll need to have the following installed:

```
fluidsynth
timidity
lame (for conversion to .mp3)
midicsv (to handle metadata)
find (usually included in most Linux distributions)
shuf (usually included in most Linux distributions)
pgrep (usually included in most Linux distributions)
trivia.txt (optional - place in the working directory of the script)
```


## Usage
![Screenshot 2023-05-07 22 33 07](https://user-images.githubusercontent.com/38471159/236703573-3f424a06-1703-40fe-ac5e-98d45266d16e.png)

1. Clone the repository or download the `midi_soundfont_test.sh` script.
2. Open a terminal and navigate to the directory where the script is located.
3. Run the script with the following command:

```
./midi_soundfont_test.sh [midi_dir]
```

By default, the program will look for MIDI files in the `~/MIDI/` directory. You can specify a different directory by passing its path as an argument to the script. It will also search for soundfonts in the `/usr/share/sounds/sf2/` directory.

If the program detects `trivia.txt` in the working directory it will display various interesting facts during playback. 

The program will display the metadata for the first MIDI file in the shuffled list and start playing it using the default SoundFont.
Use the following keys to control the program:

`s` : Switch to the next SoundFont.

`,` : Switch to the previous track.

`.` : Switch to the next track.

`o` : Output current track to MP3 using current soundfont (saved to `/Output/*.mp3`). 

`q` : Quit the program.

## Additional
The program will convert the MIDI file to .csv and store them in newly created `tmp/*` folders, which you can view during playback. This is purely for debugging, as all temporary folders are deleted on exit.

## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation.
