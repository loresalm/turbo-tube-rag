from TTS.api import TTS  # type: ignore
import json
import re
import os
import shutil


class AudioGenerator:
    def __init__(self, base_path, json_path):
        # Sentence Splitter
        self.base_path = base_path
        self.json_file_path = f"{base_path}/{json_path}"
        with open(self.json_file_path, 'r') as file:
            self.fun_facts = json.load(file)

        print("+--> Ready to generate Audio")
        print("|")

    def process_script(self, fact_key):
        """
        Removes all text between [] and extracts only the text between "".
        """
        script = self.fun_facts["fun_facts"][fact_key]["video_script"]
        # Remove all text between []
        script = re.sub(r'\[.*?\]', '', script)

        # Extract text between ""
        quotes_text = re.findall(r'"(.*?)"', script)

        # Join the extracted text into a single string
        processed_text = " ".join(quotes_text)

        self.processed_script = processed_text

    def recreate_folder(self, folder_path):
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        os.makedirs(folder_path)

    def generate_audio(self, fact_key, speaker_id):
        audio_folder_path = f"{self.base_path}/{fact_key}/audio"
        audio_file_path = f"{audio_folder_path}/audio.wav"
        self.recreate_folder(audio_folder_path)
        # Load a multi-speaker model
        tts = TTS(model_name="tts_models/en/vctk/vits",
                  progress_bar=False,
                  gpu=False)

        # List available speakers (optional)
        print("Available speakers:", tts.speakers)

        self.process_script(fact_key)

        # Generate audio with a specific speaker ID
        tts.tts_to_file(
            text=self.processed_script,
            speaker=speaker_id,  # Specify the speaker ID
            file_path=audio_file_path
        )
