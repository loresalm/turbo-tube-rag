from youtube_search import YouTubeSearch


def main():
    # Initialize YouTube search
    yt = YouTubeSearch()

    try:
        # Example 1: Basic search
        print("Searching for dance tutorials...")
        dance_videos = yt.search_videos(
            search_query="dance tutorial beginners",
            max_results=20
        )

        # Print results
        for video in dance_videos:
            print("\nVideo found:")
            print(f"Title: {video['title']}")
            print(f"URL: {video['url']}")
            print(f"thumbnail: {video['thumbnail']}")
            print(f"Channel: {video['channel']}")
            print(f"Duration: {video['duration']} seconds")
            print(f"Views: {video['view_count']}")
            print("-" * 50)

    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
