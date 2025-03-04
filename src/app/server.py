from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import ffmpeg
from kokoro_onnx import Kokoro
import os
import soundfile as sf
from redvid import Downloader
import threading
import time

from generate_video import VideoProcessor

app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# Define the dummy file path
DUMMY_FILE_PATH = "src/assets/dummy/dummy_audio.wav"

# POST endpoint to calculate the length of two voices (audio files)
@app.route('/getLength', methods=['POST'])
def get_length():
    try:
        VOICE_SPEED = 1.1
        VOICE_BLEND = {"am_echo": 30, "am_liam": 70}
        
        # Initialize Kokoro with the model
        kokoro = Kokoro("src/assets/onnx-voices/kokoro-v1.0.onnx", "src/assets/onnx-voices/voices-v1.0.bin")
        
        # Retrieve voice1 and voice2 from the request JSON
        data = request.json
        voice1 = data.get('voice1')  # Get voice1 text input
        voice2 = data.get('voice2')  # Get voice2 text input
        
        if not voice1:
            return jsonify({"error": "voice1 required."}), 400
        
        # Load voice styles and blend
        v1 = kokoro.get_voice_style("am_echo")
        v2 = kokoro.get_voice_style("am_liam")
        blend = np.add(v1 * (VOICE_BLEND["am_echo"] / 100), v2 * (VOICE_BLEND["am_liam"] / 100))

        # Generate the speech audio in memory
        samples, sample_rate = kokoro.create(voice1 + " " + voice2, voice=blend, speed=VOICE_SPEED, lang="en-us")
        
        # Save the audio to a dummy file
        sf.write(DUMMY_FILE_PATH, samples, sample_rate)
        # Use ffmpeg to get the duration from the saved audio file
        probe = ffmpeg.probe(DUMMY_FILE_PATH, v='error', select_streams='a', show_entries='stream=duration')
        audio_duration = float(probe['streams'][0]['duration'])

        # Return the total duration as JSON
        return jsonify({"total_length": audio_duration}), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


VIDEO_QUEUE = []  # A queue to keep track of pending tasks

def process_video(video_data):
    """ Function to download and process the video in a separate thread. """
    try:
        title = video_data['title']
        url = video_data['url']
        video_dir = f"videos/new/{title}"
        os.makedirs(video_dir, exist_ok=True)
        
        # Define paths
        video_path = os.path.join(video_dir, f"{title}.mp4")
        metadata_path = os.path.join(video_dir, "metadata.txt")

        # Download video
        reddit = Downloader()
        reddit.auto_max = True
        reddit.url = url
        reddit.path = video_dir
        reddit.filename = title
        reddit.download()

        # Save metadata
        with open(metadata_path, "w") as file:
            file.write(f"Title: {video_data['title']}\n")
            file.write(f"Description: {video_data['description']}\n")
            file.write(f"Voice 1: {video_data['voice1']}\n")
            file.write(f"Voice 2: {video_data['voice2']}\n")
            file.write(f"Caption Position: {video_data['captionPosition']}\n")
            file.write(f"Song: {video_data['song']}\n")
            file.write(f"Tags: {video_data['tags']}\n")
            file.write(f"Voice Length: {video_data['voiceLength']}\n")
            file.write(f"URL: {video_data['url']}\n")
            file.write("\n---\n")  

        print(f"[✔] Video processed: {title}")

        # Now remove the empty redvidTemp folder inside the title directory
        redvid_temp_dir = os.path.join(video_dir, "redvid_temp")
        if os.path.exists(redvid_temp_dir) and os.path.isdir(redvid_temp_dir):
            os.rmdir(redvid_temp_dir)  # Remove the empty folder

        video = VideoProcessor.process_video(video_path, video_data['title'], video_data['voice1'], video_data['voice2'], video_data['captionPosition'], video_data['song'], video_data['volume'])
        print(f"video saved as {video}")
        
    except Exception as e:
        print(f"[❌] Error processing {video_data['title']}: {str(e)}")

def background_worker():
    """ Background worker that processes videos in the queue. """
    while True:
        if VIDEO_QUEUE:
            video_data = VIDEO_QUEUE.pop(0)  # Get the next video task
            process_video(video_data)
        time.sleep(1)  # Prevent CPU overuse

# Start the background worker thread
worker_thread = threading.Thread(target=background_worker, daemon=True)
worker_thread.start()

@app.route('/save', methods=['POST'])
def save_data():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data received"}), 400
        
        # Add task to the queue
        print(f"[✔] Video added to Queue: {data['title']}")
        VIDEO_QUEUE.append(data)

        return jsonify({"message": "Video processing added to queue"}), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)