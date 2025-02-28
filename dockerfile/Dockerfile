FROM ubuntu:22.04

# Set non-interactive mode to avoid prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_LOG_LEVEL=error

# Install system dependencies (curl, sudo, jq, Python)
RUN apt-get update && apt-get install -y \
    curl \
    sudo \
    python3 \
    python3-pip \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama CLI
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install Python dependencies
RUN pip install ollama llama-index chromadb
RUN pip install pandas
RUN pip install numpy==1.25
RUN pip install yt-dlp
RUN pip install llama-index
RUN pip  install  llama-index-readers-web
RUN pip install llama-index-llms-ollama
RUN pip install opencv-python
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y
RUN pip install ffmpeg-python
RUN pip install coqui-tts

RUN apt-get update && \
    apt-get install -y espeak-ng && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install moondream==0.0.5
RUN pip install moviepy  
RUN python3 -m pip install moviepy==1.0.3 
RUN pip install --user requests  

# Set the working directory
WORKDIR /home