from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import os
import shutil
import zipfile
from werkzeug.utils import secure_filename
import subprocess
import pickle

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configuration
UPLOAD_FOLDER = './image_directory/merged_folder'
TAGGED_FOLDER = './image_directory/tagged_images'
DETECT_FOLDER = './runs/detect'
ZIP_FOLDER = './zips'
ALLOWED_EXTENSIONS = {'bmp', 'dng', 'jpeg', 'jpg', 'mpo', 'png', 'tif', 'tiff', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TAGGED_FOLDER'] = TAGGED_FOLDER
app.config['DETECT_FOLDER'] = DETECT_FOLDER
app.config['ZIP_FOLDER'] = ZIP_FOLDER

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TAGGED_FOLDER, exist_ok=True)
os.makedirs(DETECT_FOLDER, exist_ok=True)
os.makedirs(ZIP_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clear_directory(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory, exist_ok=True)

def zip_tagged_images():
    zip_filename = os.path.join(app.config['ZIP_FOLDER'], 'tagged_images.zip')
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, dirs, files in os.walk(app.config['TAGGED_FOLDER']):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=app.config['TAGGED_FOLDER'])
                zipf.write(file_path, arcname)
    return zip_filename

@app.route('/')
def index():
    # Scan the tagged images folder to get categories
    categories = [f.name for f in os.scandir(TAGGED_FOLDER) if f.is_dir()]
    categorized_images = {}
    for category in categories:
        category_path = os.path.join(TAGGED_FOLDER, category)
        images = [f for f in os.listdir(category_path) if allowed_file(f)]
        categorized_images[category] = images
    with open('species_mapping.pkl', 'rb') as f:
        species_mapping = pickle.load(f)
    return render_template('index.html', categories=categories, categorized_images=categorized_images, species_mapping=species_mapping)

@app.route('/', methods=['POST'])
def upload_files():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    files = request.files.getlist('file')
    
    # Clear directories
    clear_directory(app.config['UPLOAD_FOLDER'])
    clear_directory(app.config['TAGGED_FOLDER'])
    clear_directory(app.config['DETECT_FOLDER'])
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            print(f"Saved file to {file_path}")

    # Run detect.py
    detect_process = subprocess.run(["python", "detect.py"], capture_output=True, text=True)
    print(detect_process.stdout)
    print(detect_process.stderr)

    # Run tag_images.py
    tag_process = subprocess.run(["python", "tag_images.py"], capture_output=True, text=True)
    print(tag_process.stdout)
    print(tag_process.stderr)

    return redirect(url_for('index'))

@app.route('/download')
def download_files():
    zip_filepath = zip_tagged_images()
    return send_from_directory(directory=app.config['ZIP_FOLDER'], path='tagged_images.zip', as_attachment=True)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/display_image/<path:filename>')
def display_image(filename):
    return send_from_directory(TAGGED_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True)
