import os
from flask import Flask, request, render_template, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from cartoonify import cartoonify_image

# --- Configuration ---
UPLOAD_FOLDER = 'static/uploads/'
PROCESSED_FOLDER = 'static/processed/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Checks if the file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    """Renders the main page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles file upload and cartoonification."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        processed_filename = f"cartoon_{filename}"
        processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
        
        try:
            file.save(original_path)
            cartoonify_image(original_path, processed_path)
            
            return jsonify({
                'cartoon_image_url': f'/{PROCESSED_FOLDER}{processed_filename}'
            })
            
        except Exception as e:
            print(f"Error during processing: {e}")
            return jsonify({'error': 'Failed to process the image.'})
    
    return jsonify({'error': 'File type not allowed.'})

# Route to serve processed images
@app.route('/static/processed/<filename>')
def processed_file(filename):
    """Serves a processed file from the PROCESSED_FOLDER."""
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename)

# This is the critical part that actually runs the server
if __name__ == '__main__':
    app.run(debug=True)
