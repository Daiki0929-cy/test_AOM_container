docker desktopを開く

powershellで以下の手順でコマンド

docker init

docker network create edge-surveillance-network

docker compose --profile build-only build --no-cache

docker compose up -d
