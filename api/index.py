from flask import Flask, request, jsonify
import os
from audio_separator.separator import Separator
from flask_cors import CORS
import whisper_timestamped as whisper
import torch
import librosa
import pykakasi
from moviepy.editor import TextClip, CompositeVideoClip, AudioFileClip
import requests
import re
import time
import yt_dlp
import json # For debug inputs

import asyncio
from shazamio import Shazam
from lyricsgenius import Genius
from jiwer import wer
import cutlet

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests from the Next.js front end
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['OUTPUT_FOLDER'] = 'output/'
app.config['TMP_FOLDER'] = 'output/tmp/'
app.config['ALLOWED_EXTENSIONS'] = {'mp3', 'wav'}

# Function to check if the file extension is allowed
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

###### Functions for video rendering ######
# Takes a word containing kanjis and returns a list of list: the first list are kanjis and the second are associated furiganas
# Done by scraping jisho.org
def get_furigana_from_jisho(word):
    furiganas = []
    
    # Isolate kanjis (between 4E00 and 9FBF)
    kanjis = [c for c in word if 0x4E00 <= ord(c) <= 0x9FBF]

    try:
        r = requests.get('https://jisho.org/search/' + word)
        html = r.text

        # Get first text between <span class="furigana"> and </span>
        first_entry_and_more = html.split('<span class="furigana">')[1]
        first_entry = re.split(r'</span>\s+?<span class="text">', first_entry_and_more)[0]

        # Get all text between <span class="kanji-X-up kanji"> and </span>
        furiganas = [x.split('</span>')[0] for x in re.split(r'<span class="kanji-\d+-up kanji">', first_entry) if '</span>' in x]
    except:
        pass
    
    return [kanjis, furiganas]

# Function to create 2 lists, one with the kanji and one with the furigana. They're matched by index.
def get_furigana_mapping(text):
    # Initialize kakasi for kanji to furigana conversion
    kks = pykakasi.kakasi()

    kanji_list = []
    furigana_list = []
    result = kks.convert(text)

    for item in result:
        orig = item['orig']
        kata = item['kana']
        hira = item['hira']
        if orig != hira and orig != kata:
            kanji_count = 0
            for c in orig:
                if 0x4E00 <= ord(c) <= 0x9FBF:
                    kanji_count += 1

            if kanji_count == 1:
                while orig[-1] == hira[-1]:
                    orig = orig[:-1]
                    hira = hira[:-1]
                kanji_list.append(orig)
                furigana_list.append(hira)

                continue
            
            res_map = get_furigana_from_jisho(orig)

            if len(res_map[1]) == 0:
                # Fallback method if jisho.org is not available (less accurate)
                while orig[-1] == hira[-1]:
                    orig = orig[:-1]
                    hira = hira[:-1]
                kanji_list.append(orig)
                furigana_list.append(hira)
            else:
                kanji_list.extend(res_map[0])
                furigana_list.extend(res_map[1])

    return [kanji_list, furigana_list]

# Helper function to create text clips with furigana, also returns how many furigana translations were used
def create_text_clip(text, start_time, end_time, color='black', fontsize=60, furigana=None, position=(0, 0), font='Meiryo-&-Meiryo-Italic-&-Meiryo-UI-&-Meiryo-UI-Italic'):
    text_clip = TextClip(text, fontsize=fontsize, color=color, font=font)
    text_clip = text_clip.set_start(start_time).set_end(end_time).set_position(position)

    furigana_clips = []
    
    if furigana:
        kanji_list, furigana_list = furigana
        for i in range(len(kanji_list)):
            if i >= len(text):
                break

            furi = ""
            kanji_pos = text.find(kanji_list[i])

            if kanji_pos == -1:
                continue

            furi = furigana_list[i]

            furi_clip = TextClip(furi, fontsize=fontsize//2, color=color, font=font)
            furi_clip = furi_clip.set_start(start_time).set_end(end_time)
            furigana_clips.append(furi_clip.set_position((position[0] + kanji_pos * fontsize, position[1] - fontsize // 2)))

        return [[text_clip] + furigana_clips, len(furigana_clips)]
    
    return [[text_clip], 0]

# Function to split big sentences in latin languages
def split_text(segments, lang):
    new_segments = []
    i = 0
    for segment in segments:
        curr_words = [segment["words"][0]]
        word_count = 0
        j = 0
        for word in segment["words"][1:]:
            first_char = word["text"][0]
            word_count += 1
            j += 1
            if (lang != "en" and first_char.isupper() or lang == "en" and first_char.isupper() and first_char != "I") or (word_count > 4 and len(segment["words"][j:]) > 2):
                new_segments.append({
                    "id": i,
                    "seek": segment["seek"],
                    "start": curr_words[0]["start"],
                    "end": curr_words[-1]["end"],
                    "text": " ".join([w["text"] for w in curr_words]),
                    "temperature": segment["temperature"],
                    "avg_logprob": segment["avg_logprob"],
                    "compression_ratio": segment["compression_ratio"],
                    "no_speech_prob": segment["no_speech_prob"],
                    "confidence": segment["confidence"],
                    "words": curr_words
                })
                curr_words = [word]
                word_count = 1
                i += 1
            else:
                curr_words.append(word)
        new_segments.append({
            "id": i,
            "seek": segment["seek"],
            "start": curr_words[0]["start"],
            "end": curr_words[-1]["end"],
            "text": " ".join([w["text"] for w in curr_words]),
            "temperature": segment["temperature"],
            "avg_logprob": segment["avg_logprob"],
            "compression_ratio": segment["compression_ratio"],
            "no_speech_prob": segment["no_speech_prob"],
            "confidence": segment["confidence"],
            "words": curr_words
        })

    return new_segments

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

# Main function to create the video
def create_video(filename):

    alphabet = request.form.get('alphabet')
    
    base_filename = os.path.splitext(filename)[0]
    filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Get parameters from the form
    model_filename = request.form.get('model_filename')

    try:
        audio_start = time.time()
        # Perform audio separation
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

        # Load audio for Whisper
        transc_start = time.time()
        audio = whisper.load_audio(vocals_filepath)

        # Load Whisper model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        whisper_model = whisper.load_model("medium", device=device)

        # Perform transcription
        transcription_result = whisper.transcribe_timestamped(whisper_model, audio)
        transc_end = time.time()

        ###### Video rendering ######
        """
        # Debug inputs to avoid running the audio separation and transcription: comment after the try: until right above the video rendering
        inst_filepath = "output/tmp/inst.wav"
        vocals_filepath = "output/tmp/voc.wav"
        with open("output/tmp/audio.json", "r", encoding="utf-8") as f:
            transcription_result = json.load(f)
        """

        compare_lyrics(filename, transcription_result["text"], transcription_result["language"])

        video_start = time.time()

        y, sr = librosa.load(inst_filepath)
        audio_duration = librosa.get_duration(y=y, sr=sr)
        
        # Video properties
        fps = 24
        video_size = (1280, 720)  # HD resolution

        # Font name
        font = 'Meiryo-&-Meiryo-Italic-&-Meiryo-UI-&-Meiryo-UI-Italic'

        # Detected language
        lang = transcription_result["language"]
        is_latin = lang == "en" or lang == "es" or lang == "fr" or lang == "de" or lang == "it" or lang == "pt"

        # Add text clips based on the segments
        text_clips = []
        last_end = 0
        base_position = (100, video_size[1] // 2)

        segments = transcription_result['segments']

        # Idea: adjust text to contain leading kanji of next text if they're meant to be read together
        # For japanese songs, create furigana mapping for the entire text or replace the text with romaji, depending on user input
        furigana_mapping = None
        if lang == "ja":
            if alphabet == "kanjitokana":
                lyrics = transcription_result["text"]
                furigana_mapping = get_furigana_mapping(lyrics)
            else:
                kks = pykakasi.kakasi()
                for segment in segments:
                    result = kks.convert(segment["text"])
                    text_list = [item["hepburn"] for item in result]
                    tr_text_without_spaces = "".join(text_list)

                    acc_text = []
                    acc_start = 0
                    words = []
                    for i, w in enumerate(segment["words"]):
                        curr_word = ""
                        for j, c in enumerate(w["text"]):
                            acc_res = kks.convert("".join(acc_text) + c)
                            curr_res = kks.convert(c)
                            acc_romaji = acc_res[0]["hepburn"]
                            curr_romaji = curr_res[0]["hepburn"]

                            already_appended = False

                            if tr_text_without_spaces.startswith(acc_romaji):
                                tr_text_without_spaces = tr_text_without_spaces[len(acc_romaji):]

                                if len(acc_text) > 0:
                                    if 0x4E00 <= ord(c) <= 0x9FBF: # If word with multiple kanjis
                                        words.append({
                                            "start": acc_start,
                                            "end": w["end"],
                                            "text": acc_romaji,
                                            "confidence": w["confidence"],
                                        })

                                        already_appended = True
                                    else:
                                        words.append({
                                            "start": acc_start,
                                            "end": w["start"],
                                            "text": acc_romaji.split(curr_romaji)[0],
                                            "confidence": w["confidence"],
                                        })

                                    acc_text = []
                                
                                if j == len(w["text"]) - 1 and not already_appended: # If last character of word and not already appended
                                    words.append({
                                        "start": w["start"],
                                        "end": w["end"],
                                        "text": curr_word + curr_romaji,
                                        "confidence": w["confidence"],
                                    })

                                else:
                                    curr_word += curr_romaji

                                acc_text = []
                            else:
                                if len(acc_text) == 0:
                                    acc_start = w["start"]
                                acc_text.append(c)

                    segment["text"] = "".join(text_list)
                    segment["words"] = words

                    # Using this method, single kanji read differently when paired with another kanji will be read differently.
                    # Fix this by creating a romaji mapping through furigana mapping and converting furigana to romaji (can limit it to words that are more than 2 kanji long)

        # Split big sentences in latin languages
        if is_latin:
            segments = split_text(segments, lang)

        for i, segment in enumerate(segments):
            start = segment['start']
            end = segment['end']
            text = segment['text']

            next_segment_exists = i < len(segments) - 1
            next_segment = None
            duration_before_next = 0
            if next_segment_exists:
                next_segment = segments[i + 1]
                duration_before_next = next_segment['start'] - end

            furigana_use_count = 0
            
            # Create progressive text clips
            words = segment['words']
            current_text = ""
            x_offset = base_position[0]
            y_position = base_position[1]
            for j, word in enumerate(words):
                word_start = word['start']
                word_end = word['end']
                next_text = word['text']
                current_text += next_text + (" " if is_latin else "")
                remaining_text = text[len(current_text):]
                
                # Calculate position based on character count
                blue_text_end = word_end if remaining_text else (next_segment['start'] if next_segment_exists and duration_before_next < 3 else end + 3)
                blue_array = create_text_clip(current_text, word_start, blue_text_end, color='blue', furigana=furigana_mapping, position=base_position)
                blue_text_clip = blue_array[0]
                blue_count = blue_array[1]
                text_clips.extend(blue_text_clip)
                furigana_use_count += blue_count
                
                current_text_width = blue_text_clip[0].size[0]
                x_offset = base_position[0] + current_text_width

                if remaining_text:
                    black_array = create_text_clip(remaining_text, word_start, word_end, color='black', furigana=furigana_mapping, position=(x_offset, y_position))
                    black_text_clip = black_array[0]
                    black_count = black_array[1]
                    text_clips.extend(black_text_clip)
                    furigana_use_count += black_count

            # Check for break longer than 5 seconds
            if i == 0 or start - last_end > 5:
                fade_clip = TextClip(text, fontsize=60, color='black', font=font).set_start(start-1).set_end(start)
                fade_clip = fade_clip.crossfadein(start if start < 1 else 1).set_position((base_position[0], y_position))
                text_clips.append(fade_clip)
            
            # Display next line of lyrics under current line if less than 5 seconds away
            if next_segment_exists and duration_before_next < 5:
                next_array = create_text_clip(next_segment['text'], start, next_segment['start'], fontsize=40, position=(base_position[0] + 80, y_position + 80))  # Adjusted position
                next_text_clip = next_array[0]
                text_clips.extend(next_text_clip)

            # Remove kanji encountered in current segment from the mapping
            if lang == "ja" and alphabet == "kanjitokana" and furigana_mapping and furigana_use_count > 0:
                furigana_use_count /= len(words)
                furigana_use_count = round(furigana_use_count)
                furigana_mapping[0] = furigana_mapping[0][furigana_use_count:]
                furigana_mapping[1] = furigana_mapping[1][furigana_use_count:]
            
            last_end = end

        # Combine text clips with the video
        # Load audio file
        audio = AudioFileClip(inst_filepath)
        final_video = CompositeVideoClip(text_clips, size=video_size, bg_color=(255, 255, 255)).set_duration(audio_duration).set_audio(audio)

        # Save the final video
        video_filename = f"{base_filename}.mp4"
        video_filepath = os.path.join(app.config['OUTPUT_FOLDER'], video_filename)
        final_video.write_videofile(video_filepath, fps=fps)

        video_end = time.time()

        # Remove tmp files (vocals and instrumental)
        os.remove(inst_filepath)
        os.remove(vocals_filepath)

        # Upload the final video
        return jsonify({
            'message': 'File successfully processed.\nAudio separation time: {:.2f}s\nTranscription time: {:.2f}s\nVideo rendering time: {:.2f}s'.format(audio_end - audio_start, transc_end - transc_start, video_end - video_start),
            'video_file': video_filepath
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def main():

    error = False
    if not('file' not in request.files):
        file = request.files['file']
        if not(file.filename == ''):
            if file and allowed_file(file.filename):
                filepathname = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepathname)

                create_video(file.filename)
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

            create_video(filename)
        else:
            error = True
    else:
        error = True

    if error:
        return jsonify({'error': 'Error in music link or file in the request'}), 400
    
    return jsonify({'message': 'File successfully uploaded'}), 200

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TMP_FOLDER'], exist_ok=True)
    app.run(debug=True)
