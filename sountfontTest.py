#!/usr/bin/env python3

import os
import subprocess
import threading
import random
import signal
import sys
import shutil
import tempfile
import time

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, Gdk, Pango, GLib, GObject
except ImportError:
    print("Error importing GTK modules. Ensure PyGObject is installed.")
    sys.exit(1)


def sigint_handler(signal_received, frame):
    print("Call to Quit received. Exiting...")
    Gtk.main_quit()
    
signal.signal(signal.SIGINT, sigint_handler)

class MidiSoundfontTester(Gtk.Window):
    def __init__(self):
        super().__init__(title="MIDI SoundFont Testing Program v0.1.4")
        self.set_default_size(1200, 600)
        self.set_border_width(5)

        self.set_icon_name("multimedia-player")
        
        # Initialize variables
        self.source_dir = os.path.expanduser("~")  # Default source directory
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
            "xmp",
            "openmpt123",
        ]
        self.check_requirements()

        # File lists
        self.all_files = self.find_all_files()
        self.sf2_files = self.find_sf2_files()
        self.fluidsynth_process = None
        self.xmp_process = None
        self.shuffle_mode = False
        self.xmp_stopped_intentionally = False  # Flag to handle intentional termination

        # Build UI
        self.build_ui()

        # Load initial data
        self.spinner.start()
        self.load_all_files()
        self.load_sf2_files()
        self.update_metadata()
        self.spinner.stop()

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
        self.all_treeview.set_has_tooltip(True)
        self.all_treeview.connect("query-tooltip", self.on_file_query_tooltip)

    def create_menu_bar(self, grid):
        menu_bar = Gtk.MenuBar()
        menu_bar.connect("realize", lambda widget: self.apply_monospace_font(widget))

        # File Menu
        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label="File")
        file_item.set_submenu(file_menu)

        select_source_item = Gtk.MenuItem(label="📂 Select Source Directory...")
        select_source_item.connect("activate", self.on_select_source_directory)
        file_menu.append(select_source_item)

        select_sf2_item = Gtk.MenuItem(label="📂 Select SoundFont Directory...")
        select_sf2_item.connect("activate", self.on_select_sf2_source)
        file_menu.append(select_sf2_item)

        quit_item = Gtk.MenuItem(label="❌ Quit")
        quit_item.connect("activate", self.on_quit)
        file_menu.append(quit_item)

        # Settings Menu
        settings_menu = Gtk.Menu()
        settings_item = Gtk.MenuItem(label="Settings")
        settings_item.set_submenu(settings_menu)

        shuffle_mode_item = Gtk.CheckMenuItem(label="🔀 Shuffle Mode")
        shuffle_mode_item.set_active(self.shuffle_mode)
        shuffle_mode_item.connect("toggled", self.on_shuffle_mode_toggled)
        settings_menu.append(shuffle_mode_item)

        # Dark Mode checkbox in the Settings menu
        dark_mode_item = Gtk.CheckMenuItem(label="🌗 Dark Mode")
        dark_mode_item.set_active(
            Gtk.Settings.get_default().get_property("gtk-application-prefer-dark-theme")
        )
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

        self.apply_monospace_font(menu_bar)

        # Attach the menu bar to the grid
        grid.attach(menu_bar, 0, 0, 1, 1)

    def create_panes(self, grid):
        hpaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        hpaned.set_hexpand(True)
        hpaned.set_vexpand(True)
        grid.attach(hpaned, 0, 1, 1, 1)

        # Left Pane: Files List (All Files)
        left_pane_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Add Search Entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Filter files...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.apply_monospace_font(self.search_entry)
        left_pane_box.pack_start(self.search_entry, False, False, 0)

        # File TreeView
        self.all_store = Gtk.ListStore(object, object, object)  # (filename, foldername, filepath)
        self.all_filter = self.all_store.filter_new()
        self.all_filter.set_visible_func(self.file_filter_func)
        self.all_treeview = Gtk.TreeView(model=self.all_filter)

        # Custom CellRenderer for Filename
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Files")
        column.pack_start(renderer, True)
        column.set_cell_data_func(renderer, self.render_filename)
        self.all_treeview.append_column(column)

        self.apply_monospace_font(self.all_treeview)
        self.all_treeview.connect("row-activated", self.on_file_selected)
        scrolled_window_files = Gtk.ScrolledWindow()
        scrolled_window_files.set_hexpand(True)
        scrolled_window_files.set_vexpand(True)
        scrolled_window_files.add(self.all_treeview)
        
        # Pack the TreeView into the left pane box
        left_pane_box.pack_start(scrolled_window_files, True, True, 0)
        hpaned.add1(left_pane_box)

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
        self.sf2_treeview.set_margin_top(35)
        scrolled_window_sf2.add(self.sf2_treeview)

        # Right Lower Pane: Metadata
        metadata_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Create a dummy TreeView to act as the header
        metadata_header = Gtk.TreeView()
        renderer_metadata = Gtk.CellRendererText()
        column_metadata = Gtk.TreeViewColumn("Metadata", renderer_metadata, text=0)
        
        metadata_header.append_column(column_metadata)
        self.apply_monospace_font(metadata_header)
        metadata_header.set_headers_visible(True)
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
        vpaned.add1(scrolled_window_sf2)
        vpaned.add2(metadata_box)
        # Connect signals to adjust pane positions
        hpaned.connect('size-allocate', self.on_hpaned_size_allocate)
        vpaned.connect('size-allocate', self.on_vpaned_size_allocate)

    def render_filename(self, column, cell, model, treeiter, data):
        # Get the filename from the model
        filename = model[treeiter][0]
        if filename:
            # Convert to string, handling surrogates
            if isinstance(filename, bytes):
                filename = filename.decode('utf-8', 'replace')
            elif isinstance(filename, str):
                filename = filename.encode('utf-8', 'surrogateescape').decode('utf-8', 'replace')
            else:
                filename = str(filename)
        else:
            filename = ''
        cell.set_property('text', filename)

    def on_hpaned_size_allocate(self, widget, allocation):
        total_width = allocation.width
        position = int(total_width * 33 / 100)
        widget.set_position(position)

    def on_vpaned_size_allocate(self, widget, allocation):
        total_height = allocation.height
        position = int(total_height * 50 / 100)
        widget.set_position(position)

    def create_media_controls(self, grid):
        controls_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10,
            margin_start=10,
            margin_end=10
        )
        
        controls_box.set_hexpand(True)
        controls_box.set_vexpand(False)
        controls_box.set_margin_top(5)
        controls_box.set_margin_bottom(5)
        controls_box.set_margin_start(5)
        controls_box.set_margin_end(5)
        grid.attach(controls_box, 0, 2, 1, 1)
    
        # Create a CSS provider for styling
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .round-button {
                border-radius: 30%; /* Makes the button round */
                padding: 5px; /* Adjust padding for proper size */
                background-color: rgba(0, 0, 0, 0);
            }
            .button {
                border-radius: 10px; /* Makes the button round */
                padding: 5px; /* Adjust padding for proper size */
                background-color: rgba(0, 0, 0, 0);
            }
            .label {
                font-size: 12px
            }
        """)
        
        # Apply the CSS to the GTK application
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Create the Gtk.Image from a file
        try:
            self.image = Gtk.Image.new_from_file("soundfontpy.png")
        except Exception as e:
            print(f"Error loading image: {e}")
            self.image = Gtk.Label(label="Image not found.")
        # Set the desired width and height
        self.image.set_size_request(50, 20)  # Width: 50px, Height: 20px
        controls_box.pack_start(self.image, False, False, 0)
    
        # Add the spinner at the end of the controls_box
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(20, 20)  # Set a size to ensure visibility
        controls_box.pack_start(self.spinner, False, False, 0)
    
        self.volume_button = Gtk.VolumeButton()
        initial_volume = self.get_current_volume()
        self.volume_button.set_value(initial_volume)  # Set initial volume to current level
        self.volume_button.connect("value-changed", self.on_volume_changed)
        self.volume_button.get_style_context().add_class("round-button")
        self.volume_button.set_size_request(50, 50)  # Width: 40px, Height: 40px
        controls_box.pack_start(self.volume_button, False, False, 0)
    
        # Helper function to create round buttons
        def create_round_button(icon_name, tooltip, callback):
            button = Gtk.Button()
            button.add(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON))
            button.set_tooltip_text(tooltip)
            button.connect("clicked", callback)
            button.get_style_context().add_class("round-button")
            return button
    
        # Previous Button
        self.prev_button = create_round_button("media-skip-backward", "Previous", self.on_previous)
        controls_box.pack_start(self.prev_button, False, False, 0)
    
        # Stop Button
        self.stop_button = create_round_button("media-playback-stop", "Stop", self.on_pause)
        controls_box.pack_start(self.stop_button, False, False, 0)
    
        # Play Button
        self.play_button = create_round_button("media-playback-start", "Play", self.on_play)
        controls_box.pack_start(self.play_button, False, False, 0)
    
        # Next Button
        self.next_button = create_round_button("media-skip-forward", "Next", self.on_next)
        controls_box.pack_start(self.next_button, False, False, 0)
    
        # Create a right-aligned box for the status label
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_box.set_hexpand(True)  # Allow it to expand horizontally within controls_box
        status_box.set_halign(Gtk.Align.END)  # Align the status_box to the right
    
        # Create the status label with ellipsizing enabled
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_ellipsize(Pango.EllipsizeMode.END)  # Ellipsize text if too long
        self.status_label.set_max_width_chars(100)  # Limit width (adjust as needed)
        self.status_label.get_style_context().add_class("label")
        self.apply_monospace_font(self.status_label)
    
        status_box.pack_end(self.status_label, False, False, 0)
        controls_box.pack_start(status_box, True, True, 0)
    
        # Create the Save button
        self.save_button = Gtk.Button()
        self.save_button.get_style_context().add_class("media-button")  # Optional: Add a custom CSS class for styling
        output_dir = os.path.join(os.getcwd(), "Output")
        self.save_button.set_tooltip_text(f"Export mp3 to {output_dir}")
        self.save_button.connect("clicked", self.on_save)
        self.apply_monospace_font(self.save_button)
        self.save_button.get_style_context().add_class("button")
        
        # Create the icon
        save_icon = Gtk.Image.new_from_icon_name("document-save", Gtk.IconSize.BUTTON)  # Use a common icon name
        
        # Create the label
        save_label = Gtk.Label(label="Export mp3...")
        
        # Create a horizontal box to pack the icon and label
        button_box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        button_box.pack_start(save_icon, False, False, 0)
        button_box.pack_start(save_label, False, False, 0)
        
        # Add the box to the button
        self.save_button.add(button_box)
        self.save_button.show_all()  # Ensure all child widgets are visible
        
        # Add the button to the controls box
        controls_box.pack_start(self.save_button, False, False, 0)
        
        # Start the spinner initially to test visibility
        self.spinner.start()

            
    def start_spinner(self):
        """Method to start the spinner."""
        self.spinner.start()

    def stop_spinner(self):
        """Method to stop the spinner."""
        self.spinner.stop()
        
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
    
        # Recursively apply the font to children if the widget is a container
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                self.apply_monospace_font(child)
    
        # Check for Gtk.MenuItem or Gtk.CheckMenuItem and apply font to their labels
        if isinstance(widget, Gtk.MenuItem):
            submenu = widget.get_submenu()
            if submenu:
                self.apply_monospace_font(submenu)
        elif isinstance(widget, Gtk.CheckMenuItem):
            # Apply the monospace font to the label of CheckMenuItem
            label = widget.get_child()
            if isinstance(label, Gtk.Label):
                css_provider = Gtk.CssProvider()
                css_provider.load_from_data(b"""
                    * {
                        font-family: monospace;
                    }
                """)
                label.get_style_context().add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def find_all_files(self):
        all_files = []
        try:
            for root, dirs, files in os.walk(self.source_dir):
                for file in files:
                    if file.lower().endswith((
                        '.mid', '.midi', '.mod', '.xm', '.it', '.s3m', '.stm', '.imf', '.ptm', '.mdl', '.ult',
                        '.liq', '.masi', '.j2b', '.amf', '.med', '.rts', '.digi', '.sym', '.dbm', '.qc', '.okt',
                        '.sfx', '.far', '.umx', '.hmn', '.slt', '.coco', '.ims', '.669', '.abk', '.uni', '.gmc'
                    )):
                        all_files.append(os.path.join(root, file))
        except Exception as e:
            print(f"Error finding all files: {e}")
        return all_files  # Ensure this always returns a list

    def find_sf2_files(self):
        sf2_files = []
        for root, dirs, files in os.walk(self.sf2_dir):
            for file in files:
                if file.lower().endswith('.sf2'):
                    sf2_files.append(os.path.join(root, file))
        return sf2_files

    def load_all_files(self):
        # Step 1: Start the spinner on the main thread
        GLib.idle_add(self.spinner.start)
    
        # Step 2: Create a background thread for loading and preparing files
        threading.Thread(target=self._load_all_files_background).start()

    def _load_all_files_background(self):
        # Stop any running processes in the background thread
        self.stop_fluidsynth()
        self.stop_xmp()
    
        # Clear the existing file store in the main thread
        GLib.idle_add(self.all_store.clear)
    
        if self.shuffle_mode:
            GLib.idle_add(self.status_label.set_text, "Shuffling playlist...")
            # Background task for shuffling and loading files
            shuffled_files = self.prepare_shuffled_files()
            GLib.idle_add(self._load_files_into_store, shuffled_files)
        else:
            # Sort files and load them in background
            sorted_files = sorted(self.all_files, key=lambda x: x.lower())
            GLib.idle_add(self._load_files_into_store, sorted_files)
    
        # Queue other UI updates once loading is done
        GLib.idle_add(self.all_filter.refilter)
        GLib.idle_add(self.update_file_column_title)
        GLib.idle_add(self.select_current_file_in_treeview)
        GLib.idle_add(self.spinner.stop)
    
    def _load_files_into_store(self, files):
        if not files:  # Check if files is None or an empty list
            self.status_label.set_text(f"Done")
            return  # Prevent further execution if no files are available
    
        for all_file in files:
            self.append_file_to_store(all_file)
    
        self.status_label.set_text(f"Loaded {len(files)} files")
        self.all_filter.refilter()
        self.update_file_column_title()
        self.select_current_file_in_treeview()
        self.update_metadata()
        
    def prepare_shuffled_files(self):
        # Perform the shuffling and loading in the background
        shuffled_files = self.all_files.copy()
        random.shuffle(shuffled_files)
        
        # After preparing the list, update the GUI in one operation
        GLib.idle_add(self.update_ui_with_shuffled_files, shuffled_files)
    
    def update_ui_with_shuffled_files(self, shuffled_files):
        for all_file in shuffled_files:
            self.append_file_to_store(all_file)
        
        # Update the status label once the shuffle is complete
        self.status_label.set_text("Shuffle complete")
        self.all_filter.refilter()
        self.update_file_column_title()
        self.select_current_file_in_treeview()
        self.update_metadata()

    def append_file_to_store(self, all_file):
        basename = os.path.basename(all_file)
        foldername = os.path.basename(os.path.dirname(all_file))
        # Store the data directly
        self.all_store.append([basename, foldername, all_file])

    def load_sf2_files(self):
        self.sf2_store.clear()
        for sf2_file in self.sf2_files:
            basename = os.path.basename(sf2_file)
            self.sf2_store.append([basename])

        # Enable tooltips and connect query-tooltip signal
        self.sf2_treeview.set_has_tooltip(True)
        self.sf2_treeview.connect("query-tooltip", self.on_sf2_query_tooltip)
        if self.sf2_store.get_iter_first():
            self.sf2_treeview.set_cursor(0)

    def on_file_query_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        result = widget.get_dest_row_at_pos(x, y)
        if result:
            path, pos = result
            model = widget.get_model()
            treeiter = model.get_iter(path)
            if treeiter:
                file_path = model.get_value(treeiter, 2)  # Get the file path
                tooltip.set_text(file_path)
                return True
        return False

    def on_volume_changed(self, volume_button, value):
        # Convert the volume to a percentage for `wpctl`
        volume_percentage = int(value * 100)
        try:
            # Adjust the volume of the default output device (sink)
            subprocess.run(
                ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{volume_percentage}%"],
                check=True
            )
        except Exception as e:
            print(f"Error adjusting volume with PipeWire: {e}")

    def on_sf2_query_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        path = widget.get_path_at_pos(x, y)
        if path:
            index = path[0].get_indices()[0]
            if index < len(self.sf2_files):
                tooltip.set_text(self.sf2_files[index])
                return True
        return False

    def get_selected_file(self):
        selection = self.all_treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            file_path = model.get_value(treeiter, 2)  # Get the file path from the third column
            return file_path
        return None

    def get_selected_sf2(self):
        selection = self.sf2_treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            index = model.get_path(treeiter)[0]
            if index < len(self.sf2_files):
                return self.sf2_files[index]
        return None

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

    def on_file_selected(self, treeview, path, column):
        self.update_metadata()
        self.update_file_column_title()
        self.on_play(None)

    def update_file_column_title(self):
        # Get total number of matching files
        total_matching_files = self.get_filtered_file_count()

        # Get the index of the selected file in the filtered list
        selection = self.all_treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            path = model.get_path(treeiter)
            current_index = path.get_indices()[0] + 1  # Convert to one-based index
        else:
            current_index = 0

        column_title = f"Files ({current_index} of {total_matching_files})"
        self.all_treeview.get_column(0).set_title(column_title)

    def get_filtered_file_count(self):
        count = 0
        iter = self.all_filter.get_iter_first()
        while iter:
            count += 1
            iter = self.all_filter.iter_next(iter)
        return count

    def on_sf2_selected(self, treeview, path, column):
        self.on_play(None)

    def update_metadata(self):
        file_path = self.get_selected_file()
        if file_path:
            metadata = self.extract_metadata(file_path)
            buffer = self.metadata_view.get_buffer()
            buffer.set_text(metadata)

    def extract_metadata(self, file_path):
        self.spinner.start()
        try:
            # File details
            filename = os.path.basename(file_path)
            path = os.path.abspath(file_path)
            filesize = os.path.getsize(file_path)  # File size in bytes
    
            # Convert filesize to KB or MB for readability
            if filesize > 1024 * 1024:
                filesize_str = f"{filesize / (1024 * 1024):.2f} MB"
            else:
                filesize_str = f"{filesize / 1024:.2f} KB"
    
            extension = os.path.splitext(file_path)[1].lower()
            metadata_lines = []
    
            if extension in ['.mid', '.midi']:
                # Extract MIDI-specific metadata using midicsv
                with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_csv:
                    temp_csv_name = temp_csv.name
                subprocess.run(["midicsv", file_path, temp_csv_name], check=True)
    
                with open(temp_csv_name, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
    
                os.remove(temp_csv_name)
                lines = content.splitlines()
    
                # Extract lines that contain metadata tags and remove the first three columns
                for line in lines:
                    if any(tag in line for tag in ["Title_t", "Text_t", "Copyright_t", "Composer", "Album", "Title", "Track_name", "Lyrics", "Metaeventtext", "Marker"]):
                        columns = line.split(',', 3)
                        if len(columns) > 3:
                            metadata_lines.append(columns[3].strip())
    
            elif extension in [
                '.mod', '.xm', '.it', '.s3m', '.stm', '.imf', '.ptm', '.mdl', '.ult',
                '.liq', '.masi', '.j2b', '.amf', '.med', '.rts', '.digi', '.sym',
                '.dbm', '.qc', '.okt', '.sfx', '.far', '.umx', '.hmn', '.slt',
                '.coco', '.ims', '.669', '.abk', '.uni', '.gmc'
            ]:
                # Extract MOD file metadata using openmpt123
                openmpt_result = subprocess.run(['openmpt123', '--info', file_path], capture_output=True, text=True)
                if openmpt_result.returncode == 0:
                    # Filter out the header lines from openmpt123 output
                    filtered_lines = []
                    header_end_reached = False
                    for line in openmpt_result.stdout.splitlines():
                        if header_end_reached:
                            filtered_lines.append(line)
                        elif line.startswith("Type"):  # Detect start of relevant metadata
                            header_end_reached = True
                            filtered_lines.append(line)
                    
                    metadata_lines.extend(filtered_lines)
                else:
                    metadata_lines.append("No metadata available for this MOD file.")
    
            else:
                metadata_lines.append("Unknown file type.")
    
            # Combine file details with extracted metadata
            metadata = (
                f"Filename: {filename}\n"
                f"Path: {path}\n"
                f"File Size: {filesize_str}\n"
                f"\n" + "\n".join(metadata_lines)
            )
    
            if not metadata_lines:  # If no metadata found, add a placeholder
                metadata += "\n\n**NO METADATA AVAILABLE FOR THIS FILE**"
    
            return metadata
    
        except Exception as e:
            return f"Error extracting metadata: {e}"
            self.spinner.stop()

    def on_play(self, button):
        self.spinner.start()
        self.stop_fluidsynth()
        self.stop_xmp()
        file_path = self.get_selected_file()
        if file_path:
            extension = os.path.splitext(file_path)[1].lower()
            if extension in ['.mid', '.midi']:
                # Use fluidsynth to play MIDI files
                sf2_file = self.get_selected_sf2()
                if sf2_file:
                    try:
                        self.fluidsynth_process = subprocess.Popen(
                            ["fluidsynth", "-a", "pulseaudio", "-m", "alsa_seq", "-i", sf2_file, file_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                        )
                        threading.Thread(target=self.monitor_fluidsynth_output, daemon=True).start()
                        self.status_label.set_text(f"Playing: {file_path} + {os.path.basename(sf2_file)}")
                        self.status_label.set_tooltip_text(f"{file_path} + {os.path.basename(sf2_file)}")

                    except Exception as e:
                        print(f"Failed to start fluidsynth: {e}")
                        self.fluidsynth_process = None
                        # self.status_label.set_text("Error: Unable to play")
                else:
                    self.status_label.set_text("No SoundFont selected")
            else:
                # Use xmp to play other files
                try:
                    self.xmp_stopped_intentionally = False  # Reset the flag
                    self.xmp_process = subprocess.Popen(
                        ["xmp", file_path],
                        stdout=subprocess.DEVNULL,  # Discard output to prevent blocking
                        stderr=subprocess.DEVNULL,
                        text=True,
                    )
                    threading.Thread(target=self.monitor_xmp_output, daemon=True).start()
                    # Update status label
                    self.status_label.set_text(f"Playing: {file_path}")
                except Exception as e:
                    print(f"Failed to start xmp: {e}")
                    self.xmp_process = None
                    self.status_label.set_text("Error: Unable to play")
        else:
            self.status_label.set_text("No file selected")
        self.update_metadata()

    def monitor_xmp_output(self):
        process = self.xmp_process
        if process:
            try:
                # Wait for the process to complete
                process.wait()

                if process.returncode != 0:
                    if self.xmp_stopped_intentionally:
                        self.xmp_stopped_intentionally = False  # Reset the flag
                        # Do not report an error
                    else:
                        print(f"xmp exited with code {process.returncode}")
                        GLib.idle_add(self.handle_xmp_error)
                else:
                    # After playback is done, move to next track
                    GLib.idle_add(self.on_next_auto)
            except Exception as e:
                print(f"Error in monitor_xmp_output: {e}")
                GLib.idle_add(self.handle_xmp_error)
        else:
            print("xmp_process is None in monitor_xmp_output")

    def handle_xmp_error(self):
        self.status_label.set_text("Error: xmp failed to play the file.")

    def monitor_fluidsynth_output(self):
        process = self.fluidsynth_process
        if process:
            try:
                # Read Fluidsynth's stderr output
                while True:
                    line = process.stderr.readline()
                    if not line:
                        break
                    line = line.strip()
                    
                    # Filter out all output, including specific warnings
                    if "Failed to set thread to high priority" in line:
                        continue
                    if "Using PulseAudio driver" in line:
                        continue
                    if "code 15" in line:
                        continue  # Skip any "code 15" errors
    
                # Wait for the process to complete and check return code
                process.wait()
                if process.returncode != 0:
                    # Handle error condition in the UI
                    GLib.idle_add(self.handle_fluidsynth_error)
                else:
                    # After playback is complete, move to the next track
                    GLib.idle_add(self.on_next_auto)
                    
            except Exception as e:
                # Only output detailed exception handling
                print(f"Error in monitor_fluidsynth_output: {type(e).__name__}: {e}")
                GLib.idle_add(self.handle_fluidsynth_error)
        else:
            # Detailed exception handling if the process is None
            print("Error: fluidsynth_process is None in monitor_fluidsynth_output")

    def handle_fluidsynth_error(self):
        self.status_label.set_text("Error: fluidsynth failed to play the file.")

    def select_current_file_in_treeview(self):
        # Select the first item in the filtered model
        iter = self.all_filter.get_iter_first()
        if iter:
            path = self.all_filter.get_path(iter)
            self.all_treeview.set_cursor(path)
            self.all_treeview.scroll_to_cell(path)
        else:
            # Clear selection if no items are present
            self.all_treeview.get_selection().unselect_all()

    def on_pause(self, button):
        self.spinner.stop()
        self.stop_fluidsynth()
        self.stop_xmp()
        self.status_label.set_text("Playback Stopped")
        self.status_label.set_tooltip_text("")

    def on_previous(self, button):
        self.stop_fluidsynth()
        self.stop_xmp()

        selection = self.all_treeview.get_selection()
        model, treeiter = selection.get_selected()

        if treeiter:
            path = model.get_path(treeiter)
            index = path.get_indices()[0]
            if index > 0:
                prev_path = Gtk.TreePath(index - 1)
            else:
                # Loop back to the last item
                total_rows = self.get_filtered_file_count()
                prev_path = Gtk.TreePath(total_rows - 1)
            self.all_treeview.set_cursor(prev_path)
            self.all_treeview.scroll_to_cell(prev_path)
        else:
            # No selection, select the last item
            total_rows = self.get_filtered_file_count()
            if total_rows > 0:
                prev_path = Gtk.TreePath(total_rows - 1)
                self.all_treeview.set_cursor(prev_path)
                self.all_treeview.scroll_to_cell(prev_path)

        self.update_metadata()
        self.update_file_column_title()
        self.on_play(None)

    def on_next(self, button):
        self.stop_fluidsynth()
        self.stop_xmp()

        selection = self.all_treeview.get_selection()
        model, treeiter = selection.get_selected()

        if treeiter:
            next_iter = self.all_filter.iter_next(treeiter)
            if next_iter:
                path = self.all_filter.get_path(next_iter)
                self.all_treeview.set_cursor(path)
                self.all_treeview.scroll_to_cell(path)
            else:
                # Loop back to the first item
                iter = self.all_filter.get_iter_first()
                if iter:
                    path = self.all_filter.get_path(iter)
                    self.all_treeview.set_cursor(path)
                    self.all_treeview.scroll_to_cell(path)
        else:
            # No selection, select the first item
            iter = self.all_filter.get_iter_first()
            if iter:
                path = self.all_filter.get_path(iter)
                self.all_treeview.set_cursor(path)
                self.all_treeview.scroll_to_cell(path)

        self.update_metadata()
        self.update_file_column_title()
        self.on_play(None)

    def on_save(self, button):
        self.spinner.start()
        file_path = self.get_selected_file()
        if file_path:
            extension = os.path.splitext(file_path)[1].lower()
            MIDI_EXTENSIONS = ['.mid', '.midi']
            NON_MIDI_EXTENSIONS = [
                '.mod', '.xm', '.it', '.s3m', '.stm', '.imf', '.ptm', '.mdl', '.ult',
                '.liq', '.masi', '.j2b', '.amf', '.med', '.rts', '.digi', '.sym',
                '.dbm', '.qc', '.okt', '.sfx', '.far', '.umx', '.hmn', '.slt',
                '.coco', '.ims', '.669', '.abk', '.uni', '.gmc'
            ]

            output_dir = os.path.join(os.getcwd(), "Output")
            os.makedirs(output_dir, exist_ok=True)
            file_basename = os.path.splitext(os.path.basename(file_path))[0]

            if extension in MIDI_EXTENSIONS:
                sf2_file = self.get_selected_sf2()
                if sf2_file:
                    sf2_basename = os.path.splitext(os.path.basename(sf2_file))[0]
                    wav_output = os.path.join(output_dir, f"{file_basename}-{sf2_basename}.wav")
                    mp3_output = os.path.join(output_dir, f"{file_basename}-{sf2_basename}.mp3")
                    try:
                        subprocess.run(["fluidsynth", "-F", wav_output, sf2_file, file_path], check=True)
                        subprocess.run(["lame", wav_output, mp3_output], check=True)
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
                    except subprocess.CalledProcessError as e:
                        print(f"Error exporting track: {e}")
                        self.status_label.set_text("Error: Unable to export track")
                else:
                    self.status_label.set_text("No SoundFont selected")
            elif extension in NON_MIDI_EXTENSIONS:
                wav_output = os.path.join(output_dir, f"{file_basename}.wav")
                mp3_output = os.path.join(output_dir, f"{file_basename}.mp3")
                try:
                    # Convert non-MIDI file to WAV using ffmpeg
                    subprocess.run(["ffmpeg", "-y", "-i", file_path, wav_output], check=True)
                    # Convert WAV to MP3 using lame
                    subprocess.run(["lame", wav_output, mp3_output], check=True)
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
                except subprocess.CalledProcessError as e:
                    print(f"Error exporting track: {e}")
                    self.status_label.set_text("Error: Unable to export track")
            else:
                self.status_label.set_text("Cannot export this file type.")
        else:
            self.status_label.set_text("No file selected")
        self.spinner.stop()

    def stop_fluidsynth(self):
        if self.fluidsynth_process:
            self.fluidsynth_process.terminate()
            try:
                self.fluidsynth_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.fluidsynth_process.kill()
            self.fluidsynth_process = None
            self.status_label.set_text("Playback Stopped")

    def stop_xmp(self):
        if self.xmp_process:
            self.xmp_stopped_intentionally = True  # Set the flag
            self.xmp_process.terminate()
            try:
                self.xmp_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.xmp_process.kill()
            self.xmp_process = None
            self.status_label.set_text("Playback Stopped")

    def on_select_source_directory(self, menuitem):
        dialog = Gtk.FileChooserDialog(
            title="Select Source Directory",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.source_dir = dialog.get_filename()
            self.spinner.start()
            threading.Thread(target=self._load_files_from_new_directory).start()
        dialog.destroy()
    
    def _load_files_from_new_directory(self):
        try:
            self.stop_fluidsynth()
            self.stop_xmp()
            # Clear the store on the main thread
            GLib.idle_add(self.all_store.clear)
            # Update the file list
            self.all_files = self.find_all_files()
            GLib.idle_add(self._load_files_into_store, self.all_files)
            GLib.idle_add(self.select_current_file_in_treeview)
            GLib.idle_add(self.update_metadata)
            GLib.idle_add(self.update_file_column_title)
            GLib.idle_add(self.status_label.set_text, "Source directory updated")
        except Exception as e:
            print(f"Error loading new directory: {e}")
        finally:
            GLib.idle_add(self.spinner.stop)

    def load_files_in_background(self):
        # Step 2: Perform long-running tasks in the background
        self.stop_fluidsynth()   # Stop processes
        self.stop_xmp()
        
        # Perform the long-running task in the background
        sorted_files = sorted(self.all_files, key=lambda x: x.lower())
        
        # Load the files into the store in a non-blocking way
        GLib.idle_add(self._load_files_into_store, sorted_files)
        GLib.idle_add(self.select_current_file_in_treeview)
        GLib.idle_add(self.update_metadata)
        GLib.idle_add(self.update_file_column_title)
        GLib.idle_add(self.status_label.set_text, "Source directory updated")
        GLib.idle_add(self.spinner.stop)

    def on_select_sf2_source(self, menuitem):
        self.spinner.start()
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
        self.spinner.stop()
        dialog.destroy()

    def on_shuffle_mode_toggled(self, menuitem):
        self.shuffle_mode = menuitem.get_active()
    
        # Create and show progress dialog
        self.spinner.start()
        progress_dialog = self.create_progress_dialog("Shuffling Playlist", "Please wait while the playlist is being shuffled...")
    
        def background_task():
            try:
                # Step 1: Load all files in background and update progress dialog
                GLib.idle_add(progress_dialog.update_text, "Loading files...")
                self.all_files = self.find_all_files()

                if not self.all_files:
                    GLib.idle_add(progress_dialog.update_text, "No files found to shuffle.")
                    GLib.idle_add(progress_dialog.close)
                    GLib.idle_add(self.spinner.stop)
                    return

                # Step 2: Shuffle files
                if self.shuffle_mode:
                    GLib.idle_add(progress_dialog.update_text, "Shuffling files...")
                    random.shuffle(self.all_files)

                # Step 3: Load shuffled files into the store
                GLib.idle_add(progress_dialog.update_text, "Loading shuffled files into store...")
                GLib.idle_add(self.load_all_files)

                # Step 4: Update UI with the shuffled data
                GLib.idle_add(self.update_metadata)
                GLib.idle_add(self.update_file_column_title)
                GLib.idle_add(self.status_label.set_text, "Shuffle mode updating...")

            except Exception as e:
                print(f"Error during shuffle mode: {e}")
                GLib.idle_add(self.status_label.set_text, "An error occurred during shuffle mode.")

            finally:
                # Close progress dialog automatically once the task is done
                GLib.idle_add(progress_dialog.close)
                GLib.idle_add(self.spinner.stop)

        threading.Thread(target=background_task, daemon=True).start()

    def create_progress_dialog(self, title, message):
        dialog = Gtk.Dialog(
            title=title,
            transient_for=self,
            modal=True,
            destroy_with_parent=True,
        )
        dialog.set_resizable(False)
        dialog.get_content_area().set_border_width(10)
    
        # Create and configure the label for the progress message
        label = Gtk.Label(label=message)
        label.set_justify(Gtk.Justification.LEFT)
        label.set_line_wrap(True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD)
        dialog.get_content_area().pack_start(label, False, False, 0)
    
        # Create and configure the progress bar
        progress_bar = Gtk.ProgressBar()
        progress_bar.set_pulse_step(0.1)
        dialog.get_content_area().pack_start(progress_bar, False, False, 10)
    
        # Show all dialog elements
        dialog.show_all()
    
        # Pulse progress bar to show activity using GLib.timeout_add
        def pulse_progress_bar():
            if dialog.get_visible():
                progress_bar.pulse()
                return True  # Continue pulsing
            return False  # Stop pulsing if dialog is closed
    
        GLib.timeout_add(100, pulse_progress_bar)  # Pulse every 100ms
    
        # Utility to update text
        def update_text(new_message):
            label.set_text(new_message)
    
        # Utility to close dialog
        def close_dialog():
            dialog.destroy()
    
        # Attach update and close methods to dialog using `setattr`
        setattr(dialog, 'update_text', update_text)
        setattr(dialog, 'close', close_dialog)
    
        return dialog


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
        self.apply_monospace_font(dialog)

        # Show everything and run the dialog
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def on_quit(self, *args):
        self.status_label.set_text(f"Attempting to Quit")
        print("Quitting application...")
        self.stop_fluidsynth()
        self.stop_xmp()
        Gtk.main_quit()

    def file_filter_func(self, model, iter, data):
        search_text = self.search_entry.get_text().lower()
        if search_text == "":
            return True  # Show all if search text is empty
        filename = model[iter][0]
        foldername = model[iter][1]
        # Ensure they are strings
        if isinstance(filename, bytes):
            filename = filename.decode('utf-8', 'replace')
        elif isinstance(filename, str):
            filename = filename.encode('utf-8', 'surrogateescape').decode('utf-8', 'replace')
        else:
            filename = str(filename)
        if isinstance(foldername, bytes):
            foldername = foldername.decode('utf-8', 'replace')
        elif isinstance(foldername, str):
            foldername = foldername.encode('utf-8', 'surrogateescape').decode('utf-8', 'replace')
        else:
            foldername = str(foldername)
        return search_text in filename.lower() or search_text in foldername.lower()

    def on_search_changed(self, search_entry):
        self.spinner.start()
        self.all_filter.refilter()
        # Adjust selection after filtering
        iter = self.all_filter.get_iter_first()
        if iter:
            path = self.all_filter.get_path(iter)
            self.all_treeview.set_cursor(path)
            self.all_treeview.scroll_to_cell(path)
        else:
            # Clear selection if no items match
            self.all_treeview.get_selection().unselect_all()
        self.update_file_column_title()
        self.spinner.stop()

    def handle_fluidsynth_error(self):
        error=1
        # self.status_label.set_text("Error: fluidsynth failed to play the file.")

    def handle_xmp_error(self):
        self.status_label.set_text("Error: xmp failed to play the file.")

    def append_file_to_store(self, all_file):
        basename = os.path.basename(all_file)
        foldername = os.path.basename(os.path.dirname(all_file))
        # Store the data directly
        self.all_store.append([basename, foldername, all_file])

    def on_next_auto(self):
        self.stop_fluidsynth()
        self.stop_xmp()

        selection = self.all_treeview.get_selection()
        model, treeiter = selection.get_selected()

        if treeiter:
            next_iter = self.all_filter.iter_next(treeiter)
            if next_iter:
                path = self.all_filter.get_path(next_iter)
                self.all_treeview.set_cursor(path)
                self.all_treeview.scroll_to_cell(path)
                self.update_metadata()
                self.update_file_column_title()
                self.on_play(None)
            else:
                # Loop back to the first item
                iter = self.all_filter.get_iter_first()
                if iter:
                    path = self.all_filter.get_path(iter)
                    self.all_treeview.set_cursor(path)
                    self.all_treeview.scroll_to_cell(path)
                    self.update_metadata()
                    self.update_file_column_title()
                    self.on_play(None)
        else:
            # No selection, select the first item
            iter = self.all_filter.get_iter_first()
            if iter:
                path = self.all_filter.get_path(iter)
                self.all_treeview.set_cursor(path)
                self.all_treeview.scroll_to_cell(path)
                self.update_metadata()
                self.update_file_column_title()
                self.on_play(None)
        return False

if __name__ == "__main__":
    app = MidiSoundfontTester()
    app.show_all()
    Gtk.main()
