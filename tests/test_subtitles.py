from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

mp4filename = "test_short.mp4"

video = VideoFileClip(mp4filename)
begin, end = mp4filename.split(".mp4")
output_video_file = begin+'_subtitled'+".mp4"

start_time = 2
duration = 5
clip_txt = "test"
fontsize=24
font='Arial'
color='yellow'
video_width, video_height = video.size
text_clip = TextClip(clip_txt, fontsize=fontsize, font=font, color=color, bg_color = 'black',size=(video_width*3/4, None), method='caption').set_start(start_time).set_duration(duration)
subtitle_x_position = 'center'
subtitle_y_position = video_height* 4 / 5 

text_position = (subtitle_x_position, subtitle_y_position)
subtitle_clips = [text_clip.set_position(text_position)]

final_video = CompositeVideoClip([video] + subtitle_clips)
final_video.write_videofile(output_video_file)
