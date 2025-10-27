# エッジ監視システム クリーンアップスクリプト

param(
    [switch]$All = $false,
    [switch]$Images = $false
)

Write-Host "🧹 エッジ監視システムをクリーンアップします..." -ForegroundColor Yellow

$ProjectRoot = "edge-surveillance-system"

# プロジェクトディレクトリが存在する場合
if (Test-Path $ProjectRoot) {
    Set-Location $ProjectRoot
    
    # コンテナ停止・削除
    Write-Host "🛑 コンテナを停止・削除中..." -ForegroundColor Cyan
    docker-compose down --remove-orphans --volumes
    
    Set-Location ..
}

# Dockerイメージ削除
if ($Images -or $All) {
    Write-Host "🗑️  Dockerイメージを削除中..." -ForegroundColor Cyan
    
    $imageNames = @(
        "detector-capturing",
        "detector-processing", 
        "surveillance-disarmed",
        "surveillance-analyzing",
        "surveillance-alarm"
    )
    
    foreach ($imageName in $imageNames) {
        try {
            docker rmi "${imageName}:latest" 2>$null
            Write-Host "✅ $imageName イメージを削除しました" -ForegroundColor Green
        } catch {
            Write-Host "⚠️  $imageName イメージが見つかりませんでした" -ForegroundColor Yellow
        }
    }
}

# Dockerネットワーク削除
Write-Host "🌐 Dockerネットワークを削除中..." -ForegroundColor Cyan
try {
    docker network rm edge-surveillance-network 2>$null
    Write-Host "✅ edge-surveillance-network を削除しました" -ForegroundColor Green
} catch {
    Write-Host "⚠️  ネットワークが見つかりませんでした" -ForegroundColor Yellow
}

# プロジェクトディレクトリ削除
if ($All) {
    if (Test-Path $ProjectRoot) {
        Write-Host "📁 プロジェクトディレクトリを削除しますか? (y/N)" -ForegroundColor Yellow
        $response = Read-Host
        if ($response -eq 'y' -or $response -eq 'Y') {
            Remove-Item -Recurse -Force $ProjectRoot
            Write-Host "✅ プロジェクトディレクトリを削除しました" -ForegroundColor Green
        }
    }
}

# Docker システムクリーンアップ（オプション）
if ($All) {
    Write-Host "🔧 Dockerシステム全体をクリーンアップしますか? (y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq 'y' -or $response -eq 'Y') {
        docker system prune -f
        Write-Host "✅ Dockerシステムクリーンアップ完了" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "🎉 クリーンアップ完了!" -ForegroundColor Green