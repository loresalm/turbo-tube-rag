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
    def __init__(self, base_path, json_path, prompt_file_path):
        with open(prompt_file_path, 'r') as file:
            self.prompts = json.load(file)
        # Sentence Splitter
        self.base_path = base_path
        self.json_file_path = f"{base_path}/{json_path}"
        with open(self.json_file_path, 'r') as file:
            self.fun_facts = json.load(file)
        self.sent_video_matches = []

        print("+--> Ready to process videos")
        print("|")

    def get_pompt(self, prompt_id, var_dict=None):
        prompt = self.prompts[prompt_id]
        if var_dict is None:
            return prompt
        else:
            return prompt.format(**var_dict)

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
        print(f"+--> Script splitted into {num_parts} sections")
        print("|")

    def match_sentence_video(self, fact_key, video_match):
        video_titles = self.fun_facts["fun_facts"][fact_key]["video_titles"]
        self.sent_video_matches = []

        print("+--> Matching script sections to videos")
        print("|")
        print("+--+")
        print("   |")
        for sent_id, sentence in enumerate(self.sentences):
            prompt = self.get_pompt("match_sentences",
                                    {"sentence": sentence,
                                     "video_titles": video_titles,
                                     "video_match": video_match})
            print(f"   +-- Script section: {sent_id}")
            print("   |")
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
        video_id = {}
        for s_id in range(len(self.sent_video_matches)):
            vid_idx = self.sent_video_matches[s_id][1]
            video_id[str(s_id)] = vid_idx

        fact = self.fun_facts["fun_facts"][fact_key]
        fact["best_video_idx"] = video_id
        self.fun_facts["fun_facts"][fact_key] = fact
        # Save results to a JSON file
        with open(self.json_file_path, "w", encoding="utf-8") as f:
            json.dump(self.fun_facts, f, indent=4, ensure_ascii=False)

        print("+--+")
        print("|")

    def reduce_resolution(self, frame, factor):
        height, width = frame.shape[:2]
        new_width = int(width * factor)
        new_height = int(height * factor)
        return cv2.resize(frame, (new_width, new_height))

    def evaluate_frame_with_llava(self, frame, prompt):
        print("------------------> evaluate frame")
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
                print(" ")
                print(res)
                print(" ")
                # Get the response and clean it
                response = res['message']['content'].lower().strip()
                print(response)
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
        try:
            (
                ffmpeg
                .input(video_path, ss=start_time, to=end_time)
                .output(output_path, codec="copy")
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            print("FFmpeg error occurred:", e)
            print("STDOUT:", e.stdout.decode())
            print("STDERR:", e.stderr.decode())

    def recreate_folder(self, folder_path):
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        os.makedirs(folder_path)

    def get_frame(self, video_path, factor, frames_folder_path, sent_id, clip_id):  # noqa: E501
        cap = cv2.VideoCapture(video_path)
        cap = cv2.VideoCapture(video_path)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # Select a random frame index
        random_frame_index = random.randint(0, total_frames - 1)
        # Set the video capture to the random frame index
        cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame_index)
        # Read the frame
        ret, frame = cap.read()
        timestamp = random_frame_index // fps
        frame_path = f"{frames_folder_path}/sent_{sent_id}_clip_{clip_id}_frame_{timestamp}.png"   # noqa: E501
        frame = self.reduce_resolution(frame, factor)
        cv2.imwrite(frame_path, frame)
        cap.release()
        return timestamp, frame

    def get_clips(self, fact_key, factor, max_nb_trials, offset):
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
        if len(self.sent_video_matches) == 0:
            best_vid = self.fun_facts["fun_facts"][fact_key]["best_video_idx"] 
            for sentence, indices in best_vid.items():
                self.sent_video_matches.append((sentence, indices))

        for sent, vid_ids in self.sent_video_matches:
            print(f"   +--> Extracting for section: {sent_id}")
            print("   |")
            print("   +--+")
            print("      |")
            for vid_id in vid_ids:
                print(f"      +--> Extracting from video id: {vid_id}")
                print("      |")
                video_path = video_paths[vid_id]
                clip_found = False
                for t in range(max_nb_trials):
                    timestamp, frame = self.get_frame(video_path, factor,
                                                      frames_folder_path,
                                                      sent_id,
                                                      clip_id)
                    print("      +--+")
                    print("         |")
                    print(f"         +-- Evaluating frame: {timestamp}")
                    print("         |")

                    """
                    prompt = self.get_pompt("eval_frame",
                                            {"sent": sent})
                    """
                    prompt = self.get_pompt("simple_eval_frame")
                    is_good_fit = self.evaluate_frame_with_llava(frame, prompt)
                    print("         |")
                    if is_good_fit:
                        print("         +-- Good fit, extracting clip.")
                        print("         |")
                        clip_path = f"{clips_folder_path}/sent_{sent_id}_clip_{clip_id}.mp4"  # noqa: E501
                        self.cut_video_clip(video_path, timestamp, clip_path, offset)   # noqa: E501
                        clip_id += 1
                        clip_found = True
                    else:
                        print("         +-- Bad fit, trying again.")
                        print("         |")
                if not clip_found:
                    print(f"         +-- good fit not found after {max_nb_trials} trials. Getting a random clip")  # noqa: E501
                    print("         |")
                    timestamp, frame = self.get_frame(video_path, factor,
                                                      frames_folder_path,
                                                      sent_id,
                                                      clip_id)
                    clip_path = f"{clips_folder_path}/sent_{sent_id}_clip_{clip_id}_rand.mp4"  # noqa: E501
                    self.cut_video_clip(video_path, timestamp, clip_path, offset)  # noqa: E501
                    print("      +--+")
                    print("      |")
            sent_id += 1
            print("   +--+")
            print("   |")
        print("+--+")
        print("|")

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
                    print(f"         +-- Evaluating frame: {timestamp}")
                    print("         |")
                    prompt = self.get_pompt("eval_frame",
                                            {"sent": sent})
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
                        print(f"         +-- good fit not found after {find_trial} trials. Getting a random clip")  # noqa: E501
                        print("         |")
                        timestamp, frame = self.get_frame(video_path, factor,
                                                          frames_folder_path,
                                                          sent_id,
                                                          clip_id)
                        clip_path = f"{clips_folder_path}/sent_{sent_id}_clip_{clip_id}.mp4"  # noqa: E501
                        self.cut_video_clip(video_path, timestamp, clip_path, offset)  # noqa: E501
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
