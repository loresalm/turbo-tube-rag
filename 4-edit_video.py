import os
from collections import defaultdict
import shutil
from moviepy.editor import VideoFileClip  # type: ignore
from moviepy.editor import AudioFileClip  # type: ignore
from moviepy.editor import concatenate_videoclips  # type: ignore
# Define paths
base_path = "data/output/MS"
video_folder = f"{base_path}/fact1/clips"
audio_folder = f"{base_path}/fact1/audio"
output_dir = f"{base_path}/fact1/final_videos"

if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
os.makedirs(output_dir)

# Get all video and audio files
video_files = sorted(
    [os.path.join(video_folder, f)
     for f in os.listdir(video_folder) if f.endswith(".mp4")]
)
audio_files = sorted(
    [os.path.join(audio_folder, f)
     for f in os.listdir(audio_folder) if f.endswith(".wav")]
)

if not video_files or not audio_files:
    raise ValueError("No video or audio files found!")

# Load the audio file
audio = AudioFileClip(audio_files[0]).set_fps(44100).volumex(2.0)
audio_duration = audio.duration

# Group videos by their sentence prefix (sent_0, sent_1, sent_2, etc.)
grouped_clips = defaultdict(list)

for video_file in video_files:
    filename = os.path.basename(video_file)
    sent_prefix = filename.split("_clip_")[0]  # Extract "sent_X"
    grouped_clips[sent_prefix].append(video_file)

# Ensure we have at least sent_0, sent_1, and sent_2 in each final video
required_groups = ["sent_0", "sent_1", "sent_2"]

# Create 3 final videos
for i in range(3):
    selected_clips = []

    # Ensure at least one clip from each required group
    for sent in required_groups:
        if grouped_clips[sent]:  
            selected_clips.append(VideoFileClip(grouped_clips[sent].pop(0)).without_audio())

    # Distribute remaining clips evenly
    remaining_clips = [clip for clips in grouped_clips.values() for clip in clips]
    extra_clips = remaining_clips[i::3]  # Distribute clips among the 3 videos

    for clip_path in extra_clips:
        selected_clips.append(VideoFileClip(clip_path).without_audio())

    # Concatenate selected clips
    final_video = concatenate_videoclips(selected_clips, method="compose")

    # Trim the video if it's longer than the audio
    if final_video.duration > audio_duration:
        final_video = final_video.subclip(0, audio_duration)

    # Set the new audio
    final_video = final_video.set_audio(audio)

    # Export final video
    output_path = os.path.join(output_dir, f"final_output_{i+1}.mp4")
    final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", bitrate="192k", fps=24)

    print(f"Video {i+1} processing complete! Saved as:", output_path)