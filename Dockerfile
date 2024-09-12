# Use an official Python runtime as a parent image
ARG PYTHON_VERSION=3.10.12
FROM python:${PYTHON_VERSION}-slim

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Set the local timezone
ENV TZ=Asia/Riyadh

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt ./
RUN apt-get update && apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxcomposite1 libxrandr2 libgbm-dev libpangocairo-1.0-0
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps

# Copy the current directory contents into the container
COPY . .

CMD ["python", "-u", "main.py"]
