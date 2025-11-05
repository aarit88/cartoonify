import os
import uuid
from flask import Flask, request, render_template, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from cartoonify import cartoonify_image

# Folders
UPLOAD_FOLDER = 'static/uploads'
PROCESSED_FOLDER = 'static/processed'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    # Read options with sane defaults
    blur_type = request.form.get('blur_type', 'bilateral')
    try:
        num_colors = int(request.form.get('num_colors', 8))
    except Exception:
        num_colors = 8

    try:
        line_strength = float(request.form.get('line_strength', 0.5))
        line_strength = min(max(line_strength, 0.1), 1.0)
    except Exception:
        line_strength = 0.5

    try:
        target_long_side = int(request.form.get('target_long_side', 1024))
        target_long_side = max(256, min(target_long_side, 2048))
    except Exception:
        target_long_side = 1024

    try:
        upscale_small = request.form.get('upscale_small', 'true').lower() == 'true'
    except Exception:
        upscale_small = True

    try:
        quantizer = request.form.get('quantizer', 'kmeans')
        if quantizer not in ('kmeans', 'mediancut'):
            quantizer = 'kmeans'
    except Exception:
        quantizer = 'kmeans'

    # Save original with uuid to avoid collisions
    basename = secure_filename(file.filename)
    name, ext = os.path.splitext(basename)
    uid = uuid.uuid4().hex[:8]
    original_filename = f'{name}_{uid}{ext.lower()}'
    processed_filename = f'cartoon_{name}_{uid}.png'  # always PNG output for consistent edges

    original_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
    processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)

    try:
        file.save(original_path)
        cartoonify_image(
            original_path,
            processed_path,
            target_long_side=target_long_side,
            num_colors=num_colors,
            line_strength=line_strength,
            blur_type=blur_type,
            upscale_small=upscale_small,
            quantizer=quantizer,
        )
        return jsonify({'cartoon_image_url': f'/{PROCESSED_FOLDER}/{processed_filename}'})
    except Exception as e:
        print(f'[cartoonify] Error: {e}')
        return jsonify({'error': 'Failed to process image'}), 500

@app.route('/static/processed/<path:filename>')
def send_processed(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
