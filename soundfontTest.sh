#!/bin/bash

# List of required commands
required_commands=(
  "fluidsynth"
  "timidity"
  "strings"
  "lame"
  "find"
  "shuf"
  "pgrep"
  "midicsv"
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
    echo "Please install the missing software and try again. Note 'strings' is part of the 'binutils' package"
    exit 1
  fi
}

# Run the check at the start of the script
check_requirements

midi_dir=${1:-~/MIDI/}

# Set to false to disable .csv output
debug=false

# Set version
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
red=$'\033[3;90m'
bright_red=$'\033[0;91m'
cyan=$'\033[2;96m'
magenta=$'\033[0;35m'
black=$'\033[0;30m'
green=$'\033[0;32m'
yellow=$'\033[0;33m'
blue=$'\033[0;34m'
purple=$'\033[0;35m'
white=$'\033[0;37m'
grey=$'\033[0;90m'
lgrey=$'\033[3;31m'
orange=$'\033[1;33m'
light_yellow=$'\033[1;93m'
highlight=$'\033[46m'
nocolor=$'\033[0m'

# Function to repeat a character
repeat_char() {
  for ((i=0; i<$1; i++)); do
    printf '%s' "$2"
  done
}

display_metadata() {
  # Set fixed content widths for columns
  content_width_sf2=28
  content_width_track=28
  content_width_next_track=28

  # Total column widths including padding and borders
  col_width_sf2=$((content_width_sf2 + 2))         # Add padding spaces
  col_width_track=$((content_width_track + 2))
  col_width_next_track=$((content_width_next_track + 2))

  # Extract the directory and file name from the track path
  track_name=$(basename "$1")
  track_dir=$(basename "$(dirname "$1")")

  # Prepare the text for each column
  sf2_text="$2"
  track_text="$track_dir/$track_name"
  next_track_text="$(basename "$(dirname "$3")")/$(basename "$3")"

  # Wrap text to fixed width per line
  sf2_lines=()
  while IFS= read -r line; do
    sf2_lines+=("$line")
  done < <(echo "$sf2_text" | fold -s -w $content_width_sf2)

  track_lines=()
  while IFS= read -r line; do
    track_lines+=("$line")
  done < <(echo "$track_text" | fold -s -w $content_width_track)

  next_track_lines=()
  while IFS= read -r line; do
    next_track_lines+=("$line")
  done < <(echo "$next_track_text" | fold -s -w $content_width_next_track)

  # Determine the maximum number of lines
  max_lines=${#sf2_lines[@]}
  if [ ${#track_lines[@]} -gt $max_lines ]; then
    max_lines=${#track_lines[@]}
  fi
  if [ ${#next_track_lines[@]} -gt $max_lines ]; then
    max_lines=${#next_track_lines[@]}
  fi

  # Print top border
  printf "${blue}╔"
  repeat_char $col_width_sf2 '═'
  printf "╦"
  repeat_char $col_width_track '═'
  printf "╦"
  repeat_char $col_width_next_track '═'
  printf "╗${nocolor}\n"

  # Print headers
  printf "${blue}║${white} %-*s ${blue}║${white} %-*s ${blue}║${white} %-*s ${blue}║${nocolor}\n" \
    $content_width_sf2 "SoundFont" \
    $content_width_track "Track" \
    $content_width_next_track "Next Track"

  # Print header separator
  printf "${blue}╠"
  repeat_char $col_width_sf2 '═'
  printf "╬"
  repeat_char $col_width_track '═'
  printf "╬"
  repeat_char $col_width_next_track '═'
  printf "╣${nocolor}\n"

  # Print data rows
  for ((i=0; i<$max_lines; i++)); do
    sf2_line="${sf2_lines[$i]}"
    track_line="${track_lines[$i]}"
    next_track_line="${next_track_lines[$i]}"
    sf2_line=${sf2_line:-""}
    track_line=${track_line:-""}
    next_track_line=${next_track_line:-""}

    printf "${blue}║ ${green}%-*s${blue} ║ ${yellow}%-*s${blue} ║ ${magenta}%-*s${blue} ║${nocolor}\n" \
      $content_width_sf2 "$sf2_line" \
      $content_width_track "$track_line" \
      $content_width_next_track "$next_track_line"
  done

  # Print bottom border
  printf "${blue}╚"
  repeat_char $col_width_sf2 '═'
  printf "╩"
  repeat_char $col_width_track '═'
  printf "╩"
  repeat_char $col_width_next_track '═'
  printf "╝${nocolor}\n"

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
  echo "╔════════════════════════════════════════════════════════════════════════════════════════════╗"
  echo "║                                         Controls                                           ║"
  echo "╠════════════════════════════════════════════════════════════════════════════════════════════╣"
  echo "║            (s)witch soundfont   (,)previous   (.)next   (o)utput MP3   (q)uit              ║"
  echo "╚════════════════════════════════════════════════════════════════════════════════════════════╝"
}

# Function to save the current track as an mp3
save_track() {
  case "$current_track" in
    *.mid) current_track_basename=$(basename "$current_track" .mid);;
    *.MID) current_track_basename=$(basename "$current_track" .MID);;
    *) echo "Error: Invalid file extension for MIDI file.";;
  esac
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
  fluidsynth -F "$output_dir/$current_track_basename-$sf2_current.wav" "$current_sf2" "$current_track"
  lame "$output_dir/$current_track_basename-$sf2_current.wav" "$output_file"
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
    next_track="${shuffled_midi_files[$(( (current_track_index + 1) % ${#shuffled_midi_files[@]} ))]}"
    current_sf2="${sf2_files[$current_sf2_index]}"
    sf2_basename=$(basename "$current_sf2")
    clear
    echo "╔════════════════════════════════════════════════════════════════════════════════════════════╗${nocolor}"
    printf "║${nocolor}                             MIDI Soundfont Testing Program v$version                            ║${nocolor}\n"
    echo "╚════════════════════════════════════════════════════════════════════════════════════════════╝${nocolor}"
        echo -e " Playing Track ${orange}$((current_track_index + 1))${nocolor} of ${orange}${#shuffled_midi_files[@]}${nocolor}"
    display_metadata "$current_track" "$current_sf2" "$next_track"

    
    # Display available sf2
    echo -e "${blue}╔════════════════════════════════════════════════════════════════════════════════════════════╗${nocolor}"
    echo -e "${blue}║ ${white}                                  Available Soundfonts${blue}                                     ║"
    echo -e "${blue}╚════════════════════════════════════════════════════════════════════════════════════════════╝${nocolor}"
    
    sf2_files_list=($(find /usr/share/sounds/sf2/ -type f -iname "*.sf2" -printf "%f\n"))
    sf2_columns=3  # number of columns to display
    sf2_max_per_col=$(( (${#sf2_files_list[@]} + sf2_columns - 1) / sf2_columns ))  # maximum number of items per column
    sf2_width=$(( (60 - sf2_columns + 1) / sf2_columns ))  # width of each column, including the tab character
    
    for (( row=0; row<sf2_max_per_col; row++ )); do
      for (( col=0; col<sf2_columns; col++ )); do
        index=$((col * sf2_max_per_col + row))
        if [[ "$index" -lt "${#sf2_files_list[@]}" ]]; then
          sf2="${sf2_files_list[$index]}"
          if [[ "$sf2" == "$sf2_basename" ]]; then
            # Highlight the current .sf2 file in the list using ANSI color codes
            printf "${white}[${blue}%-*s${white}]${nocolor} " $((sf2_width - 2)) "$sf2"
          else
            printf "${grey} %-*s ${nocolor}" $((sf2_width)) "$sf2"
          fi
        else
          # Print empty space to fill the last row
          printf "%-*s" $((sf2_width + 2)) ""
        fi
      done
      echo
    done

    if [[ -f "trivia.txt" ]]; then
      echo -e " "
      echo -e "${bright_red}Trivia"
      echo -e "------"
      echo -e "${red}$(shuf -n 1 trivia.txt | tr -d '\r' | sed 's/^ *//;s/ *$//' | sed 's/.\{1\}$//').${nocolor}" | fold -s -w 90
      echo -e "${nocolor} "
    else
    echo -e "${bright_red}╔════════════════════════════════════════════════════════════════════════════════════════════╗${nocolor}"
    echo -e "${bright_red}║ ${white}                                        Metadata${bright_red}                                           ║"
    echo -e "${bright_red}╚════════════════════════════════════════════════════════════════════════════════════════════╝${nocolor}"
      midicsv "$current_track" > "$temp_dir/data.csv"

      metadata=$(strings "$temp_dir/data.csv" | grep -a -E "Text_t|Copyright|Composer|Album|Title|Track_name|Lyrics|Metaeventtext|Marker" \
      | sed -E 's/.*"(.*)"/\1/' | grep -v -E '^\s*$' \
      | grep -v -E '^[^a-zA-Z0-9]+$' \
      | grep -v -E '(Piano|Guitar|Brass|Bass|Drum|Trombone|Violin|Sax|Trumpet|Percussion|Organ|Flute|Clarinet|Harp|Synth|Strings|Vibraphone|Accordion|Timpani|Cello|Contrabass|Fiddle|Voice|Chime|Xylophone|Bell|Cymbal|Tom|Snare|Congas|Tambourine|Lead|Echo|Left Hand|Right Hand|Oboe|French Horn|Tuba|Sitar|Kalimba|Shamisen|Bagpipe|Maracas|Whistle|Guiro|Claves|Conga|Cuica|Triangle|Woodblock|NoteWorthy Composer|Bongo|Track|Staff|Melody|Copyright_t)' \
      | grep -E '.{3,}')
      if [ -z "$metadata" ]; then
        echo -e "${bright_red}**NO METADATA AVAILABLE FOR THIS MIDI**${nocolor}"
      fi
      if [ ! -z "$metadata" ]; then
        echo -e "${bright_red}$metadata${nocolor}"
      fi
    fi
    display_menu

    # Start fluidsynth
    fluidsynth -a pulseaudio -m alsa_seq -l -i "$current_sf2" "$current_track" >/dev/null 2>&1 &
    fluidsynth_pid=$!

    # Wait for user input
    input=$(handle_input 2)
    if [[ "$input" == "next" ]]; then
      kill $fluidsynth_pid
      current_track_index=$((current_track_index + 1))
      if (( current_track_index >= ${#shuffled_midi_files[@]} )); then
        current_track_index=0
      fi
    elif [[ "$input" == "prev" ]]; then
      kill $fluidsynth_pid
      current_track_index=$((current_track_index - 1))
      if (( current_track_index < 0 )); then
        current_track_index=$((${#shuffled_midi_files[@]} - 1))
      fi
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
      if (( current_track_index >= ${#shuffled_midi_files[@]} )); then
        current_track_index=0
      fi
    fi
  
  done
}

play
