from TTS.api import TTS
import json

import re


def process_script(script):
    """
    Removes all text between [] and extracts only the text between "".
    """
    # Remove all text between []
    script = re.sub(r'\[.*?\]', '', script)

    # Extract text between ""
    quotes_text = re.findall(r'"(.*?)"', script)

    # Join the extracted text into a single string
    processed_text = " ".join(quotes_text)

    return processed_text


with open("fun_facts_output.json", 'r') as file:
    data = json.load(file)

# Access a specific fact
fact1 = data['fun_facts']['fact1']

script = fact1["video_script"]
script = process_script(script)

# Load a multi-speaker model
tts = TTS(model_name="tts_models/en/vctk/vits", progress_bar=False, gpu=False)

# List available speakers (optional)
print("Available speakers:", tts.speakers)

# Generate audio with a specific speaker ID
speaker_id = "p301"  # Replace with a valid speaker ID
tts.tts_to_file(
    text=script,
    speaker=speaker_id,  # Specify the speaker ID
    file_path="output.wav"
)

print(f"Audio generated with speaker ID: {speaker_id}")
