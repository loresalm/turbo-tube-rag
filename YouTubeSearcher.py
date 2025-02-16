from yt_dlp import YoutubeDL  # type: ignore
from typing import Dict
import time
from functools import lru_cache
import os
import json


class YouTubeSearcher:
    def __init__(self, basepath, json_file):
        """Initialize YouTubeSearch with default options"""
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Don't download videos
        }
        self.basepath = basepath
        self.data = self.load_json(f"{basepath}/{json_file}")
        self.last_request_time = 0
        self.min_interval = 1  # Minimum seconds between requests
        print("+--> Ready search youtube videos")
        print("|")

    def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_passed = current_time - self.last_request_time
        if time_passed < self.min_interval:
            time.sleep(self.min_interval - time_passed)
        self.last_request_time = time.time()

    def load_json(self, file_path):
        """Load the JSON file."""
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data

    def save_json(self, data, file_path):
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)

    @lru_cache(maxsize=100)
    def search_videos(self, search_query: str, max_results: int = 5):
        """
        Search for YouTube videos based on keywords
        Args:
            search_query (str): Search terms
            max_results (int): Maximum number of results to return
        Returns:
            List[Dict]: List of video information dictionaries
        """
        self._rate_limit()

        try:
            with YoutubeDL(self.ydl_opts) as ydl:
                # Construct search URL
                search_results = ydl.extract_info(
                    f"ytsearch{max_results}:{search_query}",
                    download=False
                )

                videos = []
                if search_results.get('entries'):
                    for entry in search_results['entries']:
                        video = {
                            'title': entry.get('title', 'No title'),
                            'video_id': entry.get('id', 'No ID'),
                            'description': entry.get('description', 'No desc'),
                            'duration': entry.get('duration', 0),
                            'view_count': entry.get('view_count', 0),
                            'url': f"https://www.youtube.com/watch?v={entry.get('id')}",  # noqa: E501
                            'thumbnail': entry.get('thumbnail', ''),
                            'channel': entry.get('channel', 'Unknown channel'),
                            'upload_date': entry.get('upload_date', 'No date')
                        }
                        videos.append(video)

                return videos

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return []

    def get_video_details(self, video_url: str) -> Dict:
        """
        Get detailed information for a specific video
        Args:
            video_url (str): YouTube video URL or ID
        Returns:
            Dict: Detailed video information
        """
        try:
            with YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                return info
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return {}

    def download_video(self, video_url: str, output_dir: str = "downloads"):
        """
        Download a YouTube video to the specified directory
        Args:
            video_url (str): YouTube video URL or ID
            output_dir (str): Directory to save the downloaded video
        Returns:
            str: Path to the downloaded video file
        """
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Configure yt_dlp options for downloading
        download_opts = {
            'format': 'best',  # Download the best quality available
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with YoutubeDL(download_opts) as ydl:
                # Download the video
                info = ydl.extract_info(video_url, download=True)
                file_path = ydl.prepare_filename(info)
                return file_path
        except Exception as e:
            print(f"   | Download error for the video: {str(e)}")
            return None

    def get_unique_videos(self, fact):
        unique_videos = []
        fact_queries = self.data['fun_facts'][fact]['youtube_queries']
        print("   | Getting youtube videos from generated queries")
        print("   |")
        try:
            # Iterate over each query in "fact1"
            for query in fact_queries:
                search_results = self.search_videos(
                    search_query=query,
                    max_results=3  # Get the first 3 videos for each query
                )

                # Check if the video is already in the list and add it if not
                for video in search_results:
                    if video['url'] not in [v['url'] for v in unique_videos]:
                        unique_videos.append(video)

        except Exception as e:
            print(f"   | An error occurred: {str(e)}")
            print("   |")
        print(f"   | {len(unique_videos)} videos found")
        print("   |")
        return unique_videos

    def download_all_videos(self, max_duration):

        print("+--+")
        print("   |")
        for fact_key, _ in self.data["fun_facts"].items():
            print(f"   +-- {fact_key}")
            print("   |")
            download_folder = f"{self.basepath}/{fact_key}"
            os.makedirs(f"{download_folder}", exist_ok=True)
            unique_videos = self.get_unique_videos(fact_key)
            rej = 0
            ok = 0
            for video in unique_videos:
                duration = round(video['duration']/60, 2)
                if duration < max_duration:
                    ok += 1
                    self.download_video(video['url'], download_folder)
                else:
                    rej += 1
            print(f"   | Downloaded {ok} videos, rejected {rej} videos longer than {max_duration} min.")   # noqa: E501
            print("   |")
        print("+--+")
        print("|")
