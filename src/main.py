import asyncio
import os
import argparse
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import yt_dlp
import sys
import re

# Define constants
DOWNLOAD_DIR = "downloads"


def parse_netscape_cookies(file_path):
    """Parses a Netscape HTTP Cookie File."""
    cookies = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    cookie = {
                        'domain': parts[0],
                        'path': parts[2],
                        'secure': parts[3].upper() == 'TRUE',
                        'expires': float(parts[4]) if parts[4] else -1,
                        'name': parts[5],
                        'value': parts[6]
                    }
                    cookies.append(cookie)
    except Exception as e:
        print(f"Error parsing cookies file: {e}")
        return []
    return cookies

class TikTokScanner:
    def __init__(self, profile_url, headless=True, cookies=None):
        self.profile_url = profile_url
        self.headless = headless
        self.cookies = cookies or []
        self.video_urls = set()

    async def scan(self):
        """Scans the profile for video URLs."""
        print(f"Starting scan for: {self.profile_url}")
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            if self.cookies:
                console_manager.print_final(f"🍪 Loading {len(self.cookies)} cookies...", color=YELLOW)
                await context.add_cookies(self.cookies)

            page = await context.new_page()
            # Apply stealth techniques
            stealth = Stealth()
            await stealth.apply_stealth_async(page)

            try:
                # Go to profile
                console_manager.print_status("🚀 Navigating to profile...", color=CYAN)
                await page.goto(self.profile_url, timeout=60000)
                await page.wait_for_load_state("networkidle")
                
                # Check for errors or login walls
                if "login" in page.url:
                    console_manager.print_final("⚠️ Redirected to login. You might need to handle captcha manually or provide cookies.", color=RED)

                # Advanced Captcha Verification
                # Check URL or common captcha overlay texts
                captcha_detected = False
                if "verify" in page.url or "captcha" in page.url:
                   captcha_detected = True
                else:
                    # Check for overlay elements in main frame
                    if await page.locator("text=Drag the slider").count() > 0:
                        captcha_detected = True
                    elif await page.locator("text=Verify to continue").count() > 0:
                        captcha_detected = True
                    elif await page.locator(".captcha-container").count() > 0:
                        captcha_detected = True
                    else:
                        # Check frames
                        for frame in page.frames:
                            try:
                                if await frame.locator("text=Drag the slider").count() > 0:
                                    captcha_detected = True
                                    break
                                if await frame.locator("text=Verify to continue").count() > 0:
                                    captcha_detected = True
                                    break
                            except:
                                pass

                if captcha_detected:
                    console_manager.print_final("\n🚨 !!! Captcha or Verification detected !!!", color=RED)
                    console_manager.print_final("Please solve the captcha in the browser window.", color=YELLOW)
                    input("Press Enter here once you have solved it and the page has loaded...")
                    # Give it a moment to settle
                    await page.wait_for_timeout(3000)
                
                console_manager.print_status("🔍 Scanning for videos...", color=CYAN)
                # Scroll and collect
                last_height = await page.evaluate("document.body.scrollHeight")
                while True:
                    # Collect links before scrolling
                    # Try specific data-e2e selector first, fallback to generic video links
                    links = await page.locator('[data-e2e="user-post-item"] a').all()
                    if not links:
                        links = await page.locator("a").all()

                    for link in links:
                        href = await link.get_attribute("href")
                        if href and "/video/" in href:
                            self.video_urls.add(href)
                    
                    console_manager.print_status(f"🔍 Scanning... Videos found so far: {len(self.video_urls)} ✨", color=CYAN)

                    # Scroll down
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    
                    # Random wait to mimic human behavior slightly
                    await page.wait_for_timeout(2000)
                    
                    # Check if reached bottom
                    new_height = await page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        # Check for captcha again in case it popped up during scrolling
                        captcha_scroll_detected = False
                        if await page.locator("text=Drag the slider").count() > 0 or \
                           await page.locator("text=Verify to continue").count() > 0:
                            captcha_scroll_detected = True
                        
                        if not captcha_scroll_detected:
                             for frame in page.frames:
                                try:
                                    if await frame.locator("text=Drag the slider").count() > 0 or \
                                       await frame.locator("text=Verify to continue").count() > 0:
                                        captcha_scroll_detected = True
                                        break
                                except:
                                    pass

                        if captcha_scroll_detected:
                            console_manager.print_final("🚨 !!! Captcha detected during scroll !!!", color=RED)
                            input("Press Enter here once you have solved it...")
                            await page.wait_for_timeout(3000)
                            new_height = await page.evaluate("document.body.scrollHeight") # Re-read height
                        else:
                            # Try one more wait to be sure
                            await page.wait_for_timeout(3000)
                            new_height = await page.evaluate("document.body.scrollHeight")
                            if new_height == last_height:
                                break
                    last_height = new_height
                
                console_manager.print_final(f"✨ Scan complete. Total videos found: {len(self.video_urls)}", color=GREEN)

            except Exception as e:
                print(f"Error during scan: {e}")
            finally:
                await browser.close()
        
        return list(self.video_urls)

class MyLogger:
    def debug(self, msg):
        # For compatibility with youtube-dl, both debug and info are passed into debug
        # You can distinguish them by the prefix '[debug] '
        if msg.startswith('[debug] '):
            pass
        else:
            self.info(msg)

    def info(self, msg):
        # Filter out default download progress lines to avoid clutter
        if "[download]" in msg and "%" in msg:
            pass
        else:
            print(msg)

    def warning(self, msg):
        print(f"WARNING: {msg}")

    def error(self, msg):
        print(f"ERROR: {msg}")

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

class ConsoleManager:
    def __init__(self):
        self.last_line_len = 0

    def print_status(self, msg, color=RESET):
        """Prints a message that overwrites the previous line."""
        sys.stdout.write('\r' + ' ' * self.last_line_len + '\r')  # Clear line
        sys.stdout.write(f"{color}{msg}{RESET}")
        sys.stdout.flush()
        # Calculate parsed length without color codes for clearing
        clean_msg = re.sub(r'\x1b\[[0-9;]*m', '', msg)
        self.last_line_len = len(clean_msg) + 10 # Buffer

    def print_final(self, msg, color=RESET):
        """Prints a final message and moves to the next line."""
        self.print_status(msg, color)
        sys.stdout.write('\n')
        self.last_line_len = 0

console_manager = ConsoleManager()

def progress_hook(d):
    if d['status'] == 'downloading':
        try:
            p = d.get('_percent_str', 'N/A').replace('%','')
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            filename = os.path.basename(d.get('filename', 'Unknown'))
            
            msg = f"⬇️  [Downloading] {filename} | {p}% | Speed: {speed} | ETA: {eta}"
            console_manager.print_status(msg, color=YELLOW)
        except:
            pass
    elif d['status'] == 'finished':
        console_manager.print_final(f"✅ [Finished] Download complete: {os.path.basename(d['filename'])}", color=GREEN)

def download_videos(video_urls, output_folder=DOWNLOAD_DIR, cookie_file=None):
    """Downloads videos using yt-dlp."""
    if not video_urls:
        print("No videos to download.")
        return

    print(f"Starting download of {len(video_urls)} videos to '{output_folder}'...")
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    ydl_opts = {
        # Better naming scheme: Cookie_Date_ID_Title
        'outtmpl': os.path.join(output_folder, '%(uploader)s_%(upload_date)s_%(id)s_%(title).50s.%(ext)s'),
        'ignoreerrors': True,
        'format': 'bestvideo+bestaudio/best',
        'quiet': True, # We will handle output via logger and hook
        'no_warnings': True,
        'logger': MyLogger(),
        'progress_hooks': [progress_hook],
    }
    
    if cookie_file and os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file

    # Download videos one by one to have better control over progress display
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for index, url in enumerate(video_urls, 1):
            console_manager.print_final(f"⬇️  [{index}/{len(video_urls)}] Processing: {url}", color=CYAN)
            ydl.download([url])

async def main():
    parser = argparse.ArgumentParser(description="TikTok Profile Scanner & Downloader")
    parser.add_argument("url", help="TikTok Profile URL (e.g., https://www.tiktok.com/@username)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (default: False)", default=False)
    parser.add_argument("--dry-run", action="store_true", help="Only scan and list videos without downloading")
    parser.add_argument("--output", default="downloads", help="Output directory for downloads")

    args = parser.parse_args()

    # Auto-detect headless mode for Linux/Codespaces without DISPLAY
    is_headless = args.headless
    if sys.platform == "linux" and not os.environ.get("DISPLAY") and not is_headless:
        print("No DISPLAY detected. Forcing headless mode.")
        is_headless = True

    cookies_path = os.path.join("src", "cookies.txt")
    cookies = []
    
    if os.path.exists(cookies_path):
        print(f"Found cookies file at '{cookies_path}'. Loading...")
        cookies = parse_netscape_cookies(cookies_path)
    else:
        print(f"No cookies file found at '{cookies_path}'. Continuing without cookies.")

    # Normalize input to URL
    profile_url = args.url
    if not profile_url.startswith("http"):
        if profile_url.startswith("@"):
            profile_url = f"https://www.tiktok.com/{profile_url}"
        else:
            profile_url = f"https://www.tiktok.com/@{profile_url}"
    
    print(f"Target Profile URL: {profile_url}")

    scanner = TikTokScanner(profile_url, headless=is_headless, cookies=cookies)
    video_urls = await scanner.scan()
    
    if video_urls:
         # Fix URLs if they are relative
        full_urls = []
        for url in video_urls:
            if url.startswith("http"):
                full_urls.append(url)
            else:
                full_urls.append(f"https://www.tiktok.com{url}")
        
        print(f"Found {len(full_urls)} videos.")
        
        # Extract username for folder creation
        username = "unknown_user"
        match = re.search(r'@([a-zA-Z0-9_.-]+)', profile_url)
        if match:
            username = match.group(1)
        
        user_output_dir = os.path.join(args.output, username)

        if args.dry_run:
            print(f"Dry run enabled. Skipping download to '{user_output_dir}'.")
            for url in full_urls:
                print(url)
        else:
            download_videos(full_urls, user_output_dir, cookie_file=cookies_path if os.path.exists(cookies_path) else None)
    else:
        print("No videos found to download.")

if __name__ == "__main__":
    asyncio.run(main())
