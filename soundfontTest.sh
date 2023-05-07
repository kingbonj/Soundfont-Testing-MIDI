#!/bin/bash
espeak "welcome"
midi_dir=${1:-~/MIDI/}

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

display_metadata() {
  # Set color codes for output
  red='\033[0;31m'
  bright_red='\033[0;91m'
  cyan='\033[0;36m'
  magenta='\033[0;35m'
  black='\033[0;30m'
  green='\033[0;32m'
  yellow='\033[0;33m'
  blue='\033[0;34m'
  purple='\033[0;35m'
  white='\033[0;37m'
  grey='\033[0;90m'    # Grey color code
  orange='\033[0;33m'  # Orange color code
  light_yellow='\e[93m'
  nocolor='\033[0m'
  
  # Reset color code
  nocolor='\033[0m'
  
  # Set maximum width for each column
  col_width=30
  
  # Wrap long text using fold command
  sf2_text=$(echo -e "$2" | fold -s -w $col_width)
  track_text=$(echo -e "$1" | fold -s -w $col_width)
  next_track_text=$(echo -e "${3:-None}" | fold -s -w $col_width)
  
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
  echo "(s)witch soundfont (,)previous (.)next (o)utput MP3 (q)uit"
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

    clear

    echo ""
    echo "╔╦╗╦╔╦╗╦  ╔═╗┌─┐┬ ┬┌┐┌┌┬┐┌─┐┌─┐┌┐┌┌┬┐       ╔╦╗┌─┐┌─┐┌┬┐"
    echo "║║║║ ║║║  ╚═╗│ ││ ││││ ││├┤ │ ││││ │   ───   ║ ├┤ └─┐ │   v1.3.0"
    echo "╩ ╩╩═╩╝╩  ╚═╝└─┘└─┘┘└┘─┴┘└  └─┘┘└┘ ┴         ╩ └─┘└─┘ ┴ "
    echo ""
    echo ""
    display_metadata "$current_track" "$current_sf2" "$next_track"
    
    echo " "
    if [ -f "trivia.txt" ]; then
      echo -e "${bright_red}Trivia"
      echo -e "------"
      echo -e "${red}$(shuf -n 1 trivia.txt | tr -d '\r' | sed 's/^ *//;s/ *$//' | sed 's/.\{1\}$//').\033[0m" | fold -s -w 90
      echo " "
    fi
    display_menu
    echo " "

    # Start fluidsynth
    fluidsynth -a pulseaudio -m alsa_seq -l -i "$current_sf2" "$current_track" >/dev/null 2>&1 &
    fluidsynth_pid=$!
    
    # Create a temporary directory for split MIDI files.
    if [ ! -d "tmp" ]; then
      mkdir tmp
    fi
    temp_dir=$(mktemp -d -p "$(pwd)/tmp")
    
    # Convert the input file to csv.
    midicsv "$current_track" > "$temp_dir/data.csv"
    
    input=$(handle_input 5)  # Wait for up to 5 seconds for user input
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
    elif [[ "$input" == "sf2" ]]; then
      kill $fluidsynth_pid
      current_sf2_index=$((current_sf2_index + 1))
      current_sf2_index=$((current_sf2_index % ${#sf2_files[@]}))
    elif [[ "$input" == "" ]]; then
        kill $fluidsynth_pid
        current_track_index=$((current_track_index + 1))
    fi

  done
}

play


