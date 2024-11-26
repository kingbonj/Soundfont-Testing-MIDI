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
import requests
import re
import webbrowser
import gi
import io
from PIL import Image, ImageDraw
import base64
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')  # Specify the GdkPixbuf version
from gi.repository import Gtk, Gdk, Pango, GLib, GObject, GdkPixbuf
import mido

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

class ImageScraper:
    def __init__(self, webdriver_path, search_key="default", output_path=".", headless=True):
        self.driver = self._init_driver(webdriver_path, headless)
        self.search_key = search_key
        self.output_path = output_path

    @staticmethod
    def _init_driver(webdriver_path, headless):
        options = Options()
        if headless:
            options.add_argument("--headless")
        service = Service(webdriver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_window_size(800, 600)
        print("Initialising webdriver...")
        return driver

    def find_image_url(self):
        search_url = f"https://www.google.com/search?q=%22{self.search_key}%22+retro+videogame+cover&source=lnms&tbm=isch"
        self.driver.get(search_url)
        print(f"Searching for {self.search_key} image...")

        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "H8Rx8c"))
            )
            div_container = self.driver.find_element(By.CLASS_NAME, "H8Rx8c")
            target_image = div_container.find_element(By.TAG_NAME, "img")
            img_src = target_image.get_attribute("src")
            return img_src
        except (TimeoutException, NoSuchElementException):
            print("Image search timed out!")
            return None

    def save_image(self, img_url):
        output_filepath = os.path.join(self.output_path, "image.jpg")
        if img_url.startswith("data:image"):  # Handle base64-encoded image
            header, encoded = img_url.split(",", 1)
            data = base64.b64decode(encoded)
            with open(output_filepath, "wb") as f:
                f.write(data)
            print("Image found!")
            print(f"Image saved to {output_filepath}")
        else:  # Handle normal image URL
            response = requests.get(img_url, stream=True, timeout=5)
            if response.status_code == 200:
                with Image.open(io.BytesIO(response.content)) as img:
                    img.save(output_filepath)
                    print(f"Image saved to {output_filepath}")

    def process_directory(self):
        image_url = self.find_image_url()
        if image_url:
            self.save_image(image_url)

class MidiSoundfontTester(Gtk.Window):
    def __init__(self):
        super().__init__(title="MIDI SoundFont Testing Program v0.1.4")
        self.set_default_size(1200, 600)
        self.set_border_width(5)

        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)

        self.set_icon_name("multimedia-player")

        #build favourites
        self.favourites_file = os.path.join(os.getcwd(), "favourites.list")
        self.favourites = set()  # Store favourited file paths
        self.load_favourites()  # Load favourites on startup
        
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
            "mplayer",
        ]
        self.check_requirements()

        self.elapsed_timer = None  # Ensure this is initialized here

        # File lists
        self.all_files = self.find_all_files()
        self.sf2_files = self.find_sf2_files()
        self.fluidsynth_process = None
        self.xmp_process = None
        self.shuffle_mode = False
        self.streams = [
            {'url': 'http://83.240.65.106:8000/dos', 'title': 'LiquidDOS Classic'},
            {'url': 'http://83.240.65.106:8000/doom', 'title': 'LiquidDOS Doom'},
            {'url': 'https://relay.rainwave.cc/chiptune.mp3', 'title': 'Rainwave Chiptune'},
            # Add more streams as needed
        ]
        self.current_stream_index = 0  # Start with the first URL
        self.radio = False
        self.stream_title = "Unassigned title"
        self.mplayer_process = None  # Initialize mplayer_process
        self.xmp_stopped_intentionally = False  # Flag to handle intentional termination
        self.online_services = False  # Default: disabled
        self.image_viewer = True
        self.current_pixbuf = None  # Initialise as None
        self.meta_extract = True
        self.image_viewer = True
        self.fluidsynth_stopped_intentionally = False  # Initialize the flag

        # Build UI
        self.build_ui()
        print("Building UI...")

        # Load initial data
        self.load_all_files()
        self.load_sf2_files()
        self.update_metadata()
        GLib.idle_add(self.update_image_pane)
        # Handle close event
        self.connect("destroy", self.on_quit)

        # Connect key-press-event to the window
        self.connect("key-press-event", self.on_key_press_event)
        self.set_focus(self.all_treeview)

    def on_key_press_event(self, widget, event):

        focused_widget = self.get_focus()
    
        # If the focused widget is a Gtk.Entry or Gtk.TextView, do not handle the key press
        if isinstance(focused_widget, (Gtk.Entry, Gtk.TextView)):
            return False  # Allow the event to propagate and be handled by the text widget

        # Check for left arrow key
        if event.keyval == Gdk.KEY_Left:
            self.on_previous(None)
            return True  # Event has been handled
    
        # Check for right arrow key
        elif event.keyval == Gdk.KEY_Right:
            self.on_next(None)
            return True  # Event has been handled
    
        # Check for space bar
        elif event.keyval == Gdk.KEY_space:
            self.toggle_play_pause()
            return True  # Event has been handled
    
        # Check for up arrow key
        elif event.keyval == Gdk.KEY_Up:
            self.set_focus(self.sf2_treeview)
            self.select_previous_soundfont()
            return True  # Event has been handled
    
        # Check for down arrow key
        elif event.keyval == Gdk.KEY_Down:
            self.set_focus(self.sf2_treeview)
            self.select_next_soundfont()
            return True  # Event has been handled

            # Check for 'i' key (both lowercase and uppercase if needed)
        elif event.keyval == Gdk.KEY_i or event.keyval == Gdk.KEY_I:
            self.toggle_image_viewer()
            return True  # Event has been handled
    
        # For other keys, do not block the event
        return False

    def is_playing(self):
        # Check if either fluidsynth_process or xmp_process is running
        return self.fluidsynth_process is not None or self.xmp_process is not None or self.radio

    def toggle_play_pause(self):
        if self.is_playing():
            self.on_pause(None)
        else:
            self.on_play(None)
            
    def select_previous_soundfont(self):
        selection = self.sf2_treeview.get_selection()
        model, treeiter = selection.get_selected()
    
        if treeiter:
            path = model.get_path(treeiter)
            index = path.get_indices()[0]
            if index > 0:
                new_index = index - 1
            else:
                new_index = len(model) - 1  # Wrap around to last item
    
            new_path = Gtk.TreePath(new_index)
            self.sf2_treeview.set_cursor(new_path)
            self.sf2_treeview.scroll_to_cell(new_path)
            self.on_play(None)
    
            # Update status label
            sf2_file = self.get_selected_sf2()
            if sf2_file:
                self.status_label.set_text(f"Selected SoundFont: {os.path.basename(sf2_file)}")
        else:
            # No selection, select the last item
            last_index = len(model) - 1
            new_path = Gtk.TreePath(last_index)
            self.sf2_treeview.set_cursor(new_path)
            self.sf2_treeview.scroll_to_cell(new_path)
            self.on_play(None)

    def select_next_soundfont(self):
        selection = self.sf2_treeview.get_selection()
        model, treeiter = selection.get_selected()
    
        if treeiter:
            path = model.get_path(treeiter)
            index = path.get_indices()[0]
            if index < len(model) - 1:
                new_index = index + 1
            else:
                new_index = 0  # Wrap around to first item
    
            new_path = Gtk.TreePath(new_index)
            self.sf2_treeview.set_cursor(new_path)
            self.sf2_treeview.scroll_to_cell(new_path)
            self.on_play(None)
    
            # Update status label
            sf2_file = self.get_selected_sf2()
            if sf2_file:
                self.status_label.set_text(f"Selected SoundFont: {os.path.basename(sf2_file)}")
        else:
            # No selection, select the first item
            new_path = Gtk.TreePath(0)
            self.sf2_treeview.set_cursor(new_path)
            self.sf2_treeview.scroll_to_cell(new_path)
            self.on_play(None)

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
        self.create_context_menu()
        self.apply_monospace_font(self.context_menu)

    def create_menu_bar(self, grid):
        # Create the menu bar
        menu_bar = Gtk.MenuBar()
        menu_bar.connect("realize", lambda widget: self.apply_monospace_font(widget))
    
        # Create the File Menu
        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label="File")
        file_item.set_submenu(file_menu)  # Associate the File menu with the File item
    
        select_source_item = Gtk.MenuItem(label="📂 Select Source Directory...")
        select_source_item.connect("activate", self.on_select_source_directory)
        file_menu.append(select_source_item)
    
        select_sf2_item = Gtk.MenuItem(label="📂 Select SoundFont Directory...")
        select_sf2_item.connect("activate", self.on_select_sf2_source)
        file_menu.append(select_sf2_item)

        select_output_item = Gtk.MenuItem(label="📂 Open Output Directory...")
        select_output_item.connect("activate", self.on_select_output_source)
        file_menu.append(select_output_item)
    
        quit_item = Gtk.MenuItem(label="❌ Quit")
        quit_item.connect("activate", self.on_quit)
        file_menu.append(quit_item)
    
        # Create the Settings Menu
        settings_menu = Gtk.Menu()
        settings_item = Gtk.MenuItem(label="Settings")
        settings_item.set_submenu(settings_menu)  # Associate the Settings menu with the Settings item
    
        shuffle_mode_item = Gtk.CheckMenuItem(label="🔀 Shuffle Mode")
        shuffle_mode_item.set_active(self.shuffle_mode)
        shuffle_mode_item.connect("toggled", self.on_shuffle_mode_toggled)
        settings_menu.append(shuffle_mode_item)
    
        # Create Online Services menu item
        self.online_services_menuitem = Gtk.CheckMenuItem(label="🌐 Scrape Images")
        self.online_services_menuitem.set_active(self.online_services)
        self.online_services_menuitem.connect("toggled", self.on_online_services_toggled)
        settings_menu.append(self.online_services_menuitem)
    
        # Create the View Menu
        view_menu = Gtk.Menu()
        view_item = Gtk.MenuItem(label="View")
        view_item.set_submenu(view_menu)  # Associate the Settings menu with the Settings item

         # Create Image Viewer menu item
        self.image_viewer_menuitem = Gtk.CheckMenuItem(label="🖻 Image Viewer")
        self.image_viewer_menuitem.set_active(self.image_viewer)
        self.image_viewer_menuitem.connect("toggled", self.on_image_viewer_toggled)
        view_menu.append(self.image_viewer_menuitem)

        # Create Metadata Extractor menu item
        self.meta_extract_menuitem = Gtk.CheckMenuItem(label="🏷️ Embedded Metadata")
        self.meta_extract_menuitem.set_active(self.meta_extract)
        self.meta_extract_menuitem.connect("toggled", self.on_meta_extract_toggled)
        view_menu.append(self.meta_extract_menuitem)

        # Create Dark Mode menu item
        dark_mode_item = Gtk.CheckMenuItem(label="🌗 Dark Mode")
        dark_mode_item.set_active(
            Gtk.Settings.get_default().get_property("gtk-application-prefer-dark-theme")
        )
        dark_mode_item.connect("toggled", self.on_dark_mode_toggled)
        view_menu.append(dark_mode_item)

        # Theme submenu
        theme_menu = Gtk.Menu()
        theme_item = Gtk.MenuItem(label="🎨 Themes...")
        theme_item.set_submenu(theme_menu)
        view_menu.append(theme_item)
    
        # MS-DOS theme menu item
        msdos_theme_item = Gtk.MenuItem(label="MS-DOS")
        msdos_theme_item.connect("activate", self.on_msdos_theme_selected)
        theme_menu.append(msdos_theme_item)
        deus_ex_amber_theme_item = Gtk.MenuItem(label="Sarif Industries")
        deus_ex_amber_theme_item.connect("activate", self.on_deus_ex_amber_theme_selected)
        theme_menu.append(deus_ex_amber_theme_item)
        chiptune_theme_item = Gtk.MenuItem(label="Chiptune Blues")
        chiptune_theme_item.connect("activate", self.on_chiptune_blue_theme_selected)
        theme_menu.append(chiptune_theme_item)

        # Create the About Menu
        about_menu = Gtk.Menu()
        about_item = Gtk.MenuItem(label="About")
        about_item.set_submenu(about_menu)  # Associate the About menu with the About item
    
        licence_item = Gtk.MenuItem(label="🐧 Licence")
        licence_item.connect("activate", self.on_licence)
        about_menu.append(licence_item)
    
        # Add items to the menu bar
        menu_bar.append(file_item)
        menu_bar.append(settings_item)
        menu_bar.append(view_item)
        menu_bar.append(about_item)
    
        # Apply monospace font to the menu bar
    
        # Attach the menu bar to the grid
        grid.attach(menu_bar, 0, 0, 1, 1)
    
        # Show the menu bar and its items
        menu_bar.show_all()

    def create_panes(self, grid):
        # Define absolute variables for image pane size
        self.image_pane_width = 300  # Fixed width for the image pane
        
        hpaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        hpaned.set_hexpand(True)
        hpaned.set_vexpand(True)
        grid.attach(hpaned, 0, 1, 1, 1)
        
        # Left Pane: Files List
        left_pane_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Filter files...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        left_pane_box.pack_start(self.search_entry, False, False, 0)
        
        self.all_store = Gtk.ListStore(object, object, object)
        self.all_filter = self.all_store.filter_new()
        self.all_filter.set_visible_func(self.file_filter_func)
        self.all_treeview = Gtk.TreeView(model=self.all_filter)
        self.all_treeview.connect("button-press-event", self.on_treeview_button_press)
        self.all_treeview.set_has_tooltip(True)
        self.all_treeview.connect("query-tooltip", self.on_file_query_tooltip)
        
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
        
        left_pane_box.pack_start(scrolled_window_files, True, True, 0)
        hpaned.add1(left_pane_box)
        hpaned.set_position(300)
        
        vpaned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        vpaned.set_hexpand(True)
        vpaned.set_vexpand(True)
        vpaned.connect("size-allocate", self.on_resize_upper_pane)
        vpaned.set_hexpand(True)
        vpaned.set_vexpand(True)
        hpaned.add2(vpaned)
        
        # Upper Right Pane: SF2 and Image
        upper_hpaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        upper_hpaned.set_hexpand(True)
        upper_hpaned.set_vexpand(True)
        upper_hpaned.set_size_request(-1, 280)  # Set minimum height
        vpaned.add1(upper_hpaned)
        vpaned.connect("size-allocate", self.on_resize_set_upper_pane_height)
        
        # SoundFonts Pane
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
        upper_hpaned.set_margin_top(35)  # Add the margin here
        upper_hpaned.add1(scrolled_window_sf2)
        
        # Image Pane
        image_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        treeview_header = Gtk.TreeView()
        treeview_header.set_headers_visible(True)
        treeview_header.set_model(Gtk.ListStore(str))
        header_renderer = Gtk.CellRendererText()
        header_column = Gtk.TreeViewColumn("Image Viewer")
        header_column.pack_start(header_renderer, True)
        treeview_header.append_column(header_column)

        image_vbox.pack_start(treeview_header, False, False, 0)
        
        # Encapsulate image viewer components into a container
        self.image_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.image_box.set_hexpand(False)
        self.image_box.set_vexpand(False)
        
        # Dummy header
        treeview_header = Gtk.TreeView()
        treeview_header.set_headers_visible(True)
        treeview_header.set_model(Gtk.ListStore(str))
        header_renderer = Gtk.CellRendererText()
        header_column = Gtk.TreeViewColumn("Image Viewer")
        header_column.pack_start(header_renderer, True)
        treeview_header.append_column(header_column)
        self.image_box.pack_start(treeview_header, False, False, 0)
        
        # Image Pane
        self.image_pane = Gtk.Image()
        self.image_pane.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        self.image_pane.set_hexpand(False)
        self.image_pane.set_vexpand(False)
        self.image_pane.set_size_request(280, 220)
        scrolled_window_image = Gtk.ScrolledWindow()
        scrolled_window_image.set_hexpand(False)
        scrolled_window_image.set_vexpand(False)
        scrolled_window_image.set_size_request(300, 220)
        scrolled_window_image.add(self.image_pane)
        self.image_box.pack_start(scrolled_window_image, True, True, 0)

        self.image_box.set_name("image_viewer_container")  # Assign ID
        
        # Add image_box to the upper pane
        upper_hpaned.add2(self.image_box)
    
        # Dynamically set SF2 pane width
        upper_hpaned.set_size_request(280, 220)  # Fixed width and height
        upper_hpaned.connect("size-allocate", self.on_resize_set_sf2_pane_width)

        # Metadata Pane
        metadata_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        metadata_header = Gtk.TreeView()
        renderer_metadata = Gtk.CellRendererText()
        column_metadata = Gtk.TreeViewColumn("Metadata", renderer_metadata, text=0)
        metadata_header.append_column(column_metadata)
        self.apply_monospace_font(metadata_header)
        metadata_header.set_headers_visible(True)
        metadata_header.set_model(Gtk.ListStore(str))
        metadata_box.pack_start(metadata_header, False, False, 0)
        
        self.metadata_view = Gtk.TextView()
        self.metadata_view.set_editable(False)
        self.metadata_view.set_cursor_visible(True)
        self.metadata_view.set_wrap_mode(Pango.WrapMode.WORD)
        self.apply_monospace_font(self.metadata_view)
        scrolled_window_metadata = Gtk.ScrolledWindow()
        scrolled_window_metadata.set_hexpand(False)
        scrolled_window_metadata.set_vexpand(False)
        scrolled_window_metadata.add(self.metadata_view)
        metadata_box.pack_start(scrolled_window_metadata, True, True, 0)
        
        vpaned.add2(metadata_box)

        # Assign IDs to parent containers if not already done
        upper_hpaned.set_name("upper_pane")
        vpaned.set_name("vertical_pane")

    def on_resize_upper_pane(self, widget, allocation):
        total_height = allocation.height
        current_position = widget.get_position()
    
        # Ensure the upper pane maintains its minimum height
        if current_position < 200:
            widget.set_position(200)
        elif current_position > total_height - 200:
            # Ensure the lower pane has enough space
            widget.set_position(200)
        
    def on_resize_set_sf2_pane_width(self, widget, allocation):
        total_width = allocation.width  # Get the total width of the parent container
        sf2_pane_width = max(total_width - self.image_pane_width, 0)  # Ensure non-negative width
        widget.set_position(sf2_pane_width)  # Dynamically adjust the SF2 pane's width

    def on_resize_set_upper_pane_height(self, widget, allocation):
        min_height = 280  # Minimum height for upper panes
        current_position = widget.get_position()
    
        # If the current position is smaller than the minimum, set it back to min_height
        if current_position < min_height:
            widget.set_position(min_height)

    def update_image_pane(self):
        file_path = self.get_selected_file()
    
        if file_path:
            folder_path = os.path.dirname(file_path)
            image_path = os.path.join(folder_path, "image.jpg")
    
            # Check if the local image file exists
            if os.path.isfile(image_path):
                self.scale_image_to_fit(image_path)
            elif self.online_services:  # If online services are enabled
                search_key = os.path.basename(folder_path)
                webdriver_path = "/usr/bin/chromedriver"  # Adjust this path as necessary
    
                try:
                    scraper = ImageScraper(webdriver_path, search_key=search_key, output_path=folder_path, headless=True)
                    scraper.process_directory()
                    # Retry loading the image after scraping
                    if os.path.isfile(image_path):
                        self.scale_image_to_fit(image_path)
                    else:
                        self.image_pane.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
                        self.image_pane.set_tooltip_text("Image missing")
                except Exception as e:
                    print(f"[ERROR] Failed to fetch and save image: {e}")
                    traceback.print_exc()
                    self.image_pane.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
                    self.image_pane.set_tooltip_text("[ERROR] Failed to fetch and save image")
            else:
                # Fallback to a default image
                default_image_path = os.path.join(os.getcwd(), "image.jpg")
                if os.path.isfile(default_image_path):
                    self.scale_image_to_fit(default_image_path)
                    self.image_pane.set_tooltip_text("Fallback Image")
                else:
                    self.image_pane.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
                    self.image_pane.set_tooltip_text("Default image not found")
        else:
            # On launch or when no file is selected, display the default image
            default_image_path = os.path.join(os.getcwd(), "image.jpg")
            if os.path.isfile(default_image_path):
                self.scale_image_to_fit(default_image_path)
                self.image_pane.set_tooltip_text("Default Image")
            else:
                self.image_pane.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
                self.image_pane.set_tooltip_text("Default image not found")

    def scale_image_to_fit(self, image_path):
        try:
            # Load the image from the file
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_path)
            scaled_pixbuf = pixbuf.scale_simple(300, 220, GdkPixbuf.InterpType.BILINEAR)
            self.image_pane.set_from_pixbuf(scaled_pixbuf)
            self.image_pane.set_tooltip_text(f"{image_path}")
        except Exception as e:
            print(f"Error scaling image: {e}")
            self.image_pane.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
            self.image_pane.set_tooltip_text("Error scaling image")
    
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

    def apply_custom_theme(self, theme_name, font_filename, font_family, css_body):
        try:
            # Load the custom font
            font_path = os.path.join(os.getcwd(), font_filename)
            if not os.path.isfile(font_path):
                self.status_label.set_text(f"Error: {font_filename} not found.")
                return
    
            # Create a temporary directory for custom fonts
            font_dir = os.path.join(tempfile.gettempdir(), "custom_fonts")
            os.makedirs(font_dir, exist_ok=True)
            shutil.copy(font_path, font_dir)
    
            # Update the font cache for the temporary directory
            subprocess.run(["fc-cache", "-f", font_dir], check=True)
    
            # Ensure the font directory is included in Fontconfig paths
            if "FONTCONFIG_PATH" in os.environ:
                os.environ["FONTCONFIG_PATH"] += os.pathsep + font_dir
            else:
                os.environ["FONTCONFIG_PATH"] = font_dir
    
            # Apply the CSS
            css = f"""
            * {{
                font-family: "{font_family}", Monospace;
            }}
            {css_body}
            """
    
            style_provider = Gtk.CssProvider()
            style_provider.load_from_data(css_body.encode('utf-8'))
            
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION  # Ensure high priority
            )
            # Update status label to confirm theme change
            self.status_label.set_text(f"{theme_name} Theme Applied")
        except subprocess.CalledProcessError as e:
            print(f"Fontconfig error: {e}")
            self.status_label.set_text(f"Error: Unable to apply {theme_name} theme (Fontconfig issue).")
        except Exception as e:
            print(f"Error applying {theme_name} theme: {e}")
            self.status_label.set_text(f"Error: Unable to apply {theme_name} theme.")

    def on_chiptune_blue_theme_selected(self, menuitem):
        # Define theme configurations
        font_filename = "DOS.ttf"
        font_family = "DOS"
    
        css_body = """
        * {
            font-family: "DOS", Monospace;
            font-size: 14px;
            font-weight: bold;
            background-color: #000088;
            color: #FFFF00;
            border: none;
        }
        menuitem > label {
            color: darkgray;
            background-color: darkblue;
        }

        menuitem:hover, menuitem:selected > label,
        menuitem:hover > label {
            color: darkblue;
            background-color: darkgray;
        }

        textview * {
            background-color: transparent;
            color: darkgray;
        }
        textview text selection {
            background-color: darkgray;
            color: darkblue;
        }
        treeview {
            background-color: transparent;
            color: darkgray;
        }

        treeview row:hover {
            background-color: darkgray;
            color: darkblue;
        }
        
        treeview row:selected {
            background-color: darkgray;
            color: #000088;
        }

        treeview:selected {
            background-color: darkgray;
            color: #000088;
        }
        treeview:hover {
            background-color: darkgray;
            color: darkblue;
        }
        treeview row {
            background-color: #000088;
            color: #FFFFFF;
        }

        treeview > header {
            background-color: inherit;
            color: darkgray;
            font-weight: bold;
            padding: 5px;
        }
        
        /* Buttons */
        button {
            background-color: #000088; /* Default button background */
            color: #FFFF00;           /* Default button text/icon colour */
            border: 1px solid #FFFF00; /* Add a border to distinguish buttons */
            margin: 0;
        }
        scrolledwindow {
            background-color: transparent; /* Ensure ScrolledWindow background is unaffected */
            border: none;                 /* Remove any borders applied by the global rule */
        }
        
        scrolledwindow > * {
            background-color: transparent; /* Ensure child widgets of ScrolledWindow inherit transparency */
        }
        
        treeview {
            background-color: transparent; /* Ensure TreeView rows are transparent */
        }
        
        overshoot {
            background-color: transparent; /* Prevent coloured blocks in overshoot areas */
        }


        button:active {
            background-color: #000088; /* Active button retains dark blue background */
            color: #FFFF00;
        }
        
        button:focus {
            background-color: #000088; /* Focused button retains dark blue background */
            color: #FFFF00;
        }
        
        button:disabled {
            background-color: darkgray; /* Disabled button greyed out */
            color: black;
        }
        
        /* Round Buttons (custom class) */
        button.round-button {
            background-color: #000088;
            color: darkgray;
            border-radius: 15px;      /* Makes buttons round */
            border: 1px solid #FFFF00;
            padding: 10px;
        }
        
        button.round-button:hover {
            background-color: darkgray;
            color: darkblue;
        }

        button.round-button:hover > image {
            background-color: transparent;
            color: darkblue;
        }
        
        button.round-button:active {
            background-color: #000088;
            color: #FFFF00;
        }
        
        button.round-button:focus {
            background-color: darkgray;
            color: #FFFF00;
        }
        
        button > image,
        button.round-button > image,
        button.media-button > image {
            background-color: transparent;
            color: inherit; 
        }

        button > label,
        button.round-button > label,
        button.media-button > label {
            background-color: #000088;
            color: #FFFF00; 
        }

        button > box > label,
            button.round-button > label,
            button.media-button > label {
            background-color: #000088;
            color: #FFFF00; 
        }

        button:hover > box > label,
            button.round-button > label,
            button.media-button > label {
            background-color: darkgray;
            color: darkblue; 
        }        

        button:hover > box > image,
            button.round-button > label,
            button.media-button > label {
            background-color: transparent;
            color: darkblue; 
        }
        volumebutton > *{
            background-color: #000088;
            color: #FFFF00;
            border: none; /* Flat button style */
            padding: 5px;
            border-radius: 10px; /* Slight rounding for modern aesthetics */
        }
        
        /* Hover and Active States */
        volumebutton:hover > * {
            background-color: darkgray;
            color: darkblue;
        }
        
        volumebutton:active > * {
            background-color: #000088;
            color: #FFFF00;
        }
        
        /* Scrollbars */
        scrollbar * {
            background-color: darkgray;
        }
        
        label {
            background-color: #000088;
            color: #FFFF00; 
        }

        label:hover {
            background-color: darkgray;
            color: darkblue; 
        }

        button:hover > box,
        button:hover > label,
        button:hover > image,
        button:hover > box > label, 
        button:hover > box > image {
            background-color: transparent; /* Label background on hover */
            color: #FFFF00;            /* Optional: Change label text colour */
            padding: 0;                /* Remove extra padding */
            margin: 0;                 /* Remove any default margin */
        }

        button:focus > box,
        button:focus > label,
        button:focus > image,
        button:focus > box > label, 
        button:focus > box > image {
            background-color: darkgray; /* Label background on hover */
            color: darkblue;            /* Optional: Change label text colour */
            padding: 0;                /* Remove extra padding */
            margin: 0;                 /* Remove any default margin */
        }   
        
        scrollbar slider {
            background-color: #000088;
            border: 1px solid darkgray;
        }
        
        scrollbar slider:hover {
            background-color: darkgray;
        }

        scrollbar trough {
            background-color: #000088;
        }
        
        /* Tooltip */
        tooltip {
            background-color: #000088;
            color: #FFFF00;
            border: 1px solid #FFFF00;
            padding: 5px;
        }
        """
    
        # Apply the theme
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css_body.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
        # Apply font
        self.apply_custom_theme("Chiptune Blue", font_filename, font_family, css_body)

    def on_msdos_theme_selected(self, menuitem):
        # Define font details
        font_filename = "DOS.ttf"  # Ensure this font file exists in the working directory
        font_family = "Perfect DOS VGA 437 Win"
            
        # Define the CSS body
        css_body = """
        * {
            font-family: "Perfect DOS VGA 437 Win", Monospace;
            font-size: 14px;
            font-weight: bold;
            background-color: #000000;  /* Black background */
            color: darkgray;            /* Grey text */
            border: none;
        }
    
        menuitem > label {
            color: darkgray;            /* Grey text */
            background-color: #000000; /* Black */
        }
    
        menuitem:hover, menuitem:selected > label,
        menuitem:hover > label {
            color: #000000;            /* Black text on hover */
            background-color: darkgray; /* Grey */
        }
    
        textview * {
            background-color: transparent;
            color: darkgray;
        }

        textview text selection {
            background-color: darkgray;
            color: #000000;
        }
        
        treeview {
            background-color: transparent;
            color: darkgray;
        }
    
        treeview row:hover {
            background-color: darkgray; /* Grey */
            color: #000000;            /* Black */
        }
    
        treeview row:selected {
            background-color: darkgray;
            color: #000000;
        }
    
        treeview:selected {
            background-color: darkgray;
            color: #000000;
        }
    
        treeview:hover {
            background-color: darkgray;
            color: #000000;
        }
    
        treeview row {
            background-color: #000000;
            color: #FFFFFF;            /* White text */
        }
    
        treeview > header {
            background-color: inherit;
            color: darkgray;
            font-weight: bold;
            padding: 5px;
        }
        
        /* Buttons */
        button {
            background-color: #000000; /* Default button background */
            color: #C0C0C0;           /* Grey text/icon */
            border: 1px solid darkgray;
            margin: 0;
        }
    
        button:hover {
            background-color: darkgray; /* Grey */
            color: #000000;            /* Black text */
        }
    
        button:active {
            background-color: #000000;
            color: #C0C0C0;
        }
    
        button:focus {
            background-color: #000000;
            color: #C0C0C0;
        }
    
        button:disabled {
            background-color: #808080; /* Dim grey */
            color: #000000;
        }
    
        /* Round Buttons */
        button.round-button {
            background-color: #000000;
            color: #C0C0C0;
            border-radius: 15px;
            border: 1px solid darkgray;
            padding: 10px;
        }
    
        button.round-button:hover {
            background-color: darkgray;
            color: #000000;
        }
    
        button.round-button:active {
            background-color: #000000;
            color: darkgray;
        }
    
        button.round-button:focus {
            background-color: darkgray;
            color: darkgray;
        }
    
        button > image,
        button.round-button > image,
        button.media-button > image {
            background-color: transparent;
            color: white;
        }
    
        button > label,
        button.round-button > label,
        button.media-button > label {
            background-color: transparent;
            color: red;
        }
    
        volumebutton > * {
            background-color: #000000;
            color: darkgray;
            border: none;
            padding: 5px;
            border-radius: 10px;
        }
    
        volumebutton:hover > * {
            background-color: darkgray;
            color: #000000;
        }
    
        volumebutton:active > * {
            background-color: #000000;
            color: darkgray;
        }
    
        scrollbar * {
            background-color: darkgray;
        }
    
        scrollbar slider {
            background-color: #000000;
            border: 1px solid darkgray;
        }
    
        scrollbar slider:hover {
            background-color: darkgray;
        }
    
        scrollbar trough {
            background-color: #000000;
        }
    
        label {
            background-color: #000000;
            color: darkgray;
        }
    
        label:hover {
            background-color: darkgray;
            color: #000000;
        }
    
        tooltip {
            background-color: #000000;
            color: darkgray;
            border: 1px solid darkgray;
            padding: 5px;
        }
        scrolledwindow {
            background-color: transparent; /* Ensure ScrolledWindow background is unaffected */
            border: none;                 /* Remove any borders applied by the global rule */
        }
        
        scrolledwindow > * {
            background-color: transparent; /* Ensure child widgets of ScrolledWindow inherit transparency */
        }
        """
            
        # Apply the theme
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css_body.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
        # Apply font
        self.apply_custom_theme("MS-DOS", font_filename, font_family, css_body)
    
    def on_deus_ex_amber_theme_selected(self, menuitem):
        # Define font details
        font_filename = "deusex.otf"  # Ensure this font file exists in the working directory
        font_family = "Deus Ex"
        
        # Define the CSS body
        css_body = """
        * {
            font-family: "Deus Ex", Monospace;
            font-size: 14px;
            font-weight: normal;
            background-color: #1a1a1a; /* Dark base background */
            color: #b38235;           /* Amber text */
            border: none;
        }

        menuitem {
            color: #b38235;           /* Amber text */
            background-color: #1a1a1a; /* Slightly lighter dark background */
        }
    
        menuitem > label {
            color: #b38235;           /* Amber text */
            background-color: #1a1a1a; /* Slightly lighter dark background */
        }
    
        menuitem:hover, menuitem:selected > label,
        menuitem:hover > label {
            color: #121212;           /* Dark text on hover */
            background-color: #b38235; /* Amber background */
        }
    
        textview * {
            background-color: transparent;
            color: #b38235;
        }

        textview text selection {
            background-color: #b38235;
            color: #121212;
        }
        
        treeview {
            background-color: transparent;
            color: #b38235;
        }
    
        treeview row:hover {
            background-color: #242424; /* Highlighted grey */
            color: #b38235;
        }
        
        treeview row:selected {
            background-color: #b38235; /* Amber selection */
            color: #121212;           /* Inverse text */
        }
    
        treeview:selected {
            background-color: #b38235;
            color: #121212;
        }
    
        treeview:hover {
            background-color: #242424;
            color: #b38235;
        }
    
        treeview row {
            background-color: #121212;
            color: #b38235;
        }
    
        treeview > header {
            background-color: inherit;
            color: #b38235;
            font-weight: bold;
            padding: 5px;
        }
        
        /* Buttons */
        button {
            background-color: #1a1a1a;
            color: #b38235;
            border: 1px solid #b38235;
            margin: 0;
        }
    
        button:hover {
            background-color: #242424;
            color: #b38235;
        }
    
        button:active {
            background-color: #b38235;
            color: #121212;
        }
    
        button:focus {
            background-color: #1a1a1a;
            color: #b38235;
        }
    
        button:disabled {
            background-color: #2e2e2e;
            color: #555555;
        }
    
        button.round-button {
            background-color: #1a1a1a;
            color: #b38235;
            border-radius: 15px;
            border: 1px solid #b38235;
            padding: 10px;
        }
    
        button.round-button:hover {
            background-color: #242424;
            color: #b38235;
        }
    
        button.round-button:active {
            background-color: #b38235;
            color: #121212;
        }

        button > image,
        button.round-button > image,
        button.media-button > image {
                background-color: transparent;
                color: #b38235;
        }
    
        button > label,
        button.round-button > label,
        button.media-button > label {
            background-color: transparent;
            color: #b38235;
        }
    
        volumebutton > * {
            background-color: #1a1a1a;
            color: #b38235;
            border: none;
            padding: 5px;
            border-radius: 10px;
        }
    
        volumebutton:hover > * {
            background-color: #242424;
            color: #b38235;
        }
    
        volumebutton:active > * {
            background-color: #b38235;
            color: #121212;
        }
    
        scrollbar * {
            background-color: #1a1a1a;
        }
    
        scrollbar slider {
            background-color: #b38235;
            border: 1px solid #1a1a1a;
        }
    
        scrollbar slider:hover {
            background-color: #b38235;
        }
    
        scrollbar trough {
            background-color: #121212;
        }
    
        label {
            background-color: #1a1a1a;
            color: #b38235;
        }
    
        label:hover {
            background-color: #242424;
            color: #b38235;
        }
    
        tooltip {
            background-color: #1a1a1a;
            color: #b38235;
            border: 1px solid #b38235;
            padding: 5px;
        }

        scrolledwindow {
            background-color: transparent;
            border: none;
        }
        
        scrolledwindow > * {
            background-color: transparent;
        }
        
        """
        
        # Apply the theme
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css_body.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
        # Apply font
        self.apply_custom_theme("Deus Ex Amber", font_filename, font_family, css_body)
    
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
        
        # Create the Gtk.Image from a file
        try:
            self.image = Gtk.Image.new_from_file("soundfontpy.png")
        except Exception as e:
            print(f"Error loading image: {e}")
            self.image = Gtk.Label(label="Image not found.")
        # Set the desired width and height
        self.image.set_size_request(50, 20)  # Width: 50px, Height: 20px
        controls_box.pack_start(self.image, False, False, 0)
    
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(20, 20)  # Set a size to ensure visibility
        controls_box.pack_start(self.spinner, False, False, 0)
        # Create a CSS provider and apply it globally
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .round-button {
                padding: 10px; /* Ensure round-button padding is consistent */
            }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
    
        # Helper function to create round buttons
        # Helper function to create round buttons with symbolic icons
        def create_round_button(icon_name, tooltip, callback):
            button = Gtk.Button()
            icon = Gtk.Image.new_from_icon_name(f"{icon_name}-symbolic", Gtk.IconSize.BUTTON)
            button.add(icon)
            button.set_tooltip_text(tooltip)
            button.connect("clicked", callback)
            button.set_size_request(50, 50)  # Optional size to make buttons consistent
            button.get_style_context().add_class("round-button")  # Add the custom CSS class
            return button

        self.volume_button = Gtk.VolumeButton()
        initial_volume = self.get_current_volume()
        self.volume_button.set_value(initial_volume)  # Set initial volume to current level
        self.volume_button.connect("value-changed", self.on_volume_changed)
        self.volume_button.set_size_request(50, 50)  # Optional size to match round button size
        self.volume_button.get_style_context().add_class("round-button")  # Apply the CSS class
        controls_box.pack_start(self.volume_button, False, False, 0)

        # Radio Button
        self.fav_button = create_round_button("starred", "Favourites", self.on_fav)
        controls_box.pack_start(self.fav_button, False, False, 0)
        
        # Radio Button
        self.radio_button = create_round_button("network-wireless", "Stream Online Radio", self.on_radio)
        controls_box.pack_start(self.radio_button, False, False, 0)
    
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

        # **Add the new playback label here**
        self.playback_label = Gtk.Label(label="00:00 / 00:00")
        self.playback_label.set_margin_start(10)  # Add some space between the button and label
        self.playback_label.set_justify(Gtk.Justification.LEFT)
        controls_box.pack_start(self.playback_label, False, False, 0)

        # Create a right-aligned box for the status label
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_box.set_hexpand(True)  # Allow it to expand horizontally within controls_box
        status_box.set_halign(Gtk.Align.END)  # Align the status_box to the right
    
        # Create the status label with ellipsizing enabled
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_ellipsize(Pango.EllipsizeMode.END)  # Ellipsize text if too long
        self.status_label.set_max_width_chars(100)  # Limit width (adjust as needed)
        self.status_label.get_style_context().add_class("label")    
        status_box.pack_end(self.status_label, False, False, 0)
        controls_box.pack_start(status_box, True, True, 0)
    
        # Create the Save button
        self.save_button = Gtk.Button()
        self.save_button.get_style_context().add_class("media-button")  # Optional: Add a custom CSS class for styling
        output_dir = os.path.join(os.getcwd(), "Output")
        self.save_button.set_tooltip_text(f"Export mp3 to {output_dir}")
        self.save_button.connect("clicked", self.on_save)
        self.save_button.get_style_context().add_class("round-button")
        
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

    def on_button_press(self, widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:  # Left mouse button
            buffer = self.metadata_view.get_buffer()
            x, y = self.metadata_view.window_to_buffer_coords(Gtk.TextWindowType.TEXT, int(event.x), int(event.y))
            found_iter, text_iter = self.metadata_view.get_iter_at_location(x, y)
    
            if found_iter:
                tag_table = buffer.get_tag_table()
                link_tag = tag_table.lookup("link")
                if link_tag and link_tag in text_iter.get_tags():
                    # Extract the link from the iter range
                    start = text_iter.copy()
                    end = text_iter.copy()
                    start.backward_to_tag_toggle(link_tag)
                    end.forward_to_tag_toggle(link_tag)
    
                    # Get the text within the tag
                    link_text = buffer.get_text(start, end, include_hidden_chars=False).strip()
    
                    # Handle mailto links
                    if re.match(r'^[\w\.-]+@[\w\.-]+$', link_text):  # Plain email address
                        selected_file = self.get_selected_file()
                        if selected_file:
                            filename = os.path.basename(selected_file)
                            foldername = os.path.basename(os.path.dirname(selected_file))
                            subject = f"Subject={filename} in {foldername}"
                            mailto_link = f"mailto:{link_text}?{subject}"
                        else:
                            mailto_link = f"mailto:{link_text}"
                        
                        webbrowser.open(mailto_link)
                    elif re.match(r'^mailto:', link_text):  # Email with mailto:
                        selected_file = self.get_selected_file()
                        if selected_file:
                            filename = os.path.basename(selected_file)
                            foldername = os.path.basename(os.path.dirname(selected_file))
                            subject = f"Subject={filename} in {foldername}"
                            mailto_link = f"{link_text}&{subject}"
                        else:
                            mailto_link = link_text
                        
                        webbrowser.open(mailto_link)
                    elif re.match(r'^https?://', link_text):  # URL
                        webbrowser.open(link_text)
                    else:
                        print(f"Unhandled link type: {link_text}")

    def create_context_menu(self):
        """Creates a context menu for the file list."""
        self.context_menu = Gtk.Menu()
        
        # Add a non-interactive menu item at the top to display the file path
        self.path_display_item = Gtk.MenuItem()
        label = Gtk.Label()
        label.set_line_wrap(True)  # Enable word wrapping
        label.set_max_width_chars(20)  # Limit to 25 characters per line
        label.set_ellipsize(Pango.EllipsizeMode.NONE)  # Do not truncate with ellipses
        label.set_name("path_label")  # Add a name for targeted CSS styling
        label.set_line_wrap(True)  # Enable word wrapping
        label.set_max_width_chars(25)  # Limit to 25 characters per line
        label.set_line_wrap(True)  # Enable word wrapping
        label.set_max_width_chars(25)  # Limit to 25 characters per line

        # Set up CSS styling
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data("""
        #path_label {
            color: #6885b4;
        }
        """.encode('utf-8'))
        
        # Apply the CSS to the current screen
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        self.path_display_item.add(label)
        self.path_display_item.set_sensitive(False)  # Make it non-interactive
        self.context_menu.append(self.path_display_item)
        
        # Add "Open file location" option
        open_location_item = Gtk.MenuItem(label="Open File Location...")
        open_location_item.connect("activate", self.on_open_file_location)
        self.context_menu.append(open_location_item)
        
        # Add "Details..." option
        details_item = Gtk.MenuItem(label="Game Details...")
        details_item.connect("activate", self.on_details)
        self.context_menu.append(details_item)

        # Add "Toggle Favourite" Option
        self.toggle_favourite_item = Gtk.MenuItem(label="Add to Favourites")
        self.toggle_favourite_item.connect("activate", self.on_toggle_favourite)
        self.context_menu.append(self.toggle_favourite_item)
        self.context_menu.show_all()

        # Add "Export to .CSV" option
        self.csv_item = Gtk.MenuItem(label="Export to .CSV...")
        self.csv_item.connect("activate", self.on_csv)
        self.context_menu.append(self.csv_item)
        self.csv_item.set_visible(False)  # Initially hide it

        # Add "View Metadata" Option
        self.view_meta_item = Gtk.MenuItem(label="View Metadata...")
        self.view_meta_item.connect("activate", self.on_view_meta)
        self.context_menu.append(self.view_meta_item)
        self.view_meta_item.set_visible(False)  # Initially hide it

        # Add "Add/Replace Artwork" Option
        self.add_replace_artwork_item = Gtk.MenuItem(label="Add/Replace Artwork...")
        self.add_replace_artwork_item.connect("activate", self.on_add_replace_artwork)
        self.context_menu.append(self.add_replace_artwork_item)
        self.add_replace_artwork_item.set_visible(False)  # Initially hide it
        
        self.context_menu.show_all()

    def on_toggle_favourite(self, menuitem):
        file_path = self.get_selected_file()
        if file_path:
            iter = self.find_row_iter_by_file(file_path)
            if iter:
                display_name = self.all_store[iter][0]
                if file_path in self.favourites:
                    self.favourites.remove(file_path)
                    self.all_store[iter][0] = display_name.lstrip("*")
                    self.status_label.set_text(f"{display_name} removed from favourites.")
                else:
                    self.favourites.add(file_path)
                    self.all_store[iter][0] = f"*{display_name}"
                    self.status_label.set_text(f"{display_name} added to favourites.")
                self.save_favourites()  # Save changes to the file
            self.all_filter.refilter()
            self.update_file_column_title()

    def toggle_image_viewer(self):
        # Toggle the image_viewer flag
        self.image_viewer = not self.image_viewer
    
        # Update the visibility of the image viewer
        self.update_image_viewer_visibility()
    
        # Update the status label
        self.status_label.set_text(f"Image Viewer {'Enabled' if self.image_viewer else 'Disabled'}")
    
        # Update the menu item state if you have one
        if hasattr(self, 'image_viewer_menuitem'):
            self.image_viewer_menuitem.handler_block_by_func(self.on_image_viewer_toggled)
            self.image_viewer_menuitem.set_active(self.image_viewer)
            self.image_viewer_menuitem.handler_unblock_by_func(self.on_image_viewer_toggled)
    
        # Handle online services dependency
        if not self.image_viewer and self.online_services:
            self.online_services = False
            # Update the online services menu item
            if hasattr(self, 'online_services_menuitem'):
                self.online_services_menuitem.handler_block_by_func(self.on_online_services_toggled)
                self.online_services_menuitem.set_active(False)
                self.online_services_menuitem.handler_unblock_by_func(self.on_online_services_toggled)
            self.status_label.set_text("Online Services Disabled because Image Viewer was turned off")
    
        # If the image viewer is enabled, update the image pane
        if self.image_viewer:
            self.update_image_pane()

    def find_row_iter_by_file(self, file_path):
        # Iterate through the ListStore to find the row with the matching file path
        iter = self.all_store.get_iter_first()
        while iter:
            if self.all_store[iter][2] == file_path:  # Compare file paths (3rd column)
                return iter
            iter = self.all_store.iter_next(iter)
        return None
    
    def update_context_menu_tooltip(self, file_path):
        """Updates the tooltip at the top of the context menu."""
        if self.path_display_item:
            # Get the label from the path display item
            label = self.path_display_item.get_child()
            if file_path:
                label.set_text(file_path)
            else:
                label.set_text("No file selected")
            print(f"Updated context menu tooltip: {file_path}")  # Debugging
            
    def on_add_replace_artwork(self, menuitem):
        file_path = self.get_selected_file()
        if file_path:
            folder_path = os.path.dirname(file_path)
            image_path = os.path.join(folder_path, "image.jpg")
            
            # Open file chooser dialog to select an image
            dialog = Gtk.FileChooserDialog(
                title="Select an Image for Artwork",
                parent=self,
                action=Gtk.FileChooserAction.OPEN,
            )
            dialog.add_buttons(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
            )
            dialog.set_filter(self._get_image_filter())
            
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                selected_image_path = dialog.get_filename()
                try:
                    self._scale_and_save_image(selected_image_path, image_path)
                    self.status_label.set_text(f"Artwork {'replaced' if os.path.isfile(image_path) else 'added'} successfully!")
                    self.update_image_pane()  # Refresh the image pane
                except Exception as e:
                    print(f"Error adding/replacing artwork: {e}")
                    self.status_label.set_text("Error: Unable to add/replace artwork.")
            dialog.destroy()
        else:
            self.status_label.set_text("No file selected.")

    def _get_image_filter(self):
        image_filter = Gtk.FileFilter()
        image_filter.set_name("Image Files")
        image_filter.add_mime_type("image/jpeg")
        image_filter.add_mime_type("image/png")
        image_filter.add_pattern("*.jpg")
        image_filter.add_pattern("*.jpeg")
        image_filter.add_pattern("*.png")
        return image_filter

    def _scale_and_save_image(self, input_path, output_path, target_size=(300, 220)):
        with Image.open(input_path) as img:
            # Preserve aspect ratio while scaling
            img.thumbnail(target_size, Image.ANTIALIAS)
            img.save(output_path, format="JPEG", quality=90)

    def on_csv(self, menuitem=None):
        file_path = self.get_selected_file()
        if file_path:
            extension = os.path.splitext(file_path)[1].lower()
            if extension in ['.mid', '.midi']:
                # Generate the .csv file path
                base_dir = os.path.dirname(file_path)
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                csv_file_path = os.path.join(base_dir, f"{base_name}.csv")
                
                try:
                    # Run midicsv to convert the MIDI file to CSV
                    subprocess.run(["midicsv", file_path, csv_file_path], check=True)
                    print(f"Converted {file_path} to {csv_file_path}")
                    self.status_label.set_text(f"Exported {csv_file_path}")
                    
                    # Open the folder containing the exported .csv
                    if sys.platform == "win32":
                        subprocess.run(["explorer", base_dir], check=True)
                    elif sys.platform == "darwin":
                        subprocess.run(["open", base_dir], check=True)
                    else:
                        subprocess.run(["xdg-open", base_dir], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error converting to CSV: {e}")
                    self.status_label.set_text("Error: Unable to convert MIDI to CSV")
            else:
                self.status_label.set_text("Selected file is not a MIDI file.")
        else:
            self.status_label.set_text("No file selected.")
        
    def on_view_meta(self, menuitem=None):
        file_path = self.get_selected_file()
        if file_path:
            extension = os.path.splitext(file_path)[1].lower()
            if extension in ['.mod', '.xm', '.it', '.s3m']:  # Check for compatible file types
                # Generate the .txt file path
                base_dir = os.path.dirname(file_path)
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                txt_file_path = os.path.join(base_dir, f"{base_name}_metadata.txt")
    
                try:
                    # Extract metadata using openmpt123
                    openmpt_result = subprocess.run(
                        ['openmpt123', '--info', file_path],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    metadata = openmpt_result.stdout
    
                    # Save metadata to the .txt file
                    with open(txt_file_path, 'w', encoding='utf-8') as f:
                        f.write(metadata)
    
                    print(f"Metadata exported to {txt_file_path}")
                    self.status_label.set_text(f"Metadata exported to {txt_file_path}")
    
                    # Open the folder containing the .txt file
                    if sys.platform == "win32":
                        subprocess.run(["explorer", base_dir], check=True)
                    elif sys.platform == "darwin":
                        subprocess.run(["open", base_dir], check=True)
                    else:
                        subprocess.run(["xdg-open", base_dir], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error extracting metadata: {e}")
                    self.status_label.set_text("Error: Unable to extract metadata.")
            else:
                self.status_label.set_text("Selected file is not compatible for metadata extraction.")
        else:
            self.status_label.set_text("No file selected.")

    def on_treeview_button_press(self, treeview, event):
        """Detects right-click on the file list and shows the context menu."""
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:  # Right-click
            path_info = treeview.get_path_at_pos(int(event.x), int(event.y))
            if path_info:
                path, column, cell_x, cell_y = path_info
                treeview.set_cursor(path, column, False)  # Select the right-clicked file
                
                # Get the selected file's path
                file_path = self.get_selected_file()
                if file_path:
                    # Check the file extension for CSV export compatibility
                    extension = os.path.splitext(file_path)[1].lower()
                    self.csv_item.set_visible(extension in ['.mid', '.midi'])  # Show for MIDI files
                    self.view_meta_item.set_visible(extension in ['.mod', '.xm', '.it', '.s3m'])  # Show for MOD files
    
                    # Check if image.jpg exists for Add/Replace Artwork
                    folder_path = os.path.dirname(file_path)
                    image_path = os.path.join(folder_path, "image.jpg")
                    if os.path.isfile(image_path):
                        self.add_replace_artwork_item.set_label("Replace Artwork...")
                    else:
                        self.add_replace_artwork_item.set_label("Add Artwork...")
                    self.add_replace_artwork_item.set_visible(True)
                else:
                    # Hide items if no file is selected
                    self.csv_item.set_visible(False)
                    self.view_meta_item.set_visible(False)
                    self.add_replace_artwork_item.set_visible(False)
                
                # Update the tooltip with the full file path
                self.update_context_menu_tooltip(file_path)

                # Update "Toggle Favourite" menu item label
                file_path = self.get_selected_file()
                if file_path:
                    if file_path in self.favourites:
                        self.toggle_favourite_item.set_label("Remove from Favourites")
                    else:
                        self.toggle_favourite_item.set_label("Add to Favourites")
                
                # Show the context menu
                try:
                    self.context_menu.popup_at_pointer(event)
                except Exception as e:
                    print(f"Popup at pointer failed: {e}")
                    # Fallback to popup_at_rect if pointer method fails
                    parent_window = treeview.get_toplevel()
                    if isinstance(parent_window, Gtk.Window) and parent_window.is_realized():
                        widget_window = treeview.get_window()
                        if widget_window:
                            rect = Gdk.Rectangle(
                                x=int(event.x_root), y=int(event.y_root), width=1, height=1
                            )
                            self.context_menu.popup_at_rect(
                                widget_window, rect, Gdk.Gravity.NORTH_WEST, event
                            )
                return True
        return False

    def save_favourites(self):
        try:
            with open(self.favourites_file, "w", encoding="utf-8") as f:
                for file_path in self.favourites:
                    f.write(f"{file_path}\n")
            print("Favourites saved successfully.")
        except Exception as e:
            print(f"Error saving favourites: {e}")

    def load_favourites(self):
        try:
            if not os.path.isfile(self.favourites_file):
                with open(self.favourites_file, "w", encoding="utf-8") as f:
                    pass  # Create the file if it doesn't exist
            
            with open(self.favourites_file, "r", encoding="utf-8", errors="surrogateescape") as f:
                self.favourites = set(
                    os.path.normcase(os.path.abspath(line.strip().encode('utf-8', 'surrogateescape').decode('utf-8', 'replace')))
                    for line in f if line.strip()
                )
            print(f"Loaded favourites: {self.favourites}")
        except Exception as e:
            print(f"Error loading favourites: {e}")
        
    def on_open_file_location(self, menuitem):
        """Opens the containing folder of the selected file."""
        file_path = self.get_selected_file()
        if file_path:
            folder_path = os.path.dirname(file_path)
            try:
                if sys.platform == "win32":
                    subprocess.run(["explorer", folder_path], check=True)
                elif sys.platform == "darwin":
                    subprocess.run(["open", folder_path], check=True)
                else:
                    subprocess.run(["xdg-open", folder_path], check=True)
            except Exception as e:
                print(f"Error opening file location: {e}")
    
    def on_details(self, menuitem):
        """Performs a Google search using the file and folder name."""
        file_path = self.get_selected_file()
        if file_path:
            filename = os.path.splitext(os.path.basename(file_path))[0]  # Remove extension
            foldername = os.path.basename(os.path.dirname(file_path))
            search_term = '+'.join((foldername).split())
            search_url = f"https://thegamesdb.net/search.php?name={search_term}"
            try:
                webbrowser.open(search_url)
            except Exception as e:
                print(f"Error opening browser: {e}")
                
    def on_fav(self, button):
        # Check if the filter is already set to favourites
        if self.search_entry.get_text() == "*":
            # Clear the filter if already showing favourites
            self.search_entry.set_text("")
            self.status_label.set_text("Filter: None")
        else:
            # Set the filter to show favourites
            self.search_entry.set_text("*")
            self.status_label.set_text("Filter: Favourites")
        
        # Reapply the filter and update the UI
        self.all_filter.refilter()
        self.update_file_column_title()

    def on_radio(self, button):
        if not self.radio:
            # If radio is not active, start streaming the current URL
            self.stop_xmp()
            self.stop_fluidsynth()
            current_stream = self.streams[self.current_stream_index]
            self.start_stream(current_stream['url'], current_stream['title'])
        else:
            # If radio is active, switch to the next stream
            self.stop_stream()
            self.current_stream_index = (self.current_stream_index + 1) % len(self.streams)
            next_stream = self.streams[self.current_stream_index]
            self.start_stream(next_stream['url'], next_stream['title'])
    
    def start_stream(self, url, title):
        self.stop_stream()  # Ensure any existing stream is stopped
        stream_url = url
        self.spinner.start()
    
        if self.mplayer_process is None:
            try:
                # Set the radio flag and stream title before starting the process
                self.radio = True
                self.save_button.set_visible(False)
                self.stream_title = title if title else self.stream_title
                self.status_label.set_tooltip_text(f"{self.stream_title}")
    
                # Update metadata immediately
                self.update_metadata()  # Call directly instead of using GLib.idle_add
    
                # Start mplayer as a subprocess
                self.mplayer_process = subprocess.Popen(
                    ['mplayer', stream_url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.status_label.set_text(f"Connecting to {stream_url}...")
                print(f"Streaming {stream_url}...")
    
                # Start the thread to fetch current track
                self.track_thread = threading.Thread(
                    target=self.fetch_current_track,
                    args=(stream_url,),
                    daemon=True
                )
                self.track_thread.start()
    
            except FileNotFoundError:
                print("mplayer not found. Please install mplayer and try again.")
                self.radio = False
                self.save_button.set_visible(True)
                self.status_label.set_text("mplayer not found.")
            except Exception as e:
                print(f"Failed to start mplayer: {e}")
                self.radio = False
                self.save_button.set_visible(True)
                self.status_label.set_text("Failed to start streaming.")
        else:
            print("mplayer is already running.")
            self.status_label.set_text("Streaming already in progress.")

    def fetch_current_track(self, url):
        headers = {
            'Icy-MetaData': '1',  # Request ICY metadata
            'User-Agent': 'Python'  # Set a user agent
        }
        try:
            # Initiate a stream with metadata
            response = requests.get(url, headers=headers, stream=True, timeout=10)
            if response.status_code == 200:
                metaint = response.headers.get('icy-metaint')
                if metaint:
                    metaint = int(metaint)
                    while self.radio:
                        # Read the stream up to the metadata interval
                        stream_data = response.raw.read(metaint)
                        if not stream_data:
                            break  # Stream ended
    
                        # Read the metadata length byte
                        meta_length_byte = response.raw.read(1)
                        if not meta_length_byte:
                            break  # Stream ended
                        meta_length = meta_length_byte[0] * 16  # Metadata length
    
                        if meta_length > 0:
                            # Read the metadata
                            metadata = response.raw.read(meta_length).rstrip(b'\0')
                            metadata_str = metadata.decode('utf-8', errors='ignore')
    
                            # Extract the StreamTitle
                            for part in metadata_str.split(';'):
                                if part.startswith("StreamTitle='"):
                                    title = part.split("=", 1)[1].strip("'")
                                    # Update the status_label in the main thread only if radio is active
                                    if self.radio:
                                        # If you want to prefer manual titles, you can decide whether to overwrite
                                        # For this example, we'll overwrite with stream-provided titles if available
                                        self.stream_title = title if title else self.stream_title
                                        GLib.idle_add(self.status_label.set_text, f"Now Streaming: {self.stream_title}")
                                        print(f"Now Playing: {self.stream_title}") 
                                        GLib.idle_add(self.update_metadata)
                        time.sleep(1)  # Wait before the next update
                else:
                    # No metadata interval provided
                    if self.radio:
                        GLib.idle_add(self.status_label.set_text, "Streaming without metadata.")
                        print("Streaming without metadata.")
        except Exception as e:
            print(f"Error fetching track info: {e}")
            if self.radio:
                # Update the UI safely only if radio is active
                GLib.idle_add(self.status_label.set_text, "Streaming Radio...")

    def stop_stream(self):
        self.spinner.stop()
        self.radio = False
        self.save_button.set_visible(True)
        if self.mplayer_process:
            try:
                # Terminate the mplayer process
                self.mplayer_process.terminate()
                # self.mplayer_process.wait(timeout=1)

            except subprocess.TimeoutExpired:
                print("mplayer did not terminate in time; killing it.")
                self.mplayer_process.kill()
                GLib.idle_add(self.status_label.set_text, "Radio stopped forcefully.")
            except Exception as e:
                print(f"Error stopping mplayer: {e}")
                GLib.idle_add(self.status_label.set_text, "Error stopping radio.")
            finally:
                self.mplayer_process = None
        
        # Wait for the track_thread to finish
        if hasattr(self, 'track_thread') and self.track_thread.is_alive():
            self.track_thread.join(timeout=1)


    def stop_spinner(self):
        """Method to stop the spinner."""
        self.spinner.stop()
        
    def on_dark_mode_toggled(self, menuitem):
        settings = Gtk.Settings.get_default()
        dark_mode_enabled = menuitem.get_active()
        settings.set_property("gtk-application-prefer-dark-theme", dark_mode_enabled)
        
        if dark_mode_enabled:
            GLib.idle_add(self.status_label.set_text, "Dark Mode Enabled")
        else:
            GLib.idle_add(self.status_label.set_text, "Dark Mode Disabled")
    
    def apply_monospace_font(self, widget):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            * {
                font-size: 14px;
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
                    if file.lower().endswith(('.mid', '.midi', '.mod', '.xm', '.it', '.s3m')):
                        full_path = os.path.normcase(os.path.abspath(os.path.join(root, file)))
                        all_files.append(full_path)
        except Exception as e:
            print(f"Error finding all files: {e}")
        return all_files

    def find_sf2_files(self):
        sf2_files = []
        for root, dirs, files in os.walk(self.sf2_dir):
            for file in files:
                if file.lower().endswith('.sf2'):
                    sf2_files.append(os.path.join(root, file))
        return sf2_files

    def load_all_files(self):
        self.all_store.clear()
        for all_file in self.all_files:
            try:
                # Safely encode and decode the file path for output
                safe_file = all_file.encode('utf-8', 'surrogateescape').decode('utf-8', 'replace')
                
                # Check if the file is in favourites
                if os.path.normcase(os.path.abspath(all_file)) in self.favourites:
                    print(f"Matched favourite: {safe_file}")
                
                self.append_file_to_store(all_file)
            except Exception as e:
                print(f"Error processing file: {all_file} - {e}")
        self.all_filter.refilter()
        self.update_file_column_title()

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
    
    def append_file_to_store(self, all_file):
        try:
            # Safely decode the file path for comparison and display
            safe_file = all_file.encode('utf-8', 'surrogateescape').decode('utf-8', 'replace')
            basename = os.path.basename(safe_file)
            foldername = os.path.basename(os.path.dirname(safe_file))
            
            # Check if the file is a favorite
            if os.path.normcase(os.path.abspath(all_file)) in self.favourites:
                print(f"Matched favourite: {safe_file}")
                display_name = f"*{basename}"
            else:
                display_name = basename
            
            self.all_store.append([display_name, foldername, all_file])
        except Exception as e:
            print(f"Error appending file: {all_file} - {e}")

    def update_favourites_in_listview(self):
        # Refresh the TreeView display
        self.all_store.clear()
        for file_path in self.all_files:
            self.append_file_to_store(file_path)
        self.all_filter.refilter()
        self.update_file_column_title()

    def load_sf2_files(self):
        self.sf2_store.clear()
        for sf2_file in self.sf2_files:
            basename = os.path.basename(sf2_file)
            self.sf2_store.append([basename])

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
        """
        Adjusts the system or application volume based on the value from the volume button.
        """
        # Convert the volume to a percentage for PipeWire or other audio backends
        volume_percentage = int(value * 100)
        try:
            # Adjust the volume of the default output device
            subprocess.run(
                ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{volume_percentage}%"],
                check=True
            )
            self.status_label.set_text(f"Volume set to {volume_percentage}%")
        except Exception as e:
            print(f"Error adjusting volume: {e}")
            self.status_label.set_text("Error adjusting volume")

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
        if self.image_viewer:  # Update image pane only if enabled
                            self.update_image_pane()  # Update image pane
        self.update_file_column_title()
        self.on_play(None)

    def update_file_column_title(self):
        # Calculate the current index and total files
        total_matching_files = self.get_filtered_file_count()
    
        selection = self.all_treeview.get_selection()
        model, treeiter = selection.get_selected()
    
        if treeiter:
            path = model.get_path(treeiter)
            current_index = path.get_indices()[0] + 1  # Convert to one-based index
        else:
            current_index = 0
    
        column_title = f"Files ({current_index} of {total_matching_files})"
        column = self.all_treeview.get_column(0)
    
        # Only update the title if it has changed to prevent unnecessary redraws
        if column.get_title() != column_title:
            def update_title():
                column.set_title(column_title)
            GLib.idle_add(update_title)  # Defer title update until other UI actions complete

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
        if self.radio:
            metadata = self.extract_metadata(None)
        else:
            file_path = self.get_selected_file()
            if file_path:
                metadata = self.extract_metadata(file_path)
            else:
                # Clear the metadata pane if no file is selected and radio is not playing
                buffer = self.metadata_view.get_buffer()
                buffer.set_text("")
                return
    
        buffer = self.metadata_view.get_buffer()
        # Clear the buffer
        buffer.set_text("")
    
        # Ensure the 'link' tag exists and is connected to the event signal
        tag_table = buffer.get_tag_table()
        link_tag = tag_table.lookup("link")
        if not link_tag:
            link_tag = buffer.create_tag(
                "link",
                foreground="#5275ba",
                underline=Pango.Underline.SINGLE
            )
            link_tag.connect("event", self.on_link_clicked)
    
        # Regex to detect URLs and email addresses
        url_regex = re.compile(r'(https?://[^\s]+)')
        email_regex = re.compile(r'[\w.-]+@[\w.-]+\.\w+')
    
        # Insert metadata into the buffer, formatting URLs and emails as links
        start_iter = buffer.get_start_iter()
        for line in metadata.splitlines():
            url_matches = list(url_regex.finditer(line))
            email_matches = list(email_regex.finditer(line))
    
            if not url_matches and not email_matches:
                # Insert line without links
                buffer.insert(start_iter, line + "\n")
                continue
    
            # Insert line with links
            pos = 0
            for match in sorted(url_matches + email_matches, key=lambda m: m.start()):
                start, end = match.start(), match.end()
                # Insert text before the match
                if pos < start:
                    buffer.insert(start_iter, line[pos:start])
                # Insert the match as a link
                link_text = line[start:end]
                buffer.insert_with_tags_by_name(start_iter, link_text, "link")
                pos = end
            # Insert the rest of the line
            if pos < len(line):
                buffer.insert(start_iter, line[pos:])
            buffer.insert(start_iter, "\n")
    
    def on_link_clicked(self, tag, widget, event, iter):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:  # Left-click
            buffer = widget.get_buffer()
            start = iter.copy()
            if not start.starts_tag(tag):
                start.backward_to_tag_toggle(tag)
            end = start.copy()
            if not end.ends_tag(tag):
                end.forward_to_tag_toggle(tag)
            link = buffer.get_text(start, end, True)
            if link.startswith("http"):
                # Open the URL in the default web browser
                subprocess.run(["xdg-open", link])
            elif "@" in link:
                # Open the mail client for email links
                subprocess.run(["xdg-email", link])
            return True  # Event handled
        return False

    def extract_metadata(self, file_path):
        if not self.radio:
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
    
                if extension in ['.mid', '.midi'] and self.meta_extract:
                    # Extract MIDI-specific metadata using midicsv
                    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_csv:
                        temp_csv_name = temp_csv.name
                    subprocess.run(["midicsv", file_path, temp_csv_name], check=True)
    
                    with open(temp_csv_name, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
    
                    os.remove(temp_csv_name)
    
                    # Extract lines that contain metadata tags
                    lines = content.splitlines()
                    for line in lines:
                        if any(tag in line for tag in [
                            "Title_t", "Text_t", "Copyright_t", "Composer", "Album",
                            "Title", "Track_name", "Lyrics", "Metaeventtext", "Marker"
                        ]):
                            # Keep only the meaningful part of the line (after the first three columns)
                            columns = line.split(',', 3)
                            if len(columns) > 3:
                                metadata_lines.append(columns[3].strip())
    
                elif extension in [
                    '.mod', '.xm', '.it', '.s3m', '.stm', '.imf', '.ptm', '.mdl', '.ult',
                    '.liq', '.masi', '.j2b', '.amf', '.med', '.rts', '.digi', '.sym',
                    '.dbm', '.qc', '.okt', '.sfx', '.far', '.umx', '.hmn', '.slt',
                    '.coco', '.ims', '.669', '.abk', '.uni', '.gmc'
                ] and self.meta_extract:
                    # Extract MOD file metadata using openmpt123
                    openmpt_result = subprocess.run(
                        ['openmpt123', '--info', file_path],
                        capture_output=True,
                        text=True,
                        errors='replace'  # Ensure subprocess output handles encoding errors
                    )
    
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
                    metadata_lines.append("Unknown file type or file metadata extraction disabled.")
    
                # Extract the containing directory from the file path
                containing_directory = os.path.dirname(path)
                info_txt_path = os.path.join(containing_directory, "info.txt")
                info_txt = ""
    
                # Check if info.txt exists in the containing directory
                if os.path.isfile(info_txt_path):
                    with open(info_txt_path, "r", encoding="utf-8", errors="replace") as f:
                        info_txt = f.read()  # Read the contents of info.txt
    
                # Combine file details with extracted metadata
                if not metadata_lines:  # If no metadata found, add a placeholder
                    metadata = (
                        f"Filename: {filename}\n"
                        f"Path: {path}\n"
                    f"File Size: {filesize_str}\n\n"
                    + "*** Metadata Info ***\n"
                    + "Unavailable\n"
                    + (f"\nInfo.txt: {info_txt}\n" if info_txt else "")
                    )
                else:
                    metadata = (
                        f"Filename: {filename}\n"
                        f"Path: {path}\n"
                    f"File Size: {filesize_str}\n\n"
                    + "*** Metadata Info ***\n"
                    + "\n".join(metadata_lines) + "\n"
                    + (f"\nInfo.txt: {info_txt}\n" if info_txt else "")
                    )
    
                return metadata
    
            except Exception as e:
                return f"Error extracting metadata: {e}"
        else:
            # Radio metadata
            metadata = (
                f"Track Name: {self.stream_title}\n"
                f"Title: {self.streams[self.current_stream_index]['title']}\n"
                f"URL: {self.streams[self.current_stream_index]['url']}\n"
                f"Genre: Game\n"
            )
    
            return metadata
    
    def on_play(self, button):
        self.spinner.start()
        self.stop_fluidsynth()
        self.stop_xmp()
        self.stop_stream()
        file_path = self.get_selected_file()
        if file_path:
            self.total_length = None  # Initialize total length
            self.play_start_time = time.time()  # Record start time
    
            extension = os.path.splitext(file_path)[1].lower()
            if extension in ['.mid', '.midi']:
                # Use fluidsynth to play MIDI files
                sf2_file = self.get_selected_sf2()
                if sf2_file:
                    try:
                        self.fluidsynth_stopped_intentionally = False
                        # Calculate total length of MIDI file
                        self.total_length = self.get_midi_length(file_path)
                        self.fluidsynth_process = subprocess.Popen(
                            ["fluidsynth", "-g", "1.3", "-a", "pulseaudio", "-m", "alsa_seq", "-i", sf2_file, file_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL,
                            text=True,
                        )
                        threading.Thread(target=self.monitor_fluidsynth_output, daemon=True).start()
                        self.status_label.set_text(f"Playing: {os.path.basename(file_path)} + {os.path.basename(sf2_file)}")
                        self.status_label.set_tooltip_text(f"{file_path} + {os.path.basename(sf2_file)}")
                        if self.image_viewer:  # Update image pane only if enabled
                            self.update_image_pane()
                        # Start the timer to update playback progress
                        if self.total_length:
                            self.elapsed_timer = GLib.timeout_add(1000, self.update_playback_progress)
                            self.update_playback_progress()  # Update immediately
                    except Exception as e:
                        print(f"Failed to start fluidsynth: {e}")
                        self.fluidsynth_process = None
                else:
                    self.status_label.set_text("No SoundFont selected")
            else:
                # Use xmp to play other files
                try:
                    # Calculate total length of module file
                    self.total_length = self.get_module_length(file_path)
                    self.xmp_stopped_intentionally = False  # Reset the flag
                    self.xmp_process = subprocess.Popen(
                        ["xmp", file_path],
                        stdout=subprocess.DEVNULL,  # Discard output to prevent blocking
                        stderr=subprocess.DEVNULL,
                        text=True,
                    )
                    threading.Thread(target=self.monitor_xmp_output, daemon=True).start()
                    # Update status label
                    self.status_label.set_text(f"Playing: {os.path.basename(file_path)}")
                    if self.image_viewer:  # Update image pane only if enabled
                        self.update_image_pane()
                    # Start the timer to update playback progress
                    if self.total_length:
                        self.elapsed_timer = GLib.timeout_add(1000, self.update_playback_progress)
                        self.update_playback_progress()  # Update immediately
                except Exception as e:
                    print(f"Failed to start xmp: {e}")
                    self.xmp_process = None
                    self.status_label.set_text("Error: Unable to play")
            self.metadata_view.set_editable(False)  # Make it read-only
            self.metadata_view.set_cursor_visible(True)  # Allow cursor interaction
            self.update_metadata()
        else:
            self.status_label.set_text("No file selected")

    def handle_fluidsynth_error(self):
        """Handles errors from the Fluidsynth process."""
        self.status_label.set_text("Error: fluidsynth failed to play the file.")
    
    def handle_xmp_error(self):
        """Handles errors from the xmp process."""
        self.status_label.set_text("Error: xmp failed to play the file.")

    def monitor_fluidsynth_output(self):
        process = self.fluidsynth_process
        if process:
            self.spinner.start()
            stderr_output = ''
            try:
                # Wait for the process to finish and capture stderr
                _, stderr_output = process.communicate()
    
                exit_code = process.returncode
                print(f"Fluidsynth exited with code {exit_code}")
                print(f"Fluidsynth stderr output:\n{stderr_output}")
    
                if exit_code != 0:
                    if self.fluidsynth_stopped_intentionally or exit_code == -15:
                        self.fluidsynth_stopped_intentionally = False  # Reset the flag
                    else:
                        # Check for actual error messages
                        if 'error' in stderr_output.lower():
                            GLib.idle_add(self.handle_fluidsynth_error)
                        else:
                            # No actual error, treat as normal termination
                            GLib.idle_add(self.stop_playback_timer)
                            GLib.idle_add(self.on_next_auto)
                else:
                    GLib.idle_add(self.stop_playback_timer)
                    GLib.idle_add(self.on_next_auto)
            except Exception as e:
                print(f"Exception in monitor_fluidsynth_output: {e}")
                GLib.idle_add(self.handle_fluidsynth_error)
        else:
            self.spinner.stop()
    
    def monitor_xmp_output(self):
        process = self.xmp_process
        if process:
            self.spinner.start()
            try:
                process.wait()
                if process.returncode != 0:
                    if self.xmp_stopped_intentionally:
                        self.xmp_stopped_intentionally = False
                    else:
                        GLib.idle_add(self.handle_xmp_error)
                else:
                    GLib.idle_add(self.stop_playback_timer)
                    GLib.idle_add(self.on_next_auto)
            except Exception as e:
                GLib.idle_add(self.handle_xmp_error)
        else:
            self.spinner.stop()

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
        self.stop_stream()
        self.status_label.set_text("Playback Stopped")
        self.status_label.set_tooltip_text("")

    def on_previous(self, button):
        # Stop any active streams or playback
        self.stop_stream()
        self.stop_fluidsynth()
        self.stop_xmp()
        
        def scroll_to_path(path):
            if path:
                column = self.all_treeview.get_column(0)
                self.all_treeview.set_cursor(path, column, False)  # Set the cursor
                self.all_treeview.scroll_to_cell(path, column, True, 0.5, 0.0)  # Scroll to the cell
                self.all_treeview.queue_draw()  # Force a redraw after scrolling
                scrolled_window = self.all_treeview.get_parent()
                if isinstance(scrolled_window, Gtk.ScrolledWindow):
                    scrolled_window.queue_draw()  # Ensure the scrolled window updates its state
    
        # Determine the previous path
        if self.shuffle_mode:
            # Shuffle mode: Pick a random visible row
            iter_list = []
            iter = self.all_filter.get_iter_first()
            while iter:
                iter_list.append(iter)
                iter = self.all_filter.iter_next(iter)
            
            if iter_list:
                random_iter = random.choice(iter_list)
                path = self.all_filter.get_path(random_iter)
            else:
                path = None
        else:
            # Sequential mode: Move to the previous visible row
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
                path = prev_path
            else:
                # No selection, select the last item
                total_rows = self.get_filtered_file_count()
                if total_rows > 0:
                    path = Gtk.TreePath(total_rows - 1)
                else:
                    path = None
    
        # Ensure the tree view updates to the selected path
        if path:
            scroll_to_path(path)
        else:
            self.all_treeview.get_selection().unselect_all()
    
        # Update metadata and play the file
        self.update_metadata()
        self.on_play(None)

    def get_tree_path_for_file(self, file_path):
        """Finds the tree path for the given file in the filtered list."""
        iter = self.all_filter.get_iter_first()
        while iter:
            if self.all_filter[iter][2] == file_path:  # Compare file paths
                return self.all_filter.get_path(iter)
            iter = self.all_filter.iter_next(iter)
        return None

    def get_tree_path_for_iter(self, iter):
        """Helper function to retrieve path for a given iter."""
        if iter:
            return self.all_filter.get_path(iter)
        return None

    def reset_horizontal_scroll(self):
        """Ensure the horizontal scroll bar resets to the left using the ScrolledWindow."""
        scrolled_window = self.all_treeview.get_parent()
        if isinstance(scrolled_window, Gtk.ScrolledWindow):
            h_adjustment = scrolled_window.get_hadjustment()
            if h_adjustment:
                h_adjustment.set_value(0)  # Set the horizontal adjustment value to 0

    def on_next(self, button):
        # Stop any active streams or playback
        self.stop_stream()
        self.stop_fluidsynth()
        self.stop_xmp()
    
        def scroll_to_path(path):
            if path:
                column = self.all_treeview.get_column(0)
                self.all_treeview.set_cursor(path, column, False)  # Set the cursor
                self.all_treeview.scroll_to_cell(path, column, True, 0.5, 0.0)  # Scroll to the cell
                self.all_treeview.queue_draw()  # Force a redraw after scrolling
                scrolled_window = self.all_treeview.get_parent()
                if isinstance(scrolled_window, Gtk.ScrolledWindow):
                    scrolled_window.queue_draw()  # Ensure the scrolled window updates its state
    
        # Determine the next path
        if self.shuffle_mode:
            # Shuffle mode: Pick a random visible row
            iter_list = []
            iter = self.all_filter.get_iter_first()
            while iter:
                iter_list.append(iter)
                iter = self.all_filter.iter_next(iter)
    
            if iter_list:
                random_iter = random.choice(iter_list)
                path = self.all_filter.get_path(random_iter)
            else:
                path = None
        else:
            # Sequential mode: Move to the next visible row
            selection = self.all_treeview.get_selection()
            model, treeiter = selection.get_selected()
    
            if treeiter:
                next_iter = self.all_filter.iter_next(treeiter)
                path = self.all_filter.get_path(next_iter) if next_iter else None
            else:
                # If no selection, start from the first row
                iter = self.all_filter.get_iter_first()
                path = self.all_filter.get_path(iter) if iter else None
    
        # Ensure the tree view updates to the selected path
        if path:
            scroll_to_path(path)
        else:
            self.all_treeview.get_selection().unselect_all()

        # Update metadata and play the file
        self.update_metadata()
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
                    self.on_pause(button)  # Pause playback
                    try:
                        subprocess.run(["ffmpeg", "-y", "-i", file_path, wav_output], check=True)
                        subprocess.run(["lame", wav_output, mp3_output], check=True)
                    finally:
                        self.on_play(button)  # Resume playback
                    # Convert non-MIDI file to WAV using ffmpeg
                    # subprocess.run(["ffmpeg", "-y", "-i", file_path, wav_output], check=True)
                    # Convert WAV to MP3 using lame
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
            self.fluidsynth_stopped_intentionally = True  # Set the flag
            self.fluidsynth_process.terminate()
            try:
                self.fluidsynth_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.fluidsynth_process.kill()
            self.fluidsynth_process = None
            self.status_label.set_text("Playback Stopped")
        if self.elapsed_timer:
            GLib.source_remove(self.elapsed_timer)
            self.elapsed_timer = None
        self.playback_label.set_text("00:00 / 00:00")  # Reset the playback label
    
    def stop_xmp(self):
        if self.xmp_process:
            self.xmp_stopped_intentionally = True
            self.xmp_process.terminate()
            try:
                self.xmp_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.xmp_process.kill()
            self.xmp_process = None
            self.status_label.set_text("Playback Stopped")
        if self.elapsed_timer:
            GLib.source_remove(self.elapsed_timer)
            self.elapsed_timer = None
        self.playback_label.set_text("00:00 / 00:00")  # Reset the playback label

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

    def on_select_output_source(self, menuitem):
        # Determine the output directory path relative to the root program directory
        output_dir = os.path.join(os.getcwd(), "Output")
    
        # Create the directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
        try:
            # Open the directory in the file manager
            if sys.platform == "win32":
                subprocess.run(["explorer", output_dir], check=True)
            elif sys.platform == "darwin":
                subprocess.run(["open", output_dir], check=True)
            else:
                subprocess.run(["xdg-open", output_dir], check=True)
            self.status_label.set_text(f"Opened output directory: {output_dir}")
        except Exception as e:
            print(f"Error opening output directory: {e}")
            self.status_label.set_text("Error: Unable to open output directory")
    
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


    def on_meta_extract_toggled(self, menuitem):
        self.meta_extract = not self.meta_extract
        GLib.idle_add(self.status_label.set_text, f"Metadata Extraction {'Enabled' if self.meta_extract else 'Disabled'}")

    def on_shuffle_mode_toggled(self, menuitem):
        self.shuffle_mode = not self.shuffle_mode
        GLib.idle_add(self.status_label.set_text, f"Shuffle Mode {'Enabled' if self.shuffle_mode else 'Disabled'}")

    def on_image_viewer_toggled(self, menuitem):
        self.image_viewer = menuitem.get_active()  # Update the toggle state
        self.update_image_viewer_visibility()
        self.status_label.set_text(f"Image Viewer {'Enabled' if self.image_viewer else 'Disabled'}")
        
        # Disable Online Services if Image Viewer is turned off
        if not self.image_viewer and self.online_services:
            self.online_services = False
            self.online_services_menuitem.handler_block_by_func(self.on_online_services_toggled)
            self.online_services_menuitem.set_active(False)  # Update the menu item state
            self.online_services_menuitem.handler_unblock_by_func(self.on_online_services_toggled)
            self.status_label.set_text("Online Services Disabled because Image Viewer was turned off")
    
        # Update the image pane only if Image Viewer is enabled
        if self.image_viewer:
            self.update_image_pane()
    
    def on_online_services_toggled(self, menuitem):
        self.online_services = menuitem.get_active()  # Update the toggle state
        self.status_label.set_text(f"Online Services {'Enabled' if self.online_services else 'Disabled'}")
        
        # If Online Services is enabled, ensure Image Viewer is also enabled
        if self.online_services and not self.image_viewer:
            self.image_viewer = True
            self.image_viewer_menuitem.handler_block_by_func(self.on_image_viewer_toggled)
            self.image_viewer_menuitem.set_active(True)  # Update the menu item state
            self.image_viewer_menuitem.handler_unblock_by_func(self.on_image_viewer_toggled)
            self.update_image_viewer_visibility()
            self.status_label.set_text("Image Viewer Enabled because Online Services were enabled")
        
        # Update the image pane only if Online Services is enabled
        if self.online_services:
            self.update_image_pane()

    def update_image_viewer_visibility(self):
        if self.image_viewer:
            self.image_box.show_all()
        else:
            self.image_box.hide()

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
        print("Quitting application...")
        self.stop_fluidsynth()
        self.stop_xmp()
        self.stop_stream()  # Ensure mplayer is terminated
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

    def on_next_auto(self):
        self.stop_fluidsynth()
        self.stop_xmp()
    
        def scroll_to_path(path):
            if path:
                column = self.all_treeview.get_column(0)
                self.all_treeview.set_cursor(path, column, False)  # Set the cursor
                self.all_treeview.scroll_to_cell(path, column, True, 0.5, 0.0)  # Scroll to the cell
                self.all_treeview.queue_draw()  # Force a redraw after scrolling
                scrolled_window = self.all_treeview.get_parent()
                if isinstance(scrolled_window, Gtk.ScrolledWindow):
                    scrolled_window.queue_draw()  # Ensure the scrolled window updates its state
    
        # Determine the next path
        if self.shuffle_mode:
            # Shuffle mode: Pick a random visible row
            iter_list = []
            iter = self.all_filter.get_iter_first()
            while iter:
                iter_list.append(iter)
                iter = self.all_filter.iter_next(iter)
    
            if iter_list:
                random_iter = random.choice(iter_list)
                path = self.all_filter.get_path(random_iter)
            else:
                path = None
        else:
            # Sequential mode: Move to the next visible row
            selection = self.all_treeview.get_selection()
            model, treeiter = selection.get_selected()
    
            if treeiter:
                next_iter = self.all_filter.iter_next(treeiter)
                path = self.all_filter.get_path(next_iter) if next_iter else None
            else:
                # If no selection, start from the first row
                iter = self.all_filter.get_iter_first()
                path = self.all_filter.get_path(iter) if iter else None
    
        # Ensure the tree view updates to the selected path
        if path:
            scroll_to_path(path)
        else:
            self.all_treeview.get_selection().unselect_all()
    
        # Update metadata and play the file
        self.update_metadata()
        self.on_play(None)

    def get_midi_length(self, file_path):
        try:
            mid = mido.MidiFile(file_path)
            if mid.type == 2:
                print("Type 2 MIDI files cannot have their length computed.")
                return None
            total_time = mid.length
            return total_time
        except TypeError as e:
            print(f"Unable to compute MIDI length due to TypeError: {e}")
            return None
        except Exception as e:
            print(f"Unable to compute MIDI length: {e}")
            return None
    
    def get_module_length(self, file_path):
        try:
            result = subprocess.run(
                ['openmpt123', '--info', file_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout
                for line in output.splitlines():
                    if line.startswith('Duration'):
                        duration_str = line.split(':', 1)[1].strip()
                        # Convert duration string to seconds
                        parts = duration_str.split(':')
                        parts = [float(p) for p in parts]
                        duration_seconds = sum(t * 60 ** (len(parts) - i - 1) for i, t in enumerate(parts))
                        return duration_seconds
            return None
        except Exception as e:
            print(f"Error getting module length: {e}")
            return None

    def stop_playback_timer(self):
        if self.elapsed_timer:
            GLib.source_remove(self.elapsed_timer)
            self.elapsed_timer = None
        self.playback_label.set_text("00:00 / 00:00")  # Reset the playback label

    def update_playback_progress(self):
        if self.play_start_time:
            elapsed_time = time.time() - self.play_start_time
            elapsed_str = self.format_time(elapsed_time)
            if self.total_length:
                total_str = self.format_time(self.total_length)
                self.playback_label.set_text(f"{elapsed_str} / {total_str}")
            else:
                self.playback_label.set_text(f"{elapsed_str} / --:--")
            return True
        else:
            return False
        
    def format_time(self, seconds):
        mins, secs = divmod(int(seconds), 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{hours}:{mins:02d}:{secs:02d}"
        else:
            return f"{mins}:{secs:02d}"

if __name__ == "__main__":
    app = MidiSoundfontTester()
    app.show_all()
    Gtk.main()
