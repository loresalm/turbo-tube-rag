from VideoProcessor import VideoProcessor


# Load the JSON file
base_path = "data/output/MS"
json_file = "fun_facts.json"
fact_key = "fact1"
video_sections = 3
video_match_per_section = 2
factor = 0.2
max_nb_trials = 1
offset = 10

# Initialize YouTube search
vp = VideoProcessor(base_path, json_file)
vp.get_script_sentences(fact_key, video_sections)
vp.match_sentence_video(fact_key, video_match_per_section)
vp.extract_clips(fact_key, factor, max_nb_trials, offset)
