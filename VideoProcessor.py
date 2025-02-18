import os
import cv2  # type: ignore
import json
import ollama  # type: ignore
import base64
import re
import logging
from contextlib import contextmanager
import random
import shutil
import ffmpeg  # type: ignore


@contextmanager
def suppress_logging():
    """Temporarily suppress logging."""
    logging.disable(logging.CRITICAL)  # Disable all logs
    try:
        yield
    finally:
        logging.disable(logging.NOTSET)  # Re-enable logging


class VideoProcessor:
    def __init__(self, base_path, json_path):
        # Sentence Splitter
        self.base_path = base_path
        self.json_file_path = f"{base_path}/{json_path}"
        with open(self.json_file_path, 'r') as file:
            self.fun_facts = json.load(file)

        print("+--> Ready to process videos")
        print("|")

    def get_script_sentences(self, fact_key, num_parts=3):
        text = self.fun_facts["fun_facts"][fact_key]["video_script"]
        # Step 1: Remove all text between []
        cleaned_text = re.sub(r"\[.*?\]", "", text)
        # Step 2: Extract all text between ""
        self.sentences = re.findall(r'"(.*?)"', cleaned_text)
        # Calculate the approximate number of sentences per part
        total_sentences = len(self.sentences)
        part_size = total_sentences // num_parts
        # Split sentences into parts
        parts = []
        for i in range(num_parts):
            start = i * part_size
            # Ensure last part gets any remaining sentences
            end = (start + part_size) if i < num_parts - 1 else total_sentences
            parts.append(" ".join(self.sentences[start:end]))
        self.sentences = parts
        print(f"+--> Script splitted into {num_parts}")
        print("|")

    def match_sentence_video(self, fact_key, video_match):
        video_titles = self.fun_facts["fun_facts"][fact_key]["video_titles"]
        self.sent_video_matches = []
        print("+--> Matching script sections to videos")
        print("|")
        print("+--+")
        print("   |")
        for sent_id, sentence in enumerate(self.sentences):
            print(f"   +-- Script section: {sent_id}")
            print("   |")
            prompt = f"""
                        You are an expert in matching sentences to video titles based on their content. Your task is to analyze the following sentence and rank the provided video titles by how likely they are to contain footage related to the sentence. Return only the indices of the top 3 matching videos as a list.
                        Sentence:{sentence}
                        Video Titles:{video_titles}

                        Instructions:
                        2. Rank the video titles based on how closely they align with these themes.
                        3. Return only the indices of the top {video_match} matching videos as a list, in order of relevance.

                        Output format:
                        [<index1>, <index2>, <index3>]
                    """  # noqa: E501
            with suppress_logging():
                response = ollama.chat(
                    model="Zephyr",
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                prompt),
                        }
                    ],
                )
            print("   |")
            # Extract the indices from the response
            response_text = response["message"]["content"]
            match = re.search(r"\[([\d,\s]+)\]", response_text)
            if match:
                indices_str = match.group(1)
                indices = [int(idx) for idx in indices_str.split(",")]
                print(f"   +-- Extracted indices: {indices}")
                print("   |")
            else:
                indices = random.sample(range(len(video_titles)), video_match)
                print(f"   +-- No indices found in the response. Random selection: {indices}")   # noqa: E501
                print("   |")
            self.sent_video_matches.append((sentence, indices))
        print("+--+")
        print("|")

    def reduce_resolution(self, frame, factor):
        height, width = frame.shape[:2]
        new_width = int(width * factor)
        new_height = int(height * factor)
        return cv2.resize(frame, (new_width, new_height))

    def evaluate_frame_with_llava(self, frame, prompt):
        # Save the frame as a temporary image
        temp_image_path = "temp_frame.jpg"
        cv2.imwrite(temp_image_path, frame)
        # Read the image file and convert to base64
        with open(temp_image_path, 'rb') as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        # Clean up the temporary file
        os.remove(temp_image_path)
        # Prepare a more structured prompt for LLaVA
        try:
            # Make the API call to Ollama with base64 encoded image
            with suppress_logging():
                res = ollama.chat(
                    model="llava",
                    messages=[{
                        'role': 'user',
                        'content': prompt,
                        'images': [image_data]
                    }]
                )
                # Get the response and clean it
                response = res['message']['content'].lower().strip()
                # Convert to boolean based on exact match
                if response == 'good':
                    return True
                elif response == 'bad':
                    return False
                else:
                    print(f"Unexpected response from LLaVA: {response}")
                    return False
        except Exception as e:
            print(f"Error calling Ollama API: {e}")
            return False

    def cut_video_clip(self, video_path, timestamp, output_path, offset=10):
        start_time = max(0, timestamp - offset)
        end_time = timestamp + offset
        (
            ffmpeg
            .input(video_path, ss=start_time, to=end_time)
            .output(output_path, codec="copy")
            .run(quiet=True)  # Suppresses output
        )

    def recreate_folder(self, folder_path):
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        os.makedirs(folder_path)
        print(f"Folder '{folder_path}' has been recreated.")

    def get_frame(self, video_path, factor, frames_folder_path, sent_id, clip_id):  # noqa: E501
        cap = cv2.VideoCapture(video_path)
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # Select a random frame index
        random_frame_index = random.randint(0, total_frames - 1)
        frame_path = f"{frames_folder_path}/sent_{sent_id}_clip_{clip_id}_frame_{random_frame_index}.png"   # noqa: E501
        # Set the video capture to the random frame index
        cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame_index)
        # Read the frame
        ret, frame = cap.read()
        timestamp = random_frame_index // fps
        frame = self.reduce_resolution(frame, factor)
        cv2.imwrite(frame_path, frame)
        cap.release()
        return timestamp, frame

    def extract_clips(self, fact_key, factor, max_nb_trials, offset):
        print("+--> Exctracting clips")
        print("|")
        clips_folder_path = f"{self.base_path}/{fact_key}/clips"
        frames_folder_path = f"{self.base_path}/{fact_key}/frames"
        video_paths = self.fun_facts["fun_facts"][fact_key]["video_paths"]
        self.recreate_folder(clips_folder_path)
        self.recreate_folder(frames_folder_path)
        clip_id = 0
        sent_id = 0
        print("+--+")
        print("   |")
        for sent, vid_ids in self.sent_video_matches:
            print(f"   +--> Extracting for section: {sent_id}")
            print("   |")
            print("   +--+")
            print("      |")
            for vid_id in vid_ids:
                print(f"      +--> Extracting from video id: {vid_id}")
                print("      |")
                find_clip = True
                find_trial = 0
                while find_clip:
                    video_path = video_paths[vid_id]
                    timestamp, frame = self.get_frame(video_path, factor,
                                                      frames_folder_path,
                                                      sent_id,
                                                      clip_id)
                    print("      +--+")
                    print("         |")
                    print(f"         +-- Evaluationg frame: {timestamp}")
                    print("         |")
                    prompt = (
                            "Evaluate if this image is a good fit for the following video script. "  # noqa: E501
                            f"Script: {sent}\n"
                            "Respond with EXACTLY one word: either 'good' or 'bad'. "  # noqa: E501
                            "Use 'good' if the image fits well with the script, 'bad' if it doesn't."  # noqa: E501
                            )
                    is_good_fit = self.evaluate_frame_with_llava(frame, prompt)
                    print("         |")
                    if is_good_fit:
                        print("         +-- Good fit, extracting clip.")
                        print("         |")
                        clip_path = f"{clips_folder_path}/sent_{sent_id}_clip_{clip_id}.mp4"  # noqa: E501
                        self.cut_video_clip(video_path, timestamp, clip_path, offset)  # noqa: E501
                        clip_id += 1
                        find_clip = False
                    elif find_trial > max_nb_trials:
                        print(f"         +-- good fit not found after {find_trial} trials")  # noqa: E501
                        print("         |")
                        find_clip = False
                    else:
                        print("         +-- Bad fit, trying again.")
                        print("         |")
                    find_trial += 1
                    print("      +--+")
                    print("      |")
            sent_id += 1
            print("   +--+")
            print("   |")
        print("+--+")
        print("|")
