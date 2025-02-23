import moondream as md
from PIL import Image
import numpy as np
import time
import cv2
import os



def extract_center_frames(video_path, output_dir, interval_seconds=10):
    # Open the video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return []

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Calculate the frame interval (number of frames in `interval_seconds`)
    frame_interval = int(fps * interval_seconds)

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    frames_info = []
    current_frame_idx = 0

    while current_frame_idx < total_frames:
        # Calculate the middle frame of the current 10-second window
        middle_frame_idx = current_frame_idx + frame_interval // 2

        # Ensure the middle frame does not exceed the total number of frames
        if middle_frame_idx >= total_frames:
            break

        # Set the video capture to the middle frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame_idx)
        ret, frame = cap.read()

        if not ret:
            break

        # Save the frame as an image
        frame_filename = f"frame_{middle_frame_idx}.jpg"
        frame_path = os.path.join(output_dir, frame_filename)
        cv2.imwrite(frame_path, frame)

        # Append frame info to the list
        frames_info.append({
            "frame_path": frame_path,
            "clip_start": current_frame_idx,
            "clip_end": current_frame_idx + frame_interval
        })

        # Move to the next 10-second window
        current_frame_idx += frame_interval

    # Release the video capture object
    cap.release()
    print(frames_info)

    return frames_info, total_frames, fps


def apply_color_filter(frame, color):
    """
    Apply a red or green filter to the frame by setting other channels to 0.
    :param frame: Input frame (numpy array in BGR format).
    :param color: 'red' or 'green'.
    :return: Filtered frame.
    """
    # Create a copy of the frame to avoid modifying the original
    filtered_frame = frame.copy()

    if color == "red":
        # Keep only the red channel (BGR format: set blue and green to 0)
        filtered_frame[:, :, 0] = 0  # Blue channel
        filtered_frame[:, :, 1] = 0  # Green channel
    elif color == "green":
        # Keep only the green channel (BGR format: set blue and red to 0)
        filtered_frame[:, :, 0] = 0  # Blue channel
        filtered_frame[:, :, 2] = 0  # Red channel
    else:
        # If no valid color is provided, return the original frame
        return frame

    return filtered_frame


def process_video_with_filters(video_path, output_video_path, response_array, fps):
    """
    Process the video and apply color filters based on the response array.
    :param video_path: Path to the input video.
    :param output_video_path: Path to save the output video.
    :param response_array: Array of 1s (good) and 0s (bad) for each frame.
    :param fps: Frames per second of the video.
    """
    # Open the video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Create a VideoWriter object to save the output video
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for .mp4
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Apply the corresponding color filter based on the response array
        if frame_idx < len(response_array):
            color = "green" if response_array[frame_idx] == 1 else "red"
            frame = apply_color_filter(frame, color)

        # Write the frame to the output video
        out.write(frame)

        # Increment the frame index
        frame_idx += 1

    # Release the video capture and writer objects
    cap.release()
    out.release()


def extract_good_clips(video_path, output_clips_dir, response_array, fps, clips_length):
    """
    Extract and save only the sections of the video where more than half the frames are labeled as 'good'.
    :param video_path: Path to the input video.
    :param output_clips_dir: Directory to save the good clips.
    :param response_array: Array of 1s (good) and 0s (bad) for each frame.
    :param fps: Frames per second of the video.
    :param clips_length: Length of each clip in seconds.
    """
    # Open the video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames_per_clip = int(fps * clips_length)

    # Create output directory if it doesn't exist
    if not os.path.exists(output_clips_dir):
        os.makedirs(output_clips_dir)

    # Process each clip-length section of the video
    clip_idx = 0
    for start_frame in range(0, total_frames, frames_per_clip):
        end_frame = min(start_frame + frames_per_clip, total_frames)
        section = response_array[start_frame:end_frame]
        
        # Check if more than half of the frames in the section are labeled as 'good'
        if np.sum(section) > (len(section) / 2):
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            # Create VideoWriter for the clip
            clip_path = os.path.join(output_clips_dir, f"clip_{clip_idx}.mp4")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for .mp4
            out = cv2.VideoWriter(clip_path, fourcc, fps, (width, height))
            
            # Write frames
            for frame_idx in range(start_frame, end_frame):
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
            out.release()
            
            clip_idx += 1
    
    # Release the video capture object
    cap.release()


def evaluate_frame_with_moondream(frames_info, total_frames, prompt):
    # Initialize the model
    print("Loading model...")
    print(frames_info)
    model = md.vl(model="/home/tests/vision_models/moondream-2b-int8.mf")
    # Process frames and get responses
    responses = []
    for f_i in frames_info:
        print(f_i)
        image = Image.open(f_i["frame_path"])
        encoded_image = model.encode_image(image)
        answer = model.query(encoded_image, prompt)["answer"].lower().strip()
        if answer == "good":
            responses.append(1)
        elif answer == "bad":
            responses.append(0)
        else:
            print("answer not formatted correctly")
            print(answer)
            responses.append(0)
        print(f"Frame {f_i['frame_path']}: {answer}")

    # Generate the response array
    response_array = np.zeros(total_frames, dtype=int)
    for i, f_i in enumerate(frames_info):
        start = f_i["clip_start"]
        end = f_i["clip_end"]
        response_array[start:end] = responses[i]
    return response_array


# Main script
video_path = "tests/data/video_test.mp4"
output_dir = "tests/data/video_frames"
output_video_path = "tests/data/video_test_colored.mp4"
output_clips_dir = "tests/data/clips"

# Extract center frames and get video properties
frames_info, total_frames, fps = extract_center_frames(video_path,
                                                       output_dir,
                                                       interval_seconds=5)

prompt = "Does this image fit at least one of the following keywords: Motorsports, Michael Schumacher, Go-karting? Answer with 'good' or 'bad'."


response_array = evaluate_frame_with_moondream(frames_info, total_frames, prompt)

# Apply color filters and export the video
process_video_with_filters(video_path, output_video_path, response_array, fps)
print(f"Colored video saved to {output_video_path}")

clips_length = 5
extract_good_clips(video_path, output_clips_dir, response_array, fps, clips_length)
print(f"Good clips saved to {output_clips_dir}")
