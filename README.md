# DuckDuckGo search-click script

This repository contains a small Python script that:

- Reads queries (one per line) from `input.txt`.
- Searches DuckDuckGo for each query.
- Clicks the first result's heading (attempts to click the first `<h3>`; falls back to other link selectors).
- Writes the URL opened after the click to `output.txt` in tab-separated format: `query\turl`.

Requirements
- Python 3.8+
- Chrome browser installed on Windows
- Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run

```bash
python main.py --input input.txt --output output.txt --headless
```

Notes
- By default the script runs in headless mode when `--headless` is supplied. Omit it to see the browser.
- The script uses `webdriver-manager` to download the matching ChromeDriver automatically.
- If a search triggers a CAPTCHA or the site blocks automation, the script will record an error line in `output.txt`.

Be polite and avoid sending a large number of automated queries in a short time.
