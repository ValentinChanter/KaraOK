from flask import Flask, request, jsonify
import os
from audio_separator.separator import Separator
from flask_cors import CORS
import whisper_timestamped as whisper
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests from the Next.js front end
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'mp3'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400

    if file and allowed_file(file.filename):
        base_filename = os.path.splitext(file.filename)[0]
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)

        # Get parameters from the form
        output_format = request.form.get('output_format', 'mp3')
        model_filename = request.form.get('model_filename')

        try:
            # Perform audio separation
            separator = Separator(
                output_dir=app.config['UPLOAD_FOLDER'],
                output_format=output_format
            )
            separator.load_model(model_filename=model_filename)
            separator.separate(filename)

            # Define the output file name based on the chosen model and output format
            base_model_filename = os.path.splitext(model_filename)[0]
            output_filename = f"{base_filename}_(Vocals)_{base_model_filename}.{output_format}"
            output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

            # Check if the separated file exists
            if not os.path.exists(output_filepath):
                return jsonify({'error': 'Audio separation failed, file not found'}), 500

            # Load audio for Whisper
            audio = whisper.load_audio(output_filepath)

            # Load Whisper model
            whisper_model = whisper.load_model("large-v3", device="gpu")

            # Perform transcription
            transcription_result = whisper.transcribe_timestamped(whisper_model, audio)

            # Save transcription result
            transcription_output = f"{base_filename}_transcription.json"
            transcription_output_path = os.path.join(app.config['UPLOAD_FOLDER'], transcription_output)
            with open(transcription_output_path, 'w', encoding='utf-8') as f:
                json.dump(transcription_result, f, indent=2, ensure_ascii=False)

            return jsonify({
                'message': 'File successfully processed',
                'transcription_file': transcription_output
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Allowed file types are mp3'}), 400

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
