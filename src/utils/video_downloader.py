from redvid import Downloader
import os

# Function to extract the title from the URL
def get_title(reddit_url):
    return reddit_url.rstrip("/").split("/")[-1]

# Reddit post URL
URL = "https://www.reddit.com/r/MadeMeSmile/comments/1ixpetf/ngl_this_made_me_smile_and_tear_up/"
TITLE = get_title(URL)

# Define the folder and filename
VIDEO_DIR = f"videos/{TITLE}"
VIDEO_PATH = f"{VIDEO_DIR}/{TITLE}.mp4"

# Create a directory with the title
os.makedirs(VIDEO_DIR, exist_ok=True)

# Initialize RedVid Downloader
reddit = Downloader()
reddit.auto_max = True
reddit.url = URL
reddit.path = VIDEO_DIR  # Save in the new directory
reddit.filename = TITLE  # Save with the extracted title

# Download the video
reddit.download()

print(f"Video saved as: {VIDEO_PATH}")
