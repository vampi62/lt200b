import tkinter as tk
import argparse
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import subprocess
import threading
import tempfile

import os
os.chdir(os.path.dirname(os.path.abspath(__name__)))

# Define the printer Bluetooth address
address = "AA:BB:CC:DD:EE:FF"

parser = argparse.ArgumentParser(description='Print image or text on a DYMO LetraTag 200B')
parser.add_argument('--address', type=str, help='MAC address of printer', default=address)
args = parser.parse_args()

def text_to_image(text, font_size=20):
    """Convert text to an image"""
    # Try to use a truetype font, fallback to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Create a temporary image to calculate text size
    temp_img = Image.new('RGB', (1, 1), (255, 255, 255))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Add padding
    padding = 10
    img_width = text_width + 2 * padding
    img_height = text_height + 2 * padding
    
    # Create the actual image
    img = Image.new('RGB', (img_width, img_height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((padding, padding), text, fill=(0, 0, 0), font=font)
    
    return img

def crop_white_borders(img):
    # Convert image to grayscale to detect non-white areas
    bg = Image.new(img.mode, img.size, (255, 255, 255))
    diff = Image.new('L', img.size)
    
    if img.mode == 'RGBA':
        img_rgb = img.convert('RGB')
    else:
        img_rgb = img
    
    # Get bounding box of non-white content
    pixels = img_rgb.load()
    bbox = img_rgb.getbbox()
    
    # More aggressive cropping by checking for near-white pixels
    img_gray = img_rgb.convert('L')
    # Threshold: consider pixels darker than 250 as content
    from PIL import ImageChops
    bg_gray = Image.new('L', img.size, 255)
    diff = ImageChops.difference(img_gray, bg_gray)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    
    if bbox:
        # Adjust bbox to keep one extra pixel on top and bottom
        left, top, right, bottom = bbox
        top = max(0, top - 1)
        bottom = min(img.height, bottom + 1)
        return img.crop((left, top, right, bottom))
    return img

def update_image_display():
    if 'original_image' in globals():
        img = original_image.copy()
        
        # Apply cropping if enabled
        if crop_var.get():
            img = crop_white_borders(img)
        
        # Apply cable model if enabled
        if cable_var.get():
            try:
                diameter = float(cable_diameter_entry.get())
                # Calculate spacing: 10mm on each side of the line
                spacing_mm = 10 + 3.14 * (diameter / 2)
                spacing_px = int(spacing_mm * (img.height / 5))  # Convert mm to pixels
                
                # Create white space section with a vertical line in the middle
                # Total width: spacing + line + spacing
                line_width = 2
                white_width = spacing_px * 2 + line_width
                white_section = Image.new('RGB', (white_width, img.height), (255, 255, 255))
                
                # Draw a vertical line in the middle
                draw = ImageDraw.Draw(white_section)
                middle_x = white_width // 2
                draw.line([(middle_x, 0), (middle_x, img.height)], fill=(0, 0, 0), width=line_width)
                
                # Create new image: image + white space + image
                new_width = img.width + white_width + img.width
                cable_img = Image.new('RGB', (new_width, img.height), (255, 255, 255))
                
                # Paste: left image, white space with line, right image
                cable_img.paste(img, (0, 0))
                cable_img.paste(white_section, (img.width, 0))
                cable_img.paste(img, (img.width + white_width, 0))
                
                img = cable_img
            except ValueError:
                pass  # If diameter is not a valid number, skip cable model
        
        # Store the processed image for printing
        global processed_image
        processed_image = img.copy()
        
        # Resize for display
        display_img = img.copy()
        display_img.thumbnail((300, 300))
        img_tk = ImageTk.PhotoImage(display_img)
        
        image_label.config(image=img_tk)
        image_label.image = img_tk
        
        # Calculate dimensions in mm using processed image
        width_px, height_px = processed_image.size
        height_mm = 5  # Reference height in mm
        width_mm = (width_px / height_px) * height_mm
        
        dimensions_label.config(text=f"Dimensions: {19+width_mm:.2f} mm x 12 mm")
        new_size = 250
        if image_label.image.width() > 250:
            new_size = image_label.image.width() + 20
        root.geometry(f"{new_size}x420")

def open_file():
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")])
    if file_path:
        global selected_image_path, original_image
        selected_image_path = file_path
        original_image = Image.open(file_path)
        
        update_image_display()

def enter_text():
    """Open a dialog to enter text and convert it to an image"""
    # Create a simple dialog window
    dialog = tk.Toplevel(root)
    dialog.title("Enter Text")
    dialog.geometry("300x150")
    
    label = tk.Label(dialog, text="Enter text to print:")
    label.pack(pady=10)
    
    text_entry = tk.Entry(dialog, width=40)
    text_entry.pack(pady=10)
    text_entry.focus()
    
    def confirm_text():
        text = text_entry.get().strip()
        if text:
            # Convert text to image
            text_img = text_to_image(text, font_size=20)
            # Resize to appropriate height (50 pixels for 5mm)
            target_height = 50
            aspect_ratio = text_img.width / text_img.height
            target_width = int(target_height * aspect_ratio)
            text_img = text_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Set as the original image
            global original_image, selected_image_path
            original_image = text_img
            selected_image_path = "text_image"
            
            dialog.destroy()
            update_image_display()
        else:
            # Show warning in dialog
            label.config(text="Please enter some text!", fg="red")
    
    confirm_button = tk.Button(dialog, text="OK", command=confirm_text)
    confirm_button.pack(pady=10)
    
    # Bind Enter key to confirm
    text_entry.bind('<Return>', lambda e: confirm_text())
    
    dialog.transient(root)
    dialog.grab_set()
    root.wait_window(dialog)

def toggle_cable_options():
    if cable_var.get():
        cable_diameter_label.pack(after=cable_check, pady=5)
        cable_diameter_entry.pack(after=cable_diameter_label, pady=5)
    else:
        cable_diameter_label.pack_forget()
        cable_diameter_entry.pack_forget()
    update_image_display()

def lock_interface():
    """Lock all interface elements during printing"""
    file_button.config(state='disabled')
    text_button.config(state='disabled')
    crop_check.config(state='disabled')
    cable_check.config(state='disabled')
    cable_diameter_entry.config(state='disabled')
    print_button.config(state='disabled')

def unlock_interface():
    """Unlock all interface elements after printing"""
    file_button.config(state='normal')
    text_button.config(state='normal')
    crop_check.config(state='normal')
    cable_check.config(state='normal')
    cable_diameter_entry.config(state='normal')
    print_button.config(state='normal')

def animate_loading():
    """Animate loading indicator"""
    if loading_var.get():
        current = loading_label.cget("text")
        if current == "Printing":
            loading_label.config(text="Printing.")
        elif current == "Printing.":
            loading_label.config(text="Printing..")
        elif current == "Printing..":
            loading_label.config(text="Printing...")
        else:
            loading_label.config(text="Printing")
        root.after(500, animate_loading)

def show_message(message, msg_type="info"):
    """Display a message in the interface"""
    colors = {
        "info": "#2196F3",  # Blue
        "success": "#4CAF50",  # Green
        "warning": "#FF9800",  # Orange
        "error": "#F44336"  # Red
    }
    message_label.config(text=message, fg=colors.get(msg_type, "black"))
    message_label.pack(pady=5)

def clear_message():
    """Clear the message label"""
    message_label.config(text="")
    message_label.pack_forget()

def print_image():
    # Clear previous message
    clear_message()
    
    if 'selected_image_path' in globals() and 'processed_image' in globals():
        # Start printing in a separate thread
        print_thread = threading.Thread(target=print_image_async, daemon=True)
        print_thread.start()
    else:
        show_message("Please select an image to print.", "warning")

def print_image_async():
    """Async function to handle printing without blocking the UI"""
    # Lock interface and show loading animation
    root.after(0, lock_interface)
    loading_var.set(True)
    root.after(0, lambda: loading_label.pack(pady=5))
    root.after(0, animate_loading)
    
    try:
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "temp_print_image.png")
        processed_image.save(temp_path)
        result = subprocess.run([
            "python", "print.py", "--address", args.address,
            "--image", temp_path
        ], capture_output=True, text=True, check=True)
        
        # Show success message
        root.after(0, lambda: show_message("Print completed successfully!", "success"))
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Print error (code {e.returncode}): {e.stderr or e.stdout}"
        root.after(0, lambda msg=error_msg: show_message(msg, "error"))
    except Exception as e:
        root.after(0, lambda msg=str(e): show_message(f"Error: {msg}", "error"))
    finally:
        # Stop loading animation and unlock interface
        loading_var.set(False)
        root.after(0, lambda: loading_label.pack_forget())
        root.after(0, unlock_interface)

# Create the main window
root = tk.Tk()
root.title("Image Printing Interface")

# Create and place widgets
# Frame for file selection buttons
file_frame = tk.Frame(root)
file_frame.pack(pady=10)

file_button = tk.Button(file_frame, text="Select an image", command=open_file)
file_button.pack(side=tk.LEFT, padx=5)

text_button = tk.Button(file_frame, text="Enter text", command=enter_text)
text_button.pack(side=tk.LEFT, padx=5)

image_label = tk.Label(root)
image_label.pack(pady=10)

dimensions_label = tk.Label(root, text="Dimensions: ")
dimensions_label.pack(pady=5)

# Crop white borders option
crop_var = tk.BooleanVar()
crop_check = tk.Checkbutton(root, text="Crop white borders", variable=crop_var, command=update_image_display)
crop_check.pack(pady=5)

# Cable label option
cable_var = tk.BooleanVar()
cable_check = tk.Checkbutton(root, text="Cable label", variable=cable_var, command=toggle_cable_options)
cable_check.pack(pady=10)

# Cable diameter fields (hidden by default)
cable_diameter_label = tk.Label(root, text="Cable diameter (mm):")
cable_diameter_entry = tk.Entry(root)
cable_diameter_entry.bind('<KeyRelease>', lambda e: update_image_display())

# Loading indicator (hidden by default)
loading_var = tk.BooleanVar(value=False)
loading_label = tk.Label(root, text="Printing", fg="blue", font=('Arial', 10, 'bold'))

# Message label (hidden by default)
message_label = tk.Label(root, text="", font=('Arial', 9), wraplength=300)

print_button = tk.Button(root, text="Print", command=print_image)
print_button.pack(pady=20)

# set default window size
root.geometry("250x380")

if __name__ == "__main__":
    root.mainloop()
    
   