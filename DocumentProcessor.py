import ollama  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
import requests  # type: ignore
import re
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
    def __init__(self):
        # Sentence Splitter
        self.fun_facts = {}
        print("+--> Ready to read documents")
        print("|")

    def clean_text(self, text):
        # Remove unwanted sections based on common patterns
        noise_patterns = [
            r"Table of Contents", r"Quick Facts", r"Read Next", r"Discover",
            r"Feedback", r"References & Edit History",
            r"Share to social media", r"Copy Citation",
            r"Ask the Chatbot a Question", r"External Websites",
            r"Related Topics", r"Images",
            r"verified", r"Last Updated:", r"Select Citation Style",
            r"Show\xa0more", r"Print", r"Cite", r"More Actions"
        ]
        # Join patterns into a single regex
        noise_regex = re.compile("|".join(noise_patterns), re.IGNORECASE)
        # Remove lines that match any of the noise patterns
        cleaned_lines = [
            line for line in text.split("\n") if not noise_regex.search(line)]
        # Reconstruct the cleaned text
        cleaned_text = "\n".join(cleaned_lines)

        return cleaned_text

    def fetch_webpage_content(self, url):
        """Fetch cleaner text from a webpage."""
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            print(f"+--> Failed to fetch {url}")
            print("|")
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        # Try to extract the main content
        main_content = (soup.find("article") or
                        soup.find("main") or
                        soup.find("div", {"id": "content"}))
        if not main_content:  # Fallback if no content is found
            main_content = soup.body
        text = main_content.get_text(separator="\n",
                                     strip=True) if main_content else ""
        # **Filtering out unwanted content**
        text = self.clean_text(text)
        print(f"+--> Text extracted from: {url}")
        print("|")
        return text

    def extract_fun_facts(self, article_text):
        """Extract 3 fun and interesting facts from the given article."""
        print("+--> Generating fun facts:")
        print("|")
        with suppress_logging():
            response = ollama.chat(
                model="Zephyr",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Extract 3 fun and interesting facts from this article."  # noqa: E501
                            "Make them engaging, concise, and unique. "
                            "Avoid general infos and focus on surprising or unusual details. "  # noqa: E501
                            "Format the response as a numbered list.\n\n"
                            f"Article:\n{article_text}"
                        ),
                    }
                ],
            )
        print("|")
        print("+--> Done")
        print("|")
        return response["message"]["content"]

    def parse_fun_facts(self, response_text):
        """Parse numbered fun facts from the LLM response."""
        facts = re.findall(r"\d+\.\s(.+)", response_text)
        return facts

    def generate_youtube_queries(self, fun_fact):
        """Generate a list of YouTube search queries related to a fun fact."""
        with suppress_logging():
            response = ollama.chat(
                model="Zephyr",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Based on the following fun fact, generate a list of YouTube search queries "  # noqa: E501
                            "someone could use to find interesting videos on this topic. "  # noqa: E501
                            "Make them varied, using different angles like documentaries, expert talks, or analysis.\n\n"  # noqa: E501
                            f"Fun Fact: {fun_fact}\n\n"
                            "Format the response as a numbered list."
                        ),
                    }
                ],
            )
        return re.findall(r"\d+\.\s(.+)", response["message"]["content"])

    def generate_video_script(self, fun_fact):
        """Generate a short video script narrating
        the fun fact as an engaging story."""
        with suppress_logging():
            response = ollama.chat(
                model="Zephyr",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Write a short voiceover script for a 60-second video about the following fun fact. "  # noqa: E501
                            "Make it engaging, with a storytelling approach, as if you're narrating a short, exciting story. "  # noqa: E501
                            "Use a conversational tone and add some dramatic or fun elements to keep the viewer hooked.\n\n"   # noqa: E501
                            f"Fun Fact: {fun_fact}\n\n"
                            "Structure the response like a script with clear spoken lines."  # noqa: E501
                        ),
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

    def get_fun_facts(self, article_url, output_file):
        """Full pipeline: Extract fun facts, generate YouTube querie
        and video scripts for each, then save to JSON."""
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
        print(f"+--> Results saved at {output_file}")
        print("|")
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
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.fun_facts, f, indent=4, ensure_ascii=False)
        print(f"   +--> Results saved at {output_file}")
        print("   |")
        print("+--+")
        print("|")
