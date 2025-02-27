from DocumentProcessor import DocumentProcessor
from YouTubeSearcher import YouTubeSearcher
from VideoProcessor import VideoProcessor
from VideoEditor import VideoEditor
from AudioGenerator import AudioGenerator
import os
import json

cofig_path = "data/inputs/config.json"

with open(cofig_path, 'r') as file:
    config = json.load(file)

output_path = config["output_path"]
output_file = config['output_file']
prompt_file = config["prompts_file"]
article_url = config["article_url"]
fact_id = config["fact_id"]
max_duration = config["max_duration"]
video_sections = config["video_sections"]
video_match_per_section = config["video_match_per_section"]
factor = config["factor"]
max_nb_trials = config["max_nb_trials"]
offset = config["offset"]

os.makedirs(output_path, exist_ok=True)

output_file_path = f"{output_path}/{output_file}"

########################################
#                                      #
#      Step1: article --> script       #
#                                      #
########################################
"""
processor = DocumentProcessor(prompt_file, output_file_path)
processor.get_fun_facts(article_url, output_file_path)
processor.generate_queries_script(fact_id, output_file_path)
processor.get_script_sentences(fact_id, video_sections)
"""
########################################
#                                      #
#       Step2: script --> audio        #
#                                      #
########################################
# Initialize YouTube search
speaker_id = "p314"
ag = AudioGenerator(output_path, output_file)
ag.generate_audio(fact_id, speaker_id)


########################################
#                                      #
#   Step2: script --> download videos  #
#                                      #
########################################
"""
yt = YouTubeSearcher(output_path, output_file)
yt.download_fact_videos(fact_id, max_duration)
"""
########################################
#                                      #
#   Step3: download videos -->  clips  #
#                                      #
########################################
"""
vp = VideoProcessor(output_path, output_file, prompt_file)
interval_seconds = 10
video_name = "Three Years After Near-Fatal Accident, Michael Schumacher's Legacy Lives On.mp4"
model_path = "/home/tests/vision_models/moondream-2b-int8.mf"

factor = 0.2
vp.match_sentence_video(fact_id, video_match_per_section)
vp.convert_videos2clips(fact_id, interval_seconds, factor, model_path)
"""

########################################
#                                      #
#     Step4: edit clips -->  shorts    #
#                                      #
########################################
"""
nb_final_shorts = 3
vd = VideoEditor(output_path, output_file_path)
vd.get_video_audio_files(fact_id)
vd.edit_video(nb_final_shorts)
"""