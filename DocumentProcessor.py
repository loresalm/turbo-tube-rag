import ollama  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
import requests  # type: ignore
import re
import os
import json
import logging
from contextlib import contextmanager


@contextmanager
def suppress_logging():
    """Temporarily suppress logging."""
    logging.disable(logging.CRITICAL)  # Disable all logs
    try:
        yield
    finally:
        logging.disable(logging.NOTSET)  # Re-enable logging


class DocumentProcessor:
    def __init__(self, config_file_path):
        # load config
        with open(config_file_path, 'r') as file:
            self.config = json.load(file)
        # load or create output file
        self.json_file_path = self.config["output_file"]
        if os.path.exists(self.json_file_path):
            with open(self.json_file_path, 'r', encoding='utf-8') as file:
                self.fun_facts = json.load(file)
        else:
            self.fun_facts = {}
        # load prompt file
        prompt_file_path = self.config["prompts_file"]
        with open(prompt_file_path, 'r') as file:
            self.prompts = json.load(file)
        # load create log file
        self.log_file = self.config["log_file"]
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        self.process_id = "DocumentProcessor"
        self.log("ready to process")
        print("\n DocumentProcessor: Ready \n ")

    def log(self, text):
        # Create directory if it doesn't exist
        # Format the log entry
        log_entry = f"------- {self.process_id} -------\n{text}\n"

        # Write to the log file (create if doesn't exist, append if it does)
        with open(self.log_file, 'a') as log_file:
            log_file.write(log_entry)

    def get_pompt(self, prompt_id, var_dict):
        prompt = self.prompts[prompt_id]
        return prompt.format(**var_dict)

    def fetch_webpage_content(self, url):
        """Fetch cleaner text from a webpage."""
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                self.log(f"Failed to fetch {url}")
                print(f"\n DocumentProcessor: Failed to fetch {url} \n ")
                return None
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove common non-content elements before extraction
            self.remove_unwanted_elements(soup)
            # Try to extract the main content with more targeted selectors
            main_content = (
                soup.find("article") or
                soup.find("main") or
                soup.find(class_=lambda c: c and any(
                    x in str(c).lower() for x in ["content", "post", "entry", "article", "main"])) or
                soup.find("div", {"id": lambda i: i and any(x in str(i).lower() for x in ["content", "post", "entry", "article", "main"])}) or
                soup.find("div", {"class": lambda c: c and any(x in str(c).lower() for x in ["content", "post", "entry", "article", "main"])})
            )
            if not main_content:  # Fallback if no content is found
                main_content = soup.body
            # Get text with better formatting
            text = main_content.get_text(separator="\n", strip=True) if main_content else ""
            # Clean the extracted text
            text = self.clean_text(text)
            # Apply density-based filtering to favor content paragraphs
            text = self.filter_by_text_density(text)
            self.log(f"Text extracted from: {url}")
            self.log(f"Text content: \n - \n {text} \n - \n")
            print(f"\n DocumentProcessor: Text extracted from: {url} \n ")
            return text
        except Exception as e:
            self.log(f"Error processing {url}: {str(e)}")
            print(f"\n DocumentProcessor: Error processing {url}: {str(e)} \n")
            return None

    def remove_unwanted_elements(self, soup):
        """Remove unwanted elements from the soup before text extraction."""
        # Common selectors for non-content elements
        unwanted_selectors = [
            "nav", "header", "footer", "aside", 
            ".sidebar", ".ads", ".advertisement", ".banner", 
            ".menu", ".navigation", ".social", ".share",
            ".comments", ".related", "#comments", "#sidebar",
            "[class*='ad-']", "[class*='advertisement']", "[id*='ad-']",
            "script", "style", "noscript", "iframe"
        ]
        
        for selector in unwanted_selectors:
            for element in soup.select(selector):
                element.decompose()

    def clean_text(self, text):
        """Clean extracted text by removing noise patterns."""
        # Expanded list of noise patterns
        noise_patterns = [
            # Original patterns
            r"Table of Contents", r"Quick Facts", r"Read Next", r"Discover",
            r"Feedback", r"References & Edit History",
            r"Share to social media", r"Copy Citation",
            r"Ask the Chatbot a Question", r"External Websites",
            r"Related Topics", r"Images",
            r"verified", r"Last Updated:", r"Select Citation Style",
            r"Show\xa0more", r"Print", r"Cite", r"More Actions",
            
            # Added patterns for common web pollution
            r"Subscribe", r"Newsletter", r"Sign up", r"Follow us", 
            r"Share this", r"Like us", r"Connect with us",
            r"Sponsored", r"Advertisement", r"Promoted", r"Recommended",
            r"You might also like", r"Popular", r"Trending",
            r"Copyright ©", r"All rights reserved", r"Terms", r"Privacy Policy",
            r"Cookie Policy", r"More from", r"View all", r"Load more",
            r"See also", r"Related articles", r"Top stories",
            r"Join our community", r"Skip to content"
        ]
        
        # Join patterns into a single regex
        noise_regex = re.compile("|".join(noise_patterns), re.IGNORECASE)
        
        # Remove lines that match any of the noise patterns
        cleaned_lines = [line for line in text.split("\n") if not noise_regex.search(line)]
        
        # Filter out very short lines (likely menu items, buttons, etc.)
        cleaned_lines = [line for line in cleaned_lines if len(line.strip()) > 3]
        
        # Remove duplicate lines (often happens with repeated elements)
        unique_lines = []
        for line in cleaned_lines:
            if line not in unique_lines:
                unique_lines.append(line)

        # Reconstruct the cleaned text
        cleaned_text = "\n".join(unique_lines)

        return cleaned_text

    def filter_by_text_density(self, text):
        """Filter text based on character density to favor content paragraphs."""
        lines = text.split("\n")
        filtered_lines = []
        for line in lines:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Check for text density - content usually has higher density
            # This helps filter out menu items, headings, etc. while keeping paragraphs
            if len(line) > 40 or (len(line) > 20 and "." in line):
                filtered_lines.append(line)
        return "\n".join(filtered_lines)

    def extract_fun_facts(self, article_text):
        self.log(f"Generating fun facts")
        print(f"\n DocumentProcessor: Generating fun facts. \n ")
        prompt = self.get_pompt("extract_fun_facts",
                                {"article_text": article_text})
        with suppress_logging():
            response = ollama.chat(
                model="llama3.2:3B",
                messages=[
                    {
                        "role": "user",
                        "content": (prompt),
                    }
                ],
            )
        self.log(f"Fun facts generated: {response['message']['content']}")
        print(f"\n DocumentProcessor: Fun facts generated. \n ")
        return response["message"]["content"]

    def parse_fun_facts(self, response_text):
        facts = re.findall(r"\d+\.\s(.+)", response_text)
        return facts

    def generate_youtube_queries(self, fact):
        """Generate a list of YouTube search queries related to a fun fact."""
        with suppress_logging():
            prompt = self.get_pompt("youtube_queries",
                                    {"fact": fact})
            response = ollama.chat(
                model="llama3.2:3B",
                messages=[
                    {
                        "role": "user",
                        "content": (prompt),
                    }
                ],
            )
        return re.findall(r"\d+\.\s(.+)", response["message"]["content"])

    def generate_video_script(self, fun_fact):
        """Generate a short video script narrating
        the fun fact as an engaging story."""
        with suppress_logging():
            prompt = self.get_pompt("voiceover_script",
                                    {"fun_fact": fun_fact})
            response = ollama.chat(
                model="llama3.2:3B",
                messages=[
                    {
                        "role": "user",
                        "content": (prompt),
                    }
                ],
            )
        return response["message"]["content"]

    def process_article(self, article_url, output_file):
        """Full pipeline: Extract fun facts, generate YouTube querie
        and video scripts for each, then save to JSON."""
        article_text = self.fetch_webpage_content(article_url)
        fun_facts_text = self.extract_fun_facts(article_text)
        fun_facts = self.parse_fun_facts(fun_facts_text)
        result = {
            "article_url": article_url,  # Save article URL at the top level
            "fun_facts": {}
        }
        print("+--+")
        print("   |")
        for i, fact in enumerate(fun_facts, 1):
            fact_key = f"fact{i}"
            print(f"   +-- {fact_key}")
            print("   |")
            print("   | Generating youtube queries")
            print("   |")
            youtube_queries = self.generate_youtube_queries(fact)
            print("   | ")
            print("   | Generating video script")
            print("   |")
            video_script = self.generate_video_script(fact)
            print("   | ")
            result["fun_facts"][fact_key] = {
                "text": fact,
                "youtube_queries": youtube_queries,
                "video_script": video_script
            }
        print("+--+")
        print("|")
        # Save results to a JSON file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print("+--> Results saved at {output_file}")
        print("|")
        return result

    def get_fun_facts(self):
        article_url = self.config["article_url"]
        output_file = self.config["output_file"]
        article_text = self.fetch_webpage_content(article_url)
        fun_facts_text = self.extract_fun_facts(article_text)
        fun_facts = self.parse_fun_facts(fun_facts_text)
        result = {
            "article_url": article_url,  # Save article URL at the top level
            "fun_facts": {}
        }
        for i, fact in enumerate(fun_facts, 1):
            fact_key = f"fact{i}"
            result["fun_facts"][fact_key] = {
                "text": fact,
            }
        # Save results to a JSON file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        self.fun_facts = result

    def generate_queries_script(self, fact_id, output_file):
        fact_key = fact_id
        fact = self.fun_facts["fun_facts"][fact_key]
        print("+--+")
        print("   |")
        print(f"   +-- {fact_key}")
        print("   |")
        print("   | Generating youtube queries")
        print("   |")
        youtube_queries = self.generate_youtube_queries(fact)
        print("   | ")
        print("   | Generating video script")
        print("   |")
        video_script = self.generate_video_script(fact)
        print("   | ")

        self.fun_facts["fun_facts"][fact_key] = {
            "text": fact,
            "youtube_queries": youtube_queries,
            "video_script": video_script
        }
        # Save results to a JSON file
        self.json_file_path = output_file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.fun_facts, f, indent=4, ensure_ascii=False)
        print(f"   +--> Results saved at {output_file}")
        print("   |")
        print("+--+")
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
        keywords = {}
        for i in range(num_parts):
            start = i * part_size
            # Ensure last part gets any remaining sentences
            end = (start + part_size) if i < num_parts - 1 else total_sentences
            sent = " ".join(self.sentences[start:end])
            kw = self.get_keywords(sent)
            parts.append(sent)
            keywords[str(i)] = kw
        self.sentences = parts

        fact = self.fun_facts["fun_facts"][fact_key]
        fact["video_script_clean"] = self.sentences
        fact["video_script_sections"] = parts
        fact["keywords_sections"] = keywords
        self.fun_facts["fun_facts"][fact_key] = fact
        # Save results to a JSON file
        with open(self.json_file_path, "w", encoding="utf-8") as f:
            json.dump(self.fun_facts, f, indent=4, ensure_ascii=False)
        print(f"+--> Script splitted into {num_parts} sections")
        print("|")

    def get_keywords(self, section):
        with suppress_logging():
            prompt = self.get_pompt("keywords", {"section": section})
            response = ollama.chat(
                model="Zephyr",
                messages=[
                    {
                        "role": "user",
                        "content": (prompt),
                    }
                ],
            )
            keywords = response["message"]["content"].strip().split(",")
            return keywords
