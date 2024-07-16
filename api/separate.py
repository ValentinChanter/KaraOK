import os
import time
import re
from flask import request, jsonify, Blueprint
from flask_cors import CORS

import librosa
from audio_separator.separator import Separator

import yt_dlp

separate = Blueprint('separate', __name__)
CORS(separate)
upload_folder = 'uploads/'
output_folder = 'output/'
tmp_folder = os.path.join(output_folder, 'tmp/')
allowed_extensions = {'mp3', 'wav'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

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
    filename = os.path.join(upload_folder, filename)

    model_filename = request.form.get('model_filename')

    try:
        audio_start = time.time()
        separator = Separator(
            output_dir=tmp_folder,
            output_format="wav"
        )
        separator.load_model(model_filename=model_filename)
        separator.separate(filename)

        # Define the output file name based on the chosen model and output format
        base_model_filename = os.path.splitext(model_filename)[0]
        vocals_filename = f"{base_filename}_(Vocals)_{base_model_filename}.wav"
        vocals_filepath = os.path.join(tmp_folder, vocals_filename)
        inst_filename = f"{base_filename}_(Instrumental)_{base_model_filename}.wav"
        inst_filepath = os.path.join(tmp_folder, inst_filename)

        # Check if the separated file exists
        if not os.path.exists(inst_filepath):
            return jsonify({'error': 'Audio separation failed, file not found'}), 500
        
        audio_end = time.time()
        audio_time = audio_end - audio_start

        y, sr = librosa.load(inst_filepath)
        audio_duration = librosa.get_duration(y=y, sr=sr)

        return jsonify({
            'base_filename': base_filename,
            'vocals_filename': vocals_filename,
            'inst_filename': inst_filename,
            'separation_time': audio_time,
            'audio_duration': audio_duration
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@separate.route('/api/separate', methods=['POST'])
def upload_file():
    error = False
    if 'file' in request.files:
        file = request.files['file']
        if not(file.filename == ''):
            if file and allowed_file(file.filename):
                filepathname = os.path.join(upload_folder, file.filename)
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
            filepathname = upload_folder + filename
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