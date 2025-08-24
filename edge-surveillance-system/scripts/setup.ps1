# エッジ監視システム セットアップスクリプト

Write-Host "🔧 エッジ監視システムのセットアップを開始します..." -ForegroundColor Green

# 必要な環境確認
Write-Host "📋 環境確認中..."

# Docker確認
try {
    docker --version | Out-Null
    Write-Host "✅ Docker が利用可能です" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker がインストールされていません" -ForegroundColor Red
    exit 1
}

# Docker Compose確認
try {
    docker-compose --version | Out-Null
    Write-Host "✅ Docker Compose が利用可能です" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Compose がインストールされていません" -ForegroundColor Red
    exit 1
}

# プロジェクトディレクトリの作成
Write-Host "📁 プロジェクトディレクトリを作成中..."

$ProjectRoot = "edge-surveillance-system"

if (Test-Path $ProjectRoot) {
    Write-Host "⚠️  既存のプロジェクトディレクトリが存在します。削除しますか? (y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq 'y' -or $response -eq 'Y') {
        Remove-Item -Recurse -Force $ProjectRoot
        Write-Host "🗑️  既存ディレクトリを削除しました" -ForegroundColor Yellow
    } else {
        Write-Host "❌ セットアップを中断しました" -ForegroundColor Red
        exit 1
    }
}

# ディレクトリ構造作成
$Directories = @(
    "$ProjectRoot",
    "$ProjectRoot/event-bus",
    "$ProjectRoot/detector/states/capturing",
    "$ProjectRoot/detector/states/processing", 
    "$ProjectRoot/surveillance/states/disarmed",
    "$ProjectRoot/surveillance/states/analyzing",
    "$ProjectRoot/surveillance/states/alarm",
    "$ProjectRoot/config",
    "$ProjectRoot/scripts",
    "$ProjectRoot/kubernetes"
)

foreach ($dir in $Directories) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

Write-Host "✅ ディレクトリ構造を作成しました" -ForegroundColor Green

# Dockerネットワーク作成
Write-Host "🌐 Dockerネットワークを作成中..."
try {
    docker network create edge-surveillance-network 2>$null
    Write-Host "✅ edge-surveillance-network を作成しました" -ForegroundColor Green
} catch {
    Write-Host "⚠️  ネットワークは既に存在しています" -ForegroundColor Yellow
}

# 権限設定
Write-Host "🔐 権限設定中..."
if ($IsLinux -or $IsMacOS) {
    # Linux/macOSの場合のDocker socket権限
    Write-Host "Unix系OSでの追加設定が必要な場合があります"
}

Write-Host ""
Write-Host "🎉 セットアップが完了しました!" -ForegroundColor Green
Write-Host "次のステップ:" -ForegroundColor Cyan
Write-Host "  1. 必要なファイルをコピーしてください"  
Write-Host "  2. scripts/deploy.ps1 を実行してシステムをデプロイしてください"
Write-Host "  3. scripts/test.ps1 でテストを実行してください"