import tkinter as tk
import argparse
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import subprocess

import os
os.chdir(os.path.dirname(os.path.abspath(__name__)))

# Define the printer Bluetooth address
address = "AA:BB:CC:DD:EE:FF"

parser = argparse.ArgumentParser(description='Print image or text on a DYMO LetraTag 200B')
parser.add_argument('--address', type=str, help='MAC address of printer', default=address)
args = parser.parse_args()

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
        return img.crop(bbox)
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
        root.geometry(f"{new_size}x390")

def open_file():
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")])
    if file_path:
        global selected_image_path, original_image
        selected_image_path = file_path
        original_image = Image.open(file_path)
        
        update_image_display()

def toggle_cable_options():
    if cable_var.get():
        cable_diameter_label.pack(after=cable_check, pady=5)
        cable_diameter_entry.pack(after=cable_diameter_label, pady=5)
    else:
        cable_diameter_label.pack_forget()
        cable_diameter_entry.pack_forget()
    update_image_display()

def print_image():
    if 'selected_image_path' in globals() and 'processed_image' in globals():
        copies = int(copies_entry.get() or 1)
        
        # Always save processed image to temporary file
        import tempfile
        import os
        
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "temp_print_image.png")
        processed_image.save(temp_path)
        
        for i in range(copies):
            subprocess.run([
                "python", "print.py", "--address", args.address,
                "--image", temp_path
            ])
            if i < copies - 1:  # Don't ask for confirmation after the last print
                if not messagebox.askyesno("Cut Confirmation", "Please confirm the cut to continue with the next print."):
                    messagebox.showinfo("Print Cancelled", f"Printing stopped after {i + 1} copies.")
                    break
        messagebox.showinfo("Print", f"{copies} copies sent to printer.")
    else:
        messagebox.showwarning("No Image Selected", "Please select an image to print.")

# Create the main window
root = tk.Tk()
root.title("Image Printing Interface")

# Create and place widgets
file_button = tk.Button(root, text="Select an image", command=open_file)
file_button.pack(pady=10)

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

copies_label = tk.Label(root, text="Number of copies:")
copies_label.pack(pady=5)

copies_entry = tk.Entry(root)
copies_entry.pack(pady=5)

print_button = tk.Button(root, text="Print", command=print_image)
print_button.pack(pady=20)

# set default window size
root.geometry("250x390")

if __name__ == "__main__":
    root.mainloop()
    
   