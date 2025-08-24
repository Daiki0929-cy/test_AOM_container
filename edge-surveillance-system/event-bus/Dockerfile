FROM python:3.9-slim

WORKDIR /app

# システム依存関係のインストール
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY . .

# Dockerソケットアクセス権限設定
RUN usermod -aG docker root

EXPOSE 5000

CMD ["python", "app.py"]