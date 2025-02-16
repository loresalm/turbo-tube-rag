from youtube_search import YouTubeSearch
import json


def load_json(file_path):
    """Load the JSON file."""
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data


def save_json(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


def main():
    # Load the JSON file
    file_path = "fun_facts_output.json"  # Replace with the actual path to your JSON file
    data = load_json(file_path)

    # Initialize YouTube search
    yt = YouTubeSearch()

    # Extract YouTube queries from "fact1"
    fact1_queries = data['fun_facts']['fact1']['youtube_queries']

    # Initialize a list to store unique YouTube videos
    unique_videos = []

    try:
        # Iterate over each query in "fact1"
        for query in fact1_queries:
            print(f"Searching for: {query}")
            search_results = yt.search_videos(
                search_query=query,
                max_results=3  # Get the first 3 videos for each query
            )

            # Check if the video is already in the list and add it if not
            for video in search_results:
                if video['url'] not in [v['url'] for v in unique_videos]:
                    unique_videos.append(video)
                    print("\nNew video found:")
                    """
                    print(f"Title: {video['title']}")
                    print(f"URL: {video['url']}")
                    print(f"Thumbnail: {video['thumbnail']}")
                    print(f"Channel: {video['channel']}")
                    print(f"Duration: {video['duration']} seconds")
                    print(f"Views: {video['view_count']}")
                    print("-" * 50)
                    """
                else:
                    print(f"Duplicate video skipped: {video['title']}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

    # Print the final list of unique videos
    print("\nFinal list of unique videos:")
    downloaded_videos_metadata = []
    for video in unique_videos:
        print(f"Title: {video['title']}, URL: {video['url']}")
        duration = round(video['duration']/60, 2)
        print(f"-------> Duration: {duration} min")
        if duration < 15:
            yt.download_video(video['url'], "downloads")
            # Add metadata to the list
            downloaded_videos_metadata.append({
                            'title': video['title'],
                            'description': video.get('description', ''),
                            'url': video['url'],
                            'duration': duration,
                            'channel': video['channel'],
                            'views': video['view_count']
                        })
    save_json(downloaded_videos_metadata, "downloaded_videos_metadata.json")



if __name__ == "__main__":
    main()
