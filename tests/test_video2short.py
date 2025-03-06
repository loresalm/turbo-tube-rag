from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip

def change_format(clip_path, clip_output_path, bg_color=(0, 0, 0)):

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
        clip_output_path,
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
    return clip_output_path

# Example usage
clip_path = "data/clip2short/clip_1.mp4"
clip_output_path = "data/clip2short/short_form_clip_1.mp4"
change_format(clip_path, clip_output_path, bg_color=(0, 0, 0))
