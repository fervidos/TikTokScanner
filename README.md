# 🎥 TikTok Profile Scanner & Downloader

> A powerful, stealthy, and efficient tool to scan and download all videos from any TikTok profile.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Playwright](https://img.shields.io/badge/Playwright-Automated-green)
![yt-dlp](https://img.shields.io/badge/yt--dlp-Downloader-red)

## 🚀 Features

*   **🔍 Automated Scanning:** Navigates to a TikTok profile and intelligently scrolls to find *all* video links.
*   **🕵️ Stealth Mode:** Utilizes `playwright-stealth` to mimic real user behavior and avoid bot detection.
*   **🧩 Captcha Handling:** Detects login walls and captchas, pausing execution to allow manual solving.
*   **🍪 Cookie Support:** Bypass login restrictions by loading your session cookies from `src/cookies.txt`.
*   **⬇️ High-Quality Downloads:** Leverages `yt-dlp` to download the best available video quality without watermarks (where possible).
*   **📂 Organized Output:** Automatically saves videos into folders named after the TikTok user.
*   **👻 Headless Mode:** Run in the background without a visible browser window (perfect for servers).
*   **🧪 Dry Run Mode:** Scan a profile and list video URLs without downloading anything.

## 🛠️ Installation

1.  **Clone the repository** (if you haven't already):
    ```bash
    git clone https://github.com/yourusername/TikTokScanner.git
    cd TikTokScanner
    ```

2.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install Playwright Browsers:**
    ```bash
    playwright install chromium
    ```

## 📖 Usage

### Method 1: Interactive Mode (Windows)

Simply double-click the `run.bat` file.
1.  A terminal window will open.
2.  Paste the TikTok profile URL when prompted (e.g., `https://www.tiktok.com/@username`).
3.  Sit back and watch it work!

### Method 2: Command Line

Run the script directly from your terminal:

```bash
python src/main.py https://www.tiktok.com/@username [options]
```

### Options

| Flag | Description |
| :--- | :--- |
| `--headless` | Run the browser in headless mode (no UI). Default is `False` unless on Linux/Server. |
| `--dry-run` | Only scan for videos and print URLs; do not download them. |
| `--output <dir>` | Specify a custom base directory for downloads (default: `downloads`). |

**Example:**
```bash
python src/main.py https://www.tiktok.com/@khaby.lame --headless --output my_collection
```

## 🍪 Advanced: Using Cookies

If you encounter frequent captchas or need to access age-restricted content, you can provide your own cookies.

1.  Use a browser extension like **"Get cookies.txt LOCALLY"** (Chrome/Firefox) to export your cookies while logged into TikTok.
2.  Save the file as `cookies.txt` inside the `src/` folder.
    *   (Optional) You can rename `src/cookies.txt.example` to `src/cookies.txt` and paste your content there.
3.  The script will automatically detect and load them.

## ⚠️ Disclaimer

This tool is for educational purposes only. Please respect TikTok's terms of service and the rights of content creators. Do not use this tool for unauthorized scraping or copyright infringement.

## 🤝 Contributing

Contributions are welcome! Feel free to submit a Pull Request.

## 📄 License

MIT License
