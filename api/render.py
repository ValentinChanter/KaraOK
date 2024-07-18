import json
import os
import time
from flask import request, jsonify, Blueprint
from flask_cors import CORS

import numpy as np
import librosa
import pykakasi
from moviepy.editor import TextClip, CompositeVideoClip, AudioFileClip, ColorClip, ImageSequenceClip
from moviepy.video.tools.subtitles import SubtitlesClip

from googletrans import Translator

import unicodedata

render = Blueprint("render", __name__)
CORS(render)  # Enable CORS for cross-origin requests from the Next.js front end
output_folder = 'output/'
tmp_folder = os.path.join(output_folder, 'tmp/')
public_folder = 'public/'
public_output_folder = os.path.join(public_folder, 'output/')

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

def is_kanji(char):
    code_point = ord(char)
    if 0x4E00 <= code_point <= 0x9FFF or \
       0x3400 <= code_point <= 0x4DBF or \
       0x20000 <= code_point <= 0x2A6DF:
        return True
    return False

def split_text_ja(segments):
    i = 0
    new_segments = []
    for segment in segments:
        char_list = list(segment["text"])
        char_list_len = len(char_list)
        begin = 0
        split_index = -1
        
        while char_list_len >= 13:
            split_index += 10
            remove = 10
            while(split_index + 1 < char_list_len and is_kanji(char_list[split_index]) and is_kanji(char_list[split_index+1])):
                split_index += 1
                remove += 1

            if split_index >= char_list_len:
                split_index = char_list_len - 1 
            
            index_last_word = 0
            nb_words_tmp = 0
            for word in segment["words"]:
                nb_words_tmp += len(list(word["text"]))
                if nb_words_tmp >= split_index:
                    break
                index_last_word += 1

            new_segments.append({
                "id": i,
                "seek": segment["seek"],
                "start": segment["words"][begin]["start"],
                "end": segment["words"][index_last_word-1]["end"],
                "text": "".join([w["text"] for w in segment["words"][begin:index_last_word]]),
                "temperature": segment["temperature"],
                "avg_logprob": segment["avg_logprob"],
                "compression_ratio": segment["compression_ratio"],
                "no_speech_prob": segment["no_speech_prob"],
                "confidence": segment["confidence"],
                "words": segment["words"][begin:index_last_word]
            })

            i += 1
            begin = index_last_word
            char_list_len -= remove

        if char_list_len > 0:
            new_segments.append({
                "id": i,
                "seek": segment["seek"],
                "start": segment["words"][begin]["start"],
                "end": segment["end"],
                "text": "".join([w["text"] for w in segment["words"][begin:]]),
                "temperature": segment["temperature"],
                "avg_logprob": segment["avg_logprob"],
                "compression_ratio": segment["compression_ratio"],
                "no_speech_prob": segment["no_speech_prob"],
                "confidence": segment["confidence"],
                "words": segment["words"][begin:]
            })

            i += 1

    return new_segments

def split_text_spaces_1_ja(segments):
    new_segments = []
    id = 0 

    for segment in segments:

        words = segment["words"]
        contains_space = False

        for word in words:
            if word["text"] == ' ':
                contains_space = True
                break

        if contains_space:
    
            current_words = []
            current_words_tmp = []
            space_nb = 0
            
            for word in words:
                if(word["text"] != ' '):
                    current_words_tmp.append(word)
                else:
                    current_words.append(current_words_tmp)
                    current_words_tmp = []
                    space_nb += 1
            space_nb += 1
            current_words.append(current_words_tmp)

            i = 0
            for i in range(space_nb):
                new_segments.append({
                    "id": id,
                    "seek": segment["seek"],
                    "start": current_words[i][0]["start"],
                    "end": current_words[i][-1]["end"],
                    "text": "".join([w["text"] for w in current_words[i]]),
                    "temperature": segment["temperature"],
                    "avg_logprob": segment["avg_logprob"],
                    "compression_ratio": segment["compression_ratio"],
                    "no_speech_prob": segment["no_speech_prob"],
                    "confidence": segment["confidence"],
                    "words": current_words[i]
                })
                id += 1
        else:
            new_segments.append(segment)
            id += 1
    return new_segments

def remove_spaces_ja(segments):
    new_segments = []
    
    for segment in segments:

        words = segment["words"]
        new_words = []
        for word in words:
            new_word = word
            new_word["text"] = word["text"].replace(" ", "")
            new_words.append(new_word)

        new_text = segment["text"].replace(" ", "")

        new_segments.append({
            "id": segment["id"],
            "seek": segment["seek"],
            "start": segment["start"],
            "end": segment["end"],
            "text": new_text,
            "temperature": segment["temperature"],
            "avg_logprob": segment["avg_logprob"],
            "compression_ratio": segment["compression_ratio"],
            "no_speech_prob": segment["no_speech_prob"],
            "confidence": segment["confidence"],
            "words": new_words
        })
    
    return new_segments

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
            while orig[-1] == hira[-1]:
                orig = orig[:-1]
                hira = hira[:-1]
            kanji_list.append(orig)
            furigana_list.append(hira)

    return [kanji_list, furigana_list]

# Utility to create a dictionary for the blue rectangle movement
def generate_blue_rectangle_movement_dict(old_x, new_x, start, end):
    return {
        "start": float(start),
        "end": float(end),
        "old_x": old_x,
        "new_x": new_x
    }

def render_blue_rectangle(rect_dict_list, base_position, duration, fps, video_size, font_height=80):
    frames = []
    current_dict_index = 0
    for i in range(int(duration * fps)):
        start = rect_dict_list[current_dict_index]["start"]
        end = rect_dict_list[current_dict_index]["end"]
        old_x = rect_dict_list[current_dict_index]["old_x"]
        new_x = rect_dict_list[current_dict_index]["new_x"]
        is_last = current_dict_index == len(rect_dict_list) - 1

        curr_time = i / float(fps)

        if curr_time >= end and not is_last:
            current_dict_index += 1

        # If the frame is within the current segment, interpolate the x position between the old and new x
        if start <= curr_time <= end:
            x = np.interp(curr_time, [start, end], [old_x, new_x])
        # If the frame is between a start and end, set x to latest new_x
        elif current_dict_index > 0:
            x = rect_dict_list[current_dict_index - (0 if is_last else 1)]["new_x"]
        # If the frame is at the beginning of the video, set x to 0
        else:
            x = 0

        # Fill the frame with the blue rectangle from x = base_pos[0] to x = the calculated position and y = base_position[1] to y = base_position[1] + font_height
        frame = np.zeros((video_size[1], video_size[0], 3), dtype=np.uint8)
        frame[base_position[1] - font_height // 2:base_position[1] + font_height, base_position[0]:int(x)] = [0, 0, 255]
        frames.append(frame)

    return frames

@render.route('/api/render', methods=['POST'])
def render_audio():
    alphabet = request.form.get('alphabet')
    translation_lang = request.form.get('translation')
    base_filename = request.form.get('base_filename')
    inst_filename = request.form.get('inst_filename')
    inst_filepath = os.path.join(tmp_folder, inst_filename)

    transcription_filename = request.form.get('transcription')
    transcription_filepath = os.path.join(tmp_folder, transcription_filename)

    try:
        video_start = time.time()
        with open(transcription_filepath, 'r', encoding="utf-8") as f:
            transcription_result = json.load(f)

        y, sr = librosa.load(inst_filepath)
        audio_duration = librosa.get_duration(y=y, sr=sr)

        fps = 24
        video_size = (1280, 720)

        lang = transcription_result["language"]
        is_latin = lang == "en" or lang == "es" or lang == "fr" or lang == "de" or lang == "it" or lang == "pt"

        # Font name (monospace)
        font = 'Consolas'
        font_translated = 'Meiryo-&-Meiryo-Italic-&-Meiryo-UI-&-Meiryo-UI-Italic'
        if lang == "ja" and alphabet == "kanjitokana":
            font = 'Meiryo-&-Meiryo-Italic-&-Meiryo-UI-&-Meiryo-UI-Italic'
        font_size = 60 if lang == "ja" and alphabet == "kanjitokana" else 50
        font_size_translated = 40
        char_font_size = font_size if lang == "ja" and alphabet == "kanjitokana" else font_size * 34 / 60
        font_height = 80
        spaces_between_kana = 3

        left_margin = 100
        base_position = (left_margin, video_size[1] // 2)
        kanji_list = []
        furigana_list = []

        segments = transcription_result['segments']

        if lang == "ja":
            segments = split_text_spaces_1_ja(segments)
            segments = remove_spaces_ja(segments)
            segments = split_text_ja(segments)
            if alphabet == "kanjitokana":
                kanji_list, furigana_list = get_furigana_mapping(transcription_result["text"])
            if alphabet == "romaji":
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
                    # Fix this by creat""ing a romaji mapping through furigana mapping and converting furigana to romaji (can limit it to words that are more than 2 kanji long)

        # Split big sentences in latin languages
        if is_latin:
            segments = split_text(segments, lang)

        #Format the transcription into a list like [((ta,tb),'some text'),...]
        subs = [((0, segments[0]['start']), "[pause]")]
        furiganas = [((0, segments[0]['start']), "[pause]")] if lang == "ja" and alphabet == "kanjitokana" else []
        next_line = []

        doTranslation = translation_lang != "null" and translation_lang != lang
        translatedSubs = []
        if(doTranslation):
            translatedSubs.append(((0, segments[0]['start']), "[pause]"))
        translator = Translator()

        for i, segment in enumerate(segments):
            start = segment['start']
            end = segment['end']
            text = segment['text']
            prev_start = 0
            prev_end = 0
            next_start = segments[segments.index(segment) + 1]['start'] if segment != segments[-1] else audio_duration
            corrected_end = end + 3 if next_start - end >= 3 else next_start

            subs.append(((start, corrected_end), text))

            if doTranslation:
                translatedSubs.append(((start, corrected_end), translator.translate(text, dest=translation_lang).text))

            if i > 0:
                prev_start = segments[i - 1]['start']
                prev_end = segments[i - 1]['end']
                next_line.append(((prev_start, start if start - prev_end < 5 else prev_end + 5), text))
            
            # Also append an empty text from end to start of next subtitle (or end of song if it is the last one) to hide blue rectangle
            subs.append(((corrected_end, next_start), "[pause]"))
            if lang == "ja" and alphabet == "kanjitokana":
                furiganas.append(((corrected_end, next_start), "[pause]"))
        
        blue_rect_x_pos = 0
        blue_rectangle_dict_list = []
        mapping_index = 0
        # For every line, calculate blue rectangle position and populate furiganas
        for i, segment in enumerate(segments):
            start = segment['start']
            end = segment['end']
            text = segment['text']

            # Set blue rectangle back to the left at the beginning of each segment
            blue_rect_x_pos = base_position[0]

            next_segment_exists = i < len(segments) - 1
            next_segment = None
            duration_before_next = 0
            if next_segment_exists:
                next_segment = segments[i + 1]
                duration_before_next = next_segment['start'] - end

            # Change end to start of next segment if it's too close, otherwise add 3 seconds
            if next_segment_exists and duration_before_next < 3:
                end = next_segment['start']
            else:
                end += 3

            # Calculate blue rectangle position
            words = segment['words']
            for j, word in enumerate(words):
                word_start = word['start']
                word_end = word['end']
                word_length = len(word['text'])
                
                new_x = blue_rect_x_pos + word_length * char_font_size * (1 if lang == "ja" and alphabet == "kanjitokana" else 1) # TODO: Fix latin characters rectangle speed
                new_pos = generate_blue_rectangle_movement_dict(blue_rect_x_pos, new_x, word_start, word_end)
                blue_rectangle_dict_list.append(new_pos)
                blue_rect_x_pos = new_x

            # Add furiganas to list if there are in current line of lyrics
            if lang == "ja" and alphabet == "kanjitokana":
                line_furiganas = ""
                spaces_to_remove = 0
                chars_to_skip = 0
                for i, char in enumerate(text):
                    if(mapping_index >= len(kanji_list) or mapping_index >= len(furigana_list)):
                        break
                    if chars_to_skip == 0 and 0x4E00 <= ord(char) <= 0x9FBF:
                        line_furiganas += furigana_list[mapping_index]

                        chars_to_skip = len(kanji_list[mapping_index]) - 1
                        spaces_to_remove += len(furigana_list[mapping_index]) - 2

                        if spaces_to_remove < 0:
                            line_furiganas += " " * (spaces_between_kana * abs(spaces_to_remove))
                            
                            spaces_to_remove = 0

                        mapping_index += 1

                    else:
                        if chars_to_skip > 0:
                            chars_to_skip -= 1

                        spaces_to_add = 2 - spaces_to_remove
                        if spaces_to_add > 0:
                            line_furiganas += " " * (spaces_between_kana * spaces_to_add)
                            if spaces_to_remove > 0:
                                spaces_to_remove = 0
                        elif spaces_to_remove >= 2:
                            spaces_to_remove -= 2

                furiganas.append(((start, end), line_furiganas))

        # Create the subtitles
        subs_generator = lambda txt: TextClip(txt, font=font, fontsize=font_size, color='white', stroke_color=('white' if txt == "[pause]" else 'black'), stroke_width=2.5, size=(video_size[0] - base_position[0], font_height), align='West', method='caption', bg_color='white')
        subtitles = SubtitlesClip(subs, subs_generator).to_mask()

        # Create the next subtitles
        next_subs = lambda txt: TextClip(txt, font=font, fontsize=font_size, color='white', stroke_color='black', stroke_width=2.5, size=(video_size[0] - base_position[0] + font_height, font_height), align='West', method='caption', bg_color='white')
        next_subtitles = SubtitlesClip(next_line, next_subs).set_position((base_position[0] + font_height, base_position[1] + 80))

        # Create translated subtitles
        translated_subtitles = None
        if doTranslation:
            translated_subs_generator = lambda txt: TextClip(txt, font=font_translated, fontsize=font_size_translated, color='white', stroke_color=('white' if txt == "[pause]" else 'black'), stroke_width=1.5, align='West', method='label', bg_color='white')
            translated_subtitles = SubtitlesClip(translatedSubs, translated_subs_generator).set_position(("center", "top"))

        # Create the furigana subtitles
        if lang == "ja" and alphabet == "kanjitokana":
            furi_generator = lambda txt: TextClip(txt, font=font, fontsize=font_size // 2, color='white', stroke_color=('white' if txt == "[pause]" else 'black'), stroke_width=1.25, size=(video_size[0] - base_position[0], font_height // 2), align='West', method='caption', bg_color='white')
            furigana_subtitles = SubtitlesClip(furiganas, furi_generator).to_mask()

        # Black background displayed behind the blue rectangle
        black_background = ColorClip(video_size, color=(0, 0, 0)).set_duration(audio_duration)

        # Render blue rectangle
        blue_rect_frames = render_blue_rectangle(blue_rectangle_dict_list, base_position, audio_duration, fps, video_size, font_height)
        blue_rect = ImageSequenceClip(blue_rect_frames, fps=fps)

        # Apply mask to white rectangle
        white_rect = ColorClip(video_size, color=(255, 255, 255)).set_duration(audio_duration)
        white_rect_with_subs = white_rect.set_mask(subtitles).set_position(base_position)
        if lang == "ja" and alphabet == "kanjitokana":
            white_rect_with_furigana = white_rect.set_mask(furigana_subtitles).set_position((base_position[0], base_position[1] - font_height // 2))

        # Draw white rectangles to mask the blue rectangle
        top_white_rect = ColorClip((video_size[0], video_size[1] // 2 - (font_height // 2 if lang == "ja" and alphabet == "kanjitokana" else 0)), color=(255, 255, 255)).set_duration(audio_duration)
        left_white_rect = ColorClip((left_margin, font_height + font_height // 2), color=(255, 255, 255)).set_duration(audio_duration).set_position((0, video_size[1] // 2 - font_height // 2))
        bottom_white_rect = ColorClip((video_size[0], video_size[1] // 2 - font_height), color=(255, 255, 255)).set_duration(audio_duration).set_position((0, video_size[1] // 2 + font_height))

        # Load audio file
        audio = AudioFileClip(inst_filepath)
        clips = [black_background, blue_rect, white_rect_with_subs]
        
        if lang == "ja" and alphabet == "kanjitokana":
            clips.append(white_rect_with_furigana)
        
        clips += [top_white_rect, left_white_rect, bottom_white_rect, next_subtitles]

        if translated_subtitles != None:
            clips.append(translated_subtitles)
            
        final_video = CompositeVideoClip(clips, size=video_size).set_duration(audio_duration).set_audio(audio)

        # Save the final video
        video_filename = f"{base_filename}.mp4"
        video_filepath = os.path.join(output_folder, video_filename)
        public_video_filepath = os.path.join(public_folder, video_filepath)
        final_video.write_videofile(public_video_filepath, fps=fps)

        video_end = time.time()

        return jsonify({
            'video': video_filepath,
            'render_time': video_end - video_start
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500