import os
import time
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

from audio_separator.separator import Separator

import yt_dlp

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests from the Next.js front end
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['OUTPUT_FOLDER'] = 'output/'
app.config['TMP_FOLDER'] = app.config['OUTPUT_FOLDER'] + 'tmp/'
app.config['ALLOWED_EXTENSIONS'] = {'mp3', 'wav'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def is_youtube_link(link):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube\.com/watch\?v=|youtu\.be/)'
        '[^\s]{11}'
    )
    return re.match(youtube_regex, link) is not None

def get_youtube_video_title(url):
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'forcetitle': True,
        'skip_download': True,  # Ne télécharge pas la vidéo
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        video_title = info_dict.get('title', None)

    return video_title

def separate_audio(filename):
    base_filename = os.path.splitext(filename)[0]
    filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    model_filename = request.form.get('model_filename')

    try:
        audio_start = time.time()
        separator = Separator(
            output_dir=app.config['TMP_FOLDER'],
            output_format="wav"
        )
        separator.load_model(model_filename=model_filename)
        separator.separate(filename)

        # Define the output file name based on the chosen model and output format
        base_model_filename = os.path.splitext(model_filename)[0]
        vocals_filename = f"{base_filename}_(Vocals)_{base_model_filename}.wav"
        vocals_filepath = os.path.join(app.config['TMP_FOLDER'], vocals_filename)
        inst_filename = f"{base_filename}_(Instrumental)_{base_model_filename}.wav"
        inst_filepath = os.path.join(app.config['TMP_FOLDER'], inst_filename)

        # Check if the separated file exists
        if not os.path.exists(inst_filepath):
            return jsonify({'error': 'Audio separation failed, file not found'}), 500
        
        audio_end = time.time()
        audio_time = audio_end - audio_start

        return jsonify({
            'base_filename': base_filename,
            'vocals_filename': vocals_filename,
            'inst_filename': inst_filename,
            'audio_time': audio_time
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/separate', methods=['POST'])
def upload_file():
    error = False
    if 'file' in request.files:
        file = request.files['file']
        if not(file.filename == ''):
            if file and allowed_file(file.filename):
                filepathname = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepathname)

                return separate_audio(file.filename)
            else:
                error = True
        else:
            error = True
    elif 'musicLink' in request.form:
        musicLink = request.form.get('musicLink')
        if is_youtube_link(musicLink):

            filename = get_youtube_video_title(musicLink)
            filename = filename.replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace("\"", "_").replace("<", "_").replace(">", "_").replace("|", "_").replace("#", "_")
            filepathname = app.config['UPLOAD_FOLDER'] + filename
            filename = filename + ".mp3"

            ydl_opts = {
                'format': 'mp3/bestaudio/best',
                'postprocessors': [{  # Extract audio using ffmpeg
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'outtmpl': filepathname,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                error_code = ydl.download(musicLink)

            return separate_audio(filename)
        else:
            error = True
    else:
        error = True

    if error:
        return jsonify({'error': 'Error in music link or file in the request'}), 400