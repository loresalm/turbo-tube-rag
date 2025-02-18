from DocumentProcessor import DocumentProcessor
from YouTubeSearcher import YouTubeSearcher
import os
import json

cofig_path = "data/inputs/config.json"

with open(cofig_path, 'r') as file:
    config = json.load(file)

output_path = config["output_path"]
output_file = config['output_file']
prompt_file = config["prompts_file"]
article_url = config["article_url"]
fact_id = config["fact_id"]

os.makedirs(output_path, exist_ok=True)

output_file_path = f"{output_path}/{output_file}"

processor = DocumentProcessor(prompt_file)
processor.get_fun_facts(article_url, output_file_path)
processor.generate_queries_script(fact_id, output_file_path)

yt = YouTubeSearcher(output_path, output_file_path)
yt = YouTubeSearcher(output_path, output_file_path)
