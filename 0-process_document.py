from DocumentProcessor import DocumentProcessor
import os

# Initialize processor
processor = DocumentProcessor()
# Fetch webpage content
urls = "https://www.britannica.com/biography/Michael-Schumacher"
output_path_folder = "data/output/MS"
os.makedirs(output_path_folder, exist_ok=True)
output_file = f"{output_path_folder}/fun_facts.json"
# output_data = processor.process_article(urls, output_file)
fact_id = "fact1"
processor.get_fun_facts(urls, output_file)
processor.generate_queries_script(fact_id, output_file)
