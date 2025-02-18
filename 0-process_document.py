from DocumentProcessor import DocumentProcessor
import os

# Initialize processor
prompt_file_path = "data/inputs/prompts.json"
processor = DocumentProcessor(prompt_file_path)
# Fetch webpage content

urls = "https://www.britannica.com/biography/Michael-Schumacher"
output_path_folder = "data/outputs/MS"

"""
urls = "https://time.com/7209405/oscars-2025-what-to-know/"
output_path_folder = "data/outputs/Oscars"
"""
"""
urls = "https://www.cas.org/resources/cas-insights/green-chemistry-pharma-industry"
output_path_folder = "data/outputs/GreenChem"
"""
os.makedirs(output_path_folder, exist_ok=True)
output_file = f"{output_path_folder}/fun_facts.json"
# output_data = processor.process_article(urls, output_file)
fact_id = "fact1"
processor.get_fun_facts(urls, output_file)
processor.generate_queries_script(fact_id, output_file)
