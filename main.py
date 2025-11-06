from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import sys
import os
import traceback
import threading

# New: cross-check keyboard availability; fallback to msvcrt for console
try:
    import keyboard  # pip install keyboard
    _KEYBOARD_AVAILABLE = True
except Exception:
    _KEYBOARD_AVAILABLE = False
    try:
        import msvcrt
    except Exception:
        msvcrt = None

# New globals for stopping and active driver reference
stop_event = threading.Event()
current_driver = None

def on_f2_pressed():
    # set stop flag and attempt to quit driver, then exit
    stop_event.set()
    try:
        print("F2 pressed — stopping processes...", file=sys.stderr)
    except Exception:
        pass
    try:
        global current_driver
        if current_driver:
            try:
                current_driver.quit()
            except Exception:
                pass
    finally:
        # force exit to ensure background threads stop
        try:
            os._exit(1)
        except Exception:
            raise SystemExit(1)

def start_key_listener():
    if _KEYBOARD_AVAILABLE:
        try:
            # prefer add_hotkey which is simpler/reliable for a single key
            keyboard.add_hotkey("f2", on_f2_pressed)
        except Exception:
            # fallback to on_press_key if add_hotkey isn't available
            try:
                keyboard.on_press_key("f2", lambda e: on_f2_pressed())
            except Exception:
                pass
    elif msvcrt:
        def _poll_console_keys():
            while not stop_event.is_set():
                try:
                    if msvcrt.kbhit():
                        ch = msvcrt.getch()
                        # function keys return b'\x00' or b'\xe0' then code; F2 code is 60
                        if ch in (b'\x00', b'\xe0'):
                            ch2 = msvcrt.getch()
                            if ch2 == bytes([60]):
                                on_f2_pressed()
                    time.sleep(0.05)
                except Exception:
                    break
        t = threading.Thread(target=_poll_console_keys, daemon=True)
        t.start()
    else:
        # no listener available
        pass

def get_first_result_url(query, headless=True, timeout=15, click_delay=1.5):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # publish driver so the listener can quit it
    global current_driver
    current_driver = driver

    try:
        driver.get("https://duckduckgo.com")
        if stop_event.is_set():
            raise KeyboardInterrupt("Stopped by user (F2)")

        wait = WebDriverWait(driver, timeout)
        search_box = wait.until(EC.presence_of_element_located((By.NAME, "q")))
        if stop_event.is_set():
            raise KeyboardInterrupt("Stopped by user (F2)")
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)

        # wait for results to load (h3 titles present)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h3")))

        # optional short delay before interacting
        elapsed = 0.0
        while elapsed < click_delay:
            if stop_event.is_set():
                raise KeyboardInterrupt("Stopped by user (F2)")
            time.sleep(0.1)
            elapsed += 0.1

        # locate the first h3 and its ancestor link (if any)
        first_h3 = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h3")))
        if stop_event.is_set():
            raise KeyboardInterrupt("Stopped by user (F2)")

        parent_link = None
        try:
            parent_link = first_h3.find_element(By.XPATH, "./ancestor::a[1]")
        except Exception:
            parent_link = None

        # remember current window(s) and URL
        old_windows = driver.window_handles
        old_url = driver.current_url
        link_href = None
        if parent_link:
            try:
                link_href = parent_link.get_attribute("href")
            except Exception:
                link_href = None

        # click the element (prefer the anchor if present)
        try:
            if parent_link:
                parent_link.click()
            else:
                # clickable h3 fallback
                clickable_h3 = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "h3")))
                clickable_h3.click()
        except Exception:
            # if click fails, fall back to returning href if available
            if link_href:
                return link_href
            raise

        # wait for either a URL change or a new window/tab
        end_time = time.time() + timeout
        navigated_url = None
        while time.time() < end_time:
            if stop_event.is_set():
                raise KeyboardInterrupt("Stopped by user (F2)")
            # new window opened
            current_windows = driver.window_handles
            if len(current_windows) > len(old_windows):
                new_handles = [h for h in current_windows if h not in old_windows]
                if new_handles:
                    try:
                        driver.switch_to.window(new_handles[0])
                        navigated_url = driver.current_url
                        break
                    except Exception:
                        pass
            # same window but URL changed
            try:
                if driver.current_url != old_url:
                    navigated_url = driver.current_url
                    break
            except Exception:
                pass
            time.sleep(0.2)

        # if nothing changed, fall back to the anchor href (if available)
        if not navigated_url:
            navigated_url = link_href or old_url

        return navigated_url
    finally:
        # clear global driver reference and quit
        try:
            current_driver = None
        except Exception:
            pass
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    # start listener before heavy work
    start_key_listener()
    print("Key listener started (press F2 to stop).", file=sys.stderr)

    input_path = os.path.join(os.path.dirname(__file__), "input.txt")
    output_path = os.path.join(os.path.dirname(__file__), "output.txt")

    if not os.path.exists(input_path):
        print("input.txt not found in project folder.", file=sys.stderr)
        sys.exit(1)

    query = open(input_path, "r", encoding="utf-8").read().strip()
    if not query:
        print("input.txt is empty.", file=sys.stderr)
        sys.exit(1)

    try:
        # run with visible browser for debugging
        url = get_first_result_url(query, headless=False)
    except KeyboardInterrupt:
        print("Stopped by user (F2). Exiting.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("Search failed:", file=sys.stderr)
        traceback.print_exc()
        # also print raw exception (may be empty)
        print(repr(e), file=sys.stderr)
        sys.exit(1)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write((url or "").strip() + "\n")

    print("Wrote first result URL to", output_path)
