$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

$assetDir = "F:\AGENT\assets"
$iconPath = Join-Path $assetDir "hermes-ai-assistant.ico"
$shortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Hermes Dashboard.lnk"

New-Item -ItemType Directory -Force -Path $assetDir | Out-Null

$size = 256
$bitmap = New-Object System.Drawing.Bitmap $size, $size
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.Clear([System.Drawing.Color]::Transparent)

function New-Brush($r, $g, $b, $a = 255) {
  return New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb($a, $r, $g, $b))
}

function Fill-RoundedRectangle($graphics, $brush, $x, $y, $w, $h, $radius) {
  $path = New-Object System.Drawing.Drawing2D.GraphicsPath
  $diameter = $radius * 2
  $path.AddArc($x, $y, $diameter, $diameter, 180, 90)
  $path.AddArc($x + $w - $diameter, $y, $diameter, $diameter, 270, 90)
  $path.AddArc($x + $w - $diameter, $y + $h - $diameter, $diameter, $diameter, 0, 90)
  $path.AddArc($x, $y + $h - $diameter, $diameter, $diameter, 90, 90)
  $path.CloseFigure()
  $graphics.FillPath($brush, $path)
  $path.Dispose()
}

$blue = New-Brush 22 119 255
$cyan = New-Brush 73 232 211
$white = New-Brush 248 252 255
$face = New-Brush 225 244 255
$ink = New-Brush 16 45 92
$shadow = New-Brush 7 28 60 90

Fill-RoundedRectangle $graphics $shadow 18 22 220 216 50
Fill-RoundedRectangle $graphics $blue 18 16 220 216 50
Fill-RoundedRectangle $graphics $white 70 78 116 90 34
Fill-RoundedRectangle $graphics $face 82 92 92 62 24
Fill-RoundedRectangle $graphics $cyan 54 106 21 36 10
Fill-RoundedRectangle $graphics $cyan 181 106 21 36 10

$graphics.FillEllipse($ink, 96, 114, 17, 17)
$graphics.FillEllipse($ink, 143, 114, 17, 17)

$smilePen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 16, 45, 92)), 5
$graphics.DrawArc($smilePen, 103, 124, 50, 30, 20, 140)

$whitePen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 248, 252, 255)), 8
$graphics.DrawLine($whitePen, 128, 78, 128, 51)
$graphics.FillEllipse($cyan, 116, 34, 24, 24)

$cyanPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 73, 232, 211)), 7
$graphics.DrawLine($cyanPen, 66, 192, 101, 192)
$graphics.DrawLine($cyanPen, 155, 192, 190, 192)
$graphics.DrawLine($cyanPen, 101, 192, 117, 176)
$graphics.DrawLine($cyanPen, 155, 192, 139, 176)

foreach ($point in @(@(66, 192), @(190, 192), @(117, 176), @(139, 176))) {
  $graphics.FillEllipse($white, $point[0] - 7, $point[1] - 7, 14, 14)
}

$font = New-Object System.Drawing.Font "Segoe UI", 34, ([System.Drawing.FontStyle]::Bold)
$graphics.DrawString("H", $font, $white, 111, 181)

$handle = $bitmap.GetHicon()
$icon = [System.Drawing.Icon]::FromHandle($handle)
$stream = [System.IO.File]::Open($iconPath, [System.IO.FileMode]::Create)
$icon.Save($stream)
$stream.Close()

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.IconLocation = $iconPath
$shortcut.Save()

$graphics.Dispose()
$bitmap.Dispose()
$icon.Dispose()

Write-Output $iconPath
Write-Output $shortcutPath
