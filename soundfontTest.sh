#!/bin/bash

# List of required commands
required_commands=(
  "fluidsynth"
  "timidity"
  "pulseaudio"
  "lame"
  "find"
  "shuf"
  "pgrep"
  "midicsv"  # Optional for metadata handling
)

# Function to check if all required software is installed
check_requirements() {
  missing=()
  for cmd in "${required_commands[@]}"; do
    if ! command -v "$cmd" &>/dev/null; then
      missing+=("$cmd")
    fi
  done

  # Handle missing dependencies
  if (( ${#missing[@]} > 0 )); then
    echo "The following required software is missing:"
    for cmd in "${missing[@]}"; do
      echo "  - $cmd"
    done
    echo "Please install the missing software and try again."
    exit 1
  fi
}

# Run the check at the start of the script
check_requirements

midi_dir=${1:-~/MIDI/}

# Set to false to disable .csv output
debug=false

#Set version
version="1.4"

# Function to display usage
usage() {
  echo " "
  echo "    MIDI Soundfont Testing Program v$version (c)2023"
  echo " "
  echo "    Usage: $0 [options]"
  echo " "
  echo "    Options:"
  echo "          -h        Display this help message"
  echo "          -d DIR    Specify the MIDI directory to use (default: ~/MIDI/)"
  echo " "
  exit 0
}

# Check for parameter
while getopts "hd:" opt; do
  case ${opt} in
    h )
      usage
      ;;
    v )
      debug=true
      ;;
    d )
      midi_dir="$OPTARG"
      ;;
    \? )
      echo "Invalid option: -$OPTARG" 1>&2
      usage
      ;;
  esac
done
shift $((OPTIND -1))

mkdir -p tmp
      temp_dir=$(mktemp -d -p "$(pwd)/tmp")
      echo -e "${grey}Temporary working directory: $temp_dir"

# Kill fluidsynth
killall fluidsynth >/dev/null 2>&1
if pidof pulseaudio; then
  pulseaudio -k
fi

find_midi_files() {
    find "$midi_dir" -type f -iname '*.mid' -o -iname '*.midi'
}

# Function to find SoundFont files
find_sf2_files() {
  find /usr/share/sounds/sf2/ -type f -iname "*.sf2"
}

  # Set color codes for output
  red='\033[3;90m'
  bright_red='\033[0;91m'
  cyan='\033[2;96m'
  magenta='\033[0;35m'
  black='\033[0;30m'
  green='\033[0;32m'
  yellow='\033[0;33m'
  blue='\033[0;34m'
  purple='\033[0;35m'
  white='\033[0;37m'
  grey='\033[0;90m'
  lgrey='\033[3;31m'
  orange='\033[0;33m'
  light_yellow='\e[1;93m'
  highlight='\u001b[46m'
  nocolor='\033[0m'

display_metadata() {
  # Extract the directory and file name from the track path
  track_name=$(basename "$1")
  track_dir=$(basename "$(dirname "$1")")
  
  # Set maximum width for each column
  col_width=30
  
  # Wrap long text using fold command
  sf2_text=$(echo -e "$2" | fold -s -w $col_width)
  track_text=$(echo -e "$track_dir/$track_name" | fold -s -w $col_width)  # Include directory and track name
  next_track_text=$(echo -e "$(basename "$(dirname "$3")")/$(basename "$3")" | fold -s -w $col_width)
  
  # Pad shorter text with spaces to fill the column width
  sf2_text=$(printf "%-${col_width}s" "$sf2_text")
  track_text=$(printf "%-${col_width}s" "$track_text")
  next_track_text=$(printf "%-${col_width}s" "$next_track_text")
  
  # Print table headers
  printf "${blue}%-${col_width}s ${yellow}%-${col_width}s ${magenta}%-${col_width}s ${nocolor}\n" "SoundFont" "Track" "Next Track"
  printf "${blue}%-${col_width}s ${yellow}%-${col_width}s ${magenta}%-${col_width}s ${nocolor}\n" "---------" "-----" "----------"
  
  # Print wrapped and padded text for each row
  for ((i=1; i<=6; i++)); do
    sf2_row=$(echo "$sf2_text" | sed "${i}q;d")
    track_row=$(echo "$track_text" | sed "${i}q;d")
    next_track_row=$(echo "$next_track_text" | sed "${i}q;d")
    printf "${cyan}%-${col_width}s ${light_yellow}%-${col_width}s ${grey}%-${col_width}s ${nocolor}\n" "$sf2_row" "$track_row" "$next_track_row"
  done
  
  # Add empty line at the end
  printf "\n"
}

handle_input() {
    while [ -n "$(pgrep fluidsynth)" ]; do
        read -rsn1 -t 1 input
        if [[ "$input" == "." ]]; then
            echo "next"
            return 0
        elif [[ "$input" == "," ]]; then
            echo "prev"
            return 0
        elif [[ "$input" == "s" ]]; then
            echo "sf2"
            return 0
        elif [[ "$input" == "o" ]]; then
            echo "save"
            return 0
        elif [[ "$input" == "q" ]]; then
            echo "quit"
            return 0
        fi
    done

# If fluidsynth is not running, return an empty string
    echo ""
    return 0
}


# Function to display a menu
display_menu() {
  echo " "
  echo "Controls"
  echo "--------"
  printf "(s)witch soundfont\t(,)previous\t(.)next\t\t(o)utput MP3\t(q)uit"
}

# Function to save the current track as an mp3
save_track() {
  case "$current_track" in
    *.mid) current_track_basename=$(basename "$current_track" .mid);;
    *.MID) current_track_basename=$(basename "$current_track" .MID);;
    *) echo "Error: Invalid file extension for MIDI file.";;
  esac
  current_track_basename=$(basename "$current_track" .mid)
  sf2_basename=$(basename "$current_sf2")
  sf2_basename="${sf2_basename%.*}"
  output_dir="$(dirname "$0")/Output"
  output_file="$output_dir/$current_track_basename-$sf2_basename.mp3"

# Kill fluidsynth to ensure that the correct soundfont is used for conversion
  killall fluidsynth >/dev/null 2>&1

# Create Output folder if it doesn't exist
  if [ ! -d "$output_dir" ]; then
    mkdir "$output_dir"
  fi

  echo "Saving track as $output_file..."
  sf2_current=$(basename "$current_sf2" .sf2)
  fluidsynth -F "$output_dir/$current_track_basename-$sf2_current.wav" "$current_sf2" "$current_track" | lame - "$output_file"
  find "$output_dir" -type f -name '*.wav' | while read file; do
    output_file="${file%.*}.mp3"
    lame "$file" "$output_file"
done
  echo "Track saved to $output_dir."
  echo "Cleaning up temporary files..."
  rm "$output_dir"/*.wav
}

# Function to clean up when the script exits
cleanup() {
  clear
  echo "Deleting Temporary Directories..."
  if [[ -d "$temp_dir" ]]; then
    rm -r "$temp_dir"
  fi
  if [ -d "tmp" ]; then
    rm -r tmp
  fi
  find "." -type d -name 'tmp.*' -exec rm -r {} \; >/dev/null 2>&1
  echo "Stopping running processes..."
  killall fluidsynth
  if pidof pulseaudio; then
    pulseaudio -k
  fi
  echo "Done."
}

# Set up trap to call cleanup function when the script exits
trap cleanup EXIT

shuffled_midi_files=()
while IFS= read -r -d '' file; do
  shuffled_midi_files+=("$file")
done < <(find "$midi_dir" -type f \( -iname "*.mid" -o -iname "*.midi" \) -print0 | shuf -z)

sf2_files=($(find_sf2_files))
current_track_index=0
current_sf2_index=0

play() {
  while true; do
    current_track="${shuffled_midi_files[$current_track_index]}"
    next_track="${shuffled_midi_files[$((current_track_index + 1))]}"
    current_sf2="${sf2_files[$current_sf2_index]}"
    sf2_basename=$(basename "$current_sf2")

    clear

    echo "Midi Soundfont Testing Program v$version"
    echo " "
    echo " "
    display_metadata "$current_track" "$current_sf2" "$next_track"
    echo -e "Track ${yellow}$((current_track_index + 1)) ${nocolor}of ${yellow}${#shuffled_midi_files[@]}${nocolor}"

    echo " "
    
# Display available sf2
    echo -e "${blue}Available Soundfonts${nocolor}"
    echo -e "${blue}--------------------${nocolor}"
    
    sf2_files_list=($(find /usr/share/sounds/sf2/ -type f -iname "*.sf2" -printf "%f\n"))
    sf2_columns=5  # number of columns to display
    sf2_max_per_col=$(( (${#sf2_files_list[@]} + sf2_columns - 1) / sf2_columns ))  # maximum number of items per column
    sf2_width=$(( (90 - sf2_columns + 1) / sf2_columns ))  # width of each column, including the tab character
    
    for (( col=0; col<sf2_columns; col++ )); do
      for (( row=0; row<sf2_max_per_col; row++ )); do
        index=$((col * sf2_max_per_col + row))
        if [[ "$index" -lt "${#sf2_files_list[@]}" ]]; then
          sf2="${sf2_files_list[$index]}"
          if [[ "$sf2" == "$sf2_basename" ]]; then            
# Highlight the current .sf2 file in the list using ANSI color codes
            printf "${nocolor}${highlight}"
          else
            printf "${grey}"
          fi
          printf "%-${sf2_width}s" "$sf2"
          printf "${nocolor}\t"
        else
# Print empty space to fill the last row
          printf "%-${sf2_width}s" ""
          printf "${nocolor}\t"
        fi
      done
      printf "\n"
    done

    echo " "
    if [ -f "trivia.txt" ]; then
      echo -e "${bright_red}Metadata"
      echo -e "--------"
      midicsv "$current_track" > "$temp_dir/data.csv"
      # grep "Text_t" $temp_dir/data.csv | sed 's/.*Text_t, "\(.*\)"/\1/'
metadata=$(strings "$temp_dir/data.csv" | grep -a -E "Text_t|Copyright|Composer|Album|Title|Track_name|Lyrics|Metaeventtext|Marker" \
| sed -E 's/.*"(.*)"/\1/' | grep -v -E '^\s*$' \
| grep -v -E '^[^a-zA-Z0-9]+$' \
| grep -v -E '(Piano|Guitar|Brass|Bass|Drum|Trombone|Violin|Sax|Trumpet|Percussion|Organ|Flute|Clarinet|Harp|Synth|Strings|Vibraphone|Accordion|Timpani|Cello|Contrabass|Fiddle|Voice|Chime|Xylophone|Bell|Cymbal|Tom|Snare|Congas|Tambourine|Oboe|French Horn|Tuba|Sitar|Kalimba|Shamisen|Bagpipe|Maracas|Whistle|Guiro|Claves|Conga|Cuica|Triangle|Woodblock|Bongo)' \
| grep -E '.{4,}')

# Check if metadata is empty
if [ -z "$metadata" ]; then
  echo -e "${bright_red}**NO METADATA AVAILABLE FOR THIS MIDI**${nocolor}"
else
  echo "$metadata"
fi
      
# echo -e "${red}$(shuf -n 1 trivia.txt | tr -d '\r' | sed 's/^ *//;s/ *$//' | sed 's/.\{1\}$//').\033[0m" | fold -s -w 90    
      echo -e "${nocolor} "
    fi
    display_menu
      echo " "

# Start fluidsynth
    fluidsynth -a pulseaudio -m alsa_seq -l -i "$current_sf2" "$current_track" >/dev/null 2>&1 &
    fluidsynth_pid=$!

# notify-send "Soundfont Test Playing" "$current_track"  
    if [ "$debug" = true ]; then
      echo " "

# create tmp directory if it doesn't exist and create temporary directory inside tmp
      mkdir -p tmp
      temp_dir=$(mktemp -d -p "$(pwd)/tmp")
      echo -e "${grey}Temporary working directory: $temp_dir"
      
# convert to CSV
      midicsv "$current_track" > "$temp_dir/data.csv"
      echo -e "Converted .mid to .csv > $temp_dir""/data.csv ${nocolor}"
    fi
  
    input=$(handle_input 2)  # Wait for up to 5 seconds for user input
    if [[ "$input" == "next" ]]; then
      kill $fluidsynth_pid
      current_track_index=$((current_track_index + 1))
    elif [[ "$input" == "prev" ]]; then
      kill $fluidsynth_pid
      current_track_index=$((current_track_index - 1))
    elif [[ "$input" == "quit" ]]; then
      cleanup
      exit 0
    elif [[ "$input" == "save" ]]; then
      save_track
      notify-send "Track saved to MP3" "$current_track"
    elif [[ "$input" == "sf2" ]]; then
      kill $fluidsynth_pid
      current_sf2_index=$((current_sf2_index + 1))
      current_sf2_index=$((current_sf2_index % ${#sf2_files[@]}))
    elif [[ "$input" == "" ]]; then
        kill $fluidsynth_pid
        current_track_index=$((current_track_index + 1))
    fi
  
  done
  
  echo " "
        
}

play
