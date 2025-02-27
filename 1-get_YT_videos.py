from YouTubeSearcher import YouTubeSearcher


# Load the JSON file
base_path = "data/output/MS"
json_file = "fun_facts.json"
max_duration = 15
fact_key = "fact1"

# Initialize YouTube search
yt = YouTubeSearcher(base_path, json_file)
# yt.download_all_videos(max_duration)
yt.download_fact_videos(fact_key, max_duration)
