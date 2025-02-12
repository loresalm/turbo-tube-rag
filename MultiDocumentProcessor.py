import chromadb  # type: ignore
import ollama  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
import requests  # type: ignore
import re
import json
from llama_index.core.node_parser import SentenceSplitter  # type: ignore
from llama_index.core.schema import Document  # type: ignore


class MultiDocumentProcessor:
    def __init__(self, llm_model="llama2"):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(name="women_football_wc")
        # Sentence Splitter
        self.splitter = SentenceSplitter(chunk_size=50, chunk_overlap=10)

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
            print(f"Failed to fetch {url}")
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

        return text

    def store_documents(self, texts):
        """Convert text to `Document` objects before splitting"""
        # Convert each text (string) into a `Document` object
        document_objects = [Document(text=t[:40000]) for t in texts]
        # Split into sentences
        nodes = self.splitter.get_nodes_from_documents(document_objects)
        for i, node in enumerate(nodes):
            text = node.get_text()
            embedding = ollama.embeddings(model="mxbai-embed-large",
                                          prompt=node.get_text())['embedding']
            # embedding = self.embedding_model.get_text_embedding(text)
            self.collection.add(
                ids=[str(i)],
                embeddings=[embedding],
                metadatas=[{"source": "Wikipedia"}],
                documents=[text]
                )

    def query_chroma(self, query):
        """Query ChromaDB using Ollama"""
        queryembed = ollama.embeddings(model="mxbai-embed-large",
                                       prompt=query)['embedding']
        results = self.collection.query(query_embeddings=[queryembed],
                                        n_results=5)
        retrieved_texts = [doc for doc in results["documents"][0]]
        return "\n".join(retrieved_texts)  # Combine results into a context


def extract_fun_facts(article_text):
    """Extract 3 fun and interesting facts from the given article."""
    response = ollama.chat(
        model="Zephyr",
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract 3 fun and interesting facts from this article. "
                    "Make them engaging, concise, and unique. "
                    "Avoid general infos and focus on surprising or unusual details. "
                    "Format the response as a numbered list.\n\n"
                    f"Article:\n{article_text}"
                ),
            }
        ],
    )
    return response["message"]["content"]


def parse_fun_facts(response_text):
    """Parse numbered fun facts from the LLM response."""
    facts = re.findall(r"\d+\.\s(.+)", response_text)
    return facts


def generate_youtube_queries(fun_fact):
    """Generate a list of YouTube search queries related to a fun fact."""
    response = ollama.chat(
        model="Zephyr",
        messages=[
            {
                "role": "user",
                "content": (
                    "Based on the following fun fact, generate a list of YouTube search queries "
                    "someone could use to find interesting videos on this topic. "
                    "Make them varied, using different angles like documentaries, expert talks, or analysis.\n\n"
                    f"Fun Fact: {fun_fact}\n\n"
                    "Format the response as a numbered list."
                ),
            }
        ],
    )
    return re.findall(r"\d+\.\s(.+)", response["message"]["content"])


def generate_video_script(fun_fact):
    """Generate a short video script narrating
    the fun fact as an engaging story."""
    response = ollama.chat(
        model="Zephyr",
        messages=[
            {
                "role": "user",
                "content": (
                    "Write a short voiceover script for a 60-second video about the following fun fact. "
                    "Make it engaging, with a storytelling approach, as if you're narrating a short, exciting story. "
                    "Use a conversational tone and add some dramatic or fun elements to keep the viewer hooked.\n\n"
                    f"Fun Fact: {fun_fact}\n\n"
                    "Structure the response like a script with clear spoken lines."
                ),
            }
        ],
    )
    return response["message"]["content"]


def process_article(article_url, article_text, output_file="output.json"):
    """Full pipeline: Extract fun facts, generate YouTube querie
      and video scripts for each, then save to JSON."""
    print("🔍 Extracting Fun Facts...")
    fun_facts_text = extract_fun_facts(article_text)
    fun_facts = parse_fun_facts(fun_facts_text)

    print("\n🎯 Generating YouTube Queries and Video Scripts...")
    result = {
        "article_url": article_url,  # Save article URL at the top level
        "fun_facts": {}
    }

    for i, fact in enumerate(fun_facts, 1):
        fact_key = f"fact{i}"
        youtube_queries = generate_youtube_queries(fact)
        video_script = generate_video_script(fact)

        result["fun_facts"][fact_key] = {
            "text": fact,
            "youtube_queries": youtube_queries,
            "video_script": video_script
        }

    # Save results to a JSON file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Results saved to {output_file}")
    return result


# Initialize processor
processor = MultiDocumentProcessor(llm_model="llama2")
# Fetch webpage content
urls = ["https://www.britannica.com/biography/Michael-Schumacher"]
documents = [
    processor.fetch_webpage_content(url)
    for url in urls if processor.fetch_webpage_content(url)]
article_text = "Your cleaned article text here..."
output_data = process_article(urls[0], documents,
                              "fun_facts_output.json")
