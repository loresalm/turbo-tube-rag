from YouTubeSearcher import YouTubeSearcher


# Load the JSON file
base_path = "data/output/MS"
json_file = "fun_facts.json"
max_duration = 30

# Initialize YouTube search
yt = YouTubeSearcher(base_path, json_file)

yt.download_all_videos(max_duration)
