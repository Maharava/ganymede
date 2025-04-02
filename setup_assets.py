#!/usr/bin/env python3
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import random

def create_welcome_image():
    """Create a simple welcome image for the server."""
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
    os.makedirs(assets_dir, exist_ok=True)
    
    image_path = os.path.join(assets_dir, 'welcome.png')
    
    # Check if image already exists
    if os.path.exists(image_path):
        print(f"Welcome image already exists at {image_path}")
        return
    
    try:
        # Create a simple image with text
        width, height = 800, 400
        image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw a colored rectangle background
        colors = [(52, 152, 219), (46, 204, 113), (155, 89, 182), (230, 126, 34)]
        bg_color = random.choice(colors)
        draw.rectangle([0, 0, width, height], fill=(bg_color[0], bg_color[1], bg_color[2], 230))
        
        # Add text (using default font if no custom font is available)
        try:
            font_size = 60
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
        
        text = "GANYMEDE FILE SERVER"
        text_width = draw.textlength(text, font=font) if hasattr(draw, 'textlength') else font.getsize(text)[0]
        text_position = ((width - text_width) // 2, height // 2 - 40)
        draw.text(text_position, text, fill=(255, 255, 255), font=font)
        
        # Save the image
        image.save(image_path, "PNG")
        print(f"Created welcome image at {image_path}")
    except Exception as e:
        print(f"Error creating welcome image: {e}")
        print("You may need to install Pillow: pip install Pillow")

if __name__ == "__main__":
    create_welcome_image()