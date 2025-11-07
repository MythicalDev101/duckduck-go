#!/usr/bin/env python3
"""
Read queries from input.txt, search DuckDuckGo for each query, click the first <h3> result (or a reasonable fallback),
and write the resulting opened URL to output.txt.

Usage:
  python main.py --input input.txt --output output.txt [--headless]

Notes:
 - This script uses Selenium and webdriver-manager to auto-install ChromeDriver.
 - Ensure Chrome is installed on your system.
"""
from __future__ import annotations

import argparse
import time
from typing import List, Optional
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.common.exceptions import (
	NoSuchElementException,
	TimeoutException,
	WebDriverException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.remote.webelement import WebElement


def setup_driver(headless: bool = True):
	options = webdriver.ChromeOptions()
	if headless:
		options.add_argument("--headless=new")
	options.add_argument("--no-sandbox")
	options.add_argument("--disable-gpu")
	options.add_argument("--disable-dev-shm-usage")
	# Optional: make automation slightly less detectable
	options.add_experimental_option("excludeSwitches", ["enable-automation"])
	options.add_experimental_option("useAutomationExtension", False)

	service = Service(ChromeDriverManager().install())
	driver = webdriver.Chrome(service=service, options=options)
	driver.set_page_load_timeout(30)
	return driver


def read_queries(path: str) -> List[str]:
	queries: List[str] = []
	with open(path, "r", encoding="utf-8") as f:
		for line in f:
			q = line.strip()
			if q:
				queries.append(q)
	return queries


def write_result(path: str, query: str, url: str) -> None:
	with open(path, "a", encoding="utf-8") as f:
		f.write(f"{query}\t{url}\n")


def click_first_h3_or_fallback(driver: webdriver.Chrome, preferred_domains: Optional[List[str]] = None) -> str:
	"""
	Scan result anchors (h3 ancestors, DuckDuckGo result links, then generic anchors).
	Prefer any link whose href contains a preferred domain (e.g. 'instagram.com').
	If a preferred link is found, click/navigate to it; otherwise fall back to the first suitable link.

	Returns the URL after navigation (or an error message).
	"""
	if preferred_domains is None:
		preferred_domains = []

	before_handles = driver.window_handles

	try:
		# Wait for results to render (h3 or result links)
		WebDriverWait(driver, 8).until(
			lambda d: d.find_elements(By.TAG_NAME, "h3") or d.find_elements(By.CSS_SELECTOR, "a.result__a")
		)
	except TimeoutException:
		pass

	candidates: List[WebElement] = []

	# 1) Gather anchors that are ancestors of <h3>
	try:
		h3s = driver.find_elements(By.TAG_NAME, "h3")
		for h in h3s:
			try:
				a = h.find_element(By.XPATH, "./ancestor::a[1]")
			except NoSuchElementException:
				try:
					a = h.find_element(By.TAG_NAME, "a")
				except NoSuchElementException:
					a = None
			if a is not None:
				href = a.get_attribute("href")
				if href and href.startswith("http"):
					candidates.append(a)
	except Exception:
		pass

	# 2) DuckDuckGo result links
	try:
		ddg_links = driver.find_elements(By.CSS_SELECTOR, "a.result__a")
		for a in ddg_links:
			href = a.get_attribute("href")
			if href and href.startswith("http"):
				if a not in candidates:
					candidates.append(a)
	except Exception:
		pass

	# 3) Generic anchors as last resort
	try:
		anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
		for a in anchors:
			href = a.get_attribute("href")
			if href and href.startswith("http") and "duckduckgo.com" not in href:
				if a not in candidates:
					candidates.append(a)
	except Exception:
		pass

	# Helper to click or navigate to an element
	def _open_element(el: WebElement) -> str:
		href = el.get_attribute("href")
		try:
			el.click()
		except WebDriverException:
			if href:
				driver.get(href)
		time.sleep(0.5)
		after_handles = driver.window_handles
		if len(after_handles) > len(before_handles):
			try:
				driver.switch_to.window(after_handles[-1])
			except Exception:
				pass
		try:
			WebDriverWait(driver, 10).until(lambda d: d.current_url and d.current_url != "about:blank")
		except TimeoutException:
			pass
		return driver.current_url

	# 4) Prefer links that match preferred_domains
	if preferred_domains and candidates:
		lower_prefs = [p.lower() for p in preferred_domains]
		for el in candidates:
			href = (el.get_attribute("href") or "").lower()
			for pref in lower_prefs:
				if pref in href:
					return _open_element(el)

	# 5) Fallback: open the first candidate
	if candidates:
		return _open_element(candidates[0])

	return "ERROR: no suitable link found"


def extract_preferred_href(driver: webdriver.Chrome, preferred_domains: Optional[List[str]] = None) -> str:
	"""Return the href of a preferred candidate without clicking/navigating.

	This uses the same candidate discovery order as the click function: h3 ancestor links,
	DuckDuckGo result links, then generic external anchors. If a preferred domain is found it
	returns that href, otherwise returns the first candidate href. Returns an error string
	if nothing suitable is found.
	"""
	if preferred_domains is None:
		preferred_domains = []

	candidates: List[WebElement] = []

	# 1) Gather anchors that are ancestors of <h3>
	try:
		h3s = driver.find_elements(By.TAG_NAME, "h3")
		for h in h3s:
			try:
				a = h.find_element(By.XPATH, "./ancestor::a[1]")
			except NoSuchElementException:
				try:
					a = h.find_element(By.TAG_NAME, "a")
				except NoSuchElementException:
					a = None
			if a is not None:
				href = a.get_attribute("href")
				if href and href.startswith("http"):
					candidates.append(a)
	except Exception:
		pass

	# 2) DuckDuckGo result links
	try:
		ddg_links = driver.find_elements(By.CSS_SELECTOR, "a.result__a")
		for a in ddg_links:
			href = a.get_attribute("href")
			if href and href.startswith("http"):
				if a not in candidates:
					candidates.append(a)
	except Exception:
		pass

	# 3) Generic anchors as last resort
	try:
		anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
		for a in anchors:
			href = a.get_attribute("href")
			if href and href.startswith("http") and "duckduckgo.com" not in href:
				if a not in candidates:
					candidates.append(a)
	except Exception:
		pass

	# Prefer links that match preferred_domains
	if preferred_domains and candidates:
		lower_prefs = [p.lower() for p in preferred_domains]
		for el in candidates:
			raw = el.get_attribute("href")
			href = (raw or "").lower()
			for pref in lower_prefs:
				if pref in href:
					return raw or ""

	# Fallback: return the first candidate href
	if candidates:
		return candidates[0].get_attribute("href") or ""

	return "ERROR: no suitable link found"


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("--input", "-i", default="input.txt", help="Path to input file with queries")
	parser.add_argument("--output", "-o", default="output.txt", help="Path to output file")
	parser.add_argument("--prefer", "-p", default="instagram.com", help="Comma-separated list of preferred domains, e.g. instagram.com,facebook.com")
	parser.add_argument("--click", action="store_true", help="Actually click/open the link (default: off). When off the script only extracts the preferred href without navigating.")
	parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
	args = parser.parse_args()

	# parse prefer list
	prefer_list: Optional[List[str]] = None
	if args.prefer:
		prefer_list = [p.strip() for p in args.prefer.split(",") if p.strip()]

	queries = read_queries(args.input)
	if not queries:
		print(f"No queries found in {args.input}")
		return

	print(f"Found {len(queries)} queries. Starting browser (headless={args.headless})...")
	driver = setup_driver(headless=args.headless)

	try:
		for i, q in enumerate(queries, start=1):
			print(f"[{i}/{len(queries)}] Searching for: {q}")
			search_url = f"https://duckduckgo.com/?q={quote_plus(q)}"
			try:
				driver.get(search_url)
			except WebDriverException as e:
				print(f"Failed to load search page for '{q}': {e}")
				write_result(args.output, q, f"ERROR: could not load search page: {e}")
				continue

			try:
				if args.click:
					# actually click and navigate
					result_url = click_first_h3_or_fallback(driver, preferred_domains=prefer_list)
				else:
					# default: no-click mode, just extract preferred href
					result_url = extract_preferred_href(driver, preferred_domains=prefer_list)
			except Exception as e:
				result_url = f"ERROR: exception during processing: {e}"

			print(f" -> result: {result_url}")
			write_result(args.output, q, result_url)

			# Close any extra tabs/windows and return to a blank state before next query
			handles = driver.window_handles
			if len(handles) > 1:
				main_handle = handles[0]
				for h in handles[1:]:
					try:
						driver.switch_to.window(h)
						driver.close()
					except Exception:
						pass
				driver.switch_to.window(main_handle)

			# small polite delay
			time.sleep(1)

	finally:
		driver.quit()


if __name__ == "__main__":
	main()

