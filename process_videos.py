import os
import cv2
import subprocess
import json
from PIL import Image
import requests
import glob
import ollama
import base64


with open("fun_facts_output.json", 'r') as file:
    data = json.load(file)

# Access a specific fact
fact1 = data['fun_facts']['fact1']
VIDEO_SCRIPT = fact1['video_script']

FRAME_INTERVAL = 20                   # Extract a frame every 30 seconds
RESOLUTION_FACTOR = 0.2             # Reduce frame resolution by 50%

prompt = (
        "Evaluate if this image is a good fit for the following video script. "
        f"Script: {VIDEO_SCRIPT}\n"
        "Respond with EXACTLY one word: either 'good' or 'bad'. "
        "Use 'good' if the image fits well with the script, 'bad' if it doesn't."
    )

INPUT_VIDEO_DIR = "downloads"  # Directory containing downloaded videos


def extract_frames(video_path, interval):
    """
    Extract frames from a video at a given interval.
    Args:
        video_path (str): Path to the video file.
        interval (int): Interval in seconds between frames.
    Returns:
        List[Dict]: List of frames with their timestamps.
    """
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_interval = fps * interval
    frames = []

    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            timestamp = frame_count // fps
            frames.append({
                "frame": frame,
                "timestamp": timestamp
            })

        frame_count += 1

    cap.release()
    return frames


def save_frame(frame, video_name, frame_number, folder_path):
    """
    Save an extracted frame to the specified folder.
    Args:
        frame: The frame to save.
        video_name (str): Name of the video file.
        frame_number (int): Frame number.
    Returns:
        str: Path to the saved frame.
    """
    frame_filename = f"{os.path.splitext(video_name)[0]}-frame_{frame_number}.jpg"
    frame_path = os.path.join(folder_path, frame_filename)
    cv2.imwrite(frame_path, frame)
    return frame_path


def check_video_pertinence(prompt):
    """Generate a list of YouTube search queries related to a fun fact."""
    response = ollama.chat(
        model="Zephyr",
        messages=[
            {
                "role": "user",
                "content": (
                    prompt),
            }
        ],
    )
    return response["message"]["content"]


def reduce_resolution(frame, factor):
    """
    Reduce the resolution of a frame by a given factor.
    Args:
        frame: The frame to resize.
        factor (float): Scaling factor (e.g., 0.5 for 50% reduction).
    Returns:
        Resized frame.
    """
    height, width = frame.shape[:2]
    new_width = int(width * factor)
    new_height = int(height * factor)
    return cv2.resize(frame, (new_width, new_height))


def evaluate_frame_with_llava(frame, prompt):
    """
    Use the LLaVA model (via Ollama) to evaluate if the frame is a good fit for the script.

    Args:
        frame: numpy.ndarray
            The video frame to evaluate, in BGR format
        script (str):
            The video script to compare against

    Returns:
        bool: True if the frame is a good fit, False otherwise

    Notes:
        - Converts LLaVA's response to a boolean
        - Returns False on any error or unclear response
        - Requires Ollama to be running with the LLaVA model loaded
    """
    # Save the frame as a temporary image
    temp_image_path = "temp_frame.jpg"
    cv2.imwrite(temp_image_path, frame)
    # Read the image file and convert to base64
    with open(temp_image_path, 'rb') as image_file:
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
    # Clean up the temporary file
    os.remove(temp_image_path)
    # Prepare a more structured prompt for LLaVA
    try:
        # Make the API call to Ollama with base64 encoded image
        res = ollama.chat(
            model="llava",
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_data]
            }]
        )
        # Get the response and clean it
        response = res['message']['content'].lower().strip()
        # Convert to boolean based on exact match
        if response == 'good':
            return True
        elif response == 'bad':
            return False
        else:
            print(f"Unexpected response from LLaVA: {response}")
            return False
    except Exception as e:
        print(f"Error calling Ollama API: {e}")
        return False


def cut_video_clip(video_path, timestamp, output_path, offset=10):
    """
    Cut a clip from the video centered around the given timestamp.
    Args:
        video_path (str): Path to the video file.
        timestamp (int): Timestamp in seconds.
        output_path (str): Path to save the output clip.
        clip_duration (int): Duration of the clip in seconds.
    """

    """cap = cv2.VideoCapture(video_path)

    # Get total number of frames
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # Get frames per second (fps)
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Calculate duration in seconds
    duration_seconds = total_frames / fps"""

    start_time = max(0, timestamp - offset)
    end_time = timestamp + offset

    # Use ffmpeg to cut the clip
    command = [
        "ffmpeg",
        "-i", video_path,
        "-ss", str(start_time),
        "-to", str(end_time),
        "-c", "copy",
        output_path
    ]
    subprocess.run(command, check=True)


def process_single_video(video_name, prompt):
    video_path = f"{INPUT_VIDEO_DIR}/{video_name}"
    extract_path = "downloads/extracted_frames"
    reject_path = "downloads/rejected_frames"

    # Get a list of all files in the folder
    files = glob.glob(os.path.join(extract_path, "*"))
    # Loop through the files and delete them
    for file in files:
        try:
            if os.path.isfile(file):  # Ensure it's a file (not a directory)
                os.remove(file)
                print(f"Deleted: {file}")
        except Exception as e:
            print(f"Error deleting {file}: {e}")

    # Get a list of all files in the folder
    files = glob.glob(os.path.join(reject_path, "*"))
    # Loop through the files and delete them
    for file in files:
        try:
            if os.path.isfile(file):  # Ensure it's a file (not a directory)
                os.remove(file)
                print(f"Deleted: {file}")
        except Exception as e:
            print(f"Error deleting {file}: {e}")

    frames = extract_frames(video_path, FRAME_INTERVAL)
    for i, f in enumerate(frames):

        frame_data = f["frame"]
        timestamp = f["timestamp"]

        # Reduce frame resolution
        reduced_frame = reduce_resolution(frame_data, RESOLUTION_FACTOR)

        is_good_fit = evaluate_frame_with_llava(reduced_frame, prompt)

        if is_good_fit:
            save_frame(reduced_frame, video_name, timestamp, extract_path)
            clip_name = f"{os.path.splitext(video_name)[0]}_clip_at_{timestamp}s.mp4"
            clip_path = os.path.join(extract_path, clip_name)
            cut_video_clip(video_path, timestamp, clip_path, clip_duration=10)
        else:
            save_frame(reduced_frame, video_name, timestamp, reject_path)


def process_videos():
    """
    Process all videos in the input directory.
    """

    for video_file in os.listdir(INPUT_VIDEO_DIR):
        video_name = video_file

        video_path = os.path.join(INPUT_VIDEO_DIR, video_file)
        print(f"Processing video: {video_file}")


        # Extract frames every 30 seconds
        frames = extract_frames(video_path, FRAME_INTERVAL)

        for frame_data in frames:
            frame = frame_data["frame"]
            timestamp = frame_data["timestamp"]

            # Reduce frame resolution
            reduced_frame = reduce_resolution(frame, RESOLUTION_FACTOR)

            # Evaluate the frame with LLaVA
            is_good_fit = evaluate_frame_with_llava(reduced_frame, VIDEO_SCRIPT)

            if is_good_fit:
                print(f"Good fit found at {timestamp}s in {video_file}")

                # Cut and save the clip
                clip_name = f"{os.path.splitext(video_file)[0]}_clip_at_{timestamp}s.mp4"
                clip_path = os.path.join(OUTPUT_CLIPS_DIR, clip_name)
                cut_video_clip(video_path, timestamp, clip_path)
                print(f"Clip saved: {clip_path}")


if __name__ == "__main__":
    process_single_video(video_name, prompt)
    # process_videos()