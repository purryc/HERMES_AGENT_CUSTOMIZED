param(
    [string]$ApiBaseUrl = "http://127.0.0.1:8787",
    [string]$Text = "draft: Help me write a short progress update for today's Hermes agent work.",
    [string]$Sender = "me"
)

$ErrorActionPreference = "Stop"

$payload = @{
    message_id = "wx-" + [guid]::NewGuid().ToString("N").Substring(0, 8)
    text = $Text
    sender = $Sender
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "$ApiBaseUrl/api/messages/wechat" `
    -ContentType "application/json" `
    -Body $payload
