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
import moondream as md  # type: ignore
from PIL import Image  # type: ignore
import numpy as np  # type: ignore


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
        self.sentences = []

        print("+--> Ready to process videos")
        print("|")

    def get_pompt(self, prompt_id, var_dict=None):
        prompt = self.prompts[prompt_id]
        if var_dict is None:
            return prompt
        else:
            return prompt.format(**var_dict)

    def match_sentence_video(self, fact_key, video_match):
        video_titles = self.fun_facts["fun_facts"][fact_key]["video_titles"]
        self.sent_video_matches = []

        print("+--> Matching script sections to videos")
        print("|")
        print("+--+")
        print("   |")
        if len(self.sentences) == 0:
            self.sentences = self.fun_facts["fun_facts"][fact_key]["video_script_sections"]

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

    def extract_center_frames(self, fact_key, video_path, interval_seconds, factor):
        # Open the video file
        # nvideo_path = f"{self.base_path}/{fact_key}/downloads/{video_name}"
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("Error: Could not open video.")
            print(f"----> extract_center_frames ----> {video_path}")
            return []

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Calculate the frame interval (number of frames in `interval_seconds`)
        frame_interval = int(fps * interval_seconds)

        # Create output directory if it doesn't exist
        output_dir = f"{self.base_path}/{fact_key}/frames/{video_path[-10:-4]}"
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir)

        frames_info = []
        current_frame_idx = 0

        while current_frame_idx < total_frames:
            # Calculate the middle frame of the current 10-second window
            middle_frame_idx = current_frame_idx + frame_interval // 2

            # Ensure the middle frame does not exceed total number of frames
            if middle_frame_idx >= total_frames:
                break

            # Set the video capture to the middle frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame_idx)
            ret, frame = cap.read()
            frame = self.reduce_resolution(frame, factor)

            if not ret:
                break

            # Save the frame as an image
            frame_filename = f"frame_{middle_frame_idx}.jpg"
            frame_path = os.path.join(output_dir, frame_filename)
            cv2.imwrite(frame_path, frame)

            # Append frame info to the list
            frames_info.append({
                "frame_path": frame_path,
                "clip_start": current_frame_idx,
                "clip_end": current_frame_idx + frame_interval
            })

            # Move to the next 10-second window
            current_frame_idx += frame_interval

        # Release the video capture object
        cap.release()
        self.frames_info = frames_info
        self.total_frames = total_frames
        self.fps = fps

    def evaluate_frame_with_moondream(self, model,  prompt):

        # Process frames and get responses
        responses = []
        for f_i in self.frames_info:
            image = Image.open(f_i["frame_path"])
            encoded_image = model.encode_image(image)
            answer = model.query(encoded_image,
                                 prompt)["answer"].lower().strip()
            if answer == "yes":
                responses.append(1)
            elif answer == "no":
                responses.append(0)
            else:
                print("answer not formatted correctly")
                print(answer)
                responses.append(0)
        # Generate the response array
        response_array = np.zeros(self.total_frames, dtype=int)
        for i, f_i in enumerate(self.frames_info):
            start = f_i["clip_start"]
            end = f_i["clip_end"]
            response_array[start:end] = responses[i]
        self.response_array = response_array

    def apply_color_filter(self, frame, color):
        """
        Apply a red or green filter to the frame, setting other channels to 0.
        :param frame: Input frame (numpy array in BGR format).
        :param color: 'red' or 'green'.
        :return: Filtered frame.
        """
        # Create a copy of the frame to avoid modifying the original
        filtered_frame = frame.copy()

        if color == "red":
            # Keep only the red channel (BGR format: set blue and green to 0)
            filtered_frame[:, :, 0] = 0  # Blue channel
            filtered_frame[:, :, 1] = 0  # Green channel
        elif color == "green":
            # Keep only the green channel (BGR format: set blue and red to 0)
            filtered_frame[:, :, 0] = 0  # Blue channel
            filtered_frame[:, :, 2] = 0  # Red channel
        else:
            # If no valid color is provided, return the original frame
            return frame

        return filtered_frame

    def process_video_with_filters(self, fact_key, video_path):
        """
        Process the video and apply color filters based on the response array.
        :param video_path: Path to the input video
        :param output_video_path: Path to save the output video.
        :param response_array: Array of 1s (good) and 0s (bad) for each frame.
        :param fps: Frames per second of the video.
        """
        output_video_folder = f"{self.base_path}/{fact_key}/video_with_labels"
        output_video_path = f"{output_video_folder}/{video_path[-14:-4]}.mp4"

        if not os.path.exists(output_video_folder):
            os.makedirs(output_video_folder)

        # Open the video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("Error: Could not open video.")
            print(f"----> process_video_with_filters ----> {video_path}")
            return

        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Create a VideoWriter object to save the output video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for .mp4
        out = cv2.VideoWriter(output_video_path, fourcc,
                              self.fps, (width, height))

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Apply the corresponding color filter based on the response array
            if frame_idx < len(self.response_array):
                color = ("green" if self.response_array[frame_idx] == 1
                         else "red")
                frame = self.apply_color_filter(frame, color)

            # Write the frame to the output video
            out.write(frame)

            # Increment the frame index
            frame_idx += 1

        # Release the video capture and writer objects
        cap.release()
        out.release()

    def extract_good_clips(self, sect, fact_key, video_path, clips_length):
        """
        Extract and save only the sections of the video where more than half the frames are labeled as 'good'.
        :param video_path: Path to the input video.
        :param output_clips_dir: Directory to save the good clips.
        :param response_array: Array of 1s (good) and 0s (bad) for each frame.
        :param fps: Frames per second of the video.
        :param clips_length: Length of each clip in seconds.
        """
        # Open the video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("Error: Could not open video.")
            print(f"----> extract_good_clips ----> {video_path}")
            return

        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frames_per_clip = int(self.fps * clips_length)

        output_video_folder = f"{self.base_path}/{fact_key}/clips/{sect}/{video_path[-10:-4]}"
        print(" ")
        print("clips output path:")
        print(output_video_folder)
        print(" ")
        # Create output directory if it doesn't exist
        if os.path.exists(output_video_folder):
            shutil.rmtree(output_video_folder)
        os.makedirs(output_video_folder)

        # Process each clip-length section of the video
        clip_idx = 0
        for start_frame in range(0, total_frames, frames_per_clip):
            end_frame = min(start_frame + frames_per_clip, total_frames)
            section = self.response_array[start_frame:end_frame]
            # Check if more than half of the frames in the section are labeled as 'good'
            if np.sum(section) > (len(section) / 2):
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                # Create VideoWriter for the clip
                clip_path = os.path.join(output_video_folder, f"clip_{clip_idx}.mp4")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for .mp4
                out = cv2.VideoWriter(clip_path, fourcc, self.fps, (width, height))

                # Write frames
                for frame_idx in range(start_frame, end_frame):
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out.write(frame)
                out.release()
                clip_idx += 1
        # Release the video capture object
        cap.release()

    def convert_videos2clips(self, fact_id, interval_seconds, factor, model_path):
        # Initialize the model
        model = md.vl(model=model_path)
        if len(self.sentences) == 0:
            self.sentences = self.fun_facts["fun_facts"][fact_id]["video_script_sections"]

        video_ids = self.fun_facts["fun_facts"][fact_id]["best_video_idx"]
        video_paths = self.fun_facts["fun_facts"][fact_id]["video_paths"]
        keywords = self.fun_facts["fun_facts"][fact_id]["keywords_sections"]

        for i, _ in enumerate(self.sentences):
            print(" ")
            print(f"section: {i}")
            print(" ")
            ky = keywords[str(i)]
            prompt = self.get_pompt("moondreamer_prompt", {"keywords": ky})
            for vid_id in video_ids[str(i)]:
                video_name = video_paths[vid_id]

                self.extract_center_frames(fact_id, video_name,
                                           interval_seconds, factor)
                self.evaluate_frame_with_moondream(model,  prompt)
                self.process_video_with_filters(fact_id, video_name)
                self.extract_good_clips(str(i), fact_id, video_name,
                                        interval_seconds)

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
        if len(self.sentences) == 0:
            self.sentences = self.fun_facts["fun_facts"][fact_key]["video_script_sections"]
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

                    prompt = self.get_pompt("eval_frame",
                                            {"sent": self.sentences[int(sent)]})
                    print(prompt)
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
