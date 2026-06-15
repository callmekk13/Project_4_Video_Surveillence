import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import os
import shutil
import time
from datetime import datetime
import sqlite3 as sl

from simple_facerec import SimpleFacerec
from data_handling import init_db

# Helper to format timestamp securely
def format_time(val):
    if not val:
        return "Never"
    try:
        float_val = float(val)
        return datetime.fromtimestamp(float_val).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return str(val)

# Helper to scan for working cameras
def get_available_cameras():
    available = []
    # Test indices 0 to 4
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap is not None and cap.isOpened():
            available.append(i)
            cap.release()
    return available if available else [0]

class SurveillanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Surveillance & Tracking System")
        self.root.geometry("1050x700")
        self.root.configure(bg="#1e1e2e")
        self.root.minsize(900, 600)

        # Initialize SQLite DB
        self.con = init_db('data.db')
        
        # Ensure images directory exists
        if not os.path.exists('images'):
            os.makedirs('images')

        # Load Face Rec engine
        self.sfr = SimpleFacerec()
        self.sfr.load_encoding_images("images/")

        # Camera & Tracking variables
        self.cap = None
        self.is_tracking = False
        self.frame_counter = 0
        self.cached_faces = ([], [])  # (locations, ids)
        self.last_updates = {}        # {id: (timestamp, location)}
        self.available_cams = get_available_cameras()

        # Design & Theme styles
        self.setup_styles()
        
        # Build Navigation and Main Layout
        self.build_gui()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Colors (Catppuccin Mocha theme)
        self.bg_color = "#1e1e2e"
        self.card_color = "#252538"
        self.accent_color = "#89b4fa"
        self.green_color = "#a6e3a1"
        self.red_color = "#f38ba8"
        self.text_color = "#cdd6f4"
        self.muted_color = "#a6adc8"
        self.input_bg = "#313244"

        # Apply widget styles
        self.style.configure('.', background=self.bg_color, foreground=self.text_color)
        self.style.configure('TNotebook', background=self.bg_color, borderwidth=0)
        self.style.configure('TNotebook.Tab', 
                             background=self.card_color, 
                             foreground=self.muted_color, 
                             borderwidth=0, 
                             padding=[20, 8],
                             font=("Helvetica", 11, "bold"))
        self.style.map('TNotebook.Tab', 
                       background=[('selected', self.accent_color)], 
                       foreground=[('selected', '#11111b')])
        
        self.style.configure('Card.TFrame', background=self.card_color, relief='flat')
        
        # Treeview styling
        self.style.configure('Treeview', 
                             background=self.card_color, 
                             fieldbackground=self.card_color, 
                             foreground=self.text_color, 
                             rowheight=25,
                             font=("Helvetica", 10))
        self.style.configure('Treeview.Heading', 
                             background=self.input_bg, 
                             foreground=self.accent_color, 
                             borderwidth=0,
                             font=("Helvetica", 10, "bold"))
        self.style.map('Treeview', background=[('selected', self.accent_color)], foreground=[('selected', '#11111b')])

    def build_gui(self):
        # Header Area
        header = tk.Frame(self.root, bg=self.bg_color, pady=15)
        header.pack(fill=tk.X)
        
        title_label = tk.Label(header, 
                               text="VIDEO SURVEILLANCE & FACIAL TRACKING SYSTEM", 
                               font=("Helvetica", 18, "bold"), 
                               fg=self.accent_color, 
                               bg=self.bg_color)
        title_label.pack(side=tk.LEFT, padx=25)

        status_lbl = tk.Label(header, 
                              text="SYSTEM ACTIVE", 
                              font=("Helvetica", 9, "bold"), 
                              fg=self.green_color, 
                              bg=self.input_bg, 
                              padx=10, 
                              pady=3)
        status_lbl.pack(side=tk.RIGHT, padx=25)

        # Tab views
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # Create Tab Frames
        self.tab_cam = ttk.Frame(self.notebook)
        self.tab_register = ttk.Frame(self.notebook)
        self.tab_records = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_cam, text=" LIVE STREAM ")
        self.notebook.add(self.tab_register, text=" REGISTER MEMBER ")
        self.notebook.add(self.tab_records, text=" DATABASE RECORDS ")

        # Build individual Tabs
        self.build_camera_tab()
        self.build_register_tab()
        self.build_records_tab()

    # ------------------ LIVE STREAM TAB ------------------
    def build_camera_tab(self):
        # Layout: 2 columns (Camera Feed on Left, Live Detections Log on Right)
        self.tab_cam.columnconfigure(0, weight=3)
        self.tab_cam.columnconfigure(1, weight=2)
        self.tab_cam.rowconfigure(0, weight=1)

        # LEFT COLUMN: Camera Feed Card
        left_frame = ttk.Frame(self.tab_cam, style='Card.TFrame')
        left_frame.grid(row=0, column=0, padx=(0, 10), pady=10, sticky='nsew')
        
        # Camera Controls
        ctrl_frame = tk.Frame(left_frame, bg=self.card_color, pady=10)
        ctrl_frame.pack(fill=tk.X, padx=15)
        
        # Camera Select Dropdown
        tk.Label(ctrl_frame, text="Select Source:", fg=self.text_color, bg=self.card_color, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.cam_var = tk.IntVar(value=self.available_cams[0])
        cam_menu = ttk.Combobox(ctrl_frame, textvariable=self.cam_var, values=self.available_cams, width=5, state='readonly')
        cam_menu.pack(side=tk.LEFT, padx=5)

        # Location Input (CCTV Camera Zone)
        tk.Label(ctrl_frame, text="Zone/Location:", fg=self.text_color, bg=self.card_color, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, padx=(15, 5))
        self.selected_location = tk.StringVar(value="Main Gate")
        loc_entry = tk.Entry(ctrl_frame, textvariable=self.selected_location, bg=self.input_bg, fg=self.text_color, insertbackground=self.text_color, relief='flat', bd=0, width=15, font=("Helvetica", 10))
        # Add internal padding to entry
        loc_entry.pack(side=tk.LEFT, padx=5, ipady=3)

        # Start/Stop Button
        self.btn_cam_toggle = tk.Button(ctrl_frame, 
                                        text="Start Camera", 
                                        command=self.toggle_tracking, 
                                        bg=self.accent_color, 
                                        fg="#11111b", 
                                        activebackground="#a6e3a1", 
                                        relief='flat', 
                                        bd=0, 
                                        font=("Helvetica", 10, "bold"), 
                                        padx=15, 
                                        pady=3)
        self.btn_cam_toggle.pack(side=tk.RIGHT, padx=5)
        self.apply_button_hover(self.btn_cam_toggle, "#b4befe", self.accent_color)

        # Camera Display Viewport
        self.cam_display = tk.Label(left_frame, bg="#11111b", text="Camera Offline\nClick 'Start Camera' to begin streaming", fg=self.muted_color, font=("Helvetica", 12))
        self.cam_display.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 15))

        # RIGHT COLUMN: Live Session Log
        right_frame = ttk.Frame(self.tab_cam, style='Card.TFrame')
        right_frame.grid(row=0, column=1, padx=(10, 0), pady=10, sticky='nsew')

        tk.Label(right_frame, text="Live Detections Log", fg=self.accent_color, bg=self.card_color, font=("Helvetica", 12, "bold"), anchor='w').pack(fill=tk.X, padx=15, pady=15)

        # Scrollbar + Treeview
        log_scroll = ttk.Scrollbar(right_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_table = ttk.Treeview(right_frame, columns=("time", "name", "id", "loc", "status"), show="headings", yscrollcommand=log_scroll.set)
        log_scroll.config(command=self.log_table.yview)

        self.log_table.heading("time", text="Time")
        self.log_table.heading("name", text="Name")
        self.log_table.heading("id", text="Roll No")
        self.log_table.heading("loc", text="Location")
        self.log_table.heading("status", text="Status")

        self.log_table.column("time", width=80, anchor='center')
        self.log_table.column("name", width=120, anchor='w')
        self.log_table.column("id", width=80, anchor='center')
        self.log_table.column("loc", width=100, anchor='center')
        self.log_table.column("status", width=90, anchor='center')

        self.log_table.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

    # ------------------ REGISTER MEMBER TAB ------------------
    def build_register_tab(self):
        self.tab_register.columnconfigure(0, weight=1)
        self.tab_register.columnconfigure(1, weight=1)
        self.tab_register.rowconfigure(0, weight=1)

        # LEFT COLUMN: Registration Inputs
        reg_card = ttk.Frame(self.tab_register, style='Card.TFrame')
        reg_card.grid(row=0, column=0, padx=(0, 10), pady=10, sticky='nsew')

        tk.Label(reg_card, text="Register New Profile", fg=self.accent_color, bg=self.card_color, font=("Helvetica", 14, "bold")).pack(padx=25, pady=25, anchor='w')

        # Input container
        input_container = tk.Frame(reg_card, bg=self.card_color)
        input_container.pack(fill=tk.X, padx=25)

        # Name Entry
        tk.Label(input_container, text="Full Name", fg=self.text_color, bg=self.card_color, font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky='w', pady=(0, 5))
        self.reg_name = tk.StringVar()
        name_entry = tk.Entry(input_container, textvariable=self.reg_name, bg=self.input_bg, fg=self.text_color, insertbackground=self.text_color, relief='flat', bd=0, font=("Helvetica", 11))
        name_entry.grid(row=1, column=0, sticky='we', ipady=6, pady=(0, 15))

        # Roll Number Entry
        tk.Label(input_container, text="Roll Number / Unique ID", fg=self.text_color, bg=self.card_color, font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky='w', pady=(0, 5))
        self.reg_roll = tk.StringVar()
        roll_entry = tk.Entry(input_container, textvariable=self.reg_roll, bg=self.input_bg, fg=self.text_color, insertbackground=self.text_color, relief='flat', bd=0, font=("Helvetica", 11))
        roll_entry.grid(row=3, column=0, sticky='we', ipady=6, pady=(0, 15))

        # File Upload trigger
        tk.Label(input_container, text="Profile Photograph", fg=self.text_color, bg=self.card_color, font=("Helvetica", 10, "bold")).grid(row=4, column=0, sticky='w', pady=(0, 5))
        
        file_actions_frame = tk.Frame(input_container, bg=self.card_color)
        file_actions_frame.grid(row=5, column=0, sticky='we', pady=(0, 20))
        
        btn_upload = tk.Button(file_actions_frame, 
                               text="Browse Photo", 
                               command=self.select_register_photo, 
                               bg=self.accent_color, 
                               fg="#11111b", 
                               relief='flat', 
                               bd=0, 
                               font=("Helvetica", 10, "bold"), 
                               padx=15, 
                               pady=6)
        btn_upload.pack(side=tk.LEFT)
        self.apply_button_hover(btn_upload, "#b4befe", self.accent_color)
        
        self.lbl_selected_filename = tk.Label(file_actions_frame, text="No photo selected", fg=self.muted_color, bg=self.card_color, font=("Helvetica", 9))
        self.lbl_selected_filename.pack(side=tk.LEFT, padx=15)

        # Save Button
        btn_register = tk.Button(reg_card, 
                                 text="Save Profile to DB", 
                                 command=self.submit_registration, 
                                 bg=self.green_color, 
                                 fg="#11111b", 
                                 relief='flat', 
                                 bd=0, 
                                 font=("Helvetica", 11, "bold"), 
                                 padx=25, 
                                 pady=8)
        btn_register.pack(padx=25, pady=20, anchor='w')
        self.apply_button_hover(btn_register, "#a6e3a1", self.green_color)

        self.selected_photo_path = None

        # RIGHT COLUMN: Live Photo Preview Card
        preview_card = ttk.Frame(self.tab_register, style='Card.TFrame')
        preview_card.grid(row=0, column=1, padx=(10, 0), pady=10, sticky='nsew')
        
        tk.Label(preview_card, text="Photo Preview", fg=self.accent_color, bg=self.card_color, font=("Helvetica", 14, "bold")).pack(padx=25, pady=25, anchor='w')
        
        self.lbl_photo_preview = tk.Label(preview_card, text="Select a photograph on the left\nto preview", bg="#11111b", fg=self.muted_color, font=("Helvetica", 10))
        self.lbl_photo_preview.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 25))

    # ------------------ RECORDS TAB ------------------
    def build_records_tab(self):
        self.tab_records.columnconfigure(0, weight=2)
        self.tab_records.columnconfigure(1, weight=3)
        self.tab_records.rowconfigure(0, weight=1)

        # LEFT COLUMN: Detail Card & Search Panel
        left_pane = ttk.Frame(self.tab_records, style='Card.TFrame')
        left_pane.grid(row=0, column=0, padx=(0, 10), pady=10, sticky='nsew')
        
        # Search Bar
        search_frame = tk.Frame(left_pane, bg=self.card_color, pady=15)
        search_frame.pack(fill=tk.X, padx=20)
        
        tk.Label(search_frame, text="Search Roll No:", fg=self.text_color, bg=self.card_color, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, bg=self.input_bg, fg=self.text_color, insertbackground=self.text_color, relief='flat', bd=0, width=12, font=("Helvetica", 10))
        search_entry.pack(side=tk.LEFT, padx=5, ipady=4)
        
        btn_search = tk.Button(search_frame, text="Search", command=self.perform_search, bg=self.accent_color, fg="#11111b", relief='flat', bd=0, font=("Helvetica", 9, "bold"), padx=10)
        btn_search.pack(side=tk.LEFT, padx=5)
        self.apply_button_hover(btn_search, "#b4befe", self.accent_color)
        
        btn_reset = tk.Button(search_frame, text="Reset", command=self.load_all_records, bg=self.input_bg, fg=self.text_color, relief='flat', bd=0, font=("Helvetica", 9, "bold"), padx=10)
        btn_reset.pack(side=tk.LEFT, padx=2)

        # Details Display Panel
        self.details_panel = tk.Frame(left_pane, bg=self.card_color)
        self.details_panel.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Selected Photo View
        self.lbl_details_photo = tk.Label(self.details_panel, bg="#11111b", text="No User Selected", fg=self.muted_color)
        self.lbl_details_photo.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Labels for details
        self.lbl_details_name = tk.Label(self.details_panel, text="Name: -", font=("Helvetica", 12, "bold"), fg=self.text_color, bg=self.card_color, anchor='w')
        self.lbl_details_name.pack(fill=tk.X, pady=2)
        
        self.lbl_details_roll = tk.Label(self.details_panel, text="Roll No: -", font=("Helvetica", 11), fg=self.muted_color, bg=self.card_color, anchor='w')
        self.lbl_details_roll.pack(fill=tk.X, pady=2)
        
        self.lbl_details_loc = tk.Label(self.details_panel, text="Last Location: -", font=("Helvetica", 11), fg=self.muted_color, bg=self.card_color, anchor='w')
        self.lbl_details_loc.pack(fill=tk.X, pady=2)
        
        self.lbl_details_time = tk.Label(self.details_panel, text="Last Tracked Time: -", font=("Helvetica", 11), fg=self.muted_color, bg=self.card_color, anchor='w')
        self.lbl_details_time.pack(fill=tk.X, pady=2)

        # RIGHT COLUMN: Database Table
        right_pane = ttk.Frame(self.tab_records, style='Card.TFrame')
        right_pane.grid(row=0, column=1, padx=(10, 0), pady=10, sticky='nsew')
        
        header_row = tk.Frame(right_pane, bg=self.card_color)
        header_row.pack(fill=tk.X, padx=15, pady=15)
        
        tk.Label(header_row, text="Registered Database", fg=self.accent_color, bg=self.card_color, font=("Helvetica", 12, "bold")).pack(side=tk.LEFT)
        
        btn_refresh = tk.Button(header_row, text="Refresh DB", command=self.load_all_records, bg=self.input_bg, fg=self.text_color, relief='flat', bd=0, font=("Helvetica", 9, "bold"), padx=10, pady=3)
        btn_refresh.pack(side=tk.RIGHT)

        # Table & Scrollbar
        tbl_scroll = ttk.Scrollbar(right_pane)
        tbl_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.db_table = ttk.Treeview(right_pane, columns=("id", "name", "loc", "time"), show="headings", yscrollcommand=tbl_scroll.set)
        tbl_scroll.config(command=self.db_table.yview)

        self.db_table.heading("id", text="Roll No / ID")
        self.db_table.heading("name", text="Full Name")
        self.db_table.heading("loc", text="Last Location")
        self.db_table.heading("time", text="Last Tracked Time")

        self.db_table.column("id", width=90, anchor='center')
        self.db_table.column("name", width=140, anchor='w')
        self.db_table.column("loc", width=110, anchor='center')
        self.db_table.column("time", width=160, anchor='center')

        self.db_table.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Bind row selection to update detail card
        self.db_table.bind("<<TreeviewSelect>>", self.on_record_select)
        
        # Load initial values
        self.load_all_records()

    # ------------------ EVENT HANDLERS & LOGIC ------------------

    # Apply nice hover color shifts to standard tk.Buttons
    def apply_button_hover(self, button, hover_bg, normal_bg):
        button.bind("<Enter>", lambda e: button.config(bg=hover_bg))
        button.bind("<Leave>", lambda e: button.config(bg=normal_bg))

    # Toggle Tracking Webcam Stream
    def toggle_tracking(self):
        if self.is_tracking:
            # STOP tracking
            self.is_tracking = False
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            self.btn_cam_toggle.config(text="Start Camera", bg=self.accent_color)
            self.apply_button_hover(self.btn_cam_toggle, "#b4befe", self.accent_color)
            self.cam_display.config(image='', text="Camera Offline\nClick 'Start Camera' to begin streaming")
        else:
            # START tracking
            cam_idx = self.cam_var.get()
            self.cap = cv2.VideoCapture(cam_idx)
            if not self.cap.isOpened():
                messagebox.showerror("Camera Error", f"Could not open camera source index {cam_idx}.\nTry scanning/choosing another source index.")
                return
            
            self.is_tracking = True
            self.frame_counter = 0
            self.cached_faces = ([], [])
            self.btn_cam_toggle.config(text="Stop Camera", bg=self.red_color)
            self.apply_button_hover(self.btn_cam_toggle, "#e05a80", self.red_color)
            self.cam_display.config(text="Initializing Feed...")
            
            # Start loop
            self.update_camera_loop()

    # Camera Loop Process (updates periodically, performs lazy evaluation)
    def update_camera_loop(self):
        if not self.is_tracking or self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.root.after(15, self.update_camera_loop)
            return

        self.frame_counter += 1
        
        try:
            # Optimize: only run face-detection algorithms every 3 frames to avoid main UI thread lag
            if self.frame_counter % 3 == 1 or not self.cached_faces[0]:
                self.cached_faces = self.sfr.detect_known_faces(frame)
            
            face_locations, ids = self.cached_faces
            current_time = time.time()

            for face_loc, face_id in zip(face_locations, ids):
                y1, x2, y2, x1 = face_loc[0], face_loc[1], face_loc[2], face_loc[3]

                if face_id == "Unknown":
                    color = (50, 50, 220)  # BGR Red
                    name = "Unknown"
                else:
                    color = (50, 220, 50)  # BGR Green
                    name = face_id
                    
                    # Read name from db
                    cursor = self.con.cursor()
                    cursor.execute("SELECT name FROM USER WHERE id = ?", (face_id,))
                    row = cursor.fetchone()
                    if row:
                        name = row[0]
                    
                    # Write to database (with location/time cooldown update)
                    loc = self.selected_location.get().strip()
                    if not loc:
                        loc = "Zone " + str(self.cam_var.get())
                    
                    last_upd = self.last_updates.get(face_id)
                    # DB cooldown: update only if 10s has passed, or if location changes
                    if (last_upd is None or 
                        (current_time - last_upd[0] > 10.0) or 
                        (last_upd[1] != loc)):
                        
                        cursor.execute("UPDATE USER SET location = ?, time = ? WHERE id = ?", (loc, current_time, face_id))
                        self.con.commit()
                        self.last_updates[face_id] = (current_time, loc)

                        # Insert into Real-time GUI Log table
                        time_str = datetime.fromtimestamp(current_time).strftime('%H:%M:%S')
                        self.log_table.insert('', 0, values=(time_str, name, face_id, loc, "Registered"))

                # Draw overlay rectangles & labels
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 0.8, color, 2)

        except Exception as e:
            print(f"Error in face processing: {e}")

        # Render BGR frame to GUI canvas
        try:
            h, w = frame.shape[:2]
            # Limit displaying resolution to fit nicely in panel
            scale = min(620 / w, 440 / h)
            new_w, new_h = int(w * scale), int(h * scale)
            frame_resized = cv2.resize(frame, (new_w, new_h))
            
            rgb_frame = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            img_tk = ImageTk.PhotoImage(image=img)
            self.cam_display.img_tk = img_tk
            self.cam_display.configure(image=img_tk)
        except Exception as e:
            print(f"Rendering error: {e}")

        if self.is_tracking:
            self.root.after(15, self.update_camera_loop)

    # Register Tab: Choose local photo
    def select_register_photo(self):
        f_types = [('Jpg Files', '*.jpg'), ('Png Files', '*.png')]
        filepath = filedialog.askopenfilename(multiple=False, filetypes=f_types)
        if filepath:
            self.selected_photo_path = filepath
            filename = os.path.basename(filepath)
            self.lbl_selected_filename.config(text=filename[:25] + ("..." if len(filename) > 25 else ""), fg=self.green_color)
            
            # Show preview
            try:
                img = Image.open(filepath)
                img.thumbnail((300, 300))
                img_tk = ImageTk.PhotoImage(img)
                self.lbl_photo_preview.img_tk = img_tk
                self.lbl_photo_preview.config(image=img_tk, text="")
            except Exception as e:
                messagebox.showerror("Preview Error", f"Unable to read selected image: {e}")

    # Register Tab: Submit registration
    def submit_registration(self):
        name = self.reg_name.get().strip()
        roll = self.reg_roll.get().strip()
        photo = self.selected_photo_path

        if not name or not roll:
            messagebox.showwarning("Validation Error", "All fields (Name and Roll No) are required!")
            return
        
        if not photo:
            messagebox.showwarning("Validation Error", "Please upload a profile photograph for facial recognition!")
            return

        cursor = self.con.cursor()
        try:
            # Check if Roll No/ID already exists
            cursor.execute("SELECT name FROM USER WHERE id = ?", (roll,))
            exists = cursor.fetchone()
            if exists:
                messagebox.showerror("Database Error", f"Roll Number/ID '{roll}' is already registered under the name '{exists[0]}'.")
                return

            # Save file copy to images directory
            target_ext = os.path.splitext(photo)[1].lower()
            if not target_ext:
                target_ext = ".jpg"
            target_filename = f"images/{roll}{target_ext}"
            
            shutil.copy(photo, target_filename)

            # Register with database
            timestamp = time.time()
            cursor.execute("INSERT INTO USER (id, name, location, time) VALUES (?, ?, ?, ?)", 
                           (roll, name, "Main Gate", timestamp))
            self.con.commit()

            # Dynamic update to face recognition library
            self.sfr.load_single_image(target_filename)

            messagebox.showinfo("Success", f"Profile for '{name}' successfully registered!")

            # Reset Register fields
            self.reg_name.set("")
            self.reg_roll.set("")
            self.selected_photo_path = None
            self.lbl_selected_filename.config(text="No photo selected", fg=self.muted_color)
            self.lbl_photo_preview.config(image='', text="Select a photograph on the left\nto preview")
            
            # Reload Records
            self.load_all_records()

        except Exception as e:
            messagebox.showerror("Write Error", f"Failed to save profile: {e}")

    # Records Tab: Load all rows from SQLite
    def load_all_records(self):
        # Clear table
        for item in self.db_table.get_children():
            self.db_table.delete(item)

        cursor = self.con.cursor()
        cursor.execute("SELECT id, name, location, time FROM USER")
        for row in cursor.fetchall():
            formatted = format_time(row[3])
            self.db_table.insert('', tk.END, values=(row[0], row[1], row[2], formatted))
            
        self.search_var.set("")

    # Records Tab: Search query
    def perform_search(self):
        query = self.search_var.get().strip()
        if not query:
            return

        for item in self.db_table.get_children():
            self.db_table.delete(item)

        cursor = self.con.cursor()
        cursor.execute("SELECT id, name, location, time FROM USER WHERE id LIKE ? OR name LIKE ?", (f"%{query}%", f"%{query}%"))
        results = cursor.fetchall()
        for row in results:
            formatted = format_time(row[3])
            self.db_table.insert('', tk.END, values=(row[0], row[1], row[2], formatted))
            
        if not results:
            self.clear_detail_panel()
            self.lbl_details_photo.config(text="No matching profiles found")

    # Clear Detail card on Records tab
    def clear_detail_panel(self):
        self.lbl_details_photo.config(image='', text="No User Selected")
        self.lbl_details_name.config(text="Name: -")
        self.lbl_details_roll.config(text="Roll No: -")
        self.lbl_details_loc.config(text="Last Location: -")
        self.lbl_details_time.config(text="Last Tracked Time: -")

    # Records Tab: Handle table selection event
    def on_record_select(self, event):
        selected = self.db_table.selection()
        if not selected:
            return

        item = self.db_table.item(selected[0])
        roll, name, loc, time_val = item['values']

        # Load details
        self.lbl_details_name.config(text=f"Name: {name}")
        self.lbl_details_roll.config(text=f"Roll No: {roll}")
        self.lbl_details_loc.config(text=f"Last Location: {loc}")
        self.lbl_details_time.config(text=f"Last Tracked Time: {time_val}")

        # Search for image file with any common extension (jpg, jpeg, png)
        img_path = None
        for ext in ('.jpg', '.jpeg', '.png'):
            test_path = f"images/{roll}{ext}"
            if os.path.exists(test_path):
                img_path = test_path
                break

        if img_path:
            try:
                img = Image.open(img_path)
                # Resize to fit in detail display card
                img.thumbnail((220, 220))
                img_tk = ImageTk.PhotoImage(img)
                self.lbl_details_photo.img_tk = img_tk
                self.lbl_details_photo.config(image=img_tk, text="")
            except Exception as e:
                self.lbl_details_photo.config(image='', text=f"Error loading image:\n{e}")
        else:
            self.lbl_details_photo.config(image='', text="No Profile Photo Found")

if __name__ == "__main__":
    root = tk.Tk()
    app = SurveillanceApp(root)
    
    # Graceful shutdown handler
    def on_closing():
        if app.is_tracking:
            app.is_tracking = False
            if app.cap:
                app.cap.release()
        app.con.close()
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
