# エッジ監視システム デプロイスクリプト (Enhanced)

param(
    [switch]$Build = $false,
    [switch]$Logs = $false,
    [string]$LogService = "event-bus",
    [switch]$Clean = $false
)

Write-Host "🚀 エッジ監視システムをデプロイします..." -ForegroundColor Green

# プロジェクトルートに移動
$ProjectRoot = "edge-surveillance-system"
if (-not (Test-Path $ProjectRoot)) {
    Write-Host "❌ プロジェクトディレクトリが見つかりません。setup.ps1を最初に実行してください。" -ForegroundColor Red
    exit 1
}

Set-Location $ProjectRoot

# 必要なファイルが存在するかチェック
$RequiredFiles = @(
    "docker-compose.yml",
    "event-bus/Dockerfile",
    "event-bus/app.py",
    "config/detector-config.yaml",
    "config/surveillance-config.yaml",
    "config/transition-rules.yaml"
)

$MissingFiles = @()
foreach ($file in $RequiredFiles) {
    if (-not (Test-Path $file)) {
        $MissingFiles += $file
    }
}

if ($MissingFiles.Count -gt 0) {
    Write-Host "❌ 以下のファイルが見つかりません:" -ForegroundColor Red
    $MissingFiles | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    Write-Host "必要なファイルを配置してから再実行してください。" -ForegroundColor Red
    exit 1
}

# クリーンアップオプション
if ($Clean) {
    Write-Host "🧹 既存のリソースをクリーンアップ中..." -ForegroundColor Yellow
    docker-compose down --remove-orphans --volumes 2>$null
    docker system prune -f 2>$null
}

# 既存コンテナの停止・削除
Write-Host "🛑 既存のコンテナを停止中..." -ForegroundColor Yellow
docker-compose down --remove-orphans 2>$null

# Dockerネットワークを明示的に作成
Write-Host "🌐 Dockerネットワークを準備中..." -ForegroundColor Cyan
$NetworkExists = $false
try {
    $networkInfo = docker network inspect edge-surveillance-network 2>$null
    if ($networkInfo) {
        $NetworkExists = $true
        Write-Host "✅ ネットワーク edge-surveillance-network が存在します" -ForegroundColor Green
    }
}
catch {
    $NetworkExists = $false
}

if (-not $NetworkExists) {
    docker network create edge-surveillance-network
    Write-Host "✅ ネットワーク edge-surveillance-network を作成しました" -ForegroundColor Green
}

if ($Build) {
    Write-Host "🔨 Dockerイメージをビルド中..." -ForegroundColor Cyan
    
    # プロファイルを使用してビルド専用サービスをビルド
    docker-compose --profile build-only build --no-cache
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ ビルドに失敗しました" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ すべてのイメージのビルドが完了しました" -ForegroundColor Green
}

# システムデプロイ
Write-Host "📦 システムをデプロイ中..." -ForegroundColor Cyan
docker-compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ デプロイが完了しました!" -ForegroundColor Green
    
    # サービス状態確認
    Write-Host "⏳ サービス起動を待機中..." -ForegroundColor Yellow
    Start-Sleep 5
    
    Write-Host "📊 サービス状態:" -ForegroundColor Cyan
    docker-compose ps
    
    # システム状態API確認
    Write-Host "🔍 システム状態を確認中..." -ForegroundColor Cyan
    $MaxRetries = 12
    $RetryCount = 0
    $HealthCheckPassed = $false
    
    while ($RetryCount -lt $MaxRetries -and -not $HealthCheckPassed) {
        Start-Sleep 5
        $RetryCount++
        Write-Host "Attempt $RetryCount/$MaxRetries..." -ForegroundColor Yellow
        
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:5000/status" -Method Get -TimeoutSec 10
            Write-Host "✅ イベントバスが正常に動作しています" -ForegroundColor Green
            Write-Host "システム状態:" -ForegroundColor Cyan
            $response | ConvertTo-Json -Depth 3
            $HealthCheckPassed = $true
        } 
        catch {
            Write-Host "⚠️  イベントバス確認中... ($($_.Exception.Message))" -ForegroundColor Yellow
        }
    }
    
    if (-not $HealthCheckPassed) {
        Write-Host "❌ イベントバスのヘルスチェックに失敗しました" -ForegroundColor Red
        Write-Host "ログを確認してください: docker-compose logs event-bus" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "🌐 アクセス情報:" -ForegroundColor Green
    Write-Host "  - イベントバス API: http://localhost:5000" -ForegroundColor White
    Write-Host "  - システム状態: http://localhost:5000/status" -ForegroundColor White
    Write-Host "  - ヘルスチェック: http://localhost:5000/health" -ForegroundColor White
    
    Write-Host ""
    Write-Host "📝 利用可能なコマンド:" -ForegroundColor Cyan
    Write-Host "  - docker-compose logs -f event-bus  # リアルタイムログ監視" -ForegroundColor White
    Write-Host "  - .\scripts\test.ps1                # システムテスト実行" -ForegroundColor White
    Write-Host "  - .\scripts\cleanup.ps1             # システムクリーンアップ" -ForegroundColor White
    
} else {
    Write-Host "❌ デプロイに失敗しました" -ForegroundColor Red
    Write-Host "エラーログ:" -ForegroundColor Yellow
    docker-compose logs --tail=20
    exit 1
}

# ログ表示オプション
if ($Logs) {
    Write-Host ""
    Write-Host "📝 $LogService サービスのログを表示します... (Ctrl+C で終了)" -ForegroundColor Cyan
    docker-compose logs -f $LogService
}