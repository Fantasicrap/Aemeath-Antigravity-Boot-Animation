// 爱弥斯开机动画（《鸣潮》Aemeath · 飞行雪绒）· Windows 版 —— 外置浮层小程序
// 原生全支持主流 AI 桌面端：Antigravity / DeepSeek Harness / Claude Desktop / Codex (ChatGPT)！
// 支持多窗口同时独立播放、A / B / C 三套演出方案一键切换、自定义思源宋体台词（默认：拯救世界的事，就交给我吧……）。
// 检测目标窗口启动 → 盖在其主窗口上播放 14.5s《于电子星海轻歌》快启开屏动画 → 五次方丝滑淡出，进入半透明、点击穿透无缝循环背景。
// 全程不修改任何软件本体文件。使用系统自带 .NET Framework 4.x 编译器直编（C# 5 语法），无需安装任何 SDK。
//
// Based on wynneceles/ai-boot-animations & xxjj2024/Roxy-Antigravity-Boot-Animation (GNU GPL v3)
// This program is free software under the GNU General Public License v3.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Effects;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Microsoft.Win32;
using WF = System.Windows.Forms;
using SD = System.Drawing;

namespace AemeathAntigravityBoot
{
    // ───────────────────────── 配置 ─────────────────────────

    public class Subtitle
    {
        public string Text;
        public string SubText;
        public double Start;
        public double End;
        public Subtitle(string t, string sub, double s, double e) { Text = t; SubText = sub ?? ""; Start = s; End = e; }
    }

    public class Config
    {
        public string Mode = "a";                  // 演出方案：a = 一镜到底星海觉醒 / b = 双形态隧者机兵 / c = 多幕剧情浓缩
        public bool EnableAntigravity = true;      // 监听 Antigravity.exe
        public bool EnableDeepSeekHarness = true;  // 监听 DeepSeek Harness.exe
        public bool EnableClaude = true;           // 监听 Claude Desktop (claude.exe)
        public bool EnableCodex = true;            // 监听 Codex / ChatGPT Desktop (Codex.exe / ChatGPT.exe)
        public bool PlayIntro = true;              // 启动时播放开屏动画
        public bool LoopBackground = true;         // 开屏后保留半透明循环背景
        public double FadeStartSeconds = 12.60;    // 14.5s 快启版在 12.60s 高潮收束处启动五次方丝滑淡出
        public double FadeDurationSeconds = 1.90;  // 12.60 + 1.90 = 14.50s，无缝接 loop-x2.mp4
        public double ResidualAlpha = 0.25;        // 循环背景不透明度
        public double IntroVolume = 0.85;          // 开屏音量（再乘系统音量）
        public bool ShowSubtitles = true;          // 动态渲染自定义思源宋体台词，修改即时生效，无需重新渲染 MP4
        public double SubtitleFadeSeconds = 0.45;
        public double SubtitleWidthRatio = 0.65;
        public List<Subtitle> Subtitles = new List<Subtitle> {
            new Subtitle("拯救世界的事，就交给我吧……", "Leave saving the world to me...", 4.65, 12.65),
        };

        public static string NormalizeMode(string m)
        {
            if (string.IsNullOrEmpty(m)) return "a";
            string low = m.Trim().ToLowerInvariant();
            if (low == "a" || low == "b" || low == "c") return low;
            return "a";
        }

        public static string ModeDisplayName(string m)
        {
            string k = NormalizeMode(m);
            if (k == "b") return "方案 B · 双形态切换（电子幽灵 × 隧者机兵）";
            if (k == "c") return "方案 C · 多幕剧情（纸飞机 / 祝福 / 拯救 / 远航星）";
            return "方案 A · 一镜到底（电子星海觉醒）";
        }

        public bool IsTargetEnabled(string appKey)
        {
            if (appKey == Finder.AppAntigravity) return EnableAntigravity;
            if (appKey == Finder.AppDeepSeekHarness) return EnableDeepSeekHarness;
            if (appKey == Finder.AppClaude) return EnableClaude;
            if (appKey == Finder.AppCodex) return EnableCodex;
            return true;
        }

        public static string Dir { get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "AemeathAntigravityBoot"); } }
        public static string FilePath { get { return Path.Combine(Dir, "config.json"); } }

        static double D(Dictionary<string, object> d, string k, double def)
        {
            object v; if (d.TryGetValue(k, out v) && v != null) { try { return Convert.ToDouble(v, CultureInfo.InvariantCulture); } catch { } }
            return def;
        }
        static bool B(Dictionary<string, object> d, string k, bool def)
        {
            object v; if (d.TryGetValue(k, out v) && v is bool) return (bool)v;
            return def;
        }
        static string S(Dictionary<string, object> d, string k, string def)
        {
            object v; if (d.TryGetValue(k, out v) && v != null) return Convert.ToString(v);
            return def;
        }

        public static Config Load()
        {
            var c = new Config();
            try
            {
                if (File.Exists(FilePath))
                {
                    var d = new JavaScriptSerializer().DeserializeObject(File.ReadAllText(FilePath, Encoding.UTF8)) as Dictionary<string, object>;
                    if (d != null)
                    {
                        c.Mode = NormalizeMode(S(d, "mode", c.Mode));
                        c.EnableAntigravity = B(d, "enableAntigravity", c.EnableAntigravity);
                        c.EnableDeepSeekHarness = B(d, "enableDeepSeekHarness", c.EnableDeepSeekHarness);
                        c.EnableClaude = B(d, "enableClaude", c.EnableClaude);
                        c.EnableCodex = B(d, "enableCodex", c.EnableCodex);
                        c.PlayIntro = B(d, "playIntro", c.PlayIntro);
                        c.LoopBackground = B(d, "loopBackground", c.LoopBackground);
                        c.FadeStartSeconds = D(d, "fadeStartSeconds", c.FadeStartSeconds);
                        c.FadeDurationSeconds = D(d, "fadeDurationSeconds", c.FadeDurationSeconds);
                        c.ResidualAlpha = D(d, "residualAlpha", c.ResidualAlpha);
                        c.IntroVolume = D(d, "introVolume", c.IntroVolume);
                        c.ShowSubtitles = B(d, "showSubtitles", c.ShowSubtitles);
                        c.SubtitleFadeSeconds = D(d, "subtitleFadeSeconds", c.SubtitleFadeSeconds);
                        c.SubtitleWidthRatio = D(d, "subtitleWidthRatio", c.SubtitleWidthRatio);
                        object subs;
                        if (d.TryGetValue("subtitles", out subs) && subs is object[])
                        {
                            var list = new List<Subtitle>();
                            foreach (var o in (object[])subs)
                            {
                                var s = o as Dictionary<string, object>;
                                if (s == null || !s.ContainsKey("text")) continue;
                                list.Add(new Subtitle(
                                    Convert.ToString(s["text"]),
                                    S(s, "subText", ""),
                                    D(s, "start", 4.65),
                                    D(s, "end", 12.65)));
                            }
                            if (list.Count > 0) c.Subtitles = list;
                        }
                    }
                }
            }
            catch (Exception e) { Log.W("设置文件读不了，用默认值：" + e.Message); }
            c.Save();
            return c;
        }

        static string N(double v) { return v.ToString("0.###", CultureInfo.InvariantCulture); }
        static string L(bool v) { return v ? "true" : "false"; }

        public void Save()
        {
            try
            {
                Directory.CreateDirectory(Dir);
                var js = new JavaScriptSerializer();
                var sb = new StringBuilder();
                sb.Append("{\n");
                sb.Append("  \"mode\" : " + js.Serialize(NormalizeMode(Mode)) + ",\n");
                sb.Append("  \"enableAntigravity\" : " + L(EnableAntigravity) + ",\n");
                sb.Append("  \"enableDeepSeekHarness\" : " + L(EnableDeepSeekHarness) + ",\n");
                sb.Append("  \"enableClaude\" : " + L(EnableClaude) + ",\n");
                sb.Append("  \"enableCodex\" : " + L(EnableCodex) + ",\n");
                sb.Append("  \"fadeDurationSeconds\" : " + N(FadeDurationSeconds) + ",\n");
                sb.Append("  \"fadeStartSeconds\" : " + N(FadeStartSeconds) + ",\n");
                sb.Append("  \"introVolume\" : " + N(IntroVolume) + ",\n");
                sb.Append("  \"loopBackground\" : " + L(LoopBackground) + ",\n");
                sb.Append("  \"playIntro\" : " + L(PlayIntro) + ",\n");
                sb.Append("  \"residualAlpha\" : " + N(ResidualAlpha) + ",\n");
                sb.Append("  \"showSubtitles\" : " + L(ShowSubtitles) + ",\n");
                sb.Append("  \"subtitleFadeSeconds\" : " + N(SubtitleFadeSeconds) + ",\n");
                sb.Append("  \"subtitleWidthRatio\" : " + N(SubtitleWidthRatio) + ",\n");
                sb.Append("  \"subtitles\" : [\n");
                for (int i = 0; i < Subtitles.Count; i++)
                {
                    var s = Subtitles[i];
                    sb.Append("    {\n");
                    sb.Append("      \"start\" : " + N(s.Start) + ",\n");
                    sb.Append("      \"end\" : " + N(s.End) + ",\n");
                    sb.Append("      \"text\" : " + js.Serialize(s.Text ?? "") + ",\n");
                    sb.Append("      \"subText\" : " + js.Serialize(s.SubText ?? "") + "\n");
                    sb.Append("    }");
                    sb.Append(i < Subtitles.Count - 1 ? ",\n" : "\n");
                }
                sb.Append("  ]\n}\n");
                File.WriteAllText(FilePath, sb.ToString(), new UTF8Encoding(false));
            }
            catch (Exception e) { Log.W("设置文件写不了：" + e.Message); }
        }
    }

    // ───────────────────────── 显卡偏好与日志 ─────────────────────────

    public static class GpuPref
    {
        const string Key = @"Software\Microsoft\DirectX\UserGpuPreferences";
        public static void Ensure()
        {
            try
            {
                string exe = Process.GetCurrentProcess().MainModule.FileName;
                using (var k = Registry.CurrentUser.CreateSubKey(Key))
                {
                    if (k == null) return;
                    var cur = k.GetValue(exe) as string;
                    if (cur != null) { Log.W("显卡偏好已有设置（" + cur + "），不改动"); return; }
                    var gpus = ListGpus();
                    if (gpus.Count < 2) { Log.W("显卡：" + (gpus.Count == 0 ? "未识别" : string.Join("、", gpus)) + "，不用切换独显"); return; }
                    k.SetValue(exe, "GpuPreference=2;", RegistryValueKind.String);
                    Log.W("检测到多块显卡（" + string.Join("、", gpus) + "），已设为用高性能显卡渲染");
                }
            }
            catch (Exception ex) { Log.W("独显设置失败：" + ex.Message); }
        }

        static List<string> ListGpus()
        {
            var list = new List<string>();
            using (var q = new System.Management.ManagementObjectSearcher("SELECT Name FROM Win32_VideoController"))
            {
                foreach (System.Management.ManagementBaseObject o in q.Get())
                {
                    var name = (o["Name"] as string ?? "").Trim();
                    if (System.Text.RegularExpressions.Regex.IsMatch(name, "NVIDIA|GeForce|Quadro|RTX|AMD|Radeon|Intel|Arc", System.Text.RegularExpressions.RegexOptions.IgnoreCase))
                        list.Add(name);
                }
            }
            return list;
        }
    }

    public static class Log
    {
        public static string FilePath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AemeathAntigravityBoot", "log.txt");
        static readonly object Lock = new object();
        public static void W(string msg)
        {
            try
            {
                lock (Lock)
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(FilePath));
                    var fi = new FileInfo(FilePath);
                    if (fi.Exists && fi.Length > 2 * 1024 * 1024) fi.Delete();
                    File.AppendAllText(FilePath, DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " " + msg + "\r\n", Encoding.UTF8);
                }
            }
            catch { }
        }
    }

    // ───────────────────────── Win32 ─────────────────────────

    public static class Native
    {
        public delegate bool EnumProc(IntPtr h, IntPtr l);
        [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
        [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }

        [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
        [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
        [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
        [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
        [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr h);
        [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder sb, int n);
        [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder sb, int n);
        [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
        [DllImport("user32.dll")] public static extern IntPtr GetWindow(IntPtr h, uint cmd);
        [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
        [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
        [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
        [DllImport("user32.dll")] public static extern bool SetLayeredWindowAttributes(IntPtr h, uint key, byte alpha, uint flags);
        [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
        [DllImport("user32.dll")] static extern bool SetProcessDpiAwarenessContext(IntPtr dpiContext);
        [DllImport("shcore.dll")] static extern int SetProcessDpiAwareness(int value);
        public static void EnablePerMonitorDpi()
        {
            try { if (SetProcessDpiAwarenessContext(new IntPtr(-4))) return; } catch { }
            try { if (SetProcessDpiAwareness(2) == 0) return; } catch { }
            try { SetProcessDPIAware(); } catch { }
        }
        [DllImport("user32.dll")] public static extern IntPtr WindowFromPoint(POINT p);
        [DllImport("user32.dll")] public static extern IntPtr GetDC(IntPtr h);
        [DllImport("user32.dll")] public static extern int ReleaseDC(IntPtr h, IntPtr dc);
        [DllImport("gdi32.dll")] public static extern bool BitBlt(IntPtr dst, int x, int y, int w, int h, IntPtr src, int sx, int sy, int rop);
        [DllImport("user32.dll")] public static extern IntPtr GetAncestor(IntPtr h, uint flags);
        [DllImport("user32.dll", EntryPoint = "GetWindowLong")] static extern int GetWindowLong32(IntPtr h, int i);
        [DllImport("user32.dll", EntryPoint = "GetWindowLongPtr")] static extern IntPtr GetWindowLongPtr64(IntPtr h, int i);
        [DllImport("user32.dll", EntryPoint = "SetWindowLong")] static extern int SetWindowLong32(IntPtr h, int i, int v);
        [DllImport("user32.dll", EntryPoint = "SetWindowLongPtr")] static extern IntPtr SetWindowLongPtr64(IntPtr h, int i, IntPtr v);
        [DllImport("dwmapi.dll")] static extern int DwmGetWindowAttribute(IntPtr h, int attr, out RECT r, int size);
        [DllImport("dwmapi.dll")] static extern int DwmGetWindowAttribute(IntPtr h, int attr, out int v, int size);
        [DllImport("user32.dll")] public static extern IntPtr RegisterPowerSettingNotification(IntPtr h, ref Guid g, int flags);
        [DllImport("user32.dll")] public static extern bool UnregisterPowerSettingNotification(IntPtr h);
        public static readonly Guid GUID_CONSOLE_DISPLAY_STATE = new Guid("6FE69556-704A-47A0-8F24-C28D936FDA47");

        public const int GWL_EXSTYLE = -20, GWLP_HWNDPARENT = -8;
        public const long WS_EX_TRANSPARENT = 0x20, WS_EX_TOOLWINDOW = 0x80, WS_EX_LAYERED = 0x80000, WS_EX_NOACTIVATE = 0x8000000, WS_EX_APPWINDOW = 0x40000;
        public const uint SWP_NOSIZE = 1, SWP_NOMOVE = 2, SWP_NOZORDER = 4, SWP_NOACTIVATE = 0x10, SWP_SHOWWINDOW = 0x40, SWP_NOOWNERZORDER = 0x200;
        public const uint LWA_ALPHA = 2, GW_OWNER = 4;

        public static long GetLong(IntPtr h, int i) { return IntPtr.Size == 8 ? GetWindowLongPtr64(h, i).ToInt64() : GetWindowLong32(h, i); }
        public static void SetLong(IntPtr h, int i, long v)
        {
            if (IntPtr.Size == 8) SetWindowLongPtr64(h, i, new IntPtr(v)); else SetWindowLong32(h, i, (int)v);
        }

        public static bool Bounds(IntPtr h, out RECT r)
        {
            if (DwmGetWindowAttribute(h, 9, out r, Marshal.SizeOf(typeof(RECT))) == 0 && r.Right > r.Left) return true;
            return GetWindowRect(h, out r);
        }
        public static bool Cloaked(IntPtr h)
        {
            int v; return DwmGetWindowAttribute(h, 14, out v, 4) == 0 && v != 0;
        }
        public static string ClassOf(IntPtr h) { var sb = new StringBuilder(256); GetClassName(h, sb, 256); return sb.ToString(); }
        public static string TitleOf(IntPtr h) { var sb = new StringBuilder(512); GetWindowText(h, sb, 512); return sb.ToString(); }
    }

    // ───────────────────────── 查找 Antigravity 与 DeepSeek Harness 主窗口 ─────────────────────────

    public struct Target
    {
        public IntPtr Hwnd;
        public uint Pid;
        public string AppKey;
        public bool Valid { get { return Hwnd != IntPtr.Zero; } }
    }

    public static class Finder
    {
        public const string AppAntigravity = "antigravity";
        public const string AppDeepSeekHarness = "deepseek-harness";
        public const string AppClaude = "claude";
        public const string AppCodex = "codex";
        public const string AppTest = "test";

        public static string TestTitle;
        static readonly Dictionary<uint, string> NameCache = new Dictionary<uint, string>();

        public static string DisplayName(string appKey)
        {
            if (appKey == AppDeepSeekHarness) return "DeepSeek Harness";
            if (appKey == AppClaude) return "Claude Desktop";
            if (appKey == AppCodex) return "Codex / ChatGPT";
            if (appKey == AppAntigravity) return "Antigravity";
            return appKey ?? "目标窗口";
        }

        public static string MatchWindow(IntPtr hwnd, string procName)
        {
            if (string.IsNullOrEmpty(procName)) return null;
            string p = procName.Trim();
            if (string.Equals(p, "antigravity", StringComparison.OrdinalIgnoreCase))
                return AppAntigravity;
            if (string.Equals(p, "DeepSeek Harness", StringComparison.OrdinalIgnoreCase)
                || string.Equals(p, "DeepSeek.Harness", StringComparison.OrdinalIgnoreCase)
                || string.Equals(p, "deepseek-harness", StringComparison.OrdinalIgnoreCase)
                || string.Equals(p, "DeepSeek.Harness-x64", StringComparison.OrdinalIgnoreCase)
                || string.Equals(p, "dsh-desktop", StringComparison.OrdinalIgnoreCase))
                return AppDeepSeekHarness;
            // Claude Desktop：Electron 应用，仅匹配 Chrome_WidgetWin_1 主窗口，跳过辅助小窗
            if (string.Equals(p, "claude", StringComparison.OrdinalIgnoreCase))
                return Native.ClassOf(hwnd) == "Chrome_WidgetWin_1" ? AppClaude : null;
            // Codex / ChatGPT Desktop：Windows 上商店版包名 OpenAI.Codex 的窗口进程是 ChatGPT.exe，独立版可能叫 Codex.exe
            if (string.Equals(p, "codex", StringComparison.OrdinalIgnoreCase)
                || string.Equals(p, "chatgpt", StringComparison.OrdinalIgnoreCase))
                return AppCodex;
            return null;
        }

        static string ProcName(uint pid)
        {
            string n;
            if (NameCache.TryGetValue(pid, out n)) return n;
            try { n = Process.GetProcessById((int)pid).ProcessName; } catch { n = ""; }
            if (NameCache.Count > 500) NameCache.Clear();
            NameCache[pid] = n;
            return n;
        }

        /// 查找所有已识别且启用的目标 AI 桌面端最大主窗口（支持四款应用同时并发叠加）
        public static List<Target> FindAll(Config config, string onlyAppKey)
        {
            var bestByApp = new Dictionary<string, Target>();
            var areaByApp = new Dictionary<string, long>();
            uint self = (uint)Process.GetCurrentProcess().Id;

            Native.EnumWindows(delegate (IntPtr h, IntPtr l)
            {
                if (!Native.IsWindowVisible(h) || Native.IsIconic(h) || Native.Cloaked(h)) return true;
                if (Native.GetWindow(h, Native.GW_OWNER) != IntPtr.Zero) return true;
                uint pid; Native.GetWindowThreadProcessId(h, out pid);
                if (pid == self) return true;

                string appKey = null;
                if (TestTitle != null)
                {
                    if (Native.TitleOf(h).IndexOf(TestTitle, StringComparison.OrdinalIgnoreCase) < 0) return true;
                    appKey = AppTest;
                }
                else
                {
                    appKey = MatchWindow(h, ProcName(pid));
                    if (appKey == null) return true;
                    if (onlyAppKey != null && !string.Equals(appKey, onlyAppKey, StringComparison.OrdinalIgnoreCase)) return true;
                    if (onlyAppKey == null && config != null && !config.IsTargetEnabled(appKey)) return true;
                    if (Native.GetWindowTextLength(h) == 0) return true;
                }

                Native.RECT r; if (!Native.Bounds(h, out r)) return true;
                int w = r.Right - r.Left, ht = r.Bottom - r.Top;
                if (w < 400 || ht < 300) return true;
                long area = (long)w * ht;
                long curBest;
                if (!areaByApp.TryGetValue(appKey, out curBest) || area > curBest)
                {
                    areaByApp[appKey] = area;
                    bestByApp[appKey] = new Target { Hwnd = h, Pid = pid, AppKey = appKey };
                }
                return true;
            }, IntPtr.Zero);

            return new List<Target>(bestByApp.Values);
        }

        public static Target FindOne(string appKey)
        {
            var list = FindAll(null, appKey);
            return list.Count > 0 ? list[0] : new Target();
        }
    }

    // ───────────────────────── 思源宋体双语动态字幕 ─────────────────────────

    public class SubtitleElement : FrameworkElement
    {
        public static FontFamily Font = new FontFamily("Noto Serif SC, Source Han Serif SC, STSong, SimSun, Microsoft YaHei UI");
        string primaryText;
        string secondaryText;
        public double WidthRatio = 0.65;

        public SubtitleElement()
        {
            IsHitTestVisible = false;
            Opacity = 0;
            Effect = new DropShadowEffect { Color = Color.FromRgb(12, 4, 20), BlurRadius = 14, ShadowDepth = 0, Opacity = 0.92 };
        }

        public void SetText(string primary, string secondary)
        {
            primaryText = primary ?? "";
            secondaryText = secondary ?? "";
            InvalidateVisual();
        }

        FormattedText Make(string s, double size, FontWeight weight, Brush brush)
        {
#pragma warning disable 618
            return new FormattedText(s, CultureInfo.CurrentUICulture, FlowDirection.LeftToRight,
                new Typeface(Font, FontStyles.Normal, weight, FontStretches.Normal), size, brush);
#pragma warning restore 618
        }

        protected override void OnRender(DrawingContext dc)
        {
            if (string.IsNullOrEmpty(primaryText) || ActualWidth < 10) return;
            double W = ActualWidth, H = ActualHeight;
            double baseSize = Math.Max(20, Math.Min(H * 0.044, 42));
            var ftMain = Make(primaryText, baseSize, FontWeights.Medium, Brushes.White);
            if (ftMain.Width > W * 0.88 && ftMain.Width > 0)
            {
                baseSize = Math.Max(16, baseSize * (W * 0.88 / ftMain.Width));
                ftMain = Make(primaryText, baseSize, FontWeights.Medium, Brushes.White);
            }

            bool hasSub = !string.IsNullOrWhiteSpace(secondaryText);
            double subSize = Math.Max(13, baseSize * 0.56);
            FormattedText ftSub = hasSub ? Make(secondaryText, subSize, FontWeights.Normal, new SolidColorBrush(Color.FromArgb(236, 255, 224, 240))) : null;
            if (ftSub != null && ftSub.Width > W * 0.88 && ftSub.Width > 0)
            {
                subSize = Math.Max(11, subSize * (W * 0.88 / ftSub.Width));
                ftSub = Make(secondaryText, subSize, FontWeights.Normal, new SolidColorBrush(Color.FromArgb(236, 255, 224, 240)));
            }

            double yMain = hasSub ? (H * 0.835 - ftMain.Height / 2) : (H * 0.86 - ftMain.Height / 2);
            double xMain = (W - ftMain.Width) / 2;

            var geoMain = ftMain.BuildGeometry(new Point(xMain, yMain));
            var penMain = new Pen(new SolidColorBrush(Color.FromArgb(240, 14, 8, 26)), Math.Max(2.6, baseSize * 0.11)) { LineJoin = PenLineJoin.Round };
            dc.DrawGeometry(null, penMain, geoMain);
            dc.DrawGeometry(Brushes.White, null, geoMain);

            if (ftSub != null)
            {
                double xSub = (W - ftSub.Width) / 2;
                double ySub = yMain + ftMain.Height + Math.Max(6, baseSize * 0.22);
                var geoSub = ftSub.BuildGeometry(new Point(xSub, ySub));
                var penSub = new Pen(new SolidColorBrush(Color.FromArgb(230, 14, 8, 26)), Math.Max(1.8, subSize * 0.11)) { LineJoin = PenLineJoin.Round };
                dc.DrawGeometry(null, penSub, geoSub);
                dc.DrawGeometry(new SolidColorBrush(Color.FromArgb(238, 248, 226, 244)), null, geoSub);
            }
        }
    }

    // ───────────────────────── 开发参数 ─────────────────────────

    public static class Dev
    {
        public static double LoopCutSec = 0;
        public static double StallTestSec = 0;
        public static int StallMs = 3000;
        public static int RecycleEvery = 10;
        public static double HeartbeatSec = 600;
    }

    // ───────────────────────── 单个目标窗口的一次播放 ─────────────────────────

    public class Show
    {
        enum Phase { Intro, Revealed, Ending, Done }
        Phase phase = Phase.Intro;

        public readonly Target Target;
        public readonly string ActiveMode;
        Config config;
        readonly bool withIntro;
        readonly Action onDone;

        Window overlay;
        IntPtr overlayH;
        Grid grid, root;
        int styleFixes;
        MediaElement intro, loopA, loopB, activeLoop;
        MediaElement swapFrom, swapTo; DateTime swapT0; bool swapKicked;
        public static bool ForceLegacyLoop;
        bool overlapLoop;
        string loopFile = "loop.mp4";
        MediaElement handFrom, handTo; DateTime handT0;
        double handLead;
        int handoffs;

        readonly Stopwatch clock = Stopwatch.StartNew();
        long nextSampleMs, lastSampleMs, lastMoveMs, lastRecoverMs = -1, nextBeatMs, nextStallTestMs, pendingAt;
        double lastPos = -1;
        int laps, recoveries, failStreak, missedEnds;
        bool verifying;
        string pendingWhy;
        MediaElement retiring; long retireT0;
        Dispatcher disp;
        SessionSwitchEventHandler onSession;
        EventHandler onDisplay;
        IntPtr powerNotify;
        int displayState = -1;

        SubtitleElement sub;
        Border skipBtn;
        DispatcherTimer tick;
        int currentSub = -1;
        bool introGone, hidden, introFadeInDone;
        DateTime introStartWait;
        Native.RECT lastRect;

        double alpha, alphaFrom, alphaTo; DateTime alphaT0; double alphaDur = -1; Action alphaThen;
        bool clickThrough;
        double volFrom, volTo; DateTime volT0; double volDur = -1;

        string Asset(string name)
        {
            string p = Path.Combine(Path.Combine(App.AssetsDir, ActiveMode), name);
            if (File.Exists(p)) return p;
            return Path.Combine(Path.Combine(App.AssetsDir, "a"), name);
        }

        public Show(Target t, Config c, bool withIntro, Action onDone)
        {
            Target = t; config = c; ActiveMode = Config.NormalizeMode(c.Mode); this.withIntro = withIntro; this.onDone = onDone;

            grid = new Grid { Background = withIntro ? Brushes.Black : Brushes.Transparent, ClipToBounds = true };
            string x2 = Asset("loop-x2.mp4"), single = Asset("loop.mp4");
            overlapLoop = !ForceLegacyLoop && File.Exists(x2)
                && !(File.Exists(single) && File.GetLastWriteTimeUtc(single) > File.GetLastWriteTimeUtc(x2).AddSeconds(2));
            loopFile = overlapLoop ? "loop-x2.mp4" : "loop.mp4";
            Log.W("目标=" + Finder.DisplayName(t.AppKey) + " 模式=" + ActiveMode + "，" + (overlapLoop ? "重叠交接（loop-x2.mp4）" : "放完再接（loop.mp4）"));
            loopA = MakeLoopPlayer();
            loopB = MakeLoopPlayer();
            Panel.SetZIndex(loopA, 1); Panel.SetZIndex(loopB, 0);
            grid.Children.Add(loopA); grid.Children.Add(loopB);
            activeLoop = loopA;

            if (withIntro)
            {
                intro = MakePlayer("intro.mp4", false);
                intro.Volume = config.IntroVolume;
                Panel.SetZIndex(intro, 2);
                grid.Children.Add(intro);
                intro.MediaEnded += delegate { IntroEnded(); };
                intro.MediaFailed += delegate (object s, ExceptionRoutedEventArgs e) { Log.W("开屏视频播不了：" + e.ErrorException.Message); };
            }
            else introGone = true;

            root = new Grid { Background = Brushes.Transparent };
            root.Children.Add(grid);
            overlay = new Window
            {
                WindowStyle = WindowStyle.None, AllowsTransparency = true, ResizeMode = ResizeMode.NoResize, ShowInTaskbar = false,
                ShowActivated = false, Background = Brushes.Transparent, Content = root,
                Left = -32000, Top = -32000, Width = 10, Height = 10, Title = "Aemeath Boot Animation (" + Finder.DisplayName(t.AppKey) + ")"
            };
            clickThrough = !withIntro;
            alpha = 0;
            grid.Opacity = alpha;
            overlay.SourceInitialized += delegate
            {
                overlayH = new WindowInteropHelper(overlay).Handle;
                EnsureOverlayStyle(true);
                var hs = HwndSource.FromHwnd(overlayH);
                if (hs != null) hs.AddHook(WndProc);
                try { Guid g = Native.GUID_CONSOLE_DISPLAY_STATE; powerNotify = Native.RegisterPowerSettingNotification(overlayH, ref g, 0); }
                catch (Exception ex) { Log.W("显示器亮灭通知注册失败：" + ex.Message); }
                Native.SetLong(overlayH, Native.GWLP_HWNDPARENT, Target.Hwnd.ToInt64());
            };

            if (withIntro)
            {
                var topGrid = root;
                sub = new SubtitleElement { WidthRatio = config.SubtitleWidthRatio };
                topGrid.Children.Add(sub);
                skipBtn = new Border
                {
                    Width = 76, Height = 28, CornerRadius = new CornerRadius(14),
                    Background = new SolidColorBrush(Color.FromArgb(135, 16, 10, 26)),
                    BorderBrush = new SolidColorBrush(Color.FromArgb(145, 255, 150, 205)), BorderThickness = new Thickness(1),
                    HorizontalAlignment = HorizontalAlignment.Right, VerticalAlignment = VerticalAlignment.Top,
                    Margin = new Thickness(0, 44, 18, 0), Cursor = Cursors.Hand,
                    Child = new TextBlock
                    {
                        Text = "跳过 ›", Foreground = Brushes.White, FontSize = 13, FontWeight = FontWeights.Medium,
                        FontFamily = new FontFamily("Microsoft YaHei UI"),
                        HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center
                    }
                };
                skipBtn.MouseLeftButtonUp += delegate { SkipIntro(); };
                topGrid.Children.Add(skipBtn);
            }

            overlay.Show();
            EnsureOverlayStyle(true);
            Follow(true);

            if (withIntro)
            {
                introStartWait = DateTime.Now;
                intro.Play();
                Log.W("播放爱弥斯开屏（" + Finder.DisplayName(t.AppKey) + " / 模式 " + ActiveMode + "），窗口 " + Target.Hwnd + " " + RectStr(lastRect));
            }
            else
            {
                loopA.Play();
                phase = Phase.Revealed;
                RampAlpha(config.ResidualAlpha, config.FadeDurationSeconds, null);
                Log.W("开启爱弥斯循环背景（" + Finder.DisplayName(t.AppKey) + " / 模式 " + ActiveMode + "），窗口 " + Target.Hwnd);
            }

            disp = Dispatcher.CurrentDispatcher;
            onSession = delegate (object s, SessionSwitchEventArgs e)
            {
                var r = e.Reason;
                if (r == SessionSwitchReason.SessionUnlock || r == SessionSwitchReason.ConsoleConnect || r == SessionSwitchReason.RemoteConnect)
                    disp.BeginInvoke(new Action(delegate { LaterRebuild("解锁 / 切回桌面（" + r + "）"); }));
            };
            onDisplay = delegate { disp.BeginInvoke(new Action(delegate { LaterRebuild("显示器设置变了"); })); };
            try { SystemEvents.SessionSwitch += onSession; SystemEvents.DisplaySettingsChanged += onDisplay; }
            catch (Exception ex) { Log.W("系统事件订阅失败：" + ex.Message); }
            nextBeatMs = (long)(Dev.HeartbeatSec * 1000);
            nextStallTestMs = (long)(Dev.StallTestSec * 1000);

            tick = new DispatcherTimer(DispatcherPriority.Render) { Interval = TimeSpan.FromMilliseconds(15) };
            tick.Tick += delegate { Tick(); };
            tick.Start();
        }

        IntPtr WndProc(IntPtr h, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
        {
            if (msg == 0x02E0)
            {
                if (disp != null) disp.BeginInvoke(new Action(delegate { Follow(true); }));
                return IntPtr.Zero;
            }
            if (msg != 0x218) return IntPtr.Zero;
            try
            {
                long ev = wParam.ToInt64();
                if (ev == 0x7 || ev == 0x12) LaterRebuild("电脑从睡眠中唤醒");
                else if (ev == 0x8013 && lParam != IntPtr.Zero)
                {
                    var g = (Guid)Marshal.PtrToStructure(lParam, typeof(Guid));
                    if (g == Native.GUID_CONSOLE_DISPLAY_STATE)
                    {
                        int state = Marshal.ReadInt32(lParam, 20);
                        if (state == 1 && displayState >= 0 && displayState != 1) LaterRebuild("显示器重新亮起");
                        displayState = state;
                    }
                }
            }
            catch (Exception ex) { Log.W("电源通知处理出错：" + ex.Message); }
            return IntPtr.Zero;
        }

        static string RectStr(Native.RECT r) { return "(" + r.Left + "," + r.Top + " " + (r.Right - r.Left) + "x" + (r.Bottom - r.Top) + ")"; }

        MediaElement MakePlayer(string file, bool muted)
        {
            var m = new MediaElement
            {
                LoadedBehavior = MediaState.Manual, UnloadedBehavior = MediaState.Manual,
                Stretch = Stretch.UniformToFill, IsMuted = muted, ScrubbingEnabled = muted,
                Source = new Uri(Asset(file), UriKind.Absolute)
            };
            if (muted)
            {
                bool primed = false;
                m.MediaOpened += delegate
                {
                    if (primed) return; primed = true;
                    if ((m != activeLoop && m != handTo) || phase == Phase.Intro) { m.Pause(); m.Position = TimeSpan.Zero; }
                };
                m.Play();
            }
            return m;
        }

        MediaElement MakeLoopPlayer()
        {
            var m = MakePlayer(loopFile, true);
            m.MediaEnded += OnLoopEnded;
            m.MediaFailed += OnLoopFailed;
            return m;
        }

        MediaElement OtherLoop(MediaElement m) { return m == loopA ? loopB : loopA; }

        void OnLoopEnded(object s, RoutedEventArgs e)
        {
            var m = s as MediaElement;
            if (m == null || m != activeLoop || phase == Phase.Done) return;
            SwapLoop(m, OtherLoop(m));
        }

        void OnLoopFailed(object s, ExceptionRoutedEventArgs e)
        {
            if (s != loopA && s != loopB) return;
            Log.W("循环背景播放器报错：" + (e.ErrorException != null ? e.ErrorException.Message : "未知"));
            LaterRebuild("播放器报错", 500);
        }

        void DisposePlayer(MediaElement m)
        {
            if (m == null) return;
            m.MediaEnded -= OnLoopEnded;
            m.MediaFailed -= OnLoopFailed;
            try { m.Stop(); m.Close(); } catch { }
            grid.Children.Remove(m);
        }

        void SwapLoop(MediaElement done, MediaElement next)
        {
            if (phase == Phase.Done) return;
            handFrom = null; handTo = null;
            next.Play();
            activeLoop = next;
            BeginSwap(done, next);
        }

        void BeginSwap(MediaElement from, MediaElement to)
        {
            if (swapFrom != null && swapFrom != from) FinishSwap();
            swapFrom = from; swapTo = to; swapT0 = DateTime.Now; swapKicked = false;
        }

        void CheckSwap()
        {
            if (swapFrom == null) return;
            if (swapTo.Position.TotalSeconds > (swapFrom == intro ? 0.15 : 0.06)) { FinishSwap(); return; }
            if (!swapKicked && (DateTime.Now - swapT0).TotalSeconds > 1.5)
            {
                swapKicked = true;
                swapTo.Play();
            }
        }

        void FinishSwap()
        {
            var from = swapFrom; var to = swapTo;
            swapFrom = null; swapTo = null;
            if (from == intro)
            {
                intro.Visibility = Visibility.Collapsed;
                intro.Stop(); intro.Close();
                return;
            }
            Promote(from, to);
        }

        void Promote(MediaElement from, MediaElement to)
        {
            Panel.SetZIndex(to, 1); Panel.SetZIndex(from, 0);
            activeLoop = to;
            laps++;
            if (Dev.RecycleEvery > 0 && laps % Dev.RecycleEvery == 0) ReplaceStandby(from);
            else { from.Pause(); from.Position = TimeSpan.Zero; }
        }

        void CheckHandoff()
        {
            if (!overlapLoop || phase == Phase.Done || !introGone || swapFrom != null || activeLoop == null) return;
            if (handFrom != null && handFrom != activeLoop) { handFrom = null; handTo = null; }
            var cur = activeLoop;
            if (!cur.NaturalDuration.HasTimeSpan) return;
            double dur = cur.NaturalDuration.TimeSpan.TotalSeconds, half = dur / 2;
            double pos = cur.Position.TotalSeconds;

            if (handTo == null)
            {
                if (pos < 0.05 || pos < half - handLead) return;
                var next = OtherLoop(cur);
                next.Position = TimeSpan.Zero;
                next.Play();
                handFrom = cur; handTo = next; handT0 = DateTime.Now;
                return;
            }

            double toPos = handTo.Position.TotalSeconds;
            if (toPos < 0.8) return;
            double fromPos = handFrom.Position.TotalSeconds;
            double offset = (fromPos - half) - toPos;
            handLead = Math.Max(0, Math.Min(0.5, handLead + offset));
            var from = handFrom; var to = handTo;
            handFrom = null; handTo = null;
            Promote(from, to);
            handoffs++;
        }

        void ReplaceStandby(MediaElement old)
        {
            var fresh = MakeLoopPlayer();
            Panel.SetZIndex(fresh, 0);
            grid.Children.Add(fresh);
            if (old == loopA) loopA = fresh; else loopB = fresh;
            DisposePlayer(old);
        }

        void LaterRebuild(string why) { LaterRebuild(why, 2000); }
        void LaterRebuild(string why, int delayMs)
        {
            if (phase == Phase.Done) return;
            pendingWhy = why;
            pendingAt = clock.ElapsedMilliseconds + delayMs;
        }

        bool RebuildLoops(string why)
        {
            if (phase == Phase.Done || phase == Phase.Ending) return true;
            long now = clock.ElapsedMilliseconds;
            long gap = failStreak < 3 ? 8000 : 60000;
            if (lastRecoverMs >= 0 && now - lastRecoverMs < gap) return false;
            failStreak++;
            recoveries++; lastRecoverMs = now;
            if (swapFrom != null && swapFrom == intro) FinishSwap();
            var old = retiring != null ? retiring : swapFrom != null ? swapFrom : activeLoop;
            swapFrom = null; swapTo = null; handFrom = null; handTo = null;
            if (retiring != null && retiring != old) DisposePlayer(retiring);
            retiring = null;
            if (loopA != old) DisposePlayer(loopA);
            if (loopB != old) DisposePlayer(loopB);
            if (old != null)
            {
                old.MediaEnded -= OnLoopEnded; old.MediaFailed -= OnLoopFailed;
                Panel.SetZIndex(old, 3);
                retiring = old; retireT0 = now;
            }
            loopA = MakeLoopPlayer();
            loopB = MakeLoopPlayer();
            Panel.SetZIndex(loopA, 1); Panel.SetZIndex(loopB, 0);
            grid.Children.Add(loopA); grid.Children.Add(loopB);
            activeLoop = loopA;
            verifying = true;
            lastMoveMs = now; lastPos = -1;
            return true;
        }

        void CheckRetire(long now)
        {
            if (retiring == null) return;
            if (activeLoop.Position.TotalSeconds < 1.0 && now - retireT0 < 20000) return;
            var r = retiring; retiring = null;
            var fade = new DoubleAnimation(0, TimeSpan.FromSeconds(0.25));
            fade.Completed += delegate { DisposePlayer(r); };
            r.BeginAnimation(UIElement.OpacityProperty, fade);
        }

        void Watchdog(long now)
        {
            if (now < nextSampleMs) return;
            nextSampleMs = now + 250;
            bool timerGap = lastSampleMs > 0 && now - lastSampleMs > 2000;
            lastSampleMs = now;
            if (timerGap || phase != Phase.Revealed || !introGone || hidden || activeLoop == null)
            {
                lastMoveMs = now; lastPos = -1;
                return;
            }
            double p = activeLoop.Position.TotalSeconds;
            if (Math.Abs(p - lastPos) > 0.0005)
            {
                lastPos = p; lastMoveMs = now;
                if (verifying && p > 0.3) { verifying = false; failStreak = 0; }
                return;
            }
            long stuck = now - lastMoveMs;
            if (stuck >= 400 && swapFrom == null && activeLoop.NaturalDuration.HasTimeSpan
                && p >= activeLoop.NaturalDuration.TimeSpan.TotalSeconds - 0.08)
            {
                missedEnds++;
                SwapLoop(activeLoop, OtherLoop(activeLoop));
                lastMoveMs = now; lastPos = -1;
                return;
            }
            if (stuck < Dev.StallMs) return;
            RebuildLoops("画面卡住自动恢复");
        }

        void IntroEnded()
        {
            if (introGone) return;
            introGone = true;
            loopA.Play();
            activeLoop = loopA;
            BeginSwap(intro, loopA);
            if (phase == Phase.Intro) Reveal(false);
            CloseTop();
        }

        void CloseTop()
        {
            if (skipBtn != null) skipBtn.Visibility = Visibility.Collapsed;
        }

        void Tick()
        {
            if (phase == Phase.Done) return;
            Follow(false);
            if (phase == Phase.Done) return;
            EnsureOverlayStyle(false);
            CheckSwap();
            CheckHandoff();
            long now = clock.ElapsedMilliseconds;
            CheckRetire(now);
            if (pendingAt > 0 && now >= pendingAt && !hidden && phase == Phase.Revealed && introGone)
                pendingAt = RebuildLoops(pendingWhy) ? 0 : now + 1000;
            Watchdog(now);

            if (!introGone && intro != null)
            {
                double t = intro.Position.TotalSeconds;
                if (!introFadeInDone && phase == Phase.Intro && (t >= 0.04 || (DateTime.Now - introStartWait).TotalSeconds > 1.8))
                {
                    introFadeInDone = true;
                    RampAlpha(1, 0.28, null);
                }
                if (phase == Phase.Intro && t >= config.FadeStartSeconds) Reveal(false);
                UpdateSubtitle(t);
            }
            if (alphaDur >= 0)
            {
                double k = alphaDur <= 0 ? 1 : Math.Min(1, (DateTime.Now - alphaT0).TotalSeconds / alphaDur);
                double s = k * k * k * (k * (k * 6 - 15) + 10);
                SetAlpha(alphaFrom + (alphaTo - alphaFrom) * s);
                if (k >= 1) { alphaDur = -1; var then = alphaThen; alphaThen = null; if (then != null) then(); }
            }
            if (volDur >= 0 && intro != null)
            {
                double k = volDur <= 0 ? 1 : Math.Min(1, (DateTime.Now - volT0).TotalSeconds / volDur);
                double s = k * k * (3 - 2 * k);
                intro.Volume = volFrom + (volTo - volFrom) * s;
                if (k >= 1) volDur = -1;
            }
        }

        void Follow(bool force)
        {
            if (!Native.IsWindow(Target.Hwnd)) { Teardown(); return; }
            bool vis = Native.IsWindowVisible(Target.Hwnd) && !Native.IsIconic(Target.Hwnd) && !Native.Cloaked(Target.Hwnd);
            if (!vis) { if (!hidden) { hidden = true; ShowAll(false); } return; }
            if (hidden)
            {
                hidden = false; ShowAll(true); force = true;
                if (phase == Phase.Revealed && alphaDur < 0) { SetAlpha(0); RampAlpha(config.ResidualAlpha, 0.35, null); }
            }
            Native.RECT r;
            if (!Native.Bounds(Target.Hwnd, out r)) return;
            bool needMove = force || r.Left != lastRect.Left || r.Top != lastRect.Top || r.Right != lastRect.Right || r.Bottom != lastRect.Bottom;
            if (!needMove && overlayH != IntPtr.Zero)
            {
                Native.RECT cur;
                if (Native.GetWindowRect(overlayH, out cur) && (cur.Left != r.Left || cur.Top != r.Top || cur.Right != r.Right || cur.Bottom != r.Bottom))
                    needMove = true;
            }
            if (!needMove) return;
            lastRect = r;
            uint f = Native.SWP_NOZORDER | Native.SWP_NOACTIVATE | Native.SWP_NOOWNERZORDER;
            if (overlayH != IntPtr.Zero) Native.SetWindowPos(overlayH, IntPtr.Zero, r.Left, r.Top, r.Right - r.Left, r.Bottom - r.Top, f);
        }

        void ShowAll(bool show)
        {
            int cmd = show ? 4 : 0;
            if (overlayH != IntPtr.Zero) Native.ShowWindow(overlayH, cmd);
        }

        void EnsureOverlayStyle(bool force)
        {
            if (overlayH == IntPtr.Zero) return;
            long ex = Native.GetLong(overlayH, Native.GWL_EXSTYLE);
            long want = (ex | Native.WS_EX_TOOLWINDOW | Native.WS_EX_NOACTIVATE) & ~Native.WS_EX_APPWINDOW;
            if (clickThrough) want |= Native.WS_EX_TRANSPARENT;
            if (want != ex && styleFixes < 20)
            {
                if (!force) styleFixes++;
                Native.SetLong(overlayH, Native.GWL_EXSTYLE, want);
            }
        }

        void SetAlpha(double a) { alpha = Math.Max(0, Math.Min(1, a)); grid.Opacity = alpha; }
        void RampAlpha(double to, double seconds, Action then) { alphaFrom = alpha; alphaTo = to; alphaT0 = DateTime.Now; alphaDur = Math.Max(0, seconds); alphaThen = then; }
        void RampVolume(double to, double seconds) { if (intro == null) return; volFrom = intro.Volume; volTo = to; volT0 = DateTime.Now; volDur = seconds; }

        void UpdateSubtitle(double t)
        {
            if (sub == null) return;
            if (!config.ShowSubtitles) { sub.Opacity = 0; return; }
            double fade = Math.Max(0.01, config.SubtitleFadeSeconds);
            int idx = -1;
            for (int i = 0; i < config.Subtitles.Count; i++)
                if (t >= config.Subtitles[i].Start && t <= config.Subtitles[i].End) { idx = i; break; }
            if (idx < 0)
            {
                sub.Opacity = 0;
                return;
            }
            var s = config.Subtitles[idx];
            if (idx != currentSub)
            {
                currentSub = idx;
                sub.SetText(s.Text, s.SubText);
            }
            sub.Opacity = Math.Max(0, Math.Min(1, Math.Min((t - s.Start) / fade, (s.End - t) / fade)));
        }

        void HideSubtitles()
        {
            if (sub == null) return;
            sub.BeginAnimation(UIElement.OpacityProperty, new DoubleAnimation(0, TimeSpan.FromSeconds(0.4)));
            sub = null;
        }

        void Reveal(bool quick)
        {
            if (phase != Phase.Intro) return;
            phase = Phase.Revealed;
            clickThrough = true; EnsureOverlayStyle(true);
            grid.Background = Brushes.Transparent;
            if (skipBtn != null)
            {
                var sbFade = new DoubleAnimation(0, TimeSpan.FromSeconds(0.35));
                var btn = skipBtn;
                sbFade.Completed += delegate { btn.Visibility = Visibility.Collapsed; };
                btn.BeginAnimation(UIElement.OpacityProperty, sbFade);
            }
            if (!config.LoopBackground) { Finish(false); return; }
            double fadeSec = quick ? 0.9 : config.FadeDurationSeconds;
            RampAlpha(config.ResidualAlpha, fadeSec, null);
            RampVolume(0, fadeSec);
        }

        public void SkipIntro()
        {
            if (phase != Phase.Intro) return;
            if (!config.LoopBackground) { Finish(true); return; }
            HideSubtitles();
            loopA.Play(); activeLoop = loopA;
            introGone = true;
            var fade = new DoubleAnimation(0, TimeSpan.FromSeconds(0.9)) { EasingFunction = new SineEase { EasingMode = EasingMode.EaseInOut } };
            var iv = intro;
            fade.Completed += delegate { iv.Visibility = Visibility.Collapsed; iv.Stop(); iv.Close(); };
            intro.BeginAnimation(UIElement.OpacityProperty, fade);
            RampVolume(0, 0.9);
            Reveal(true);
            var closeTop = new DispatcherTimer { Interval = TimeSpan.FromSeconds(0.5) };
            closeTop.Tick += delegate { closeTop.Stop(); CloseTop(); };
            closeTop.Start();
        }

        public void Apply(Config c)
        {
            config = c;
            if (phase == Phase.Ending || phase == Phase.Done) return;
            if (phase == Phase.Revealed && alphaDur < 0) SetAlpha(c.ResidualAlpha);
            if (intro != null && !introGone) { volDur = -1; intro.Volume = c.IntroVolume; }
            if (sub != null && currentSub >= 0 && currentSub < c.Subtitles.Count)
                sub.SetText(c.Subtitles[currentSub].Text, c.Subtitles[currentSub].SubText);
        }

        public void Finish(bool fast)
        {
            if (phase == Phase.Ending || phase == Phase.Done) return;
            phase = Phase.Ending;
            clickThrough = true; EnsureOverlayStyle(true);
            double d = fast ? 0.4 : 1.2;
            if (skipBtn != null) skipBtn.Visibility = Visibility.Collapsed;
            HideSubtitles();
            RampVolume(0, d);
            RampAlpha(0, d, Teardown);
        }

        public void Teardown()
        {
            if (phase == Phase.Done) return;
            phase = Phase.Done;
            if (tick != null) tick.Stop();
            try { SystemEvents.SessionSwitch -= onSession; SystemEvents.DisplaySettingsChanged -= onDisplay; } catch { }
            if (powerNotify != IntPtr.Zero) { try { Native.UnregisterPowerSettingNotification(powerNotify); } catch { } powerNotify = IntPtr.Zero; }
            foreach (var m in new[] { intro, loopA, loopB, retiring })
                if (m != null) { try { m.Stop(); m.Close(); } catch { } }
            CloseTop();
            try { overlay.Close(); } catch { }
            if (onDone != null) onDone();
        }

        public bool Active { get { return phase != Phase.Done; } }

        public void Snapshot(string path)
        {
            Native.RECT r = lastRect;
            int w = r.Right - r.Left, h = r.Bottom - r.Top;
            if (w <= 0 || h <= 0) return;
            using (var bmp = new SD.Bitmap(w, h))
            {
                using (var g = SD.Graphics.FromImage(bmp))
                {
                    IntPtr dst = g.GetHdc(), src = Native.GetDC(IntPtr.Zero);
                    Native.BitBlt(dst, 0, 0, w, h, src, r.Left, r.Top, 0x00CC0020 | 0x40000000);
                    Native.ReleaseDC(IntPtr.Zero, src); g.ReleaseHdc(dst);
                }
                bmp.Save(path, SD.Imaging.ImageFormat.Png);
            }
        }
    }

    // ───────────────────────── 设置窗口（双桌面端支持 + A/B/C 切换 + 自定义台词）─────────────────────────

    public class SettingsWindow : Window
    {
        readonly App app;
        RadioButton modeA, modeB, modeC;
        CheckBox appAgBox, appDshBox, appClaudeBox, appCodexBox, introBox, loopBox, subBox;
        TextBox subMainBox, subSecBox;
        Slider alphaSlider, volSlider;
        TextBlock alphaVal, volVal;
        bool loading;

        public SettingsWindow(App app)
        {
            this.app = app;
            Title = "爱弥斯开机动画 · 设置（全主流 AI 桌面端）";
            Width = 510; SizeToContent = SizeToContent.Height; ResizeMode = ResizeMode.NoResize;
            WindowStartupLocation = WindowStartupLocation.CenterScreen;
            FontFamily = new FontFamily("Microsoft YaHei UI"); FontSize = 13;
            var sp = new StackPanel { Margin = new Thickness(22, 14, 22, 18) };

            sp.Children.Add(Header("监听的 AI 桌面端（可同时勾选，多窗口独立播放）"));
            var appRow = new WrapPanel { Margin = new Thickness(0, 6, 0, 4) };
            appAgBox = new CheckBox { Content = "Antigravity", Margin = new Thickness(0, 0, 16, 4) };
            appDshBox = new CheckBox { Content = "DeepSeek Harness", Margin = new Thickness(0, 0, 16, 4) };
            appClaudeBox = new CheckBox { Content = "Claude Desktop", Margin = new Thickness(0, 0, 16, 4) };
            appCodexBox = new CheckBox { Content = "Codex / ChatGPT", Margin = new Thickness(0, 0, 0, 4) };
            appAgBox.Click += delegate { Changed(); };
            appDshBox.Click += delegate { Changed(); };
            appClaudeBox.Click += delegate { Changed(); };
            appCodexBox.Click += delegate { Changed(); };
            appRow.Children.Add(appAgBox); appRow.Children.Add(appDshBox);
            appRow.Children.Add(appClaudeBox); appRow.Children.Add(appCodexBox);
            sp.Children.Add(appRow);

            sp.Children.Add(Header("选择开场演出方案（14.5s《于电子星海轻歌》）"));
            modeA = new RadioButton { GroupName = "Mode", Content = "方案 A · 一镜到底（官方星海睁眼觉醒 → 纯白光翼）", Margin = new Thickness(0, 6, 0, 4) };
            modeB = new RadioButton { GroupName = "Mode", Content = "方案 B · 双形态切换（飞行雪绒轻歌 → 故障撕裂 → 隧者机兵）", Margin = new Thickness(0, 4, 0, 4) };
            modeC = new RadioButton { GroupName = "Mode", Content = "方案 C · 多幕剧情（纸飞机 → 祝福微笑 → 拯救共鸣 → 远航星守望）", Margin = new Thickness(0, 4, 0, 6) };
            modeA.Checked += delegate { if (!loading) ModeChanged("a"); };
            modeB.Checked += delegate { if (!loading) ModeChanged("b"); };
            modeC.Checked += delegate { if (!loading) ModeChanged("c"); };
            sp.Children.Add(modeA); sp.Children.Add(modeB); sp.Children.Add(modeC);

            sp.Children.Add(Header("自定义开屏台词字幕（即时生效）"));
            subBox = new CheckBox { Content = "显示开屏思源宋体台词", Margin = new Thickness(0, 6, 0, 5) };
            subBox.Click += delegate { Changed(); };
            sp.Children.Add(subBox);
            sp.Children.Add(new TextBlock { Text = "主台词（默认：拯救世界的事，就交给我吧……）", Foreground = Brushes.DimGray, FontSize = 11.5 });
            subMainBox = new TextBox { Padding = new Thickness(6, 4, 6, 4), Margin = new Thickness(0, 3, 0, 5) };
            subSecBox = new TextBox { Padding = new Thickness(6, 4, 6, 4), Margin = new Thickness(0, 3, 0, 6) };
            subMainBox.TextChanged += delegate { if (!loading) Changed(); };
            subSecBox.TextChanged += delegate { if (!loading) Changed(); };
            sp.Children.Add(subMainBox);
            sp.Children.Add(new TextBlock { Text = "副台词（选填，留空则只显示主台词）", Foreground = Brushes.DimGray, FontSize = 11.5 });
            sp.Children.Add(subSecBox);

            sp.Children.Add(Header("打开应用时"));
            var optRow = new WrapPanel { Margin = new Thickness(0, 6, 0, 2) };
            introBox = new CheckBox { Content = "播放开屏动画", Margin = new Thickness(0, 0, 18, 4) };
            loopBox = new CheckBox { Content = "保留半透明循环背景（点击穿透）", Margin = new Thickness(0, 0, 0, 4) };
            introBox.Click += delegate { Changed(); };
            loopBox.Click += delegate { Changed(); };
            optRow.Children.Add(introBox); optRow.Children.Add(loopBox);
            sp.Children.Add(optRow);

            alphaSlider = MakeSlider(sp, "背景不透明度", 0.8, out alphaVal);
            volSlider = MakeSlider(sp, "开屏音量（再乘系统音量）", 1, out volVal);

            sp.Children.Add(Header("立即在已打开的 AI 窗口上播放"));
            var row = new WrapPanel { Margin = new Thickness(0, 8, 0, 0) };
            row.Children.Add(Btn("自动检测播放", delegate { app.PreviewIntro(null); }));
            row.Children.Add(Btn("Antigravity", delegate { app.PreviewIntro(Finder.AppAntigravity); }));
            row.Children.Add(Btn("DeepSeek Harness", delegate { app.PreviewIntro(Finder.AppDeepSeekHarness); }));
            row.Children.Add(Btn("Claude", delegate { app.PreviewIntro(Finder.AppClaude); }));
            row.Children.Add(Btn("Codex", delegate { app.PreviewIntro(Finder.AppCodex); }));
            row.Children.Add(Btn("开启循环背景", delegate { app.PreviewLoop(null); }));
            row.Children.Add(Btn("全部关掉", delegate { app.StopAllShows(); }));
            sp.Children.Add(row);
            var row2 = new WrapPanel { Margin = new Thickness(0, 8, 0, 0) };
            row2.Children.Add(Btn("恢复默认台词", delegate
            {
                subMainBox.Text = "拯救世界的事，就交给我吧……";
                subSecBox.Text = "Leave saving the world to me...";
                subBox.IsChecked = true;
                Changed();
            }));
            row2.Children.Add(Btn("打开设置文件…", delegate { app.OpenConfig(); }));
            row2.Children.Add(Btn("卸载…", delegate { app.Uninstall(); }));
            sp.Children.Add(row2);
            Content = sp;
            Refresh();
        }

        static TextBlock Header(string t) { return new TextBlock { Text = t, FontWeight = FontWeights.Bold, Margin = new Thickness(0, 8, 0, 0) }; }
        static Button Btn(string t, RoutedEventHandler h)
        {
            var b = new Button { Content = t, Padding = new Thickness(10, 4, 10, 4), Margin = new Thickness(0, 0, 8, 6) };
            b.Click += h; return b;
        }
        Slider MakeSlider(StackPanel sp, string title, double max, out TextBlock val)
        {
            var g = new DockPanel { Margin = new Thickness(0, 5, 0, 0) };
            var v = new TextBlock { Width = 44, TextAlignment = TextAlignment.Right };
            DockPanel.SetDock(v, Dock.Right);
            g.Children.Add(v);
            g.Children.Add(new TextBlock { Text = title });
            sp.Children.Add(g);
            var s = new Slider { Minimum = 0, Maximum = max, Margin = new Thickness(0, 3, 0, 5), IsMoveToPointEnabled = true };
            s.ValueChanged += delegate { v.Text = Math.Round(s.Value * 100) + "%"; if (!loading) Changed(); };
            sp.Children.Add(s);
            val = v;
            return s;
        }

        public void Refresh()
        {
            loading = true;
            var c = app.Config;
            appAgBox.IsChecked = c.EnableAntigravity;
            appDshBox.IsChecked = c.EnableDeepSeekHarness;
            appClaudeBox.IsChecked = c.EnableClaude;
            appCodexBox.IsChecked = c.EnableCodex;
            string m = Config.NormalizeMode(c.Mode);
            modeA.IsChecked = (m == "a");
            modeB.IsChecked = (m == "b");
            modeC.IsChecked = (m == "c");
            introBox.IsChecked = c.PlayIntro;
            loopBox.IsChecked = c.LoopBackground;
            subBox.IsChecked = c.ShowSubtitles;
            if (c.Subtitles != null && c.Subtitles.Count > 0)
            {
                subMainBox.Text = c.Subtitles[0].Text ?? "";
                subSecBox.Text = c.Subtitles[0].SubText ?? "";
            }
            alphaSlider.Value = c.ResidualAlpha; volSlider.Value = c.IntroVolume;
            alphaVal.Text = Math.Round(c.ResidualAlpha * 100) + "%"; volVal.Text = Math.Round(c.IntroVolume * 100) + "%";
            loading = false;
        }

        void ModeChanged(string mode)
        {
            app.SwitchMode(mode, this);
        }

        void Changed()
        {
            if (loading) return;
            app.Update(delegate (Config c)
            {
                c.EnableAntigravity = appAgBox.IsChecked == true;
                c.EnableDeepSeekHarness = appDshBox.IsChecked == true;
                c.EnableClaude = appClaudeBox.IsChecked == true;
                c.EnableCodex = appCodexBox.IsChecked == true;
                c.PlayIntro = introBox.IsChecked == true;
                c.LoopBackground = loopBox.IsChecked == true;
                c.ShowSubtitles = subBox.IsChecked == true;
                c.ResidualAlpha = alphaSlider.Value;
                c.IntroVolume = volSlider.Value;
                if (c.Subtitles == null || c.Subtitles.Count == 0)
                    c.Subtitles = new List<Subtitle> { new Subtitle(subMainBox.Text, subSecBox.Text, 4.65, 12.65) };
                else
                {
                    c.Subtitles[0].Text = subMainBox.Text;
                    c.Subtitles[0].SubText = subSecBox.Text;
                }
            }, this);
        }
    }

    // ───────────────────────── 主程序（支持多应用并发浮层管理）─────────────────────────

    public class App : Application
    {
        public static string AssetsDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "assets");
        public Config Config;
        readonly Dictionary<string, Show> shows = new Dictionary<string, Show>();
        WF.NotifyIcon tray;
        WF.ToolStripMenuItem agItem, dshItem, claudeItem, codexItem, introItem, loopItem, stopItem, modeAItem, modeBItem, modeCItem;
        WF.ToolStripLabel alphaLabel, volLabel;
        WF.TrackBar alphaBar, volBar;
        SettingsWindow settings;
        readonly HashSet<uint> seenPids = new HashSet<uint>();
        DispatcherTimer watch;
        readonly string[] args;
        bool testMode;
        bool menuLoading;

        public App(string[] args) { this.args = args; ShutdownMode = ShutdownMode.OnExplicitShutdown; }

        string Arg(string name)
        {
            int i = Array.IndexOf(args, name);
            return i >= 0 && i + 1 < args.Length ? args[i + 1] : null;
        }
        bool Has(string name) { return Array.IndexOf(args, name) >= 0; }
        double ArgD(string name, double def)
        {
            double v; var s = Arg(name);
            return s != null && double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out v) ? v : def;
        }

        protected override void OnStartup(StartupEventArgs e)
        {
            base.OnStartup(e);
            Show.ForceLegacyLoop = Has("--legacy-loop");
            Config = Config.Load();
            string modeArg = Arg("--mode");
            if (!string.IsNullOrEmpty(modeArg)) { Config.Mode = Config.NormalizeMode(modeArg); Config.Save(); }
            LoadFont();
            Finder.TestTitle = Arg("--target-title");
            testMode = Finder.TestTitle != null;
            Dev.LoopCutSec = ArgD("--loop-cut", Dev.LoopCutSec);
            Dev.StallTestSec = ArgD("--stall-test", Dev.StallTestSec);
            Dev.RecycleEvery = (int)ArgD("--recycle-every", Dev.RecycleEvery);
            Dev.HeartbeatSec = ArgD("--heartbeat", Dev.HeartbeatSec);
            Log.W("启动 " + string.Join(" ", args) + "  模式=" + Config.Mode + " AG=" + Config.EnableAntigravity + " DSH=" + Config.EnableDeepSeekHarness);

            if (Arg("--render-subtitle") != null) { RenderSubtitleTest(); return; }

            SetupTray();
            if (Has("--settings")) OpenSettings();

            var initialTargets = Finder.FindAll(Config, null);
            if (!testMode)
                foreach (var t0 in initialTargets) seenPids.Add(t0.Pid);

            string playApp = Arg("--play-app");
            if (!string.IsNullOrEmpty(playApp)) PreviewIntro(playApp);
            else if (Has("--play-now")) PreviewIntro(null);

            watch = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(400) };
            watch.Tick += delegate { Watch(); };
            watch.Start();

            if (testMode) RunTest();
            else
            {
                var promote = new DispatcherTimer { Interval = TimeSpan.FromSeconds(6) };
                promote.Tick += delegate { promote.Stop(); PromoteTrayIcon(); };
                promote.Start();
            }
        }

        void LoadFont()
        {
            try
            {
                string winFonts = Path.Combine(Environment.GetEnvironmentVariable("WINDIR") ?? @"C:\Windows", "Fonts");
                if (File.Exists(Path.Combine(winFonts, "NotoSerifSC-VF.ttf")))
                    SubtitleElement.Font = new FontFamily("Noto Serif SC, STSong, SimSun, Microsoft YaHei UI");
            }
            catch { }
        }

        void Watch()
        {
            if (testMode) return;
            var targets = Finder.FindAll(Config, null);
            if (targets.Count == 0) return;
            foreach (var t in targets)
            {
                if (seenPids.Contains(t.Pid)) continue;
                seenPids.Add(t.Pid);
                Config = Config.Load();
                if (!Config.IsTargetEnabled(t.AppKey)) continue;
                if (!Config.PlayIntro && !Config.LoopBackground) continue;
                Start(t, Config.PlayIntro);
            }
        }

        void Start(Target t, bool withIntro)
        {
            string key = t.AppKey ?? Finder.AppAntigravity;
            Show prev;
            if (shows.TryGetValue(key, out prev) && prev != null) prev.Teardown();
            Show s = null;
            s = new Show(t, Config, withIntro, delegate
            {
                Show cur;
                if (shows.TryGetValue(key, out cur) && cur == s) shows.Remove(key);
                RefreshMenu();
            });
            shows[key] = s;
            RefreshMenu();
        }

        bool StartOnCurrent(bool withIntro, string onlyAppKey)
        {
            var targets = onlyAppKey != null ? Finder.FindAll(null, onlyAppKey) : Finder.FindAll(Config, null);
            if (targets.Count == 0 && onlyAppKey == null)
                targets = Finder.FindAll(null, null); // 若全部勾选窗口没开，也兜底找任意已开支持窗口
            if (targets.Count == 0)
            {
                string who = onlyAppKey != null ? Finder.DisplayName(onlyAppKey) : "Antigravity / DeepSeek Harness / Claude / Codex";
                if (tray != null) tray.ShowBalloonTip(3000, "爱弥斯开机动画", "没找到 " + who + " 窗口，请先把应用打开吧。", WF.ToolTipIcon.Info);
                return false;
            }
            foreach (var t in targets)
            {
                seenPids.Add(t.Pid);
                Start(t, withIntro);
            }
            return true;
        }

        public void PreviewIntro(string appKey) { StartOnCurrent(true, appKey); }
        public void PreviewLoop(string appKey) { StartOnCurrent(false, appKey); }

        public void StopAllShows()
        {
            foreach (var s in new List<Show>(shows.Values))
                if (s != null) s.Finish(true);
        }

        public void OpenConfig() { Config.Save(); try { Process.Start("notepad.exe", "\"" + Config.FilePath + "\""); } catch { } }

        public void SwitchMode(string mode, object from)
        {
            string norm = Config.NormalizeMode(mode);
            if (Config.Mode == norm) return;
            Config.Mode = norm;
            Config.Save();
            if (from != settings && settings != null) settings.Refresh();
            if (from != tray) RefreshMenu();
            foreach (var s in new List<Show>(shows.Values))
                if (s != null && s.Active) Start(s.Target, Config.PlayIntro);
        }

        public void Update(Action<Config> change, object from)
        {
            change(Config);
            Config.Save();
            foreach (var s in new List<Show>(shows.Values))
            {
                if (s == null) continue;
                if (!Config.IsTargetEnabled(s.Target.AppKey)) s.Finish(true);
                else s.Apply(Config);
            }
            if (from != settings && settings != null) settings.Refresh();
            if (from != tray) RefreshMenu();
        }

        public void OpenSettings()
        {
            Config = Config.Load();
            if (settings == null)
            {
                settings = new SettingsWindow(this);
                settings.Closed += delegate { settings = null; };
            }
            settings.Refresh();
            settings.Show();
            if (settings.WindowState == WindowState.Minimized) settings.WindowState = WindowState.Normal;
            settings.Activate();
        }

        public void Uninstall()
        {
            var r = MessageBox.Show("会删除这个小程序、开机自启、设置和日志。Antigravity、DeepSeek Harness、Claude Desktop、Codex 本体均未被改过，卸载后就是原装的样子。",
                "卸载爱弥斯开机动画？", MessageBoxButton.OKCancel, MessageBoxImage.Question);
            if (r != MessageBoxResult.OK) return;
            foreach (var s in new List<Show>(shows.Values))
                if (s != null) s.Teardown();
            string script = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "uninstall.ps1");
            if (File.Exists(script))
            {
                Process.Start(new ProcessStartInfo("powershell.exe",
                    "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"" + script + "\" -Quiet")
                { UseShellExecute = false, CreateNoWindow = true });
            }
            Quit();
        }

        void Quit()
        {
            if (tray != null) { tray.Visible = false; tray.Dispose(); }
            Shutdown();
        }

        static SD.Icon MakeIcon()
        {
            var bmp = new SD.Bitmap(32, 32);
            using (var g = SD.Graphics.FromImage(bmp))
            {
                g.SmoothingMode = SD.Drawing2D.SmoothingMode.AntiAlias;
                using (var path = new SD.Drawing2D.GraphicsPath())
                {
                    float c = 16, r = 15, q = 1.6f;
                    path.StartFigure();
                    path.AddBezier(c, c - r, c + q, c - q, c + q, c - q, c + r, c);
                    path.AddBezier(c + r, c, c + q, c + q, c + q, c + q, c, c + r);
                    path.AddBezier(c, c + r, c - q, c + q, c - q, c + q, c - r, c);
                    path.AddBezier(c - r, c, c - q, c - q, c - q, c - q, c, c - r);
                    path.CloseFigure();
                    using (var b = new SD.Drawing2D.LinearGradientBrush(new SD.PointF(2, 30), new SD.PointF(30, 2),
                        SD.Color.FromArgb(255, 255, 118, 184), SD.Color.FromArgb(255, 102, 232, 255)))
                        g.FillPath(b, path);
                }
            }
            return SD.Icon.FromHandle(bmp.GetHicon());
        }

        void SetupTray()
        {
            tray = new WF.NotifyIcon { Icon = MakeIcon(), Text = "爱弥斯开机动画（全主流 AI 桌面端）", Visible = true };
            var m = new WF.ContextMenuStrip();
            m.Items.Add(new WF.ToolStripLabel("监听的 AI 桌面端") { Enabled = false });
            agItem = new WF.ToolStripMenuItem("Antigravity");
            agItem.Click += delegate { Update(delegate (Config c) { c.EnableAntigravity = !c.EnableAntigravity; }, null); };
            dshItem = new WF.ToolStripMenuItem("DeepSeek Harness");
            dshItem.Click += delegate { Update(delegate (Config c) { c.EnableDeepSeekHarness = !c.EnableDeepSeekHarness; }, null); };
            claudeItem = new WF.ToolStripMenuItem("Claude Desktop");
            claudeItem.Click += delegate { Update(delegate (Config c) { c.EnableClaude = !c.EnableClaude; }, null); };
            codexItem = new WF.ToolStripMenuItem("Codex / ChatGPT");
            codexItem.Click += delegate { Update(delegate (Config c) { c.EnableCodex = !c.EnableCodex; }, null); };
            m.Items.Add(agItem); m.Items.Add(dshItem); m.Items.Add(claudeItem); m.Items.Add(codexItem);
            m.Items.Add(new WF.ToolStripSeparator());

            m.Items.Add(new WF.ToolStripLabel("演出方案（14.5s《于电子星海轻歌》）") { Enabled = false });
            modeAItem = new WF.ToolStripMenuItem("方案 A · 一镜到底（官方星海睁眼觉醒）");
            modeAItem.Click += delegate { SwitchMode("a", null); };
            modeBItem = new WF.ToolStripMenuItem("方案 B · 双形态（电子幽灵 × 隧者机兵）");
            modeBItem.Click += delegate { SwitchMode("b", null); };
            modeCItem = new WF.ToolStripMenuItem("方案 C · 多幕剧情（纸飞机 / 祝福 / 拯救 / 远航星）");
            modeCItem.Click += delegate { SwitchMode("c", null); };
            m.Items.Add(modeAItem); m.Items.Add(modeBItem); m.Items.Add(modeCItem);
            m.Items.Add(new WF.ToolStripSeparator());

            m.Items.Add(new WF.ToolStripLabel("启动行为") { Enabled = false });
            introItem = new WF.ToolStripMenuItem("播放开屏动画");
            introItem.Click += delegate { Update(delegate (Config c) { c.PlayIntro = !c.PlayIntro; }, null); };
            loopItem = new WF.ToolStripMenuItem("保留循环背景");
            loopItem.Click += delegate { Update(delegate (Config c) { c.LoopBackground = !c.LoopBackground; }, null); };
            m.Items.Add(introItem); m.Items.Add(loopItem);
            m.Items.Add(new WF.ToolStripSeparator());

            alphaLabel = new WF.ToolStripLabel("背景不透明度");
            alphaBar = MakeBar(80);
            alphaBar.ValueChanged += delegate
            {
                alphaLabel.Text = "背景不透明度  " + alphaBar.Value + "%";
                if (!menuLoading) Update(delegate (Config c) { c.ResidualAlpha = alphaBar.Value / 100.0; }, tray);
            };
            volLabel = new WF.ToolStripLabel("开屏音量");
            volBar = MakeBar(100);
            volBar.ValueChanged += delegate
            {
                volLabel.Text = "开屏音量  " + volBar.Value + "%";
                if (!menuLoading) Update(delegate (Config c) { c.IntroVolume = volBar.Value / 100.0; }, tray);
            };
            m.Items.Add(alphaLabel); m.Items.Add(new WF.ToolStripControlHost(alphaBar));
            m.Items.Add(volLabel); m.Items.Add(new WF.ToolStripControlHost(volBar));
            m.Items.Add(new WF.ToolStripSeparator());

            m.Items.Add(new WF.ToolStripLabel("立即播放") { Enabled = false });
            m.Items.Add("自动检测当前打开的 AI 窗口播放", null, delegate { PreviewIntro(null); });
            m.Items.Add("在 Antigravity 播放", null, delegate { PreviewIntro(Finder.AppAntigravity); });
            m.Items.Add("在 DeepSeek Harness 播放", null, delegate { PreviewIntro(Finder.AppDeepSeekHarness); });
            m.Items.Add("在 Claude Desktop 播放", null, delegate { PreviewIntro(Finder.AppClaude); });
            m.Items.Add("在 Codex / ChatGPT 播放", null, delegate { PreviewIntro(Finder.AppCodex); });
            m.Items.Add("开启循环背景", null, delegate { PreviewLoop(null); });
            stopItem = new WF.ToolStripMenuItem("关掉所有动画 / 背景");
            stopItem.Click += delegate { StopAllShows(); };
            m.Items.Add(stopItem);
            m.Items.Add(new WF.ToolStripSeparator());
            m.Items.Add("设置与自定义台词…", null, delegate { OpenSettings(); });
            m.Items.Add("打开设置文件…", null, delegate { OpenConfig(); });
            m.Items.Add("卸载爱弥斯开机动画…", null, delegate { Uninstall(); });
            m.Opening += delegate { Config = Config.Load(); RefreshMenu(); };
            tray.ContextMenuStrip = m;
            tray.MouseClick += delegate (object s, WF.MouseEventArgs ev) { if (ev.Button == WF.MouseButtons.Left) OpenSettings(); };
            RefreshMenu();
        }

        static WF.TrackBar MakeBar(int max)
        {
            return new WF.TrackBar { Minimum = 0, Maximum = max, TickStyle = WF.TickStyle.None, Width = 215, AutoSize = false, Height = 28, SmallChange = 1, LargeChange = 5 };
        }

        void RefreshMenu()
        {
            if (tray == null) return;
            menuLoading = true;
            agItem.Checked = Config.EnableAntigravity;
            dshItem.Checked = Config.EnableDeepSeekHarness;
            claudeItem.Checked = Config.EnableClaude;
            codexItem.Checked = Config.EnableCodex;
            string m = Config.NormalizeMode(Config.Mode);
            modeAItem.Checked = (m == "a");
            modeBItem.Checked = (m == "b");
            modeCItem.Checked = (m == "c");
            introItem.Checked = Config.PlayIntro;
            loopItem.Checked = Config.LoopBackground;
            stopItem.Enabled = shows.Count > 0;
            alphaBar.Value = Math.Max(0, Math.Min(80, (int)Math.Round(Config.ResidualAlpha * 100)));
            volBar.Value = Math.Max(0, Math.Min(100, (int)Math.Round(Config.IntroVolume * 100)));
            alphaLabel.Text = "背景不透明度  " + alphaBar.Value + "%";
            volLabel.Text = "开屏音量  " + volBar.Value + "%";
            menuLoading = false;
        }

        void PromoteTrayIcon()
        {
            try
            {
                string exe = Process.GetCurrentProcess().MainModule.FileName;
                using (var root = Registry.CurrentUser.OpenSubKey(@"Control Panel\NotifyIconSettings"))
                {
                    if (root == null) return;
                    foreach (var name in root.GetSubKeyNames())
                    {
                        using (var k = Registry.CurrentUser.OpenSubKey(@"Control Panel\NotifyIconSettings\" + name, true))
                        {
                            if (k == null) continue;
                            var path = k.GetValue("ExecutablePath") as string;
                            if (path == null || !string.Equals(path, exe, StringComparison.OrdinalIgnoreCase)) continue;
                            if (k.GetValue("IsPromoted") == null) k.SetValue("IsPromoted", 1, RegistryValueKind.DWord);
                        }
                    }
                }
            }
            catch { }
        }

        void RunTest()
        {
            string mode = Arg("--play") ?? "intro";
            double exitAfter = double.Parse(Arg("--exit-after") ?? "20", CultureInfo.InvariantCulture);
            string shotDir = Arg("--shot-dir");
            string shots = Arg("--shot-at");
            var startAt = DateTime.Now;
            var timer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(100) };
            bool started = false;
            var pending = new List<double>();
            if (shots != null) foreach (var s in shots.Split(',')) pending.Add(double.Parse(s, CultureInfo.InvariantCulture));
            DateTime showStart = DateTime.Now;
            timer.Tick += delegate
            {
                if (!started)
                {
                    if (StartOnCurrent(mode != "loop", Finder.AppTest)) { started = true; showStart = DateTime.Now; }
                    else if ((DateTime.Now - startAt).TotalSeconds > 15) Quit();
                    return;
                }
                double el = (DateTime.Now - showStart).TotalSeconds;
                Show activeShow;
                shows.TryGetValue(Finder.AppTest, out activeShow);
                for (int i = pending.Count - 1; i >= 0; i--)
                    if (el >= pending[i] && activeShow != null && shotDir != null)
                    {
                        double at = pending[i]; pending.RemoveAt(i);
                        try { Directory.CreateDirectory(shotDir); activeShow.Snapshot(Path.Combine(shotDir, "shot_" + at.ToString("00.0", CultureInfo.InvariantCulture) + ".png")); }
                        catch { }
                    }
                if (el >= exitAfter) { timer.Stop(); StopAllShows(); Quit(); }
            };
            timer.Start();
        }

        void RenderSubtitleTest()
        {
            try
            {
                string bg = Arg("--render-subtitle");
                string outPath = args[Array.IndexOf(args, "--render-subtitle") + 2];
                var img = new BitmapImage(new Uri(Path.GetFullPath(bg)));
                int W = img.PixelWidth, H = img.PixelHeight;
                var g = new Grid { Width = W, Height = H };
                g.Children.Add(new Image { Source = img, Stretch = Stretch.Fill });
                var s = new SubtitleElement { WidthRatio = Config.SubtitleWidthRatio, Opacity = 1 };
                var sub0 = Config.Subtitles.Count > 0 ? Config.Subtitles[0] : new Subtitle("拯救世界的事，就交给我吧……", "Leave saving the world to me...", 0, 10);
                s.SetText(sub0.Text, sub0.SubText);
                g.Children.Add(s);
                g.Measure(new Size(W, H)); g.Arrange(new Rect(0, 0, W, H)); g.UpdateLayout();
                var rtb = new RenderTargetBitmap(W, H, 96, 96, PixelFormats.Pbgra32);
                rtb.Render(g);
                var enc = new PngBitmapEncoder(); enc.Frames.Add(BitmapFrame.Create(rtb));
                using (var f = File.Create(outPath)) enc.Save(f);
            }
            catch (Exception ex) { Log.W("字幕渲染失败：" + ex); }
            Shutdown();
        }
    }

    public static class Program
    {
        [STAThread]
        public static int Main(string[] args)
        {
            Native.EnablePerMonitorDpi();
            GpuPref.Ensure();
            bool test = Array.IndexOf(args, "--target-title") >= 0 || Array.IndexOf(args, "--render-subtitle") >= 0;
            Mutex mutex = null;
            EventWaitHandle showEvent = null;
            if (!test)
            {
                bool created;
                mutex = new Mutex(true, @"Local\aemeath.antigravity-boot-animation", out created);
                showEvent = new EventWaitHandle(false, EventResetMode.AutoReset, @"Local\aemeath.antigravity-boot-animation.show");
                if (!created)
                {
                    showEvent.Set();
                    return 0;
                }
            }
            AppDomain.CurrentDomain.UnhandledException += delegate (object s, UnhandledExceptionEventArgs e) { Log.W("崩溃：" + e.ExceptionObject); };
            var app = new App(args);
            app.DispatcherUnhandledException += delegate (object s, DispatcherUnhandledExceptionEventArgs e) { Log.W("出错：" + e.Exception); e.Handled = true; };
            if (showEvent != null)
            {
                var ev = showEvent;
                var th = new Thread(delegate ()
                {
                    while (true) { ev.WaitOne(); app.Dispatcher.BeginInvoke(new Action(delegate { app.OpenSettings(); })); }
                }) { IsBackground = true };
                th.Start();
            }
            int code = app.Run();
            GC.KeepAlive(mutex);
            return code;
        }
    }
}
