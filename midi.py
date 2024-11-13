#!/usr/bin/env python3

import os
import subprocess
import threading
import random
import signal
import sys
import shutil
import tempfile

def sigint_handler(signal, frame):
    print("Call to Quit received. Exiting...")
    Gtk.main_quit()
signal.signal(signal.SIGINT, sigint_handler)

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, Gdk, Pango, GLib
except ImportError:
    print("Error importing GTK modules. Ensure PyGObject is installed.")
    sys.exit(1)

class MidiSoundfontTester(Gtk.Window):
    def __init__(self):
        super().__init__(title="MIDI SoundFont Testing Program v0.1.4")
        self.set_default_size(1200, 600)
        self.set_border_width(5)

        # icon_path = "icon.png"  # Replace with the path to your icon file
        # self.set_icon_from_file(icon_path)
        self.set_icon_name("multimedia-player")  # Alternatively, try "media-playback-start" or "audio-x-generic"

        # Initialize variables
        self.midi_dir = os.path.expanduser("~/MIDI/")
        self.sf2_dir = "/usr/share/sounds/sf2/"
        self.required_commands = [
            "fluidsynth",
            "timidity",
            "strings",
            "lame",
            "find",
            "shuf",
            "pgrep",
            "midicsv",
        ]
        self.check_requirements()
        self.midi_files = self.find_midi_files()
        self.sf2_files = self.find_sf2_files()
        self.current_midi_index = 0
        self.current_sf2_index = 0
        self.fluidsynth_process = None
        self.shuffle_mode = False

        # Pane size percentages
        self.hpaned_position_percent = 33  # Horizontal pane position (percentage)
        self.vpaned_position_percent = 50  # Vertical pane position (percentage)

        # Build UI
        self.build_ui()

        # Load initial data
        self.load_midi_files()
        self.load_sf2_files()
        self.update_metadata()

        # Handle close event
        self.connect("destroy", self.on_quit)

    def check_requirements(self):
        missing = []
        for cmd in self.required_commands:
            if not shutil.which(cmd):
                missing.append(cmd)
        if missing:
            dialog = Gtk.MessageDialog(
                parent=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE,
                text="Missing Required Software",
            )
            dialog.format_secondary_text(
                "The following required software is missing:\n" +
                "\n".join(f" - {cmd}" for cmd in missing) +
                "\nPlease install the missing software and try again."
            )
            dialog.run()
            dialog.destroy()
            sys.exit(1)

    def build_ui(self):
        # Set up the main grid
        grid = Gtk.Grid()
        grid.set_hexpand(True)
        grid.set_vexpand(True)
        self.add(grid)

        # Create menu bar
        self.create_menu_bar(grid)

        # Create the main panes
        self.create_panes(grid)

        # Create media controls
        self.create_media_controls(grid)

    def create_menu_bar(self, grid):
        menu_bar = Gtk.MenuBar()
    
        # File Menu
        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label="File")
        file_item.set_submenu(file_menu)
    
        select_sf2_item = Gtk.MenuItem(label="📂 Select Sf2 Source...")
        select_sf2_item.connect("activate", self.on_select_sf2_source)
        file_menu.append(select_sf2_item)
    
        select_midi_item = Gtk.MenuItem(label="📂 Select MIDI Source...")
        select_midi_item.connect("activate", self.on_select_midi_source)
        file_menu.append(select_midi_item)
    
        quit_item = Gtk.MenuItem(label="❌ Quit")
        quit_item.connect("activate", self.on_quit)
        file_menu.append(quit_item)
    
        # Settings Menu
        settings_menu = Gtk.Menu()
        settings_item = Gtk.MenuItem(label="Settings")
        settings_item.set_submenu(settings_menu)

        # Use custom buffer size WIP
        # buffer_size_item = Gtk.MenuItem(label="Buffer Size")
        # buffer_size_item.connect("activate", self.on_buffer_size)
        # settings_menu.append(buffer_size_item)
    
        shuffle_mode_item = Gtk.CheckMenuItem(label="🔀 Shuffle Mode")
        shuffle_mode_item.set_active(self.shuffle_mode)
        shuffle_mode_item.connect("toggled", self.on_shuffle_mode_toggled)
        settings_menu.append(shuffle_mode_item)
    
        # Dark Mode checkbox in the Settings menu
        dark_mode_item = Gtk.CheckMenuItem(label="🌗 Dark Mode")
        dark_mode_item.set_active(Gtk.Settings.get_default().get_property("gtk-application-prefer-dark-theme"))
        dark_mode_item.connect("toggled", self.on_dark_mode_toggled)
        settings_menu.append(dark_mode_item)
    
        # About Menu
        about_menu = Gtk.Menu()
        about_item = Gtk.MenuItem(label="About")
        about_item.set_submenu(about_menu)
    
        licence_item = Gtk.MenuItem(label="🐧 Licence")
        licence_item.connect("activate", self.on_licence)
        about_menu.append(licence_item)
    
        # Append menus to the menu bar
        menu_bar.append(file_item)
        menu_bar.append(settings_item)
        menu_bar.append(about_item)
    
        # Attach the menu bar to the grid
        grid.attach(menu_bar, 0, 0, 1, 1)

    def create_panes(self, grid):
        hpaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        hpaned.set_hexpand(True)
        hpaned.set_vexpand(True)
        grid.attach(hpaned, 0, 1, 1, 1)

        # Left Pane: MIDI files List
        self.midi_store = Gtk.ListStore(str)
        self.midi_treeview = Gtk.TreeView(model=self.midi_store)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("MIDI Files", renderer, text=0)
        self.midi_treeview.append_column(column)
        self.apply_monospace_font(self.midi_treeview)
        self.midi_treeview.connect("row-activated", self.on_midi_selected)
        scrolled_window_midi = Gtk.ScrolledWindow()
        scrolled_window_midi.set_hexpand(True)
        scrolled_window_midi.set_vexpand(True)
        scrolled_window_midi.add(self.midi_treeview)

        # Middle and Right Panes
        vpaned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        vpaned.set_hexpand(True)
        vpaned.set_vexpand(True)
        hpaned.add2(vpaned)

        # Right Upper Pane: SoundFonts
        self.sf2_store = Gtk.ListStore(str)
        self.sf2_treeview = Gtk.TreeView(model=self.sf2_store)
        renderer_sf2 = Gtk.CellRendererText()
        column_sf2 = Gtk.TreeViewColumn("SoundFonts", renderer_sf2, text=0)
        self.sf2_treeview.append_column(column_sf2)
        self.apply_monospace_font(self.sf2_treeview)
        self.sf2_treeview.connect("row-activated", self.on_sf2_selected)
        scrolled_window_sf2 = Gtk.ScrolledWindow()
        scrolled_window_sf2.set_hexpand(True)
        scrolled_window_sf2.set_vexpand(True)
        scrolled_window_sf2.add(self.sf2_treeview)

        # Right Lower Pane: Metadata
        metadata_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Create a dummy TreeView to act as the header
        metadata_header = Gtk.TreeView()
        renderer_metadata = Gtk.CellRendererText()
        column_metadata = Gtk.TreeViewColumn("Metadata", renderer_metadata, text=0)
        metadata_header.append_column(column_metadata)
        self.apply_monospace_font(metadata_header)
        
        # Hide row headers and set fixed height to make it act purely as a header
        metadata_header.set_headers_visible(True)
        # metadata_header.set_size_request(-1, 20)  # Adjust the height to match header size
        metadata_header.set_model(Gtk.ListStore(str))  # Empty model to display header only
        
        metadata_box.pack_start(metadata_header, False, False, 0)
        
        # Add the actual metadata text view below the header
        self.metadata_view = Gtk.TextView()
        self.metadata_view.set_editable(False)
        self.metadata_view.set_wrap_mode(Pango.WrapMode.WORD)  # Enable word wrapping
        self.apply_monospace_font(self.metadata_view)
        scrolled_window_metadata = Gtk.ScrolledWindow()
        scrolled_window_metadata.set_hexpand(True)
        scrolled_window_metadata.set_vexpand(True)
        scrolled_window_metadata.add(self.metadata_view)
        metadata_box.pack_start(scrolled_window_metadata, True, True, 0)
        vpaned.add2(metadata_box)

        # Add the panes
        hpaned.add1(scrolled_window_midi)
        vpaned.add1(scrolled_window_sf2)
        vpaned.add2(scrolled_window_metadata)
        # Connect signals to adjust pane positions
        hpaned.connect('size-allocate', self.on_hpaned_size_allocate)
        vpaned.connect('size-allocate', self.on_vpaned_size_allocate)

    def on_hpaned_size_allocate(self, widget, allocation):
        total_width = allocation.width
        position = int(total_width * self.hpaned_position_percent / 100)
        widget.set_position(position)

    def on_vpaned_size_allocate(self, widget, allocation):
        total_height = allocation.height
        position = int(total_height * self.vpaned_position_percent / 100)
        widget.set_position(position)

    def create_media_controls(self, grid):
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_start=10, margin_end=10)
        controls_box.set_hexpand(True)
        controls_box.set_vexpand(False)
        controls_box.set_margin_top(5)
        controls_box.set_margin_bottom(5)
        controls_box.set_margin_start(5)
        controls_box.set_margin_end(5)
        grid.attach(controls_box, 0, 2, 1, 1)

        self.volume_button = Gtk.VolumeButton()
        initial_volume = self.get_current_volume()
        self.volume_button.set_value(initial_volume)  # Set initial volume to current level
        self.volume_button.connect("value-changed", self.on_volume_changed)
        controls_box.pack_start(self.volume_button, False, False, 0)

        # Media control buttons
        self.prev_button = Gtk.Button(label="⏮️ Back")
        self.prev_button.connect("clicked", self.on_previous)
        self.prev_button.set_tooltip_text("Previous")
        controls_box.pack_start(self.prev_button, False, False, 0)

        self.pause_button = Gtk.Button(label="⏹️ Stop")
        self.pause_button.connect("clicked", self.on_pause)
        self.pause_button.set_tooltip_text("Stop")
        controls_box.pack_start(self.pause_button, False, False, 0)
        
        self.play_button = Gtk.Button(label="▶️ Play")
        self.play_button.connect("clicked", self.on_play)
        self.play_button.set_tooltip_text("Play")
        controls_box.pack_start(self.play_button, False, False, 0)

        self.next_button = Gtk.Button(label="⏭️ Next")
        self.next_button.connect("clicked", self.on_next)
        self.next_button.set_tooltip_text("Next")
        controls_box.pack_start(self.next_button, False, False, 0)
        
        # Create a right-aligned box for the status label
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_box.set_hexpand(True)  # Allow it to expand horizontally within controls_box
        status_box.set_halign(Gtk.Align.END)  # Align the status_box to the right
        
        # Create the status label with ellipsizing enabled
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_ellipsize(Pango.EllipsizeMode.END)  # Ellipsize text if too long
        self.status_label.set_max_width_chars(100)  # Limit width (adjust as needed)
        
        # Pack the label into the status_box
        status_box.pack_end(self.status_label, False, False, 0)
        
        # Add status_box to controls_box
        controls_box.pack_start(status_box, True, True, 0)
        
        self.save_button = Gtk.Button(label="💾 Export mp3...")
        self.save_button.connect("clicked", self.on_save)
        self.save_button.set_tooltip_text("Export to mp3...")
        self.save_button.set_halign(Gtk.Align.CENTER)
        controls_box.pack_end(self.save_button, False, False, 0)

    def on_dark_mode_toggled(self, menuitem):
        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-application-prefer-dark-theme", menuitem.get_active())

    def apply_monospace_font(self, widget):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            * {
                font-family: monospace;
            }
        """)
        style_context = widget.get_style_context()
        style_context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def find_midi_files(self):
        midi_files = []
        for root, dirs, files in os.walk(self.midi_dir):
            for file in files:
                if file.lower().endswith(('.mid', '.midi')):
                    midi_files.append(os.path.join(root, file))
        return midi_files

    def find_sf2_files(self):
        sf2_files = []
        for root, dirs, files in os.walk(self.sf2_dir):
            for file in files:
                if file.lower().endswith('.sf2'):
                    sf2_files.append(os.path.join(root, file))
        return sf2_files

    def load_midi_files(self):
        self.stop_fluidsynth()
        self.midi_store.clear()
        if self.shuffle_mode:
            random.shuffle(self.midi_files)
        else:
            self.midi_files.sort()
        for midi_file in self.midi_files:
            basename = os.fsdecode(os.path.basename(midi_file))
            basename = basename.encode('utf-8', 'replace').decode('utf-8')
            self.midi_store.append([basename])
    
        # Set the initial column title with the first track as the current selection
        self.update_midi_column_title()
    
        # Enable tooltips and connect query-tooltip signal
        self.midi_treeview.set_has_tooltip(True)
        self.midi_treeview.connect("query-tooltip", self.on_midi_query_tooltip)
        self.current_midi_index = (0) % len(self.midi_files)
        self.midi_treeview.set_cursor(self.current_midi_index)

    def load_sf2_files(self):
        self.sf2_store.clear()
        for sf2_file in self.sf2_files:
            basename = os.fsdecode(os.path.basename(sf2_file))
            basename = basename.encode('utf-8', 'replace').decode('utf-8')
            self.sf2_store.append([basename])
    
        # Enable tooltips and connect query-tooltip signal
        self.sf2_treeview.set_has_tooltip(True)
        self.sf2_treeview.connect("query-tooltip", self.on_sf2_query_tooltip)
        self.sf2_treeview.set_cursor(self.current_sf2_index)

    def on_midi_query_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        path = widget.get_path_at_pos(x, y)
        if path:
            index = path[0].get_indices()[0]
            tooltip.set_text(self.midi_files[index])
            return True
        return False

    def on_volume_changed(self, volume_button, value):
        # Convert the volume to a percentage for `wpctl`
        volume_percentage = int(value * 100)
        try:
            # Adjust the volume of the default output device (sink)
            subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{volume_percentage}%"], check=True)
        except Exception as e:
            print(f"Error adjusting volume with PipeWire: {e}")

    def on_sf2_query_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        path = widget.get_path_at_pos(x, y)
        if path:
            index = path[0].get_indices()[0]
            tooltip.set_text(self.sf2_files[index])
            return True
        return False

    def get_selected_midi(self):
        selection = self.midi_treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            index = model.get_path(treeiter)[0]
            return self.midi_files[index], index
        return None, None

    def get_selected_sf2(self):
        selection = self.sf2_treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            index = model.get_path(treeiter)[0]
            return self.sf2_files[index], index
        return None, None

    def get_current_volume(self):
        try:
            # Retrieve current volume of the default sink
            result = subprocess.run(
                ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
                capture_output=True,
                text=True,
                check=True
            )
            # Parse the volume value from the output
            output = result.stdout.strip()
            # Assume output format is similar to: `Volume: 0.45 [45%]`
            volume_level = float(output.split()[1])  # e.g., `0.45` for 45%
            return volume_level
        except Exception as e:
            print(f"Error retrieving current volume: {e}")
            return 0.5  # Default to 50% if unable to fetch

    def on_midi_selected(self, treeview, path, column):
        # Update the current MIDI index based on the selected row
        self.current_midi_index = path.get_indices()[0]
        self.update_metadata()
        self.update_midi_column_title()
        self.on_play(None)

    def update_midi_column_title(self):
        # Update the MIDI Files column title to show the current track out of the total
        current_track = self.current_midi_index + 1  # Convert zero-based index to one-based
        total_tracks = len(self.midi_files)
        column_title = f"MIDI Files ({current_track} of {total_tracks})"
        self.midi_treeview.get_column(0).set_title(column_title)

    def on_sf2_selected(self, treeview, path, column):
        self.current_sf2_index = path.get_indices()[0]
        self.on_play(None)

    def update_metadata(self):
        midi_file, _ = self.get_selected_midi()
        if midi_file:
            metadata = self.extract_metadata(midi_file)
            buffer = self.metadata_view.get_buffer()
            buffer.set_text(metadata)

    def extract_metadata(self, midi_file):
        try:
            # File details
            filename = os.path.basename(midi_file)
            path = os.path.abspath(midi_file)
            filesize = os.path.getsize(midi_file)  # File size in bytes
            
            # Convert filesize to KB or MB for readability
            if filesize > 1024 * 1024:
                filesize_str = f"{filesize / (1024 * 1024):.2f} MB"
            else:
                filesize_str = f"{filesize / 1024:.2f} KB"
    
            # Extract MIDI-specific metadata using midicsv
            with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_csv:
                temp_csv_name = temp_csv.name
            subprocess.run(["midicsv", midi_file, temp_csv_name], check=True)
            
            with open(temp_csv_name, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            os.remove(temp_csv_name)
            lines = content.splitlines()
            
            # Extract lines that contain metadata tags and remove the first three columns
            metadata_lines = []
            for line in lines:
                if any(tag in line for tag in ["Title_t", "Text_t", "Copyright_t", "Composer", "Album", "Title", "Track_name", "Lyrics", "Metaeventtext", "Marker"]):
                    # Split the line by commas and skip the first three columns
                    columns = line.split(',', 3)
                    if len(columns) > 3:
                        metadata_lines.append(columns[3].strip())
    
            # Combine file details with extracted metadata
            metadata = (
                f"Filename: {filename}\n"
                f"Path: {path}\n"
                f"File Size: {filesize_str}\n"
                f"\n" + "\n".join(metadata_lines)
            )
            
            if not metadata_lines:  # If no metadata found, add a placeholder
                metadata += "\n\n**NO METADATA AVAILABLE FOR THIS MIDI**"
            
            return metadata
    
        except Exception as e:
            return f"Error extracting metadata: {e}"

    def on_play(self, button):
        self.stop_fluidsynth()
        midi_file, _ = self.get_selected_midi()
        sf2_file, _ = self.get_selected_sf2()
        if midi_file and sf2_file:
            try:
                self.fluidsynth_process = subprocess.Popen(
                    ["fluidsynth", "-a", "pulseaudio", "-m", "alsa_seq", "-i", sf2_file, midi_file],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                threading.Thread(target=self.monitor_fluidsynth_output, daemon=True).start()
                # Update status label
                self.status_label.set_text(f"Playing: {midi_file} + {os.path.basename(sf2_file)}")
            except Exception as e:
                print(f"Failed to start fluidsynth: {e}")
                self.fluidsynth_process = None
                self.status_label.set_text("Error: Unable to play")
        else:
            self.status_label.set_text("No MIDI or SoundFont selected")

    def monitor_fluidsynth_output(self):
        if self.fluidsynth_process:
            # Read Fluidsynth's stderr output
            for line in self.fluidsynth_process.stderr:
                line = line.strip()
                # Filter out specific warnings
                if "Failed to set thread to high priority" in line:
                    continue
                if "Using PulseAudio driver" in line:
                    continue
                print(f"fluidsynth error: {line}")
            
            # Wait for the process to complete, ensuring it’s not None
            if self.fluidsynth_process:
                self.fluidsynth_process.wait()
    
            # Check if the process ended naturally
            if self.fluidsynth_process and self.fluidsynth_process.returncode == 0:
                GLib.idle_add(self.on_next_auto)

    def on_next_auto(self):
        # Stop any existing Fluidsynth process
        self.stop_fluidsynth()
        # Move to the next MIDI file
        self.current_midi_index = (self.current_midi_index + 1) % len(self.midi_files)
        self.midi_treeview.set_cursor(self.current_midi_index)
        self.update_metadata()
        self.update_midi_column_title()
        self.on_play(None)
        return False  # Returning False to indicate we don't want to be called again

    def on_pause(self, button):
        if self.fluidsynth_process:
            self.fluidsynth_process.send_signal(signal.SIGSTOP)
            self.status_label.set_text("Playback Stopped")

    def on_resume(self, button):
        if self.fluidsynth_process:
            self.fluidsynth_process.send_signal(signal.SIGCONT)
            self.status_label.set_text("Playback Resumed")

    def on_previous(self, button):
        self.stop_fluidsynth()
        self.current_midi_index = (self.current_midi_index - 1) % len(self.midi_files)
        self.midi_treeview.set_cursor(self.current_midi_index)
        self.update_metadata()
        self.update_midi_column_title()
        self.on_play(None)

    def on_next(self, button):
        self.stop_fluidsynth()
        self.current_midi_index = (self.current_midi_index + 1) % len(self.midi_files)
        self.midi_treeview.set_cursor(self.current_midi_index)
        self.update_metadata()
        self.update_midi_column_title()
        self.on_play(None)

    def on_save(self, button):
        midi_file, _ = self.get_selected_midi()
        sf2_file, _ = self.get_selected_sf2()
        if midi_file and sf2_file:
            output_dir = os.path.join(os.getcwd(), "Output")
            os.makedirs(output_dir, exist_ok=True)
            midi_basename = os.path.splitext(os.path.basename(midi_file))[0]
            sf2_basename = os.path.splitext(os.path.basename(sf2_file))[0]
            midi_basename = midi_basename.encode('utf-8', 'replace').decode('utf-8')
            sf2_basename = sf2_basename.encode('utf-8', 'replace').decode('utf-8')
            wav_output = os.path.join(output_dir, f"{midi_basename}-{sf2_basename}.wav")
            mp3_output = os.path.join(output_dir, f"{midi_basename}-{sf2_basename}.mp3")
            subprocess.run(["fluidsynth", "-F", wav_output, sf2_file, midi_file])
            subprocess.run(["lame", wav_output, mp3_output])
            os.remove(wav_output)
            dialog = Gtk.MessageDialog(
                parent=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Track Saved",
            )
            dialog.format_secondary_text(f"Track saved as {mp3_output}")
            dialog.run()
            dialog.destroy()
            self.status_label.set_text(f"Track saved as {mp3_output}")
        else:
            self.status_label.set_text("No MIDI or SoundFont selected")

    def stop_fluidsynth(self):
        if self.fluidsynth_process:
            self.fluidsynth_process.terminate()
            try:
                self.fluidsynth_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.fluidsynth_process.kill()
            self.fluidsynth_process = None
            self.status_label.set_text("Playback Stopped")

    def on_select_sf2_source(self, menuitem):
        dialog = Gtk.FileChooserDialog(
            title="Select SoundFont Directory",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.sf2_dir = dialog.get_filename()
            self.sf2_files = self.find_sf2_files()
            self.load_sf2_files()
            self.status_label.set_text("SoundFont directory updated")
        dialog.destroy()

    def on_select_midi_source(self, menuitem):
        dialog = Gtk.FileChooserDialog(
            title="Select MIDI Directory",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.stop_fluidsynth()
            self.midi_dir = dialog.get_filename()
            self.midi_files = self.find_midi_files()
            self.load_midi_files()
            self.current_midi_index = 0
            self.midi_treeview.set_cursor(self.current_midi_index)
            self.update_metadata()
            self.update_midi_column_title()
            self.status_label.set_text("MIDI directory updated")
        dialog.destroy()

    def on_buffer_size(self, menuitem):
        # Implement buffer size settings if needed
        pass

    def on_shuffle_mode_toggled(self, menuitem):
        self.shuffle_mode = menuitem.get_active()
        self.load_midi_files()
        self.update_metadata()
        mode = "enabled" if self.shuffle_mode else "disabled"
        self.status_label.set_text(f"Shuffle mode {mode}")

    def on_licence(self, menuitem):
        # Licence information text
        licence_text = (
            "MIDI SoundFont Testing Program v0.1.4 ©2024 Kingbonj\n\n"
            "This software is licensed under the GNU General Public License v3.0.\n\n"
            "You may redistribute and/or modify it under the terms of the GPLv3.\n\n"
            "For the full license text, please visit:\n"
            "https://www.gnu.org/licenses/gpl-3.0.en.html\n"
        )
    
        # Create the dialog
        dialog = Gtk.Dialog(
            title="Licence Information",
            transient_for=self,
            modal=True,
            destroy_with_parent=True,
        )
        dialog.set_resizable(False)
        dialog.get_content_area().set_border_width(10)
    
        # Create a horizontal box to hold the image and text
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    
        # Add Tux-like GTK about icon
        tux_image = Gtk.Image.new_from_icon_name("dialog-information", Gtk.IconSize.DIALOG)
        hbox.pack_start(tux_image, False, False, 0)
    
        # Create and configure the label for licence text
        label = Gtk.Label(label=licence_text)
        label.set_justify(Gtk.Justification.LEFT)
        label.set_line_wrap(True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD)
        label.set_margin_start(10)
        label.set_margin_end(10)
    
        # Add the label to the horizontal box
        hbox.pack_start(label, True, True, 0)
    
        # Add the horizontal box to the dialog content area
        dialog.get_content_area().pack_start(hbox, False, False, 0)
    
        # Make sure both image and label are visible
        hbox.show_all()
    
        # Create a box to hold the buttons horizontally and centre them
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)  # Center the button box horizontally
    
        # Create the "Buy me a coffee?" link button
        donate_button = Gtk.LinkButton.new_with_label(
            uri="https://www.paypal.com/paypalme/bleeves",
            label="Buy me a coffee?"
        )
        
        # Add the link button and OK button to the button box
        button_box.pack_start(donate_button, False, False, 0)
        ok_button = Gtk.Button.new_with_label("Close")
        ok_button.connect("clicked", lambda w: dialog.response(Gtk.ResponseType.OK))
        button_box.pack_start(ok_button, False, False, 0)
        donate_button.set_tooltip_text("https://www.paypal.com/paypalme/bleeves")
    
        # Add button box to the dialog content area
        dialog.get_content_area().pack_start(button_box, False, False, 10)
    
        # Show everything and run the dialog
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def on_quit(self, *args):
        self.status_label.set_text(f"Attempting to Quit")
        print ("Quitting application...")
        self.stop_fluidsynth()
        Gtk.main_quit()
        
if __name__ == "__main__":
    app = MidiSoundfontTester()
    app.show_all()
    Gtk.main()
