from yt_dlp import YoutubeDL
from typing import List, Dict
import time
from functools import lru_cache
import os


class YouTubeSearch:
    def __init__(self):
        """Initialize YouTubeSearch with default options"""
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Don't download videos
        }
        self.last_request_time = 0
        self.min_interval = 1  # Minimum seconds between requests

    def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_passed = current_time - self.last_request_time
        if time_passed < self.min_interval:
            time.sleep(self.min_interval - time_passed)
        self.last_request_time = time.time()

    @lru_cache(maxsize=100)
    def search_videos(self, search_query: str, max_results: int = 5) -> List[Dict]:
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
                            'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
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

    def download_video(self, video_url: str, output_dir: str = "downloads") -> str:
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
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),  # Save file with title as name
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with YoutubeDL(download_opts) as ydl:
                # Download the video
                info = ydl.extract_info(video_url, download=True)
                file_path = ydl.prepare_filename(info)
                print(f"Video downloaded successfully: {file_path}")
                return file_path
        except Exception as e:
            print(f"An error occurred while downloading the video: {str(e)}")
            return None