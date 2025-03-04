import os 
import cv2
import re
import numpy as np
import whisper_timestamped
import ffmpeg
import time
from kokoro_onnx import Kokoro
import soundfile as sf
import warnings
import random
from PIL import ImageFont, ImageDraw, Image, ImageFilter

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

class VideoProcessor:
    def __init__(self):
        pass

    def process_video(input_video, title, text1, text2=None, text_position="bottom", song="default", video_volume=0.2):
        # === Constants ===
        TEXT_POSITION = {"top": 0.75, "middle": 1, "bottom": 1.25}

        kokoro = Kokoro("src/assets/onnx-voices/kokoro-v1.0.onnx", "src/assets/onnx-voices/voices-v1.0.bin")
        FONT_PATH = "src/assets/fonts/OpenSans-Bold.ttf"
        FONT_SIZE = 95
        OUTLINE_SIZE = 5
        VOICE_SPEED = 1.10
        WHISPER_MODEL = "large-v3"
        VOICE_BLEND = {"am_echo": 10, "am_liam": 90}
        TEXT_COLORS = [
            (255, 255, 255),
            (255, 255, 255),
            (255, 255, 255),
            (255, 255, 20),
        ]

        SONG_MOOD = {
            "ambient": "src/assets/songs/ambient",
            "cool": "src/assets/songs/cool",
            "curious": "src/assets/songs/curious",
            "mysterious": "src/assets/songs/mysterious",
            "playful": "src/assets/songs/playful",
        }

        # Get the folder path for the selected mood
        song_folder = SONG_MOOD.get(song, SONG_MOOD["ambient"])  # Default to "ambient" if not found

        # List all .wav files in the folder
        try:
            wav_files = [f for f in os.listdir(song_folder) if f.endswith('.wav')]
            if not wav_files:
                raise FileNotFoundError("No .wav files found in the selected song folder.")

            # Select a random song
            selected_song = random.choice(wav_files)
            selected_song_path = os.path.join(song_folder, selected_song)

        except FileNotFoundError as e:
            print(f"Error: {e}")
            selected_song_path = None  # Handle error gracefully

        print(f"Selected song: {selected_song_path}")  # Debugging output
        
        # Get the directory of the input video
        input_video_dir = os.path.dirname(input_video)

        # Set the output paths for audio files in the same directory as the input video
        AUDIO_OUTPUT_1 = os.path.join(input_video_dir, "voice1.wav")
        AUDIO_OUTPUT_2 = os.path.join(input_video_dir, "voice2.wav")

        TEMP_VIDEO = os.path.join(input_video_dir, "temp_video.avi")
        
        print(f"[✔] Generating speech")
        # === Step 1: Generate Speech ===
        def generate_speech(text, output_file):
            v1 = kokoro.get_voice_style("am_echo")
            v2 = kokoro.get_voice_style("am_liam")
            blend = np.add(v1 * (VOICE_BLEND["am_echo"] / 100), v2 * (VOICE_BLEND["am_liam"] / 100))
            samples, sample_rate = kokoro.create(text, voice=blend, speed=VOICE_SPEED, lang="en-us")
            sf.write(output_file, samples, sample_rate)
            return output_file

        generate_speech(text1, AUDIO_OUTPUT_1)
        use_text2 = bool(text2)
        if use_text2:
            generate_speech(text2, AUDIO_OUTPUT_2)

        # === Step 2: Get Video Duration ===
        probe = ffmpeg.probe(input_video)
        video_duration = float(next(s for s in probe["streams"] if s["codec_type"] == "video")["duration"])
        audio_duration_1 = float(ffmpeg.probe(AUDIO_OUTPUT_1)["streams"][0]["duration"])

        if use_text2:
            start_time_2 = max(video_duration - float(ffmpeg.probe(AUDIO_OUTPUT_2)["streams"][0]["duration"]) - 0.2, audio_duration_1 + 0.5)
        else:
            start_time_2 = None

        print(f"[✔] Extracting timestamps")
        # === Step 3: Extract Word Timestamps ===
        model = whisper_timestamped.load_model(WHISPER_MODEL)
        
        def get_word_timestamps(audio_file):
            try:
                result = model.transcribe(audio_file, word_timestamps=True)
                return result["segments"]
            except Exception as e:
                print(f"Whisper error: {e}")
                return []

        timestamps_1 = get_word_timestamps(AUDIO_OUTPUT_1)
        
        def remove_punctuation(text):
            return re.sub(r'[^a-zA-Z\s]', '', text)

        word_objects_1 = [
            {"text": remove_punctuation(word["word"]).lower(), "start": word["start"], "end": word["end"], "color": random.choice(TEXT_COLORS)}
            for segment in timestamps_1 for word in segment["words"]
        ]

        if use_text2:
            timestamps_2 = get_word_timestamps(AUDIO_OUTPUT_2)
            word_objects_2 = [
                {"text": remove_punctuation(word["word"]).lower(), "start": word["start"] + start_time_2, "end": word["end"] + start_time_2, "color": random.choice(TEXT_COLORS)}
                for segment in timestamps_2 for word in segment["words"]
            ]
        else:
            word_objects_2 = []

        print(f"[✔] Processing text overlay")
        # === Step 4: Process Video with Text Overlay ===
        cap = cv2.VideoCapture(input_video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_width, frame_height = int(cap.get(3)), int(cap.get(4))
        mobile_width, mobile_height = 1080, 1920

        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        out = cv2.VideoWriter(TEMP_VIDEO, fourcc, fps, (mobile_width, mobile_height))

        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            current_time = frame_count / fps
            frame_count += 1

            # Background Blur Effect
            blurred_bg = cv2.GaussianBlur(frame, (99, 99), 50)
            blurred_bg = cv2.resize(blurred_bg, (mobile_width, mobile_height))

            # Resized main video
            video_scale = min(mobile_width / frame_width, mobile_height / frame_height)
            new_width, new_height = int(frame_width * video_scale), int(frame_height * video_scale)
            resized_frame = cv2.resize(frame, (new_width, new_height))

            # Composite Background & Foreground
            y_video, x_video = (mobile_height - new_height) // 2, (mobile_width - new_width) // 2
            canvas = blurred_bg.copy()
            canvas[y_video:y_video + new_height, x_video:x_video + new_width] = resized_frame
            pil_img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)

            def draw_text(word_objects, position):
                upscale_factor = 1  # Higher resolution for sharp text rendering
                text_layer = Image.new("RGBA", (mobile_width * upscale_factor, mobile_height * upscale_factor), (0, 0, 0, 0))
                text_draw = ImageDraw.Draw(text_layer)

                # Get the most recent active word (ensuring only one word is displayed at a time)
                active_word = None
                for word in word_objects:
                    if word["start"] <= current_time <= word["end"]:
                        active_word = word
                        break  # Stop at the first word that matches

                if not active_word:
                    return  # No word to display, skip frame rendering

                # Prepare text rendering
                font_scaled = ImageFont.truetype(FONT_PATH, int(FONT_SIZE * upscale_factor))
                bbox = text_draw.textbbox((0, 0), active_word["text"], font=font_scaled)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                final_x = (mobile_width * upscale_factor - text_width) // 2
                final_y = (int(mobile_height * position // 2)) * upscale_factor

                # Outline for better readability
                for dx in range(-OUTLINE_SIZE * upscale_factor, OUTLINE_SIZE * upscale_factor + 1, upscale_factor):
                    for dy in range(-OUTLINE_SIZE * upscale_factor, OUTLINE_SIZE * upscale_factor + 1, upscale_factor):
                        text_draw.text((final_x + dx, final_y + dy), active_word["text"], font=font_scaled, fill=(0, 0, 0, 255))

                # Main text
                text_draw.text((final_x, final_y), active_word["text"], font=font_scaled, fill=active_word["color"] + (255,))

                # Apply slight Gaussian blur for smooth edges
                text_layer = text_layer.filter(ImageFilter.GaussianBlur(radius=0.2 * upscale_factor))

                # Resize back for crisp rendering
                text_layer = text_layer.resize((mobile_width, mobile_height), Image.LANCZOS)

                # Paste onto the main image
                pil_img.paste(text_layer, (0, 0), text_layer)

            draw_text(word_objects_1, TEXT_POSITION[text_position])
            if use_text2:
                draw_text(word_objects_2, TEXT_POSITION[text_position])

            canvas = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            out.write(canvas)

        cap.release()
        out.release()


        # === Step 5: Merge Audio, Video, and Music ===
        print(f"[✔] Merging audio, video, and music")

        # Decrease volume for video audio and normalize
        video_audio = ffmpeg.input(input_video).audio.filter("volume", video_volume)

        # Normalize and boost voice tracks (AUDIO_OUTPUT_1)
        audio_output_1 = (
            ffmpeg.input(AUDIO_OUTPUT_1)
            .filter("loudnorm")  # Normalize audio to standard levels
            .filter("volume", 3.0)  # Boost volume after normalization
            .filter("adelay", '200|200')  # Add delay
        )

        inputs = [video_audio, audio_output_1]

        # Add second voice track if needed
        if use_text2:
            audio_output_2 = (
                ffmpeg.input(AUDIO_OUTPUT_2)
                .filter("loudnorm")  # Normalize second voice
                .filter("volume", 3.0)  # Match volume boost
                .filter("adelay", f"{int(start_time_2 * 1000)}|{int(start_time_2 * 1000)}")
            )
            inputs.append(audio_output_2)

        background_music = ffmpeg.input(selected_song_path).filter("volume", 0.50)  # Keep background music quiet
        inputs.append(background_music)

        # Mix all audio streams and apply final normalization
        mixed_audio = ffmpeg.filter(
            inputs, 
            "amix", 
            inputs=len(inputs), 
            duration="first",
        )  # Final normalization to prevent clipping

        # Apply 60fps frame interpolation to the video
        video_input = ffmpeg.input(TEMP_VIDEO)
        video_interpolated = video_input.filter("minterpolate", fps=45)

        # Generate output video with interpolated frames and mixed audio
        ffmpeg.output(
            video_interpolated,
            mixed_audio,
            input_video_dir + '/video.mp4',
            vcodec="libx264",
            acodec="aac",
            audio_bitrate="192k"
        ).overwrite_output().run()

        # Cleanup temporary files
        os.remove(AUDIO_OUTPUT_1)
        if use_text2:
            os.remove(AUDIO_OUTPUT_2)
        os.remove(TEMP_VIDEO)

        return f"Video saved as: {title}"
