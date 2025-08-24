# エッジ監視システム テストスクリプト (Enhanced)

param(
    [switch]$Verbose = $false,
    [switch]$Interactive = $false,
    [int]$TestInterval = 3
)

Write-Host "🧪 エッジ監視システムのテストを開始します..." -ForegroundColor Green

# プロジェクトディレクトリに移動
$ProjectRoot = "edge-surveillance-system"
if (Test-Path $ProjectRoot) {
    Set-Location $ProjectRoot
}

function Show-TestResult {
    param([string]$TestName, [bool]$Success, [string]$Details = "")
    
    if ($Success) {
        Write-Host "✅ $TestName" -ForegroundColor Green
        if ($Verbose -and $Details) {
            Write-Host "   Details: $Details" -ForegroundColor Gray
        }
    } else {
        Write-Host "❌ $TestName" -ForegroundColor Red
        if ($Details) {
            Write-Host "   Error: $Details" -ForegroundColor Yellow
        }
    }
}

function Wait-ForInput {
    if ($Interactive) {
        Write-Host "Press Enter to continue..." -ForegroundColor Cyan
        Read-Host
    } else {
        Start-Sleep $TestInterval
    }
}

# テスト1: 基本接続テスト
Write-Host "`n1️⃣  基本接続テスト..." -ForegroundColor Cyan

$BaseUrlReachable = $false
$StatusResponse = $null

try {
    $StatusResponse = Invoke-RestMethod -Uri "http://localhost:5000/status" -Method Get -TimeoutSec 10
    $BaseUrlReachable = $true
    Show-TestResult "イベントバスへの接続" $true "Status API accessible"
    
    Write-Host "システム初期状態:" -ForegroundColor Yellow
    $StatusResponse | ConvertTo-Json -Depth 3 | Write-Host
    
} catch {
    Show-TestResult "イベントバスへの接続" $false $_.Exception.Message
    Write-Host "システムが起動しているか確認してください" -ForegroundColor Yellow
    Write-Host "Command: docker-compose ps" -ForegroundColor Cyan
    exit 1
}

Wait-ForInput

# テスト2: ヘルスチェック
Write-Host "2️⃣  ヘルスチェック..." -ForegroundColor Cyan

try {
    $HealthResponse = Invoke-RestMethod -Uri "http://localhost:5000/health" -Method Get -TimeoutSec 5
    Show-TestResult "ヘルスチェック" $true "Health endpoint responsive"
    
    if ($Verbose) {
        Write-Host "Health Response:" -ForegroundColor Yellow
        $HealthResponse | ConvertTo-Json | Write-Host
    }
    
} catch {
    Show-TestResult "ヘルスチェック" $false $_.Exception.Message
}

Wait-ForInput

# テスト3: Detector状態遷移テスト
Write-Host "3️⃣  Detector状態遷移テスト..." -ForegroundColor Cyan

# 3a: capturing -> processing
Write-Host "🔄 テスト: capturing -> processing" -ForegroundColor Yellow
try {
    $TransitionRequest = @{
        machine_id = "detector"
        transition_name = "image_captured"
        event_data = @{
            image_path = "/tmp/test_image_$(Get-Date -Format 'yyyyMMdd_HHmmss').jpg"
            timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
            test_mode = $true
            image_size = @(640, 480, 3)
        }
    }
    
    $TransitionResponse = Invoke-RestMethod -Uri "http://localhost:5000/transition" -Method Post -Body ($TransitionRequest | ConvertTo-Json) -ContentType "application/json" -TimeoutSec 10
    
    Show-TestResult "Detector遷移 (capturing->processing)" $true "$($TransitionResponse.old_state) -> $($TransitionResponse.new_state)"
    
    if ($Verbose) {
        Write-Host "Transition Response:" -ForegroundColor Yellow
        $TransitionResponse | ConvertTo-Json | Write-Host
    }
    
} catch {
    Show-TestResult "Detector遷移 (capturing->processing)" $false $_.Exception.Message
}

Start-Sleep 2

# 状態確認
try {
    $StatusAfterTransition = Invoke-RestMethod -Uri "http://localhost:5000/status" -Method Get -TimeoutSec 5
    Write-Host "遷移後の Detector 状態: $($StatusAfterTransition.detector.current_state)" -ForegroundColor Yellow
} catch {
    Write-Host "⚠️  状態確認に失敗" -ForegroundColor Yellow
}

Wait-ForInput

# テスト4: 人物検出シミュレーション
Write-Host "4️⃣  人物検出シミュレーション..." -ForegroundColor Cyan

try {
    $PersonDetectionRequest = @{
        machine_id = "detector"  
        transition_name = "person_detected"
        event_data = @{
            detection_confidence = 0.89
            timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
            person_count = 1
            test_mode = $true
            detected_persons = @(
                @{
                    bbox = @(200, 150, 400, 350)
                    confidence = 0.89
                }
            )
        }
    }
    
    $PersonDetectionResponse = Invoke-RestMethod -Uri "http://localhost:5000/transition" -Method Post -Body ($PersonDetectionRequest | ConvertTo-Json -Depth 4) -ContentType "application/json" -TimeoutSec 10
    
    Show-TestResult "人物検出イベント送信" $true "Triggered events: $($PersonDetectionResponse.triggered_events)"
    
    if ($Verbose) {
        Write-Host "Person Detection Response:" -ForegroundColor Yellow
        $PersonDetectionResponse | ConvertTo-Json -Depth 3 | Write-Host
    }
    
} catch {
    Show-TestResult "人物検出イベント送信" $false $_.Exception.Message
}

Start-Sleep 3

# テスト5: Surveillance システム連携確認
Write-Host "5️⃣  Surveillance システム連携確認..." -ForegroundColor Cyan

try {
    $FinalStatus = Invoke-RestMethod -Uri "http://localhost:5000/status" -Method Get -TimeoutSec 5
    
    $DetectorState = $FinalStatus.detector.current_state
    $SurveillanceState = $FinalStatus.surveillance.current_state
    
    Write-Host "Final System State:" -ForegroundColor Yellow
    Write-Host "  - Detector: $DetectorState" -ForegroundColor White
    Write-Host "  - Surveillance: $SurveillanceState" -ForegroundColor White
    
    # 期待される状態をチェック
    $ExpectedSurveillanceStates = @("analyzing", "disarmed")
    $SurveillanceStateCorrect = $SurveillanceState -in $ExpectedSurveillanceStates
    
    Show-TestResult "Surveillance システム連携" $SurveillanceStateCorrect "State: $SurveillanceState"
    
    if ($Verbose) {
        Write-Host "Complete System Status:" -ForegroundColor Yellow
        $FinalStatus | ConvertTo-Json -Depth 3 | Write-Host
    }
    
} catch {
    Show-TestResult "Surveillance システム連携確認" $false $_.Exception.Message
}

Wait-ForInput

# テスト6: コンテナ状態確認
Write-Host "6️⃣  コンテナ状態確認..." -ForegroundColor Cyan

try {
    $DockerPsOutput = docker-compose ps --format table
    if ($LASTEXITCODE -eq 0) {
        Show-TestResult "Docker Compose サービス確認" $true "Services are running"
        Write-Host "Service Status:" -ForegroundColor Yellow
        $DockerPsOutput | Write-Host
    } else {
        Show-TestResult "Docker Compose サービス確認" $false "docker-compose ps failed"
    }
} catch {
    Show-TestResult "Docker Compose サービス確認" $false $_.Exception.Message
}

Wait-ForInput

# テスト7: ログサンプリング
Write-Host "7️⃣  ログサンプリング..." -ForegroundColor Cyan

try {
    Write-Host "Event Bus 最新ログ (最新10行):" -ForegroundColor Yellow
    $LogOutput = docker-compose logs --tail=10 event-bus 2>$null
    if ($LASTEXITCODE -eq 0) {
        Show-TestResult "ログアクセス" $true "Log retrieval successful"
        if ($Verbose) {
            $LogOutput | Write-Host
        }
    } else {
        Show-TestResult "ログアクセス" $false "Failed to retrieve logs"
    }
} catch {
    Show-TestResult "ログアクセス" $false $_.Exception.Message
}

# テスト結果サマリー
Write-Host ""
Write-Host "🎉 テスト完了!" -ForegroundColor Green
Write-Host ""

# 推奨次ステップ
Write-Host "📋 推奨次ステップ:" -ForegroundColor Cyan
Write-Host "  - 継続監視: docker-compose logs -f event-bus" -ForegroundColor White
Write-Host "  - 手動テスト: curl -X GET http://localhost:5000/status" -ForegroundColor White
Write-Host "  - システム停止: docker-compose down" -ForegroundColor White
Write-Host "  - 完全クリーンアップ: .\scripts\cleanup.ps1 -All" -ForegroundColor White

# インタラクティブモードの場合、継続監視オプション
if ($Interactive) {
    Write-Host ""
    Write-Host "継続的なログ監視を開始しますか? (y/N)" -ForegroundColor Yellow
    $ContinueResponse = Read-Host
    
    if ($ContinueResponse -eq 'y' -or $ContinueResponse -eq 'Y') {
        Write-Host "🔍 リアルタイムログ監視を開始します... (Ctrl+C で終了)" -ForegroundColor Cyan
        docker-compose logs -f event-bus
    }
}