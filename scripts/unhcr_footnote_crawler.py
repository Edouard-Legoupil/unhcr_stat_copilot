import argparse
import hashlib
import json
import re
import sys
import time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse

from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError as e:
    raise SystemExit(
        "Playwright is required. Install with:\n"
        "pip install playwright beautifulsoup4\n"
        "playwright install chromium"
    ) from e


BASE_URL = "https://www.unhcr.org/refugee-statistics/download"
FOOTNOTE_FRAME_SELECTOR = "turbo-frame#data_finder_footnotes"


def normalize_whitespace(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_url(base_url: str, params: Dict[str, Any]) -> str:
    parts = list(urlparse(base_url))
    existing = dict(parse_qsl(parts[4], keep_blank_values=True))
    for k, v in params.items():
        if v is None:
            continue
        existing[k] = str(v)
    parts[4] = urlencode(existing, doseq=True)
    return urlunparse(parts)


def canonical_url(url: str) -> str:
    """
    Normalize query ordering to improve dedupe.
    """
    parts = urlparse(url)
    q = parse_qsl(parts.query, keep_blank_values=True)
    q_sorted = sorted(q, key=lambda kv: (kv[0], kv[1]))
    return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, urlencode(q_sorted), parts.fragment))


@dataclass
class ControlOption:
    value: str
    label: str = ""
    disabled: bool = False
    selected: bool = False


@dataclass
class ControlDescriptor:
    control_id: str
    selector: str
    tag: str
    type: str
    name: str
    label: str = ""
    options: Optional[List[ControlOption]] = None


@dataclass
class StateRecord:
    state_id: str
    url: str
    canonical_url: str
    control_fingerprint: str
    footnote_hash: str
    footnote_text: str
    footnote_text_normalized: str
    footnote_html: str
    title: str
    depth: int
    source_control: str = ""
    source_value: str = ""
    source_label: str = ""
    found: bool = False
    error: str = ""


def get_page_title(page) -> str:
    try:
        return page.title()
    except Exception:
        return ""


def extract_footnote_frame(page) -> Dict[str, Any]:
    """
    Extract the turbo-frame content and compute a content hash.
    """
    frame = page.locator(FOOTNOTE_FRAME_SELECTOR)
    if frame.count() == 0:
        return {
            "found": False,
            "html": "",
            "text": "",
            "text_normalized": "",
            "hash": "",
        }

    try:
        html = frame.inner_html(timeout=5000)
    except Exception:
        html = ""

    try:
        text = frame.inner_text(timeout=5000)
    except Exception:
        text = ""

    text_norm = normalize_whitespace(text)
    h = sha256_text(html if html else text_norm)

    return {
        "found": bool(html or text_norm),
        "html": html,
        "text": text,
        "text_normalized": text_norm,
        "hash": h,
    }


def get_control_descriptors(page) -> List"""
    Discover interactive controls on the page.
    This is generic and works without hard-coding the filter structure.
    """
    controls_js = """
    () => {
      const controls = [];
      const seen = new Set();

      const labelFor = (el) => {
        if (!el) return "";
        const id = el.id;
        if (id) {
          const lbl = document.querySelector(`label[for="${CSS.escape(id)}"]`);
          if (lbl) return lbl.innerText.trim();
        }
        const parentLabel = el.closest("label");
        if (parentLabel) return parentLabel.innerText.trim();
        const aria = el.getAttribute("aria-label");
        if (aria) return aria.trim();
        return "";
      };

      const addControl = (el, extra = {}) => {
        const tag = el.tagName.toLowerCase();
        const type = (el.getAttribute("type") || "").toLowerCase();
        const name = el.getAttribute("name") || "";
        const id = el.id || `${tag}_${name}_${Math.random().toString(36).slice(2,8)}`;
        if (seen.has(id)) return;
        seen.add(id);

        controls.push({
          control_id: id,
          selector: extra.selector || (el.id ? `#${CSS.escape(el.id)}` : `${tag}[name="${CSS.escape(name)}"]`),
          tag,
          type,
          name,
          label: labelFor(el),
          options: extra.options || null
        });
      };

      const formControls = Array.from(document.querySelectorAll('form select, form input, form textarea, select, input, textarea'))
        .filter(el => {
          const tag = el.tagName.toLowerCase();
          const type = (el.getAttribute("type") || "").toLowerCase();
          if (el.disabled) return false;
          if (tag === "input" && ["hidden", "submit", "button", "image", "reset", "file"].includes(type)) return false;
          return true;
        });

      for (const el of formControls) {
        const tag = el.tagName.toLowerCase();
        const type = (el.getAttribute("type") || "").toLowerCase();

        if (tag === "select") {
          const options = Array.from(el.options).map(opt => ({
            value: opt.value,
            label: opt.textContent.trim(),
            disabled: opt.disabled,
            selected: opt.selected
          }));
          addControl(el, { options });
        } else if (tag === "input" && (type === "checkbox" || type === "radio")) {
          addControl(el);
        } else if (tag === "input" || tag === "textarea") {
          addControl(el);
        }
      }

      return controls;
    }
    """
    return page.evaluate(controls_js)


def get_control_state(page) -> Dict[str, Any]:
    js = """
    () => {
      const vals = [];
      const els = Array.from(document.querySelectorAll('form select, form input, form textarea, select, input, textarea'))
        .filter(el => {
          const tag = el.tagName.toLowerCase();
          const type = (el.getAttribute("type") || "").toLowerCase();
          if (el.disabled) return false;
          if (tag === "input" && ["hidden", "submit", "button", "image", "reset", "file"].includes(type)) return false;
          return true;
        });

      for (const el of els) {
        const tag = el.tagName.toLowerCase();
        const type = (el.getAttribute("type") || "").toLowerCase();
        const id = el.id || "";
        const name = el.getAttribute("name") || "";
        let value = "";

        if (tag === "select") {
          value = el.value;
        } else if (tag === "input" && (type === "checkbox" || type === "radio")) {
          value = el.checked ? "checked" : "unchecked";
        } else {
          value = el.value || "";
        }

        vals.push({ id, name, tag, type, value });
      }

      return vals;
    }
    """
    state = page.evaluate(js)
    stable = json.dumps(sorted(state, key=lambda x: (x.get("id",""), x.get("name",""), x.get("tag",""), x.get("type",""))), ensure_ascii=False)
    return {
        "raw": state,
        "fingerprint": sha256_text(stable),
    }


def set_control_value(page, control: ControlDescriptor, option_value: str) -> None:
    selector = control.selector
    tag = control.tag
    type_ = control.type

    if tag == "select":
        page.locator(selector).select_option(option_value)
        return

    if tag == "input" and type_ in ("checkbox", "radio"):
        loc = page.locator(selector)
        if not loc.is_checked():
            loc.check()
        return

    if tag in ("input", "textarea"):
        loc = page.locator(selector)
        loc.fill(option_value)
        return

    raise RuntimeError(f"Unsupported control type: {tag}/{type_}")


def clear_control(page, control: ControlDescriptor) -> None:
    selector = control.selector
    tag = control.tag
    type_ = control.type

    if tag == "select":
        select = page.locator(selector)
        try:
            select.select_option("")
        except Exception:
            # fallback to first empty option if present
            pass
        return

    if tag == "input" and type_ in ("checkbox", "radio"):
        loc = page.locator(selector)
        if loc.is_checked():
            loc.uncheck()
        return

    if tag in ("input", "textarea"):
        loc = page.locator(selector)
        loc.fill("")
        return


def wait_for_footnote_change(page, prev_hash: str, timeout_ms: int = 15000) -> Dict[str, Any]:
    """
    Wait until footnote frame content changes or timeout.
    """
    start = time.time()
    last = None
    while (time.time() - start) * 1000 < timeout_ms:
        cur = extract_footnote_frame(page)
        last = cur
        if cur["hash"] and cur["hash"] != prev_hash:
            return cur
        time.sleep(0.5)
    return last or extract_footnote_frame(page)


def click_apply_if_present(page) -> bool:
    """
    Some filter UIs require an explicit Apply/Update button.
    """
    buttons = [
        "button:has-text('Apply')",
        "button:has-text('Update')",
        "button:has-text('Search')",
        "input[type='submit']",
        "button[type='submit']",
    ]
    for sel in buttons:
        loc = page.locator(sel)
        if loc.count() > 0:
            try:
                loc.first.click(timeout=3000)
                return True
            except Exception:
                continue
    return False


def safe_navigate(page, url: str, timeout_ms: int = 45000) -> None:
    page.goto(url, wait_until="networkidle", timeout=timeout_ms)


def state_key(url: str, control_fp: str) -> str:
    return sha256_text(f"{canonical_url(url)}||{control_fp}")


def unique_label(control: ControlDescriptor, option_value: str) -> str:
    return f"{control.name or control.control_id}:{option_value}"


def crawl(
    base_url: str,
    max_states: int = 500,
    max_depth: int = 3,
    max_options_per_control: int = 30,
    page_timeout_ms: int = 45000,
    footnote_timeout_ms: int = 15000,
) -> Dict[str, Any]:
    """
    BFS crawler over page states.
    """
    seen_states = {}
    unique_footnotes = {}
    records: List[StateRecord] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})

        q = deque()
        q.append({
            "url": base_url,
            "depth": 0,
            "source_control": "",
            "source_value": "",
            "source_label": "",
        })

        while q and len(records) < max_states:
            item = q.popleft()
            url = canonical_url(item["url"])
            depth = item["depth"]

            try:
                safe_navigate(page, url, timeout_ms=page_timeout_ms)
                controls = get_control_descriptors(page)
                ctrl_state = get_control_state(page)
                ctrl_fp = ctrl_state["fingerprint"]
                s_key = state_key(url, ctrl_fp)

                if s_key in seen_states:
                    continue

                prev_foot = extract_footnote_frame(page)
                if not prev_foot["found"]:
                    # give the page a moment in case the turbo frame is late
                    time.sleep(1.5)
                    prev_foot = extract_footnote_frame(page)

                rec = StateRecord(
                    state_id=s_key,
                    url=page.url,
                    canonical_url=canonical_url(page.url),
                    control_fingerprint=ctrl_fp,
                    footnote_hash=prev_foot["hash"],
                    footnote_text=prev_foot["text"],
                    footnote_text_normalized=prev_foot["text_normalized"],
                    footnote_html=prev_foot["html"],
                    title=get_page_title(page),
                    depth=depth,
                    source_control=item["source_control"],
                    source_value=item["source_value"],
                    source_label=item["source_label"],
                    found=prev_foot["found"],
                    error="",
                )

                seen_states[s_key] = True
                records.append(rec)

                if prev_foot["hash"]:
                    if prev_foot["hash"] not in unique_footnotes:
                        unique_footnotes[prev_foot["hash"]] = {
                            "footnote_hash": prev_foot["hash"],
                            "footnote_html": prev_foot["html"],
                            "footnote_text": prev_foot["text"],
                            "footnote_text_normalized": prev_foot["text_normalized"],
                            "occurrences": [],
                        }
                    unique_footnotes[prev_foot["hash"]]["occurrences"].append({
                        "state_id": s_key,
                        "url": page.url,
                        "canonical_url": canonical_url(page.url),
                        "depth": depth,
                        "source_control": item["source_control"],
                        "source_value": item["source_value"],
                        "source_label": item["source_label"],
                    })

                if depth >= max_depth:
                    continue

                # For each control, try a limited set of options.
                for control in controls:
                    tag = control["tag"]
                    ctype = control["type"]
                    name = control["name"]
                    selector = control["selector"]
                    label = control.get("label", "")

                    # Build options list
                    options_to_try: List[Tuple[str, str]] = []

                    if tag == "select" and control.get("options"):
                        seen_values = set()
                        for opt in control["options"]:
                            value = opt["value"]
                            if not value:
                                continue
                            if opt["disabled"]:
                                continue
                            if value in seen_values:
                                continue
                            seen_values.add(value)
                            options_to_try.append((value, opt.get("label", "")))
                        options_to_try = options_to_try[:max_options_per_control]

                    elif tag == "input" and ctype in ("checkbox", "radio"):
                        # For radios/checkboxes, two actions: set/check or uncheck
                        if ctype == "radio":
                            options_to_try = [("checked", "checked")]
                        else:
                            options_to_try = [("checked", "checked"), ("unchecked", "unchecked")]

                    elif tag in ("input", "textarea"):
                        # Skip free-text controls by default; too explosive to brute-force.
                        continue

                    if not options_to_try:
                        continue

                    # Explore each option by reopening the current URL fresh.
                    for option_value, option_label in options_to_try:
                        try:
                            safe_navigate(page, url, timeout_ms=page_timeout_ms)
                            # Re-extract baseline hash for comparing after change
                            baseline = extract_footnote_frame(page)
                            baseline_hash = baseline["hash"]

                            # Re-discover controls after reload because DOM may change
                            current_controls = get_control_descriptors(page)
                            current_control = None
                            for c in current_controls:
                                if c["selector"] == selector or (c["name"] == name and c["tag"] == tag and c["type"] == ctype):
                                    current_control = c
                                    break
                            if current_control is None:
                                continue

                            current_desc = ControlDescriptor(
                                control_id=current_control["control_id"],
                                selector=current_control["selector"],
                                tag=current_control["tag"],
                                type=current_control["type"],
                                name=current_control["name"],
                                label=current_control.get("label", ""),
                                options=None,
                            )

                            if tag == "select":
                                set_control_value(page, current_desc, option_value)
                            elif tag == "input" and ctype == "radio":
                                set_control_value(page, current_desc, option_value)
                            elif tag == "input" and ctype == "checkbox":
                                if option_value == "checked":
                                    set_control_value(page, current_desc, "checked")
                                else:
                                    clear_control(page, current_desc)
                            else:
                                continue

                            # If there is an apply/update button, click it.
                            click_apply_if_present(page)

                            # Wait for URL or footnote update
                            try:
                                page.wait_for_load_state("networkidle", timeout=page_timeout_ms)
                            except PlaywrightTimeoutError:
                                pass

                            updated = wait_for_footnote_change(
                                page,
                                prev_hash=baseline_hash,
                                timeout_ms=footnote_timeout_ms,
                            )

                            new_url = canonical_url(page.url)
                            new_ctrl = get_control_state(page)
                            new_key = state_key(new_url, new_ctrl["fingerprint"])

                            if new_key not in seen_states:
                                q.append({
                                    "url": new_url,
                                    "depth": depth + 1,
                                    "source_control": unique_label(current_desc, option_value),
                                    "source_value": option_value,
                                    "source_label": f"{current_desc.label} :: {option_label}".strip(" ::"),
                                })

                        except Exception as e:
                            # Keep crawling; record errors only if desired
                            sys.stderr.write(f"Warning: control crawl failed for {selector}={option_value}: {e}\n")
                            continue

            except Exception as e:
                sys.stderr.write(f"Warning: failed to process {url}: {e}\n")
                continue

        browser.close()

    return {
        "meta": {
            "base_url": base_url,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "max_states": max_states,
            "max_depth": max_depth,
            "max_options_per_control": max_options_per_control,
            "total_states": len(records),
            "unique_footnotes": len(unique_footnotes),
        },
        "states": [asdict(r) for r in records],
        "unique_footnotes": list(unique_footnotes.values()),
    }


def main():
    parser = argparse.ArgumentParser(description="Fully automatic Playwright crawler for UNHCR turbo-frame footnotes.")
    parser.add_argument("--url", default=BASE_URL, help="Base URL to crawl.")
    parser.add_argument("--output", default="unhcr_footnotes_full.json", help="Output JSON file.")
    parser.add_argument("--max-states", type=int, default=500, help="Maximum number of states to capture.")
    parser.add_argument("--max-depth", type=int, default=3, help="Maximum crawl depth.")
    parser.add_argument("--max-options-per-control", type=int, default=30, help="Max options per select control.")
    parser.add_argument("--page-timeout-ms", type=int, default=45000, help="Page navigation timeout.")
    parser.add_argument("--footnote-timeout-ms", type=int, default=15000, help="Wait timeout for footnote updates.")
    args = parser.parse_args()

    result = crawl(
        base_url=args.url,
        max_states=args.max_states,
        max_depth=args.max_depth,
        max_options_per_control=args.max_options_per_control,
        page_timeout_ms=args.page_timeout_ms,
        footnote_timeout_ms=args.footnote_timeout_ms,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Saved {args.output}")
    print(f"States captured: {result['meta']['total_states']}")
    print(f"Unique footnote variants: {result['meta']['unique_footnotes']}")


if __name__ == "__main__":
    main()