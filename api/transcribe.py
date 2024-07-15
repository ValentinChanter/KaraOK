import os
import time
import json
from flask import request, jsonify, Blueprint
from flask_cors import CORS
import torch

import whisper_timestamped as whisper

# Libraries WER calculation
import asyncio
from shazamio import Shazam
from lyricsgenius import Genius
from jiwer import wer
import cutlet

transcribe = Blueprint("transcribe", __name__)
CORS(transcribe)  # Enable CORS for cross-origin requests from the Next.js front end
output_folder = 'output/'
tmp_folder = os.path.join(output_folder, 'tmp/')

async def get_and_compare_lyrics(filename, hypothesis, lang):
    shazam = Shazam()
    song = await shazam.recognize(filename)
    song_title = song.get("track", {}).get("title")
    song_artist = song.get("track", {}).get("subtitle")

    genius = Genius("asn_VTCc9Oa_Xz50SJC4zMg4W7w4uwpG9ZNxkvDgiGkKC_pz1muLiwPIHq2fshCa")
    genius.verbose = False
    genius.remove_section_headers = True
    genius.skip_non_songs = False
    genius.excluded_terms = ["(Remix)", "(Live)"]
    song = genius.search_song(song_title, song_artist)
    lyrics = song.lyrics
    lyrics = lyrics.replace("You might also like", " ")
    lyrics = lyrics.replace("5Embed", " ")
    lyrics = '\n'.join(lyrics.split('\n')[1:])

    lyrics = lyrics.replace("\n", " ").replace("?", " ").replace("!", " ").replace(".", " ").replace(",", " ").replace("(", " ").replace(")", " ").replace("[", " ").replace("]", " ").replace("{", " ").replace("}", " ").replace(":", " ").replace(";", " ").replace("-", " ").replace("—", " ")
    lyrics = lyrics.lower()

    hypothesis = hypothesis.replace("\n", " ").replace("?", " ").replace("!", " ").replace(".", " ").replace(",", " ").replace("(", " ").replace(")", " ").replace("[", " ").replace("]", " ").replace("{", " ").replace("}", " ").replace(":", " ").replace(";", " ").replace("-", " ").replace("—", " ")
    hypothesis = hypothesis.lower()

    try:
        if lang == "ja":
            katsu = cutlet.Cutlet()
            lyrics = katsu.romaji(lyrics, False, False)
            hypothesis = katsu.romaji(hypothesis, False, False)
    except Exception as e:
        print(f"Error in romaji conversion: {e}")

    error = wer(lyrics, hypothesis)
    print(f"WER: {error:.2f}")

def compare_lyrics(filename, hypothesis, lang):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(get_and_compare_lyrics(filename, hypothesis, lang))

@transcribe.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    vocals_filename = request.form.get('vocals_filename')
    vocals_filepath = os.path.join(tmp_folder, vocals_filename)

    try:
        transc_start = time.time()
        audio = whisper.load_audio(vocals_filepath)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        whisper_model = whisper.load_model("medium", device=device)

        transcription_result = whisper.transcribe_timestamped(whisper_model, audio)
        transcription_filename = f"{request.form.get('base_filename')}.json"
        transcription_path = os.path.join(tmp_folder, transcription_filename)
        with open(transcription_path, "w") as f:
            json.dump(transcription_result, f)

        transc_end = time.time()
        transc_time = transc_end - transc_start

        # WER calculation (optional)
        # compare_lyrics(filename, transcription_result["text"], transcription_result["language"])

        return jsonify({
            'transcription': transcription_filename,
            'transc_time': transc_time
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500