"""
selenium_handler.py
────────────────────────────
Browser automation for the eCourts portal (services.ecourts.gov.in/ecourtindia_v6/).

All selectors verified against live DOM inspection:
  - CNR input      : id="cino"
  - CAPTCHA input  : id="fcaptcha_code"
  - Search button  : id="searchbtn"
  - Results div    : id="history_cnr"
  - Court heading  : id="chHeading"
  - Interim orders : class="table_order table"
  - PDF links      : href + onclick="displayPdf(...)"
"""

import os
import re
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementClickInterceptedException
)

ECOURTS_URL = "https://services.ecourts.gov.in/ecourtindia_v6/"

STATE_CODES = {
    "AP": "Andhra Pradesh",  "AR": "Arunachal Pradesh", "AS": "Assam",
    "BR": "Bihar",           "CG": "Chhattisgarh",      "DL": "Delhi",
    "GA": "Goa",             "GJ": "Gujarat",            "HP": "Himachal Pradesh",
    "HR": "Haryana",         "JH": "Jharkhand",          "JK": "Jammu & Kashmir",
    "KA": "Karnataka",       "KL": "Kerala",             "MH": "Maharashtra",
    "ML": "Meghalaya",       "MN": "Manipur",            "MP": "Madhya Pradesh",
    "MZ": "Mizoram",         "NL": "Nagaland",           "OR": "Odisha",
    "PB": "Punjab",          "RJ": "Rajasthan",          "SK": "Sikkim",
    "TN": "Tamil Nadu",      "TR": "Tripura",            "TS": "Telangana",
    "UK": "Uttarakhand",     "UP": "Uttar Pradesh",      "WB": "West Bengal",
}


# ─────────────────────────────────────────────────────────────────────────────
#  BROWSER SETUP
# ─────────────────────────────────────────────────────────────────────────────

def setup_driver() -> tuple:
    """Launch Chrome. Returns (driver, download_dir)."""
    download_dir = os.path.abspath(os.path.join("data", "downloads"))
    os.makedirs(download_dir, exist_ok=True)

    options = Options()
    options.add_experimental_option("prefs", {
        "download.default_directory":         download_dir,
        "download.prompt_for_download":        False,
        "download.directory_upgrade":          True,
        "plugins.always_open_pdf_externally":  True,   # force PDF download
        "safebrowsing.enabled":                True,
    })
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")

    options.add_argument("--log-level=3")
    options.add_experimental_option(
        "excludeSwitches",
        ["enable-logging"],
    )

    service = Service(
        ChromeDriverManager().install()
    )

    driver = webdriver.Chrome(
        service=service,
        options=options,
    )

    driver.set_page_load_timeout(60)
    driver.implicitly_wait(2)

    return driver, download_dir


# ─────────────────────────────────────────────────────────────────────────────
#  SMALL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _wait(driver, by, value, timeout=30):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def _safe_text(el, default="") -> str:
    try:
        return el.text.strip()
    except Exception:
        return default


def _state_from_cnr(cnr: str) -> str:
    return STATE_CODES.get(cnr[:2].upper(), "Unknown") if len(cnr) >= 2 else "Unknown"


def _calc_consecutive_adjournments(history: list) -> int:
    """Count trailing consecutive adjournments (history is newest-first)."""
    count = 0
    for entry in history:
        purpose = entry.get("purpose", "").lower()
        if any(kw in purpose for kw in ("adjourn", "adj.", "nbd", "nb date")):
            count += 1
        else:
            break
    return count


def _wait_for_new_pdf(download_dir: str, before: set, timeout=30) -> str | None:
    """Poll until a new .pdf appears in download_dir. Returns path or None."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = {
            f for f in os.listdir(download_dir)
            if f.lower().endswith(".pdf") and not f.endswith(".crdownload")
        }
        new = current - before
        if new:
            latest = max(new, key=lambda f: os.path.getmtime(os.path.join(download_dir, f)))
            return os.path.join(download_dir, latest)
        time.sleep(1)
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE NAVIGATION
# ─────────────────────────────────────────────────────────────────────────────

def open_search_page(driver):
    """Navigate to eCourts and ensure the CNR search form is visible."""
    driver.get(ECOURTS_URL)
    time.sleep(2)

    # Click "CNR Number" tile in the left Search Menu if present
    try:
        tile = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH,
                "//a[normalize-space()='CNR Number'] | "
                "//li[contains(.,'CNR Number')]//a"
            ))
        )
        tile.click()
        time.sleep(1)
    except TimeoutException:
        pass  # already on CNR form


def enter_cnr_number(driver, cnr: str):
    """
    Type the CNR into id='cino'.
    The user then manually types the CAPTCHA (id='fcaptcha_code') and
    clicks Search (id='searchbtn').
    """
    field = _wait(driver, By.ID, "cino", timeout=15)
    field.clear()
    field.send_keys(cnr)
    print(f"  [{cnr}] CNR entered into #cino.")
    print(f"  [{cnr}] ⏸  Please type the CAPTCHA and click Search...")


def wait_for_case_results(driver, timeout=120) -> bool:
    """
    Block until the results div (id='history_cnr') is present and non-empty.
    This fires only after the user solves the CAPTCHA and the page reloads.
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "history_cnr"))
        )
        # Also wait for the court heading to be populated
        WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.ID, "chHeading").text.strip() != ""
        )
        return True
    except TimeoutException:
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  DATA EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def _row_value(table_el, label_text: str) -> str:
    """
    Inside a <table>, find the <td> whose text matches label_text
    and return the text of the next sibling <td>.
    """
    try:
        label_td = table_el.find_element(
            By.XPATH, f".//td[normalize-space()='{label_text}']"
        )
        return label_td.find_element(By.XPATH, "following-sibling::td[1]").text.strip()
    except NoSuchElementException:
        return ""


def extract_case_data(driver) -> dict:
    """
    Scrape the entire case-detail page inside id='history_cnr'.
    Returns a flat dict whose keys match the 'cases' table in db_handler.
    """
    root = driver.find_element(By.ID, "history_cnr")
    d = {}

    # ── Court name ────────────────────────────────────────────────────────────
    d["court_name"] = root.find_element(By.ID, "chHeading").text.strip()

    # ── Case Details (headers-based cells) ───────────────────────────────────
    # eCourts uses  headers="fn6" … "fn10" as the data cells

    def _by_headers(hdr):
        try:
            return root.find_element(
                By.XPATH, f".//td[@headers='{hdr}']"
            ).text.strip()
        except NoSuchElementException:
            return ""

    # case_type lives in class="fw-bold text-uppercase" + headers="fn6"
    try:
        d["case_type"] = root.find_element(
            By.XPATH, ".//td[@headers='fn6' and contains(@class,'fw-bold')]"
        ).text.strip()
    except NoSuchElementException:
        d["case_type"] = _by_headers("fn6")

    d["filing_number"]       = _by_headers("fn7")
    d["filing_date"]         = _by_headers("fn8")
    d["registration_number"] = _by_headers("fn9")
    d["registration_date"]   = _by_headers("fn10")

    # CNR number — grab the red/bold CNR text; strip the "(Note...)" suffix
    try:
        raw_cnr = root.find_element(
            By.XPATH, ".//td[normalize-space()='CNR Number']/following-sibling::td[1]"
        ).text.strip()
        d["cnr_number"] = raw_cnr.split("(")[0].strip()
    except NoSuchElementException:
        d["cnr_number"] = ""

    # ── Case Status table ─────────────────────────────────────────────────────
    # class="table case_status_table table-bordered"
    try:
        status_table = root.find_element(
            By.CSS_SELECTOR, "table.case_status_table"
        )
        d["first_hearing_date"] = _row_value(status_table, "First Hearing Date")
        d["next_hearing_date"]  = _row_value(status_table, "Next Hearing Date")
        d["case_stage"]         = _row_value(status_table, "Case Stage")
        d["court_judge"]        = _row_value(status_table, "Court Number and Judge")
    except NoSuchElementException:
        d["first_hearing_date"] = d["next_hearing_date"] = ""
        d["case_stage"]         = d["court_judge"]       = ""

    # ── Petitioner & Advocate ─────────────────────────────────────────────────
    # class="table table-bordered Petitioner_Advocate_Table petitioner-advocate-list border"
    petitioner, lawyer = "", ""
    try:
        pet_table = root.find_element(
            By.CSS_SELECTOR, "table.Petitioner_Advocate_Table"
        )
        # All visible text in the table; format is:
        #   "1) ICICI Bank Ltd.\n   Advocate- Sh. Anil Kumar Kaushik"
        lines = [l.strip() for l in pet_table.text.split("\n") if l.strip()]
        for line in lines:
            if line and line[0].isdigit() and ")" in line:
                petitioner = re.sub(r"^\d+\)\s*", "", line).strip()
            elif re.search(r"Advocate|Adv\.", line, re.IGNORECASE):
                lawyer = re.sub(r"^Advocate[- ]*", "", line, flags=re.IGNORECASE).strip()
            if petitioner and lawyer:
                break
    except NoSuchElementException:
        pass
    d["petitioner"] = petitioner
    d["lawyer"]     = lawyer

    # ── Respondent & Advocate ─────────────────────────────────────────────────
    # class="table table-bordered Respondant_Advocate_Table respondant-advocate-list border"
    opposite_party, op_lawyer = "", ""
    try:
        res_table = root.find_element(
            By.CSS_SELECTOR, "table.Respondant_Advocate_Table"
        )
        lines = [l.strip() for l in res_table.text.split("\n") if l.strip()]
        for line in lines:
            if line and line[0].isdigit() and ")" in line:
                opposite_party = re.sub(r"^\d+\)\s*", "", line).strip()
            elif re.search(r"Advocate|Adv\.", line, re.IGNORECASE):
                op_lawyer = re.sub(r"^Advocate[- ]*", "", line, flags=re.IGNORECASE).strip()
            if opposite_party and op_lawyer:
                break
    except NoSuchElementException:
        pass
    d["opposite_party"] = opposite_party
    d["op_lawyer"]      = op_lawyer

    # ── Acts (id="act_table") ─────────────────────────────────────────────────
    acts = []
    try:
        act_table = root.find_element(By.ID, "act_table")
        for row in act_table.find_elements(By.XPATH, ".//tr[position()>1]"):
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 2:
                act  = cols[0].text.strip()
                secs = cols[1].text.strip()
                if act:
                    acts.append(f"{act} § {secs}")
    except NoSuchElementException:
        pass
    d["acts"] = " | ".join(acts)

    # ── Case History ──────────────────────────────────────────────────────────
    # Columns: Judge | Business on Date | Hearing Date | Purpose of Hearing
    history = []
    try:
        # Identify the history table by its header text
        hist_table = root.find_element(
            By.XPATH,
            ".//table[.//th[contains(normalize-space(),'Business on Date')]]"
        )
        for row in hist_table.find_elements(By.XPATH, ".//tr[position()>1]"):
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 4:
                history.append({
                    "judge":         cols[0].text.strip(),
                    "business_date": cols[1].text.strip(),
                    "hearing_date":  cols[2].text.strip(),
                    "purpose":       cols[3].text.strip(),
                })
    except NoSuchElementException:
        pass

    d["case_history"]              = history
    d["hearing_count"]             = len(history)
    d["consecutive_adjournments"]  = _calc_consecutive_adjournments(history)
    d["latest_hearing_date"]       = history[0]["hearing_date"] if history else ""
    d["state"]                     = _state_from_cnr(d.get("cnr_number", ""))

    return d


# ─────────────────────────────────────────────────────────────────────────────
#  PDF DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────

def _parse_display_pdf_url(onclick: str, base_url: str) -> str | None:
    """
    eCourts uses onclick="displayPdf('...url...')" on order links.
    Extract whatever is inside the first string argument.
    """
    from urllib.parse import urljoin
    # Match the first quoted argument of displayPdf(...)
    match = re.search(r"displayPdf\s*\(\s*['\"]([^'\"]+)['\"]", onclick)
    if match:
        url = match.group(1)
        return url if url.startswith("http") else urljoin(base_url, url)
    return None


def download_latest_order(driver, download_dir: str, cnr: str) -> str | None:
    """
    Find the LAST row in class='table_order table' (most recent interim order),
    extract the PDF URL from href or onclick="displayPdf(...)", and download it.

    Three strategies, tried in order:
      1. Direct href → requests download (using browser cookies)
      2. Parse displayPdf() onclick → requests download
      3. Click the link → let Chrome auto-download
    """
    try:
        root   = driver.find_element(By.ID, "history_cnr")
        before = {
            f for f in os.listdir(download_dir)
            if f.lower().endswith(".pdf")
        }

        # Find the interim orders table
        try:
            order_table = root.find_element(By.CSS_SELECTOR, "table.table_order")
        except NoSuchElementException:
            print(f"  [{cnr}] Interim orders table not found.")
            return None

        # All links in the 3rd column (Order Details)
        order_links = order_table.find_elements(By.XPATH, ".//tr[position()>1]//td[3]//a")
        if not order_links:
            print(f"  [{cnr}] No PDF links in interim orders table.")
            return None

        latest = order_links[-1]   # last row = most recent order
        href    = latest.get_attribute("href") or ""
        onclick = latest.get_attribute("onclick") or ""

        # ── Strategy 1: href is a direct PDF URL ─────────────────────────────
        if href and href.lower() not in ("", "#", "javascript:void(0)"):
            path = _download_via_requests(driver, href, download_dir, cnr)
            if path:
                print(f"  [{cnr}] PDF via href → {os.path.basename(path)}")
                return path

        # ── Strategy 2: parse displayPdf() for the URL ───────────────────────
        if onclick:
            pdf_url = _parse_display_pdf_url(onclick, driver.current_url)
            if pdf_url:
                path = _download_via_requests(driver, pdf_url, download_dir, cnr)
                if path:
                    print(f"  [{cnr}] PDF via displayPdf() → {os.path.basename(path)}")
                    return path

        # ── Strategy 3: click the link, let Chrome download ──────────────────
        try:
            latest.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", latest)

        time.sleep(2)
        path = _wait_for_new_pdf(download_dir, before, timeout=20)
        if path:
            print(f"  [{cnr}] PDF auto-downloaded → {os.path.basename(path)}")
            _close_modal(driver)
            return path

        # ── Strategy 4: PDF opened in modal viewer — grab iframe src ─────────
        try:
            iframe = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH,
                    "//iframe[contains(@src,'.pdf') or contains(@src,'order')]"
                ))
            )
            src = iframe.get_attribute("src")
            if src:
                path = _download_via_requests(driver, src, download_dir, cnr)
                _close_modal(driver)
                if path:
                    print(f"  [{cnr}] PDF from modal iframe → {os.path.basename(path)}")
                    return path
        except TimeoutException:
            pass

        _close_modal(driver)
        print(f"  [{cnr}] All PDF strategies exhausted.")
        return None

    except Exception as e:
        print(f"  [{cnr}] PDF error: {e}")
        return None


def _download_via_requests(driver, url: str, download_dir: str, cnr: str) -> str | None:
    """
    Download a file using requests, sharing the browser's session cookies
    so authenticated/stateful eCourts URLs work correctly.
    """
    session = requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie["name"], cookie["value"])

    headers = {
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "Referer":    driver.current_url,
    }
    try:
        r = session.get(url, headers=headers, timeout=30, stream=True)
        ctype = r.headers.get("content-type", "").lower()
        if r.status_code == 200 and ("pdf" in ctype or url.lower().endswith(".pdf")):
            fname = f"{cnr}_order_{int(time.time())}.pdf"
            fpath = os.path.join(download_dir, fname)
            with open(fpath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return fpath
    except Exception as e:
        print(f"    requests error: {e}")
    return None


def _close_modal(driver):
    """Close any open PDF viewer modal. Tries common selectors then Escape."""
    for xpath in [
        "//button[contains(@class,'close')]",
        "//button[@aria-label='Close']",
        "//button[normalize-space()='×']",
        "//span[@class='close']",
    ]:
        try:
            driver.find_element(By.XPATH, xpath).click()
            time.sleep(0.5)
            return
        except Exception:
            continue
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def scrape_single_cnr(driver, cnr: str, download_dir: str, status_cb=None) -> dict:
    """
    Full scrape cycle for one CNR.

    Returns:
        {
            "cnr":      str,
            "status":   "done" | "failed",
            "data":     dict,        # extract_case_data() output
            "pdf_path": str | None,
            "error":    str | None,
        }
    """
    cnr = cnr.strip().upper()
    start_time = time.time()
    result = {"cnr": cnr, "status": "pending", "data": {}, "pdf_path": None, "error": None}

    def _cb(msg):
        if status_cb:
            status_cb(cnr, msg)

    try:
        _cb("Fetching")
        open_search_page(driver)
        enter_cnr_number(driver, cnr)

        _cb("Waiting for CAPTCHA")
        if not wait_for_case_results(driver, timeout=120):
            raise TimeoutError("CAPTCHA not solved within 120 seconds.")

        _cb("Extracting data")
        result["data"] = extract_case_data(driver)

        _cb("Downloading PDF")
        result["pdf_path"] = download_latest_order(driver, download_dir, cnr)

        result["status"] = "done"
        _cb("Done")
        print(f"  [{cnr}] ✓ Complete")

    except Exception as exc:
        result["status"] = "failed"
        result["error"]  = str(exc)
        _cb("Failed")
        print(f"  [{cnr}] ✗ Failed — {exc}")

    result['processing_time'] = round(time.time() - start_time, 2)
    return result


def scrape_cnr_list(cnr_list: list, status_cb=None) -> list:
    """
    Scrape a list of CNRs sequentially in one browser session.

    Args:
        cnr_list:  List of raw CNR strings.
        status_cb: Optional callable(cnr, status_msg) for live UI updates.

    Returns:
        List of result dicts (one per CNR, in input order).
    """
    driver, download_dir = setup_driver()
    results = []
    failed  = []

    try:
        for raw in cnr_list:
            cnr = raw.strip().upper()
            if not cnr:
                continue
            print(f"\n{'─' * 58}")
            r = scrape_single_cnr(driver, cnr, download_dir, status_cb)
            results.append(r)
            if r["status"] == "failed":
                failed.append(cnr)
            time.sleep(1.5)

    finally:
        driver.quit()
        print(f"\n{'═' * 58}")
        print(f"Done │ Success: {len(results) - len(failed)} │ Failed: {len(failed)}")
        if failed:
            print(f"Failed CNRs: {', '.join(failed)}")

    return results