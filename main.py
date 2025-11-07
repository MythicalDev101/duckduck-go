import re
import json
import time
import os
import openpyxl
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

SEARCH_URL = "https://duckduckgo.com/?q="

# Load .env (optional)
load_dotenv()

INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
USER_DATA_DIR = os.getenv("USER_DATA_DIR", "persistent_profile")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

# ---------------------
# Helpers
# ---------------------

def is_instagram_profile(url):
    # Valid only if:
    # instagram.com/<username>/  (ONLY one segment)
    pattern = r"^https:\/\/www\.instagram\.com\/[^\/]+\/?$"
    return re.match(pattern, url) is not None

def scrape_instagram_profile(page):
    """Extract followers, following, posts, and bio from Instagram profile using parent span logic."""

    # Wait for body to load
    page.wait_for_selector("body")

    try:
        # Extract bio
        bio = page.locator("meta[name='description']").get_attribute("content") or "N/A"

        def extract_stat(keyword):
            """Find keyword in HTML, extract parent span, and retrieve content excluding the keyword."""
            locator = page.locator(f"span:has-text('{keyword}')")
            if not locator:
                return "N/A"

            parent_span = locator.nth(0).locator("..")  # Get parent span
            content = parent_span.inner_text() or "N/A"
            return content.replace(keyword, "").strip()

        # Extract stats
        posts = extract_stat("posts")
        followers = extract_stat("followers")
        following = extract_stat("following")

        return {
            "bio": bio.strip(),
            "followers": followers,
            "following": following,
            "posts": posts
        }

    except Exception as e:
        print("Error scraping profile:", e)
        return None


def ensure_logged_in(page):
    """
    If the page shows a login form, fill it with credentials from .env.
    Returns True if logged in (or login appears to have succeeded).
    If INSTAGRAM_USERNAME/INSTAGRAM_PASSWORD are not set, the function
    will simply return True (no-op).
    """

    # If credentials aren't provided, don't attempt to login.
    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        print("No INSTAGRAM_USERNAME/INSTAGRAM_PASSWORD in .env — skipping automatic login.")
        return True

    page.goto("https://www.instagram.com/", timeout=60000)
    time.sleep(2)

    # If we detect a login form, perform login
    if page.query_selector("input[name='username']"):
        print("Logging into Instagram using .env credentials...")
        page.goto("https://www.instagram.com/accounts/login/", timeout=60000)
        page.wait_for_selector("input[name='username']", timeout=20000)
        page.fill("input[name='username']", INSTAGRAM_USERNAME)
        page.fill("input[name='password']", INSTAGRAM_PASSWORD)
        # submit
        page.click("button[type='submit']")

        # wait for an element that typically appears when logged in
        try:
            page.wait_for_selector("nav", timeout=20000)
        except Exception:
            # sometimes Instagram shows extra flows (save login, 2FA); give a short extra wait
            time.sleep(5)

        # try to verify by visiting the profile page
        try:
            page.goto(f"https://www.instagram.com/{INSTAGRAM_USERNAME}/", timeout=60000)
            time.sleep(2)
        except Exception:
            pass

        # Basic heuristic: if URL does not contain 'accounts/login' or 'login', assume logged in
        if "login" not in page.url:
            print("Login appears successful.")
            return True
        else:
            print("Login may have failed — please check credentials or handle 2FA manually.")
            return False
    else:
        # No login form; likely already logged in or using persistent profile
        print("Already logged into Instagram (or no visible login form).")
        return True

# ---------------------
# MAIN SCRIPT
# ---------------------

def run():
    # Load queries
    with open("input.txt", "r", encoding="utf-8") as f:
        queries = [q.strip() for q in f.readlines() if q.strip()]

    # Prepare Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    if ws is None:
        raise RuntimeError("Failed to initialize Excel worksheet.")

    ws.append(["Query", "Profile URL", "Followers", "Following", "Posts", "Bio"])

    with sync_playwright() as pw:
        browser = pw.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,  # Ensure non-headless mode for safer automation
            channel="chrome"
        )

        page = browser.new_page()

        # Ensure logged in (only attempts login if credentials are provided in .env)
        try:
            ok = ensure_logged_in(page)
            if not ok:
                print("Warning: Unable to assert successful login. You may need to manually login once.")
        except Exception as e:
            print("Warning: ensure_logged_in encountered an error:", e)

        # Loop queries
        for query in queries:
            print(f"\n=== Searching for: {query} ===")

            page.goto(SEARCH_URL + query)
            page.wait_for_selector("h2")

            # Grab result links
            results = page.locator("a[data-testid='result-extras-url-link']").all()

            instagram_profile_url = None
            scraped_data = None

            # Check first 5 results
            for i, link in enumerate(results[:5]):
                try:
                    url = link.get_attribute("href")
                except Exception as e:
                    print("Error retrieving link attribute:", e)
                    continue

                if not url:
                    continue

                print(f"Checking result {i+1}: {url}")

                page.goto(url, timeout=60000)

                if "instagram.com" in page.url:
                    final_url = page.url.split("?")[0]  # clean tracking params

                    if is_instagram_profile(final_url):
                        print("✅ Valid Instagram profile:", final_url)

                        instagram_profile_url = final_url
                        scraped_data = scrape_instagram_profile(page)
                        break
                    else:
                        print("❌ Not a profile link.")
                else:
                    print("❌ Not Instagram.")

            # Ensure workbook and worksheet are initialized
            if ws is None:
                raise ValueError("Worksheet initialization failed. Ensure the workbook is correctly created.")

            # Safely handle NoneType for scraped_data
            if scraped_data is None:
                scraped_data = {"followers": "N/A", "following": "N/A", "posts": "N/A", "bio": "N/A"}

            if instagram_profile_url:
                ws.append([
                    query,
                    instagram_profile_url,
                    scraped_data.get("followers", "N/A"),
                    scraped_data.get("following", "N/A"),
                    scraped_data.get("posts", "N/A"),
                    scraped_data.get("bio", "N/A")
                ])
            else:
                ws.append([query, "Profile Not Found", "", "", "", ""])

            wb.save("instagram_results.xlsx")
            # Add delay to reduce likelihood of being flagged
            time.sleep(5)  # 5-second delay between actions

    print("\n✅ Done! Saved to instagram_results.xlsx")


if __name__ == "__main__":
    run()
