import cv2
import numpy as np
import os

def cartoonify_image(image_path, output_path, max_width=600, num_colors=8, line_strength=1):
    """
    Applies a fast, high-quality cartoon filter with clear outlines and flat colors.

    This optimized version resizes the image before heavy processing (like color
    quantization) to ensure a fast, responsive result, then combines it with a
    full-resolution edge mask for sharp lines.

    Args:
        image_path (str): The full path to the input image.
        output_path (str): The full path where the cartoonified image will be saved.
        max_width (int): The maximum width for processing. Larger images are downscaled.
        num_colors (int): The number of distinct colors for quantization (K-Means).
        line_strength (int): Multiplier for edge thickness.
    """
    if not os.path.exists(image_path):
        print(f"Error: Input image not found at {image_path}")
        return

    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read the image from {image_path}.")
        return

    # --- 1. Resize Image for Fast Color Processing ---
    # Store original dimensions to upscale later
    original_height, original_width = img.shape[:2]
    
    # Calculate new dimensions while preserving aspect ratio
    if original_width > max_width:
        new_height = int(max_width * original_height / original_width)
        small_img = cv2.resize(img, (max_width, new_height), interpolation=cv2.INTER_AREA)
    else:
        small_img = img

    # --- 2. Color Quantization on the Small Image (K-Means) ---
    # This is the slowest step, so we run it on the downscaled image.
    pixels = np.float32(small_img.reshape(-1, 3))
    
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    _, labels, centers = cv2.kmeans(pixels, num_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    centers = np.uint8(centers)
    flat_colors_small = centers[labels.flatten()]
    flat_colors_small = flat_colors_small.reshape(small_img.shape)

    # --- 3. Edge Detection on the Full-Resolution Image ---
    # For sharp, high-quality lines, we perform edge detection on the original image.
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred_gray = cv2.medianBlur(gray, 5)
    
    edges = cv2.adaptiveThreshold(blurred_gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                  cv2.THRESH_BINARY, 9, 9)
    
    # --- 4. Thicken the Lines for "Inked" Look ---
    edges_inverted = cv2.bitwise_not(edges)
    kernel_size = 2 * line_strength + 1
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    thick_edges = cv2.dilate(edges_inverted, kernel, iterations=1)
    final_edge_mask = cv2.bitwise_not(thick_edges)

    # --- 5. Upscale the Flat Colors and Combine with Edges ---
    # Resize the flat color image back to the original dimensions
    flat_colors_large = cv2.resize(flat_colors_small, (original_width, original_height), interpolation=cv2.INTER_LINEAR)
    
    # Combine the high-resolution colors with the high-resolution edge mask
    cartoon_image = cv2.bitwise_and(flat_colors_large, flat_colors_large, mask=final_edge_mask)

    # --- 6. Save the Result ---
    try:
        cv2.imwrite(output_path, cartoon_image)
        print(f"Optimized cartoon filter applied and saved successfully: {output_path}")
    except Exception as e:
        print(f"Error: Could not save the image. Reason: {e}")