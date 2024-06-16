from flask import Flask, request, jsonify
import os
from audio_separator.separator import Separator
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests from the Next.js front end
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'mp3'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400

    if file and allowed_file(file.filename):
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)

        # Get parameters from the form
        output_format = request.form.get('output_format', 'mp3')
        model_filename = request.form.get('model_filename', 'UVR_MDXNET_KARA_2.onnx')

        # Perform audio separation
        separator = Separator(
            output_dir=app.config['UPLOAD_FOLDER'],
            output_format=output_format
        )
        separator.load_model(model_filename=model_filename)
        separator.separate(filename)

        return jsonify({'message': 'File successfully processed'}), 200
    else:
        return jsonify({'error': 'Allowed file types are mp3'}), 400

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)