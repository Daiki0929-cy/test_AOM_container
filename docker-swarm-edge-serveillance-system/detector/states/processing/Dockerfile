FROM python:3.9-slim

WORKDIR /app

# OpenCV依存関係のインストール
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# YOLOv8モデルのダウンロード（初回起動時に自動ダウンロードされる）
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

COPY process.py .

ENV MACHINE_ID=detector
ENV STATE_NAME=processing
ENV EVENT_BUS_URL=http://event-bus:5000
ENV MODEL_PATH=yolov8n.pt

CMD ["python", "process.py"]