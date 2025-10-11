FROM pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime

# Install Python 3.12 and venv
RUN apt-get update && \
    apt-get install -y gcc openjdk-21-jre-headless && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

# Copy the rest of the app
COPY . .

# Default command
CMD ["python", "main.py"]
