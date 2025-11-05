import os
import cv2
import numpy as np
from typing import Tuple
from PIL import Image, ImageOps

# ---- Utilities ----

def _load_image_with_orientation(path: str) -> np.ndarray:
    """Load with PIL to honor EXIF orientation, then convert to OpenCV BGR."""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode in ('RGBA', 'LA'):
            # Flatten transparency over white to avoid dark halos
            bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
            bg.alpha_composite(im)
            im = bg.convert('RGB')
        elif im.mode != 'RGB':
            im = im.convert('RGB')
        arr = np.array(im)  # RGB
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

def _save_png(image_bgr: np.ndarray, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # mild compression, keep edges crisp
    cv2.imwrite(path, image_bgr, [cv2.IMWRITE_PNG_COMPRESSION, 3])

def _resize_long_side(img: np.ndarray, target: int) -> np.ndarray:
    h, w = img.shape[:2]
    if max(h, w) == target:
        return img
    if h >= w:
        new_h, new_w = target, int(w * target / h)
    else:
        new_w, new_h = target, int(h * target / w)
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA if target < max(h, w) else cv2.INTER_CUBIC)

def _unsharp_mask(img: np.ndarray, radius: int = 3, amount: float = 1.25) -> np.ndarray:
    blur = cv2.GaussianBlur(img, (0, 0), sigmaX=radius, sigmaY=radius)
    return cv2.addWeighted(img, 1 + amount, blur, -amount, 0)

def _guided_smooth(bgr: np.ndarray, strength: float = 0.6) -> np.ndarray:
    """Edge-preserving smoothing without over-blurring low-res content."""
    # Use bilateral two-pass + slight median. Tuned for low-res.
    sm = cv2.bilateralFilter(bgr, d=7, sigmaColor=int(60 + strength*40), sigmaSpace=int(60 + strength*40))
    sm = cv2.bilateralFilter(sm, d=9, sigmaColor=int(70 + strength*40), sigmaSpace=int(70 + strength*40))
    sm = cv2.medianBlur(sm, 3)
    return sm

def _quantize_colors(bgr: np.ndarray, k: int, method: str = 'kmeans') -> np.ndarray:
    if method == 'mediancut':
        # Use PIL's median cut quantizer for stability on small images
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        q = pil.quantize(colors=int(k), method=Image.MEDIANCUT, dither=Image.Dither.NONE)
        out = np.array(q.convert('RGB'))
        return cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
    # k-means path
    Z = bgr.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.3)
    attempts = 5
    ret, label, center = cv2.kmeans(Z, k, None, criteria, attempts, cv2.KMEANS_PP_CENTERS)
    center = np.uint8(center)
    quant = center[label.flatten()].reshape(bgr.shape)
    quant = cv2.medianBlur(quant, 3)
    return quant

def _edge_map(gray: np.ndarray, line_strength: float) -> np.ndarray:
    """Hybrid edges: Canny + adaptive for line-art with tunable thickness."""
    # Normalize to reduce sensitivity on low-res
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    v = np.median(gray)
    # auto canny thresholds
    lower = int(max(0, (1.0 - 0.33) * v))
    upper = int(min(255, (1.0 + 0.33) * v))
    canny = cv2.Canny(gray, lower, upper)

    # Adaptive line art
    adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                  cv2.THRESH_BINARY_INV, 9, 2)

    edges = cv2.bitwise_or(canny, adapt)

    # control thickness: 0.1 => thick, 1.0 => thin
    k = max(1, int(5 * (1.1 - line_strength)))
    if k % 2 == 0:
        k += 1
    edges = cv2.dilate(edges, np.ones((k, k), np.uint8), iterations=1)
    edges = cv2.GaussianBlur(edges, (3, 3), 0)
    return edges

def cartoonify_image(
    image_path: str,
    output_path: str,
    *,
    target_long_side: int = 1024,
    num_colors: int = 8,
    line_strength: float = 0.5,
    blur_type: str = 'bilateral',
    upscale_small: bool = True,
    quantizer: str = 'kmeans',
) -> None:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f'Input image not found: {image_path}')

    bgr = _load_image_with_orientation(image_path)
    h0, w0 = bgr.shape[:2]

    # Optional smart upscale for low-res sources
    min_dim = min(h0, w0)
    if upscale_small and min_dim < 512:
        scale = 512 / min_dim
        upscale_side = int(round(max(h0, w0) * scale))
        bgr = _resize_long_side(bgr, upscale_side)
        bgr = _unsharp_mask(bgr, radius=1.6, amount=0.8)

    # Normalize working size
    bgr = _resize_long_side(bgr, min(target_long_side, 1600))

    # Edge-preserving smoothing
    if blur_type == 'median':
        smooth = cv2.medianBlur(bgr, 5)
    elif blur_type == 'gaussian':
        smooth = cv2.GaussianBlur(bgr, (5, 5), 0)
    else:
        smooth = _guided_smooth(bgr, strength=0.7)

    # Color quantization
    quant = _quantize_colors(smooth, max(4, min(16, int(num_colors))), method=quantizer)

    # Edges
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = _edge_map(gray, float(line_strength))
    edges_inv = cv2.bitwise_not(edges)
    edges_rgb = cv2.cvtColor(edges_inv, cv2.COLOR_GRAY2BGR)

    # Blend
    cartoon = cv2.addWeighted(quant, 0.88, edges_rgb, 0.12, 0)

    # Mild global tone mapping for punch
    cartoon = cv2.convertScaleAbs(cartoon, alpha=1.06, beta=0)
    cartoon = _unsharp_mask(cartoon, radius=0.8, amount=0.4)

    # Final anti-alias for jaggies
    cartoon = cv2.bilateralFilter(cartoon, 5, 30, 30)

    _save_png(cartoon, output_path)
