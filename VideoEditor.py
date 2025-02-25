import os
from collections import defaultdict
import shutil
import json
import random

from moviepy.editor import VideoFileClip  # type: ignore
from moviepy.editor import AudioFileClip  # type: ignore
from moviepy.editor import concatenate_videoclips  # type: ignore


class VideoEditor:
    def __init__(self, base_path, json_path):
        # Sentence Splitter
        self.base_path = base_path
        self.json_file_path = f"{base_path}/{json_path}"
        with open(self.json_file_path, 'r') as file:
            self.fun_facts = json.load(file)
        self.final_output_path = f"{self.base_path}/final_videos"
        if os.path.exists(self.final_output_path):
            shutil.rmtree(self.final_output_path)
        os.makedirs(self.final_output_path)
        print("+--> Ready to edit video ")
        print("|")

    def get_video_audio_files(self, fact_id):
        # Get all video and audio files
        video_folder = f"{self.base_path}/{fact_id}/clips"
        audio_folder = f"{self.base_path}/{fact_id}/audio"
        self.clips = {}
        self.sections = self.fun_facts["fun_facts"][fact_id]["video_script_sections"]
        for s_id, s in range(self.sections):
            section_clips = sorted(
                [os.path.join(video_folder, f)
                 for f in os.listdir(video_folder) if f.endswith(".mp4")]
            )
            self.clips[str(s_id)] = section_clips
        audio_files = sorted(
            [os.path.join(audio_folder, f)
             for f in os.listdir(audio_folder) if f.endswith(".wav")]
        )

        # Load the audio file
        self.audio = AudioFileClip(audio_files[0]).set_fps(44100).volumex(2.0)
        self.audio_duration = self.audio.duration
        self.section_duration = self.audio_duration/len(self.sections)

    def pick_random_clip(self, clips, nb_clips):
        if nb_clips <= len(clips):
            return random.sample(clips, nb_clips)
        else:
            result = clips.copy()
            while len(result) < nb_clips:
                result.append(random.choice(clips))
            return result

    def edit_video(self, fact_id, nb_videos):

        for s_id, s in range(self.sections):
            c = self.pick_random_clip(self.clips[str(s_id)], nb_videos)
            self.clips[str(s_id)] = c

        for vid_id in range(nb_videos):
            final_video_files = []
            for s_id, s in range(self.sections):
                final_video_files.append(self.clips[str(s_id)][vid_id])
                # concatenate clip
            # save final video


"""

    def edit_video(self, nb_video_sections):
        grouped_clips = {}
        max_nb_clips_x_sect = 0
        for i in range(nb_video_sections):
            section_videos = [video for video in self.video_files
                              if f"sent_{i}" in video]
            grouped_clips[f"sect_{i}"] = section_videos
            nb_clips = len(section_videos)
            if nb_clips > max_nb_clips_x_sect:
                max_nb_clips_x_sect = nb_clips

        for i in range(max_nb_clips_x_sect):
            
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


    from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip
import re

def parse_subtitles(subtitle_file):
    with open(subtitle_file, 'r') as file:
        content = file.read()

    # Regex to match the timecodes and subtitle text
    pattern = re.compile(r'(\d+:\d+:\d+,\d+) --> (\d+:\d+:\d+,\d+)\n(.*?)\n\n', re.DOTALL)
    subtitles = []

    for match in pattern.finditer(content):
        start_time = match.group(1).replace(',', '.')
        end_time = match.group(2).replace(',', '.')
        text = match.group(3).strip()
        subtitles.append(((start_time, end_time), text))

    return subtitles

def create_subtitle_clips(subtitles, video_size):
    subtitle_clips = []

    for ((start_time, end_time), text) in subtitles:
        # Create a TextClip for each subtitle
        txt_clip = TextClip(text, fontsize=24, color='white', bg_color='black', size=video_size)
        txt_clip = txt_clip.set_position(('center', 'bottom')).set_start(start_time).set_end(end_time)
        subtitle_clips.append(txt_clip)

    return subtitle_clips

def add_subtitles_to_video(video_file, subtitle_file, output_file):
    # Load the video
    video = VideoFileClip(video_file)

    # Parse the subtitles
    subtitles = parse_subtitles(subtitle_file)

    # Create subtitle clips
    subtitle_clips = create_subtitle_clips(subtitles, video.size)

    # Combine the video and subtitle clips
    final_video = CompositeVideoClip([video] + subtitle_clips)

    # Write the result to a new file
    final_video.write_videofile(output_file, codec='libx264', audio_codec='aac')

if __name__ == "__main__":
    video_file = "input_video.mp4"  # Replace with your video file
    subtitle_file = "subtitles.txt"  # Replace with your subtitle file
    output_file = "output_video.mp4"  # Replace with your desired output file name

    add_subtitles_to_video(video_file, subtitle_file, output_file)

"""
