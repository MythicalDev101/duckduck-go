# DuckDuckGo Instagram Scraper

This project is a Python-based automation script that searches DuckDuckGo for queries, identifies Instagram profile links, and scrapes profile data such as followers, following, posts, and bio. The results are saved to an Excel file.

## Features

- Searches DuckDuckGo for specified queries.
- Identifies valid Instagram profile links.
- Scrapes Instagram profile data (followers, following, posts, and bio).
- Saves results to an Excel file (`instagram_results.xlsx`).
- Supports persistent browser profiles for seamless login.

## Requirements

- Python 3.8 or higher
- Google Chrome installed
- The following Python packages:
  - `playwright`
  - `openpyxl`
  - `python-dotenv`

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/MythicalDev101/duckduck-go.git
   cd duckduck-go
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   source .venv/bin/activate  # On macOS/Linux
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```bash
   playwright install
   ```

## Configuration

1. Create a `.env` file in the project root and add the following variables:
   ```env
   INSTAGRAM_USERNAME=your_instagram_username
   INSTAGRAM_PASSWORD=your_instagram_password
   USER_DATA_DIR=persistent_profile
   HEADLESS=false
   ```

   - `INSTAGRAM_USERNAME` and `INSTAGRAM_PASSWORD` are optional. If not provided, the script will skip the login step.
   - `USER_DATA_DIR` specifies the directory for the persistent browser profile.
   - `HEADLESS` determines whether the browser runs in headless mode.

2. Prepare an `input.txt` file with one query per line.

## Usage

Run the script using the following command:
```bash
python main.py
```

The script will:
1. Read queries from `input.txt`.
2. Search DuckDuckGo for each query.
3. Identify Instagram profile links.
4. Scrape profile data.
5. Save the results to `instagram_results.xlsx`.

## Output

The results are saved in an Excel file (`instagram_results.xlsx`) with the following columns:
- Query
- Profile URL
- Followers
- Following
- Posts
- Bio

## Notes

- Ensure that Chrome is installed on your system.
- Use a persistent browser profile to avoid frequent logins.
- Add delays between actions to reduce the likelihood of being flagged by Instagram.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
