FROM pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime

RUN apt-get update && \
    apt-get install -y openjdk-21-jre-headless && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /code

# Copy requirements
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

# Copy the rest of the app
COPY ./app /code/app

EXPOSE 8055

# Default command
#CMD ["python", "-m", "app.main"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8055"]
