# -*- coding: utf-8 -*-
"""Package the pre-compiled Foolproof One-Click Release ZIP (傻瓜版) for friends.

Outputs:
  dist/爱弥斯Antigravity开机动画_傻瓜版_v1.0.zip
"""
import os
import shutil
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIN_BUILD = os.path.join(REPO_ROOT, "windows-overlay", "build")
PLUG_DIR = os.path.join(REPO_ROOT, "antigravity-plugin")
DIST_DIR = os.path.join(REPO_ROOT, "dist")
STAGE_NAME = "爱弥斯Antigravity开机动画_傻瓜版"
STAGE_DIR = os.path.join(DIST_DIR, STAGE_NAME)
ZIP_PATH = os.path.join(DIST_DIR, f"{STAGE_NAME}_v1.0.zip")


INSTALL_PREBUILT_PS1 = r"""# 直接安装预编译好的爱弥斯开机动画（傻瓜版，无需编译，不修改 Antigravity 本体）
param([string]$Dir)
$ErrorActionPreference = 'Stop'
$name = 'AemeathAntigravityBoot'
function Test-Writable([string]$p) {
  try { New-Item -ItemType Directory -Force -Path $p | Out-Null; $f = Join-Path $p ('.w' + [guid]::NewGuid().ToString('N')); [IO.File]::WriteAllText($f, ''); Remove-Item $f -Force; return $true } catch { return $false }
}
if (-not $Dir) { $Dir = $env:AGBA_DIR }
if (-not $Dir) {
  $disks = @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' -ErrorAction SilentlyContinue | Where-Object { $_.DeviceID -ne $env:SystemDrive -and $_.FreeSpace -gt 1GB } | Sort-Object FreeSpace -Descending)
  foreach ($d in $disks) { $p = "$($d.DeviceID)\AIBootAnimations"; if (Test-Writable $p) { $Dir = $p; break } }
  if (-not $Dir) { $Dir = "$env:LOCALAPPDATA\Programs" }
}
if (-not (Test-Writable $Dir)) { throw "无法写入目录 $Dir（没有写入权限）" }
$dest = Join-Path $Dir $name

Get-Process $name -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process $name -ErrorAction SilentlyContinue | Wait-Process -Timeout 10 -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

$run = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
if (-not (Test-Path $run)) { New-Item -Path $run -Force | Out-Null }
$old = (Get-ItemProperty -Path $run -Name $name -ErrorAction SilentlyContinue).$name
if ($old) {
  $oldDir = Split-Path ($old.Trim('"')) -Parent
  if ($oldDir -and ($oldDir.TrimEnd('\') -ne $dest.TrimEnd('\')) -and (Test-Path "$oldDir\$name.exe")) {
    Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\DirectX\UserGpuPreferences' -Name "$oldDir\$name.exe" -ErrorAction SilentlyContinue
    if ((Split-Path $oldDir -Leaf) -eq $name) { Remove-Item $oldDir -Recurse -Force -ErrorAction SilentlyContinue }
  }
}

if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Force "$PSScriptRoot\$name.exe" "$dest\"
Copy-Item -Force "$PSScriptRoot\uninstall.ps1" "$dest\"
Copy-Item -Force "$PSScriptRoot\LICENSE" "$dest\"
Copy-Item -Recurse -Force "$PSScriptRoot\assets" "$dest\assets"

Set-ItemProperty -Path $run -Name $name -Value "`"$dest\$name.exe`""
Start-Process "$dest\$name.exe" -ArgumentList '--settings'
Write-Host ''
Write-Host "✦ 安装完成！程序已安装到：$dest"
Write-Host '  右下角托盘已出现粉青四芒星图标，并已弹出设置窗口。'
Write-Host '  在设置窗口或右键托盘图标即可自由切换 方案 A / B / C 以及自定义开屏台词！'
Write-Host '  下次打开 Antigravity 就会自动播放爱弥斯开场动画。'
"""

CMD_TRY = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
taskkill /f /im AemeathAntigravityBoot.exe >nul 2>nul
echo ✦ 正在启动爱弥斯开机动画（仅本次试玩，不写入开机自启）...
echo   提示：请先确保 Antigravity 窗口已打开，设置窗口会自动弹出，可随时切换 A/B/C 方案与自定义台词。
start "" "%~dp0bin\\AemeathAntigravityBoot.exe" --settings --play-now
"""

CMD_INSTALL = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0bin\\install-prebuilt.ps1"
pause
"""

CMD_PLUGIN = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0plugin\\install-plugin.ps1"
pause
"""

CMD_UNINSTALL = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0bin\\uninstall.ps1"
pause
"""

README_TXT = """============================================================
  爱弥斯（Aemeath · 飞行雪绒）Antigravity 开场动画 · 傻瓜版
============================================================

【特色亮点】
1. 100%《鸣潮》库洛官方原片素材 + 14.5 秒《于电子星海轻歌》快启音轨
2. 内置 A / B / C 三套演出方案随时一键切换：
   - 方案 A · 一镜到底「星海睁眼觉醒」
   - 方案 B · 双形态切换「电子幽灵 × 隧者机兵」
   - 方案 C · 多幕剧情混剪「纸飞机 / 祝福 / 拯救 / 远航星」
3. 支持自定义思源宋体开屏台词（默认：拯救世界的事，就交给我吧……），修改即时生效
4. 零入侵：完全不修改 Antigravity 本体文件，随时可一键彻底卸载

【使用步骤（解压后再运行！）】
※ 请先将本压缩包完整解压到任意文件夹，不要直接在压缩软件里双击运行！

👉 想先看效果（不写入开机自启）：
   先打开 Antigravity，再双击【1_点我试玩(不改开机自启).cmd】
   （也会弹出设置窗口，可直接切换方案 A/B/C、修改台词、调透明度与音量）

👉 觉得满意，设为每次打开 Antigravity 自动播放：
   双击【2_点我安装(开机自启).cmd】
   （安装后右下角托盘会出现粉青色四芒星 ✦ 图标，左键/右键随时控制）

👉 同时安装 Antigravity 左侧 Plugins 栏内置插件（需本机有 Python 3）：
   双击【3_安装Antigravity侧栏插件.cmd】，重启或刷新 Antigravity 即可在左侧栏看到「爱弥斯开场」

👉 没开 Antigravity 也想先在浏览器预览：
   直接双击【4_浏览器直接预览动画.html】即可体验（右下角悬停可切 A/B/C 方案与改台词）

👉 不想要了，彻底清理干净：
   右键托盘 ✦ 图标 →「卸载爱弥斯开机动画…」，或直接双击【5_彻底卸载.cmd】

【开源项目地址】
https://github.com/Fantasicrap/Aemeath-Antigravity-Boot-Animation
"""


def write_text(path, text, bom=False):
    enc = "utf-8-sig" if bom else "utf-8"
    with open(path, "w", encoding=enc, newline="\r\n") as f:
        f.write(text)


def main():
    exe_path = os.path.join(WIN_BUILD, "AemeathAntigravityBoot.exe")
    if not os.path.exists(exe_path):
        raise FileNotFoundError(f"Missing prebuilt exe: {exe_path} (run windows-overlay/build.ps1 first)")

    os.makedirs(DIST_DIR, exist_ok=True)
    if os.path.exists(STAGE_DIR):
        shutil.rmtree(STAGE_DIR)
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    bin_dst = os.path.join(STAGE_DIR, "bin")
    plug_dst = os.path.join(STAGE_DIR, "plugin")
    os.makedirs(bin_dst, exist_ok=True)
    os.makedirs(os.path.join(plug_dst, "assets"), exist_ok=True)

    # Copy prebuilt Windows overlay + all 3 modes' official MP4s
    shutil.copy2(exe_path, os.path.join(bin_dst, "AemeathAntigravityBoot.exe"))
    shutil.copy2(os.path.join(WIN_BUILD, "uninstall.ps1"), os.path.join(bin_dst, "uninstall.ps1"))
    shutil.copy2(os.path.join(WIN_BUILD, "LICENSE"), os.path.join(bin_dst, "LICENSE"))
    shutil.copytree(os.path.join(WIN_BUILD, "assets"), os.path.join(bin_dst, "assets"))
    write_text(os.path.join(bin_dst, "install-prebuilt.ps1"), INSTALL_PREBUILT_PS1, bom=True)

    # Copy Antigravity MCP App plugin
    for fn in ("plugin.json", "mcp_config.json", "server.py", "intro.html", "install-plugin.ps1"):
        shutil.copy2(os.path.join(PLUG_DIR, fn), os.path.join(plug_dst, fn))
    shutil.copy2(os.path.join(PLUG_DIR, "assets", "logo.svg"), os.path.join(plug_dst, "assets", "logo.svg"))

    # Copy root foolproof launchers & standalone browser preview
    write_text(os.path.join(STAGE_DIR, "1_点我试玩(不改开机自启).cmd"), CMD_TRY, bom=False)
    write_text(os.path.join(STAGE_DIR, "2_点我安装(开机自启).cmd"), CMD_INSTALL, bom=False)
    write_text(os.path.join(STAGE_DIR, "3_安装Antigravity侧栏插件.cmd"), CMD_PLUGIN, bom=False)
    shutil.copy2(os.path.join(PLUG_DIR, "intro.html"), os.path.join(STAGE_DIR, "4_浏览器直接预览动画.html"))
    write_text(os.path.join(STAGE_DIR, "5_彻底卸载.cmd"), CMD_UNINSTALL, bom=False)
    write_text(os.path.join(STAGE_DIR, "使用说明.txt"), README_TXT, bom=True)

    # Create ZIP (use ZIP_STORED for already-compressed MP4s so creation & extraction are blazing fast, ZIP_DEFLATED for text/exe)
    with zipfile.ZipFile(ZIP_PATH, "w") as zf:
        for dirpath, _, filenames in os.walk(STAGE_DIR):
            for fn in sorted(filenames):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, DIST_DIR)
                comp = zipfile.ZIP_STORED if fn.lower().endswith((".mp4", ".webp", ".png", ".jpg")) else zipfile.ZIP_DEFLATED
                zf.write(full, rel, compress_type=comp)

    sz = os.path.getsize(ZIP_PATH)
    print(f"Foolproof release ZIP built: {ZIP_PATH} ({sz / 1048576:.2f} MiB)")


if __name__ == "__main__":
    main()
