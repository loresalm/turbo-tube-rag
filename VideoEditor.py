import os
from collections import defaultdict
import shutil
import json
import random
from PIL import Image, ImageDraw, ImageFont


from moviepy import VideoFileClip  # type: ignore
from moviepy import AudioFileClip  # type: ignore
from moviepy import concatenate_videoclips  # type: ignore
from moviepy import CompositeVideoClip  # type: ignore
from moviepy import ColorClip  # type: ignore
from moviepy import TextClip  # type: ignore
from moviepy import *
from moviepy.video.tools.subtitles import SubtitlesClip
import numpy as np


class VideoEditor:
    def __init__(self, base_path, json_path):
        # Sentence Splitter
        self.base_path = base_path
        self.json_file_path = json_path
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
        for s_id, s in enumerate(self.sections):
            section_clips = []
            print(f"- section {s_id}")
            section_dir = os.path.join(video_folder, str(s_id))
            yt_vid_dir = os.listdir(section_dir)
            yt_vid_dir = [f for f in yt_vid_dir if f != ".DS_Store"]
            for yt_vid in yt_vid_dir:
                print(f"-- video folder  {yt_vid}")
                print(section_dir, " ", yt_vid)
                clip_path = os.path.join(section_dir, yt_vid)
                clip_dir = os.listdir(clip_path)
                print("--> type", type(clip_dir))
                for clip_file in clip_dir:
                    print(f"--- clip file  {clip_file}")
                    if clip_file.endswith(".mp4"):
                        section_clips.append(os.path.join(clip_path,
                                                          clip_file))

            self.clips[str(s_id)] = section_clips

        audio_files = [
            os.path.join(audio_folder, f)
            for f in os.listdir(audio_folder) if f.endswith(".wav")]
        print(audio_files)
        # Load the audio file
        self.audio = AudioFileClip(audio_files[0])
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

    def video_2_shors(self):
        for s_id, s in enumerate(self.sections):
            clips = self.clips[str(s_id)]
            for c_path in clips:
                self.change_format(c_path)

    def change_format(self, clip_path, bg_color=(0, 0, 0)):

        output_path = clip_path
        clip = VideoFileClip(clip_path)
        # Get dimensions
        original_width = clip.w
        original_height = clip.h

        # Calculate target height for 9:16 aspect ratio (YouTube Shorts)
        target_height = int(original_width * (16/9))

        # Ensure the height is even (divisible by 2)
        if target_height % 2 != 0:
            target_height += 1

        # Create background clip with the target dimensions
        bg_clip = ColorClip(size=(original_width, target_height), 
                            color=bg_color,
                            duration=clip.duration)

        # Position the original video in the center (both horizontally and vertically)
        positioned_clip = clip.set_position("center")

        # Composite the clips
        formatted_clip = CompositeVideoClip([bg_clip, positioned_clip])

        formatted_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            preset="medium",
            bitrate="8000k",
            threads=2,
            ffmpeg_params=["-pix_fmt", "yuv420p"]
        )
        # Close the formatted clip if we're just exporting
        formatted_clip.close() 
        clip.close()
        return output_path

    def generate_subtitle_text(self, fact_id, num_sections):
        script_txt = self.fun_facts["fun_facts"][fact_id]["video_script_clean"][0]
        words = script_txt.split()
        words_per_section = len(words) // num_sections
        sections = [" ".join(words[i * words_per_section:(i + 1) * words_per_section]) for i in range(num_sections)]

        # Calculate the duration of each section
        section_duration = self.audio_duration / num_sections

        # Generate subtitles with equal durations
        subtitles = []
        for i in range(num_sections):
            start_time = i * section_duration
            end_time = (i + 1) * section_duration
            text = sections[i]
            subtitles.append((start_time, end_time, text))
        self.subtitles = subtitles

    def create_subtitle_clips(self, subtitles, video_size):
        subtitle_clips = []
        for start_time, end_time, text in subtitles:
            subtitle_clip = TextClip("Your Subtitle", fontsize=24, color='white', font="DejaVu-Sans").set_duration(end_time - start_time).set_start(start_time)
            subtitle_clips.append(subtitle_clip)
        return subtitle_clips

    def edit_video(self, fact_id, nb_videos, clip_lenght, num_subtitle_sections):

        for s_id, s in enumerate(self.sections):
            c = self.pick_random_clip(self.clips[str(s_id)], nb_videos)
            self.clips[str(s_id)] = c

        section_duration = self.audio_duration/len(self.sections)

        self.generate_subtitle_text(fact_id, num_subtitle_sections)

        for vid_id in range(nb_videos):
            final_video_files = []
            for s_id, s in enumerate(self.sections):
                current_lenght = 0
                while current_lenght < section_duration:
                    final_video_files.append(self.clips[str(s_id)][vid_id])
                    current_lenght += clip_lenght
            selected_clips = [
                VideoFileClip(clip).without_audio()
                for clip in final_video_files]
            final_video = concatenate_videoclips(selected_clips,
                                                 method="chain")
            final_video = final_video.set_audio(self.audio)
            

            # Get video dimensions
            video_width, video_height = final_video.size

            # Create a sequence of subtitle clips (just black bars)
            subtitle_clips = []

            for start, end, _ in self.subtitles:
                duration = end - start
                # Create a black bar at the bottom as a subtitle background
                bar_height = 40
                subtitle_bg = (ColorClip(size=(video_width, bar_height), 
                                        color=(0, 0, 0))
                            .set_opacity(0.8)  # Semi-transparent
                            .set_position((0, video_height-bar_height))  # Bottom of the video
                            .set_start(start)
                            .set_duration(duration))
                subtitle_clips.append(subtitle_bg)

            # First, create the video with subtitle backgrounds
            video_with_backgrounds = CompositeVideoClip([final_video] + subtitle_clips)

            # Process the original video file without creating an intermediate file
            final_video_with_subtitles = video_with_backgrounds.copy()


 

            final_video_with_subtitles.write_videofile(
                f"{self.final_output_path}/short_{vid_id}.mp4",
                codec="libx264", 
                audio_codec="aac",  # Explicitly set audio codec
                fps=24,
                bitrate="8000k",    # Set a reasonable bitrate for quality
                audio_bitrate="192k")
            for clip in subtitle_clips:
                clip.close()
            for clip in selected_clips:
                clip.close()
            final_video.close()

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
