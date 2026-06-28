import os
import sys
import time
import tkinter as tk
from PIL import Image

# Add parent directory to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import SurveillanceApp

def take_snapshots():
    # Make sure snapshots directory exists
    os.makedirs('snapshots', exist_ok=True)
    
    root = tk.Tk()
    
    # Force the Python window to the front on macOS using AppleScript
    try:
        pid = os.getpid()
        os.system(f"osascript -e 'tell application \"System Events\" to set frontmost of first process whose unix id is {pid} to true'")
    except Exception as e:
        print(f"Could not force frontmost via AppleScript: {e}")

    app = SurveillanceApp(root)
    
    # Position window on screen
    root.geometry("1050x700+100+100")
    root.lift()
    root.attributes("-topmost", True)
    root.focus_force()
    
    # Force initial updates to size the window
    root.update_idletasks()
    root.update()
    
    def step_1():
        print("Capturing Step 1: Live Stream...")
        app.notebook.select(0)
        root.update()
        time.sleep(1.5) # wait for render
        capture_window("snapshots/step_1_live_stream.png", root)
        root.after(1000, step_2)
        
    def step_2():
        print("Capturing Step 2: Register Member...")
        app.notebook.select(1)
        root.update()
        time.sleep(1) # wait for render
        capture_window("snapshots/step_2_register_member.png", root)
        root.after(1000, step_3)
        
    def step_3():
        print("Capturing Step 3: Database Records...")
        app.notebook.select(2)
        root.update()
        time.sleep(1) # wait for render
        capture_window("snapshots/step_3_database_records.png", root)
        root.after(1000, clean_up_and_exit)
        
    def clean_up_and_exit():
        print("Closing application...")
        root.destroy()
        
    # Schedule first step after window settles
    root.after(3000, step_1)
    
    root.mainloop()

def capture_window(output_path, root):
    temp_path = "temp_fullscreen.png"
    # Capture fullscreen without playing sound (-x option)
    os.system(f"screencapture -x {temp_path}")
    
    if not os.path.exists(temp_path):
        print(f"Error: failed to capture screen to {temp_path}")
        return
        
    root.update_idletasks()
    root.update()
    
    # Get Tkinter window dimensions
    rx = root.winfo_rootx()
    ry = root.winfo_rooty()
    rw = root.winfo_width()
    rh = root.winfo_height()
    
    # Load and scale coordinate for Retina display
    img = Image.open(temp_path)
    screen_w = root.winfo_screenwidth()
    scale = img.width / screen_w
    
    box = (
        int(rx * scale),
        int(ry * scale),
        int((rx + rw) * scale),
        int((ry + rh) * scale)
    )
    
    cropped = img.crop(box)
    cropped.save(output_path)
    
    # Clean up temp file
    if os.path.exists(temp_path):
        os.remove(temp_path)
    print(f"Saved screenshot: {output_path}")

if __name__ == "__main__":
    take_snapshots()
