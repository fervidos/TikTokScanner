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

# ANSI Cursor Controls
UP = "\033[A"
CLEAR = "\033[K"

class VideoLogger:
    def __init__(self, total_videos):
        self.total = total_videos
        self.current_index = 0
        self.success_count = 0
        self.error_count = 0
        self.current_video_block_start = False

    def start_video(self, index, username, video_id):
        self.current_index = index
        print(f"\n[{index:02d}/{self.total:02d}] {GREEN}🟢 STARTING:{RESET}  @{username} - {video_id}")
        # placeholders
        print(f"        {CYAN}TITLE:{RESET}     Waiting for metadata...")
        print(f"        {CYAN}FORMAT:{RESET}    Detecting...")
        sys.stdout.write(f"        {CYAN}STATUS:{RESET}    ⬇️  Initializing...")
        sys.stdout.flush()
        self.current_video_block_start = True

    def update_metadata(self, title, fmt, size):
        # Move up 2 lines to update TITLE, then FORMAT, then back to STATUS
        sys.stdout.write(f"\r{UP}{UP}")
        sys.stdout.write(f"\r        {CYAN}TITLE:{RESET}     {title[:50]}{'...' if len(title)>50 else ''}{CLEAR}\n")
        sys.stdout.write(f"\r        {CYAN}FORMAT:{RESET}    {fmt} | {size}{CLEAR}\n")
        # Restore cursor to STATUS line start
        sys.stdout.write(f"\r        {CYAN}STATUS:{RESET}    ⬇️  Downloading...")
        sys.stdout.flush()

    def update_status(self, msg, color=RESET):
        sys.stdout.write(f"\r{CLEAR}        {CYAN}STATUS:{RESET}    {color}{msg}{RESET}")
        sys.stdout.flush()

    def finish_video(self, status="success", error_msg=None):
        if status == "success":
            self.update_status(f"✅ Download Complete", color=GREEN)
            self.success_count += 1
        else:
            self.update_status(f"❌ Error: {error_msg}", color=RED)
            self.error_count += 1
        print() # Newline to commit the block

    def print_summary(self):
        print("-" * 70)
        print(f"SUMMARY: {self.success_count}/{self.total} Videos Processed Successfully | {self.error_count} Errors")

video_logger = None

def progress_hook(d):
    global video_logger
    if not video_logger:
        return

    if d['status'] == 'downloading':
        try:
            # Update metadata if we have it and haven't set it nicely yet
            # Note: yt-dlp provides info_dict in d, but sometimes keys are missing in progress
            # We check if we can update the static lines
            if d.get('info_dict'): 
                # This check might need more robustness as info_dict might not always be fully populated in progress hooks
                pass
            
            p = d.get('_percent_str', 'N/A').replace('%','')
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            
            # We can try to extract title/format if not done, but usually we might do this earlier or just update status
            # For now, let's just update status with progress
            video_logger.update_status(f"⬇️  {p}% | Speed: {speed} | ETA: {eta}", color=YELLOW)
        except:
            pass
    elif d['status'] == 'finished':
        # Don't finish here yet, we might want to wait for post-processing? 
        # Actually yt-dlp 'finished' means download finished. Post-processing might follow.
        # But for this simple script, it's mostly done.
        video_logger.update_status("✅ Finalizing...", color=GREEN)

def post_processor_hook(d):
    # This might be needed if we want to capture the final filename or post-processing status
    pass

class MyLogger:
    def debug(self, msg):
        pass
    def info(self, msg):
        pass
    def warning(self, msg):
        pass
    def error(self, msg):
        # We might want to catch errors to display in the block
        pass

def download_videos(video_urls, output_folder=DOWNLOAD_DIR, cookie_file=None):
    global video_logger
    """Downloads videos using yt-dlp."""
    if not video_urls:
        print("No videos to download.")
        return

    print(f"Starting download of {len(video_urls)} videos to '{output_folder}'...")
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    video_logger = VideoLogger(len(video_urls))

    ydl_opts = {
        'outtmpl': os.path.join(output_folder, '%(uploader)s_%(upload_date)s_%(id)s_%(title).50s.%(ext)s'),
        'ignoreerrors': True,
        'format': 'bestvideo+bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'logger': MyLogger(),
        'progress_hooks': [progress_hook],
    }
    
    if cookie_file and os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for index, url in enumerate(video_urls, 1):
            # Extract info first to populate metadata
            # We use extract_info with download=False to get metadata, then download
            # Or we just rely on download hook? extract_info is better for the UI
            try:
                # Basic ID/User extraction from URL for initial line
                # URL structure: https://www.tiktok.com/@user/video/id
                username = "unknown"
                vid_id = "unknown"
                try:
                    parts = url.split('/')
                    username = parts[3]
                    vid_id = parts[5]
                except:
                    pass

                video_logger.start_video(index, username, vid_id)

                # Get metadata (fast)
                info = ydl.extract_info(url, download=False)
                if info:
                    title = info.get('title', 'Unknown Title')
                    fmt = info.get('format', 'best')
                    # format usually is a string like "248 - 1080x1920 (1080p)+140 - audio only (medium)"
                    # Simplify format string
                    width = info.get('width', '?')
                    height = info.get('height', '?')
                    simplified_fmt = f"{info.get('ext','mp4')}_{height}p"
                    
                    filesize = info.get('filesize', 0) or info.get('filesize_approx', 0)
                    size_mb = f"{filesize / 1024 / 1024:.1f}MB" if filesize else "?MB"
                    
                    video_logger.update_metadata(title, simplified_fmt, size_mb)
                
                # Now download
                ydl.download([url])
                video_logger.finish_video(status="success")
            except Exception as e:
                video_logger.finish_video(status="error", error_msg=str(e))
    
    video_logger.print_summary()

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
