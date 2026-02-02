import os
import sys
from PIL import Image

def create_icons(source_path, output_dir):
    try:
        img = Image.open(source_path)
        
        # Define sizes
        sizes = {
            'android-chrome-192x192.png': (192, 192),
            'android-chrome-512x512.png': (512, 512),
            'apple-touch-icon.png': (180, 180),
            'favicon-32x32.png': (32, 32),
            'favicon-16x16.png': (16, 16)
        }
        
        # Ensure output dir exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Generage PNGs
        for name, size in sizes.items():
            resized = img.resize(size, Image.Resampling.LANCZOS)
            resized.save(os.path.join(output_dir, name))
            print(f"Created {name}")
            
        # Generate ICO
        img.resize((64, 64), Image.Resampling.LANCZOS).save(
            os.path.join(output_dir, 'favicon.ico'), 
            format='ICO', 
            sizes=[(64, 64), (32, 32), (16, 16)]
        )
        print("Created favicon.ico")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: make_icons.py <source> <output_dir>")
    else:
        create_icons(sys.argv[1], sys.argv[2])
