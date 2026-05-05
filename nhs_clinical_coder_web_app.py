import csv
import html
import json
import mimetypes
import re
import secrets
import shutil
import time
import urllib.request
import urllib.parse
from cgi import FieldStorage
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from nhs_clinical_coder_agent_sim import (
    FIELDNAMES,
    ICD10_REFERENCE,
    OPCS4_REFERENCE,
    WORKBOOK_FILE,
    WORKSHEET_NAME,
    code_record,
    parse_xlsm_records,
    run_coding_process,
)


APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = APP_DIR / "web_outputs"
UPLOAD_DIR = APP_DIR / "web_uploads"
STATIC_DIR = APP_DIR / "static"
DEFAULT_OUTPUT = OUTPUT_DIR / "latest_agent_output.csv"
DEFAULT_DETAIL_OUTPUT = OUTPUT_DIR / "latest_agent_output.json"
FEEDBACK_OUTPUT = OUTPUT_DIR / "coder_feedback.csv"
CLASSIFICATION_BROWSER_URL = "https://classbrowser.nhs.uk/"
HOST = "127.0.0.1"
PORT = 8080
CODE_CHECK_CACHE = {}
SESSION_COOKIE = "nhs_coder_session"
SESSIONS = {}

USERS = {
    "coder1": {"password": "coding1", "role": "Clinical Coder", "name": "Alex Coder"},
    "coder2": {"password": "coding2", "role": "Clinical Coder", "name": "Sam Coder"},
    "manager": {"password": "manage1", "role": "Coding Manager", "name": "J. Manager"},
}

FEEDBACK_FIELDNAMES = [
    "Timestamp",
    "Sample Number",
    "Decision",
    "Agent ICD-10 Code",
    "Corrected ICD-10 Code",
    "Agent OPCS-4 Code",
    "Corrected OPCS-4 Code",
    "Coder ID",
    "Comments",
]


def ensure_dirs():
    OUTPUT_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    STATIC_DIR.mkdir(exist_ok=True)


NHS_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 16" height="40" focusable="false" aria-hidden="true">
  <path fill="#fff" d="M0 0h40v16H0z"/>
  <path fill="#005eb8" d="M3.9 1.5h4.4l2.6 9h.1l1.8-9h3.3l-2.8 13H9l-2.7-9h-.1l-1.8 9H1.1M17.3 1.5h3.6l-1 4.9h4L25 1.5h3.5l-2.7 13h-3.5l1.1-5.6h-4.1l-1.2 5.6h-3.4M37.7 4.4c-.7-.3-1.6-.6-2.9-.6-1.4 0-2.5.2-2.5 1.3 0 1.8 5.1 1.2 5.1 5.1 0 3.6-3.3 4.5-6.4 4.5-1.3 0-2.9-.3-4-.7l.8-2.7c.7.4 2.1.7 3.2.7s2.8-.2 2.8-1.5c0-2.1-5.1-1.3-5.1-5 0-3.4 2.9-4.4 5.8-4.4 1.6 0 3.1.2 4 .6"/>
</svg>"""


def page_template(title, body, username=None, user_role=None):
    user_nav = ""
    if username:
        user_nav = f"""
          <nav class="nhsuk-header__navigation" aria-label="Primary navigation">
            <div class="nhsuk-header__navigation-container">
              <span class="nhsuk-header__user-info">{html.escape(username)}&ensp;&mdash;&ensp;{html.escape(user_role or "")}</span>
              <a class="nhsuk-header__nav-link" href="/logout">Sign out</a>
            </div>
          </nav>"""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} - NHS Clinical Coder</title>
  <style>
    /* NHS Design System — embedded */
    *, *::before, *::after {{ box-sizing: border-box; }}

    :root {{
      --nhsuk-blue: #005eb8;
      --nhsuk-dark-blue: #003087;
      --nhsuk-bright-blue: #0072ce;
      --nhsuk-green: #007f3b;
      --nhsuk-dark-green: #004f27;
      --nhsuk-red: #d5281b;
      --nhsuk-yellow: #ffeb3b;
      --nhsuk-warm-yellow: #ffb81c;
      --nhsuk-orange: #fa8c1d;
      --nhsuk-purple: #330072;
      --nhsuk-pale-yellow: #fff9c4;
      --nhsuk-black: #212b32;
      --nhsuk-dark-grey: #425563;
      --nhsuk-mid-grey: #768692;
      --nhsuk-pale-grey: #e8edee;
      --nhsuk-grey-5: #f0f4f5;
      --nhsuk-white: #ffffff;
      --nhsuk-border: #d8dde0;
      --nhsuk-input-border: #4c6272;
      --nhsuk-focus-color: #ffeb3b;
      --nhsuk-focus-text-color: #212b32;
      --nhsuk-link-color: #005eb8;
      --nhsuk-link-hover-color: #7b0d0d;
      --nhsuk-link-visited-color: #330072;
      --nhsuk-secondary-text-color: #425563;
    }}

    html {{ scroll-behavior: smooth; }}

    body {{
      font-family: "Frutiger W01", Arial, sans-serif;
      font-size: 16px;
      line-height: 1.5;
      color: var(--nhsuk-black);
      background: var(--nhsuk-grey-5);
      margin: 0;
      padding: 0;
      -webkit-font-smoothing: antialiased;
    }}

    /* ── Typography ── */
    h1 {{
      font-size: 2.25rem;
      font-weight: 700;
      line-height: 1.1111;
      margin-top: 0;
      margin-bottom: 24px;
      color: var(--nhsuk-black);
    }}
    h2 {{
      font-size: 1.5rem;
      font-weight: 700;
      line-height: 1.25;
      margin-top: 0;
      margin-bottom: 16px;
      color: var(--nhsuk-black);
    }}
    h3 {{
      font-size: 1.25rem;
      font-weight: 700;
      line-height: 1.4;
      margin-top: 0;
      margin-bottom: 12px;
      color: var(--nhsuk-black);
    }}
    p {{
      font-size: 1rem;
      line-height: 1.5;
      margin-top: 0;
      margin-bottom: 16px;
      color: var(--nhsuk-black);
    }}
    .nhsuk-lede-text {{
      font-size: 1.25rem;
      line-height: 1.6;
      margin-bottom: 24px;
      color: var(--nhsuk-black);
    }}
    a {{
      color: var(--nhsuk-link-color);
      text-decoration: underline;
    }}
    a:visited {{ color: var(--nhsuk-link-visited-color); }}
    a:hover {{ color: var(--nhsuk-link-hover-color); text-decoration: none; }}
    a:focus {{
      background-color: var(--nhsuk-focus-color);
      box-shadow: 0 -2px var(--nhsuk-focus-color), 0 4px var(--nhsuk-focus-text-color);
      color: var(--nhsuk-focus-text-color);
      outline: 4px solid transparent;
      text-decoration: none;
    }}

    /* ── Layout ── */
    .nhsuk-width-container {{
      max-width: 960px;
      margin: 0 auto;
      padding: 0 16px;
    }}
    @media (min-width: 641px) {{
      .nhsuk-width-container {{ padding: 0 24px; }}
    }}
    .nhsuk-main-wrapper {{
      padding: 24px 0 40px;
    }}
    @media (min-width: 641px) {{
      .nhsuk-main-wrapper {{ padding: 40px 0 56px; }}
    }}

    /* ── Header ── */
    .nhsuk-header {{
      background-color: var(--nhsuk-blue);
    }}
    .nhsuk-header__container {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      padding: 12px 0;
      gap: 8px;
    }}
    .nhsuk-header__logo {{
      display: flex;
      align-items: center;
      gap: 16px;
      text-decoration: none;
    }}
    .nhsuk-header__logo:focus {{
      background-color: transparent;
      box-shadow: none;
      outline: 4px solid var(--nhsuk-focus-color);
      outline-offset: 2px;
    }}
    .nhsuk-logo {{
      display: block;
      height: 40px;
      width: 100px;
      flex-shrink: 0;
    }}
    .nhsuk-header__service-name {{
      font-size: 1.125rem;
      font-weight: 700;
      color: #ffffff;
      text-decoration: none;
      border-left: 1px solid rgba(255,255,255,0.4);
      padding-left: 16px;
      margin-left: 4px;
    }}
    .nhsuk-header__navigation-container {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}
    .nhsuk-header__user-info {{
      font-size: 0.875rem;
      color: rgba(255,255,255,0.85);
    }}
    .nhsuk-header__nav-link {{
      font-size: 0.875rem;
      color: #ffffff;
      text-decoration: underline;
    }}
    .nhsuk-header__nav-link:visited {{ color: #ffffff; }}
    .nhsuk-header__nav-link:hover {{ color: rgba(255,255,255,0.8); }}
    .nhsuk-header__nav-link:focus {{
      background-color: var(--nhsuk-focus-color);
      color: var(--nhsuk-focus-text-color);
    }}

    /* ── Footer ── */
    .nhsuk-footer {{
      background: var(--nhsuk-white);
      border-top: 4px solid var(--nhsuk-blue);
      padding: 24px 0;
      margin-top: 40px;
    }}
    .nhsuk-footer__list {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 24px;
      list-style: none;
      margin: 0 0 16px;
      padding: 0;
    }}
    .nhsuk-footer__list-item-link {{
      font-size: 0.875rem;
      color: var(--nhsuk-black);
    }}
    .nhsuk-footer__copyright {{
      font-size: 0.875rem;
      color: var(--nhsuk-dark-grey);
      margin: 0;
    }}

    /* ── Buttons ── */
    .nhsuk-button {{
      background-color: var(--nhsuk-green);
      border: 2px solid transparent;
      border-radius: 4px;
      box-shadow: 0 4px 0 var(--nhsuk-dark-green);
      color: #ffffff;
      cursor: pointer;
      display: inline-block;
      font-family: inherit;
      font-size: 1rem;
      font-weight: 700;
      line-height: 1.5;
      margin-bottom: 8px;
      padding: 12px 20px;
      position: relative;
      text-align: center;
      text-decoration: none;
      vertical-align: top;
      width: auto;
    }}
    .nhsuk-button:link, .nhsuk-button:visited {{ color: #ffffff; }}
    .nhsuk-button:hover {{ background-color: #006229; text-decoration: none; }}
    .nhsuk-button:focus {{
      background-color: var(--nhsuk-focus-color);
      box-shadow: 0 4px 0 var(--nhsuk-focus-text-color);
      color: var(--nhsuk-focus-text-color);
      outline: 4px solid transparent;
    }}
    .nhsuk-button:active {{
      background-color: #006229;
      box-shadow: none;
      top: 4px;
    }}
    .nhsuk-button--secondary {{
      background-color: #f0f4f5;
      box-shadow: 0 4px 0 #aeb7bd;
      color: var(--nhsuk-black);
    }}
    .nhsuk-button--secondary:link, .nhsuk-button--secondary:visited {{ color: var(--nhsuk-black); }}
    .nhsuk-button--secondary:hover {{ background-color: #d5dade; }}
    .nhsuk-button--secondary:focus {{
      background-color: var(--nhsuk-focus-color);
      box-shadow: 0 4px 0 var(--nhsuk-focus-text-color);
      color: var(--nhsuk-focus-text-color);
    }}
    .nhsuk-button--reverse {{
      background-color: #ffffff;
      box-shadow: 0 4px 0 #003087;
      color: var(--nhsuk-blue);
    }}
    .nhsuk-button--reverse:link, .nhsuk-button--reverse:visited {{ color: var(--nhsuk-blue); }}
    .nhsuk-button--reverse:hover {{ background-color: #e5f0f8; }}
    .nhsuk-button--sm {{
      font-size: 0.875rem;
      padding: 8px 16px;
    }}

    /* ── Form components ── */
    .nhsuk-form-group {{
      margin-bottom: 24px;
    }}
    .nhsuk-form-group--error {{
      border-left: 4px solid var(--nhsuk-red);
      padding-left: 16px;
      margin-bottom: 24px;
    }}
    .nhsuk-label {{
      display: block;
      font-size: 1rem;
      font-weight: 700;
      line-height: 1.5;
      margin-bottom: 4px;
      color: var(--nhsuk-black);
    }}
    .nhsuk-label--l {{
      font-size: 1.25rem;
    }}
    .nhsuk-hint {{
      font-size: 0.9375rem;
      color: var(--nhsuk-dark-grey);
      margin-bottom: 4px;
    }}
    .nhsuk-error-message {{
      display: block;
      font-size: 1rem;
      font-weight: 700;
      color: var(--nhsuk-red);
      margin-bottom: 4px;
    }}
    .nhsuk-input {{
      appearance: none;
      background-color: var(--nhsuk-white);
      border: 2px solid var(--nhsuk-input-border);
      border-radius: 0;
      color: var(--nhsuk-black);
      font-family: inherit;
      font-size: 1rem;
      height: 40px;
      line-height: 1.47059;
      padding: 4px 8px;
      width: 100%;
    }}
    .nhsuk-input:focus {{
      border-color: var(--nhsuk-focus-text-color);
      box-shadow: inset 0 0 0 2px;
      outline: 4px solid var(--nhsuk-focus-color);
      outline-offset: 0;
    }}
    .nhsuk-input--error {{
      border-color: var(--nhsuk-red);
    }}
    .nhsuk-select {{
      appearance: none;
      background-color: var(--nhsuk-white);
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='13' height='17' viewBox='0 0 13 17'%3E%3Cpath fill='%23231f20' d='M6.5 0L0 6h13zM6.5 17L0 11h13z'/%3E%3C/svg%3E");
      background-position: right 8px center;
      background-repeat: no-repeat;
      border: 2px solid var(--nhsuk-input-border);
      border-radius: 0;
      color: var(--nhsuk-black);
      font-family: inherit;
      font-size: 1rem;
      height: 40px;
      padding: 4px 32px 4px 8px;
      width: 100%;
    }}
    .nhsuk-select:focus {{
      border-color: var(--nhsuk-focus-text-color);
      outline: 4px solid var(--nhsuk-focus-color);
      outline-offset: 0;
    }}
    .nhsuk-textarea {{
      appearance: none;
      background-color: var(--nhsuk-white);
      border: 2px solid var(--nhsuk-input-border);
      border-radius: 0;
      color: var(--nhsuk-black);
      font-family: inherit;
      font-size: 1rem;
      line-height: 1.5;
      padding: 8px;
      resize: vertical;
      width: 100%;
    }}
    .nhsuk-textarea:focus {{
      border-color: var(--nhsuk-focus-text-color);
      outline: 4px solid var(--nhsuk-focus-color);
      outline-offset: 0;
    }}

    /* ── Radios ── */
    .nhsuk-radios__item {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
    }}
    .nhsuk-radios__input {{
      width: 40px;
      height: 40px;
      flex-shrink: 0;
      cursor: pointer;
      margin: 0;
    }}
    .nhsuk-radios__label {{
      font-size: 1rem;
      font-weight: 400;
      cursor: pointer;
      margin: 0;
    }}
    .nhsuk-radios__conditional {{
      border-left: 4px solid var(--nhsuk-border);
      padding-left: 20px;
      margin-left: 20px;
      margin-bottom: 8px;
    }}

    /* ── Tags ── */
    .nhsuk-tag {{
      display: inline-block;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 1px;
      padding: 4px 8px;
      text-transform: uppercase;
      text-decoration: none;
    }}
    .nhsuk-tag--green  {{ background-color: #007f3b; color: #ffffff; }}
    .nhsuk-tag--yellow {{ background-color: #ffb81c; color: #212b32; }}
    .nhsuk-tag--red    {{ background-color: #d5281b; color: #ffffff; }}
    .nhsuk-tag--blue   {{ background-color: #005eb8; color: #ffffff; }}
    .nhsuk-tag--grey   {{ background-color: #425563; color: #ffffff; }}
    .nhsuk-tag--white  {{ background-color: #ffffff; color: #212b32; border: 1px solid #aeb7bd; }}

    /* ── Summary list ── */
    .nhsuk-summary-list {{
      border-top: 1px solid var(--nhsuk-border);
      margin: 0 0 24px;
      padding: 0;
      width: 100%;
    }}
    .nhsuk-summary-list__row {{
      display: flex;
      border-bottom: 1px solid var(--nhsuk-border);
      padding: 12px 0;
      gap: 16px;
    }}
    .nhsuk-summary-list__key {{
      flex: 0 0 40%;
      font-size: 0.9375rem;
      font-weight: 700;
      color: var(--nhsuk-black);
      word-break: break-word;
    }}
    .nhsuk-summary-list__value {{
      flex: 1;
      font-size: 0.9375rem;
      color: var(--nhsuk-black);
      word-break: break-word;
    }}

    /* ── Cards ── */
    .nhsuk-card {{
      background: var(--nhsuk-white);
      border: 1px solid var(--nhsuk-border);
      margin-bottom: 24px;
    }}
    .nhsuk-card__content {{
      padding: 24px;
    }}
    .nhsuk-card__heading {{
      font-size: 1.25rem;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .nhsuk-card__description {{
      font-size: 0.9375rem;
      color: var(--nhsuk-dark-grey);
      margin-bottom: 0;
    }}
    .nhsuk-card--feature {{
      border-top: 4px solid var(--nhsuk-blue);
    }}

    /* ── Table ── */
    .nhsuk-table-responsive {{
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }}
    .nhsuk-table {{
      border-collapse: collapse;
      width: 100%;
      font-size: 0.9375rem;
    }}
    .nhsuk-table__head {{
      background-color: var(--nhsuk-blue);
    }}
    .nhsuk-table__header {{
      color: #ffffff;
      font-weight: 700;
      padding: 12px 16px;
      text-align: left;
      border-right: 1px solid rgba(255,255,255,0.2);
      white-space: nowrap;
    }}
    .nhsuk-table__body .nhsuk-table__row:nth-child(even) {{
      background-color: var(--nhsuk-grey-5);
    }}
    .nhsuk-table__cell {{
      padding: 10px 16px;
      border-bottom: 1px solid var(--nhsuk-border);
      vertical-align: top;
      font-size: 0.875rem;
    }}
    .nhsuk-table__cell--truncate {{
      max-width: 220px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    /* ── Notification banner ── */
    .nhsuk-notification-banner {{
      border: 5px solid var(--nhsuk-blue);
      margin-bottom: 32px;
      padding: 16px 24px;
      background: var(--nhsuk-white);
    }}
    .nhsuk-notification-banner--success {{
      border-color: var(--nhsuk-green);
    }}
    .nhsuk-notification-banner--error {{
      border-color: var(--nhsuk-red);
    }}
    .nhsuk-notification-banner__header {{
      border-bottom: 1px solid rgba(0,0,0,0.1);
      margin-bottom: 12px;
      padding-bottom: 8px;
    }}
    .nhsuk-notification-banner__title {{
      font-size: 1rem;
      font-weight: 700;
      margin: 0;
      color: var(--nhsuk-blue);
    }}
    .nhsuk-notification-banner--success .nhsuk-notification-banner__title {{
      color: var(--nhsuk-green);
    }}
    .nhsuk-notification-banner--error .nhsuk-notification-banner__title {{
      color: var(--nhsuk-red);
    }}
    .nhsuk-notification-banner__content p {{ margin: 0; font-size: 0.9375rem; }}

    /* ── Error summary ── */
    .nhsuk-error-summary {{
      border: 4px solid var(--nhsuk-red);
      padding: 24px;
      margin-bottom: 32px;
      background: var(--nhsuk-white);
    }}
    .nhsuk-error-summary__title {{
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--nhsuk-red);
      margin: 0 0 8px;
    }}
    .nhsuk-error-summary__body {{
      font-size: 0.9375rem;
      margin: 0;
    }}

    /* ── Warning callout ── */
    .nhsuk-warning-callout {{
      background: var(--nhsuk-pale-yellow);
      border-left: 8px solid var(--nhsuk-warm-yellow);
      padding: 24px;
      margin-bottom: 24px;
    }}
    .nhsuk-warning-callout__label {{
      font-size: 1.125rem;
      font-weight: 700;
      margin: 0 0 8px;
    }}
    .nhsuk-warning-callout p {{ margin: 0; font-size: 0.9375rem; }}

    /* ── Back link ── */
    .nhsuk-back-link {{
      display: inline-block;
      font-size: 0.875rem;
      padding: 8px 0 8px 20px;
      position: relative;
      text-decoration: none;
      color: var(--nhsuk-link-color);
      margin-bottom: 24px;
    }}
    .nhsuk-back-link::before {{
      content: "";
      display: block;
      width: 8px;
      height: 8px;
      border-bottom: 2px solid currentColor;
      border-left: 2px solid currentColor;
      position: absolute;
      top: 50%;
      left: 4px;
      transform: translateY(-60%) rotate(45deg);
    }}
    .nhsuk-back-link:hover {{ text-decoration: underline; }}

    /* ── Hero ── */
    .nhsuk-hero {{
      background-color: var(--nhsuk-blue);
      padding: 40px 0;
      margin-bottom: 0;
    }}
    .nhsuk-hero__wrapper h1 {{
      color: #ffffff;
      font-size: 2.5rem;
      margin-bottom: 16px;
    }}
    .nhsuk-hero__desc {{
      color: rgba(255,255,255,0.9);
      font-size: 1.125rem;
      line-height: 1.6;
      margin-bottom: 28px;
      max-width: 560px;
    }}

    /* ── Code tags ── */
    .nhsuk-code-tag {{
      display: inline-block;
      background: var(--nhsuk-grey-5);
      border: 1px solid var(--nhsuk-border);
      border-radius: 2px;
      color: var(--nhsuk-dark-blue);
      font-family: "Courier New", Courier, monospace;
      font-size: 0.8125rem;
      font-weight: 700;
      margin: 1px 2px;
      padding: 2px 6px;
    }}

    /* ── Progress bar ── */
    .nhsuk-progress-bar {{
      background: var(--nhsuk-pale-grey);
      border: 1px solid var(--nhsuk-border);
      height: 12px;
      margin-bottom: 16px;
      overflow: hidden;
    }}
    .nhsuk-progress-bar__fill {{
      background: var(--nhsuk-blue);
      height: 100%;
      transition: width 0.3s ease;
      width: 0%;
    }}

    /* ── Stream list ── */
    .nhsuk-stream-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      max-height: 280px;
      overflow-y: auto;
    }}
    .nhsuk-stream-list__item {{
      border-bottom: 1px solid var(--nhsuk-border);
      font-size: 0.875rem;
      padding: 8px 0;
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 8px;
      align-items: start;
    }}
    .nhsuk-stream-list__item:last-child {{ border-bottom: none; }}

    /* ── Evidence box ── */
    .nhsuk-evidence-box {{
      background: var(--nhsuk-grey-5);
      border: 1px solid var(--nhsuk-border);
      border-left: 4px solid var(--nhsuk-blue);
      font-size: 0.9375rem;
      line-height: 1.7;
      padding: 16px;
      white-space: pre-wrap;
      word-break: break-word;
    }}

    /* ── Feedback items ── */
    .nhsuk-feedback-item {{
      border-bottom: 1px solid var(--nhsuk-border);
      padding: 12px 0;
      font-size: 0.875rem;
    }}
    .nhsuk-feedback-item:last-child {{ border-bottom: none; }}
    .nhsuk-feedback-item__meta {{
      color: var(--nhsuk-dark-grey);
      font-size: 0.8125rem;
      margin-top: 4px;
    }}
    .nhsuk-feedback-item__codes {{
      font-family: "Courier New", Courier, monospace;
      font-size: 0.8125rem;
      color: var(--nhsuk-dark-blue);
      margin: 4px 0;
    }}

    /* ── Two-column grid ── */
    .nhsuk-grid-row {{
      display: grid;
      gap: 24px;
    }}
    @media (min-width: 769px) {{
      .nhsuk-grid-row--two-thirds-one-third {{
        grid-template-columns: 2fr 1fr;
      }}
      .nhsuk-grid-row--halves {{
        grid-template-columns: 1fr 1fr;
      }}
      .nhsuk-grid-row--thirds {{
        grid-template-columns: 1fr 1fr 1fr;
      }}
    }}

    /* ── Login page ── */
    .nhsuk-login-wrapper {{
      max-width: 400px;
      margin: 0 auto;
      padding: 0 16px;
    }}
    .nhsuk-login-card {{
      background: var(--nhsuk-white);
      border: 1px solid var(--nhsuk-border);
      padding: 32px;
    }}

    /* ── Feature grid ── */
    .nhsuk-feature-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 0;
    }}
    @media (min-width: 641px) {{
      .nhsuk-feature-grid {{ grid-template-columns: repeat(3, 1fr); }}
    }}

    /* ── Page section ── */
    .nhsuk-section {{
      background: var(--nhsuk-white);
      padding: 40px 0;
    }}
    .nhsuk-section--grey {{
      background: var(--nhsuk-grey-5);
      padding: 40px 0;
    }}

    /* ── Hidden ── */
    .nhsuk-u-visually-hidden {{
      position: absolute;
      width: 1px;
      height: 1px;
      margin: -1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
      white-space: nowrap;
    }}
    .hidden {{ display: none !important; }}

    /* ── Skip link ── */
    .nhsuk-skip-link {{
      display: block;
      left: 0;
      padding: 16px;
      position: absolute;
      top: -100px;
      z-index: 200;
      background: var(--nhsuk-focus-color);
      color: var(--nhsuk-black);
      font-weight: 700;
      text-decoration: none;
    }}
    .nhsuk-skip-link:focus {{ top: 0; }}
  </style>
</head>
<body>
  <a class="nhsuk-skip-link" href="#maincontent">Skip to main content</a>

  <header class="nhsuk-header" role="banner">
    <div class="nhsuk-width-container">
      <div class="nhsuk-header__container">
        <a class="nhsuk-header__logo" href="/" aria-label="NHS Clinical Coder - go to homepage">
          <span class="nhsuk-logo">{NHS_LOGO_SVG}</span>
          <span class="nhsuk-header__service-name">Clinical Coder</span>
        </a>
        {user_nav}
      </div>
    </div>
  </header>

  <main id="maincontent" role="main">
    {body}
  </main>

  <footer class="nhsuk-footer" role="contentinfo">
    <div class="nhsuk-width-container">
      <ul class="nhsuk-footer__list">
        <li><a class="nhsuk-footer__list-item-link" href="/">Home</a></li>
        <li><a class="nhsuk-footer__list-item-link" href="https://classbrowser.nhs.uk/" target="_blank" rel="noopener">NHS Classifications Browser</a></li>
        <li><a class="nhsuk-footer__list-item-link" href="/health">Health check</a></li>
      </ul>
      <p class="nhsuk-footer__copyright">
        &copy; NHS England. Clinical coding support tool for authorised use only.
        ICD-10 5th Edition &amp; OPCS-4.10/4.11.
      </p>
    </div>
  </footer>
</body>
</html>"""


def render_landing():
    body = f"""
    <div class="nhsuk-hero">
      <div class="nhsuk-width-container">
        <div class="nhsuk-hero__wrapper">
          <h1>NHS Clinical Coding</h1>
          <p class="nhsuk-hero__desc">
            Assign ICD-10 and OPCS-4 codes from clinical documentation.
            Validated against the NHS England Classifications Browser with
            full audit trail and coder feedback.
          </p>
          <a class="nhsuk-button nhsuk-button--reverse" href="/login">Sign in to the tool</a>
        </div>
      </div>
    </div>

    <div class="nhsuk-section">
      <div class="nhsuk-width-container">
        <div class="nhsuk-feature-grid">
          <div class="nhsuk-card nhsuk-card--feature">
            <div class="nhsuk-card__content">
              <h2 class="nhsuk-card__heading">ICD-10 coding</h2>
              <p class="nhsuk-card__description">
                ICD-10 5th Edition (NHS England) diagnostic code assignment with
                dagger/asterisk convention and sequencing rules.
              </p>
            </div>
          </div>
          <div class="nhsuk-card nhsuk-card--feature">
            <div class="nhsuk-card__content">
              <h2 class="nhsuk-card__heading">OPCS-4 coding</h2>
              <p class="nhsuk-card__description">
                OPCS-4.10/4.11 procedure codes with laterality, imaging, and
                anaesthesia applied per NHS coding standards.
              </p>
            </div>
          </div>
          <div class="nhsuk-card nhsuk-card--feature">
            <div class="nhsuk-card__content">
              <h2 class="nhsuk-card__heading">Classifications Browser</h2>
              <p class="nhsuk-card__description">
                Each proposed code is verified against the
                NHS England Classifications Browser for the correct episode date version.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="nhsuk-section--grey">
      <div class="nhsuk-width-container">
        <div class="nhsuk-warning-callout">
          <h3 class="nhsuk-warning-callout__label">Local development environment</h3>
          <p>This tool is running locally at <strong>127.0.0.1:{PORT}</strong>.
          It is for authorised NHS users only. All data is processed locally;
          no patient data is transmitted externally.</p>
        </div>
        <h2>How it works</h2>
        <div class="nhsuk-summary-list">
          <div class="nhsuk-summary-list__row">
            <div class="nhsuk-summary-list__key">1. Upload workbook</div>
            <div class="nhsuk-summary-list__value">Ingest an approved <code>.xlsm</code> patient-data workbook. Macros are never executed.</div>
          </div>
          <div class="nhsuk-summary-list__row">
            <div class="nhsuk-summary-list__key">2. Assign codes</div>
            <div class="nhsuk-summary-list__value">The agent assigns ICD-10 and OPCS-4 codes based on clinical documentation with a confidence score per episode.</div>
          </div>
          <div class="nhsuk-summary-list__row">
            <div class="nhsuk-summary-list__key">3. Review &amp; validate</div>
            <div class="nhsuk-summary-list__value">Episodes with confidence below 0.8, or flagged case types (oncology, neurology, paediatrics, mental health), are routed for human coder review.</div>
          </div>
          <div class="nhsuk-summary-list__row">
            <div class="nhsuk-summary-list__key">4. Export</div>
            <div class="nhsuk-summary-list__value">Download the coded CSV with full audit trail for submission to SUS or local data warehouse.</div>
          </div>
        </div>
        <a class="nhsuk-button" href="/login">Sign in to get started</a>
      </div>
    </div>"""
    return page_template("Home", body)


def render_login(error=None):
    error_html = ""
    if error:
        error_html = f"""
        <div class="nhsuk-error-summary" role="alert" aria-labelledby="error-summary-title">
          <h2 class="nhsuk-error-summary__title" id="error-summary-title">There is a problem</h2>
          <p class="nhsuk-error-summary__body">{html.escape(error)}</p>
        </div>"""

    input_cls = " nhsuk-input--error" if error else ""

    body = f"""
    <div class="nhsuk-main-wrapper">
      <div class="nhsuk-login-wrapper">
        {error_html}
        <div class="nhsuk-login-card">
          <h1>Sign in</h1>
          <p class="nhsuk-hint" style="margin-bottom:24px;">
            Use your NHS Clinical Coder credentials to access this tool.
          </p>
          <form action="/login" method="post" novalidate>
            <div class="nhsuk-form-group{"  nhsuk-form-group--error" if error else ""}">
              <label class="nhsuk-label nhsuk-label--l" for="username">Username</label>
              <input class="nhsuk-input{input_cls}" id="username" name="username"
                type="text" autocomplete="username" spellcheck="false">
            </div>
            <div class="nhsuk-form-group{"  nhsuk-form-group--error" if error else ""}">
              <label class="nhsuk-label nhsuk-label--l" for="password">Password</label>
              <input class="nhsuk-input{input_cls}" id="password" name="password"
                type="password" autocomplete="current-password">
            </div>
            <button class="nhsuk-button" type="submit">Sign in</button>
          </form>
        </div>
        <div class="nhsuk-card" style="margin-top:16px;">
          <div class="nhsuk-card__content">
            <h3 class="nhsuk-card__heading" style="font-size:0.9375rem;">Test credentials</h3>
            <div class="nhsuk-summary-list" style="margin-bottom:0;">
              <div class="nhsuk-summary-list__row">
                <div class="nhsuk-summary-list__key">coder1 / coding1</div>
                <div class="nhsuk-summary-list__value">Clinical Coder</div>
              </div>
              <div class="nhsuk-summary-list__row">
                <div class="nhsuk-summary-list__key">coder2 / coding2</div>
                <div class="nhsuk-summary-list__value">Clinical Coder</div>
              </div>
              <div class="nhsuk-summary-list__row">
                <div class="nhsuk-summary-list__key">manager / manage1</div>
                <div class="nhsuk-summary-list__value">Coding Manager</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>"""
    return page_template("Sign in", body)


def read_preview(csv_path, limit=20):
    path = Path(csv_path)
    if not path.exists():
        return [], []

    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for index, row in enumerate(reader):
            if index >= limit:
                break
            rows.append(row)
        return reader.fieldnames or FIELDNAMES, rows


def check_classifications_browser():
    checked_at = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    result = {
        "checked": False,
        "url": CLASSIFICATION_BROWSER_URL,
        "checked_at": checked_at,
        "status": "not checked",
        "classification_versions": "ICD-10 5th Edition and OPCS-4 version selected according to episode date",
    }

    try:
        request = urllib.request.Request(
            CLASSIFICATION_BROWSER_URL,
            headers={"User-Agent": "NHS Clinical Coder Test App/1.0"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            result["checked"] = 200 <= response.status < 400
            result["status"] = f"reachable, HTTP {response.status}"
    except Exception as exc:
        result["status"] = f"unavailable during check: {exc}"

    return result


def javascript_hash(value):
    hash_value = 0
    for char in value:
        hash_value = ((hash_value << 5) - hash_value + ord(char)) & 0xFFFFFFFF
        if hash_value >= 0x80000000:
            hash_value -= 0x100000000
    return hash_value


def classbrowser_book_for_code(code):
    if code in ICD10_REFERENCE:
        return "ICD-10-5TH-Edition", "ICD-10 5th Edition"
    if code in OPCS4_REFERENCE:
        return "OPCS-4.11", "OPCS-4.11"
    if re.match(r"^[A-Z][0-9]", code):
        return "ICD-10-5TH-Edition", "ICD-10 5th Edition"
    return "OPCS-4.11", "OPCS-4.11"


def search_classbrowser_code(code):
    if code in CODE_CHECK_CACHE:
        cached = dict(CODE_CHECK_CACHE[code])
        cached["checked_at"] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
        return cached

    book_version, classification = classbrowser_book_for_code(code)
    search_payload = (
        '{      "branches": []  , "releaseVersions": [       "'
        + book_version
        + '"     ]  ,  "searchContent": "'
        + code.replace('"', '\\"')
        + '"  }'
    )
    encoded_payload = urllib.parse.quote(search_payload, safe="~@#$&()*!+=:;,.?/'[]")
    search_arg = base64_encode(encoded_payload)
    search_url = f"{CLASSIFICATION_BROWSER_URL}bookdoc/search/{book_version}/{javascript_hash(search_arg)}"
    checked_at = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    result = {
        "code": code,
        "classification": classification,
        "book_version": book_version,
        "checked_at": checked_at,
        "search_url": search_url,
        "found": False,
        "match_count": 0,
        "status": "not checked",
        "first_match": "",
    }

    try:
        request = urllib.request.Request(
            search_url,
            headers={
                "User-Agent": "NHS Clinical Coder Test App/1.0",
                "searchArg-base64": search_arg,
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = payload.get("text", "")
        match = re.search(r"Found:\s+(\d+)", text)
        result["match_count"] = int(match.group(1)) if match else 0
        result["found"] = result["match_count"] > 0
        result["status"] = f"searched, HTTP 200, {text}"
        result["first_match"] = first_classbrowser_match(payload)
    except Exception as exc:
        result["status"] = f"search failed: {exc}"

    CODE_CHECK_CACHE[code] = dict(result)
    return result


def base64_encode(value):
    import base64
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def first_classbrowser_match(node):
    for child in node.get("children", []) if isinstance(node, dict) else []:
        text = child.get("text", "")
        if child.get("id") and text:
            return re.sub(r"<[^>]+>", "", html.unescape(text))
        nested = first_classbrowser_match(child)
        if nested:
            return nested
    return ""


def split_codes(value):
    return [code.strip() for code in str(value or "").split(";") if code.strip()]


def classbrowser_checks_for_row(coded_row):
    checks = []
    for code in split_codes(coded_row.get("ICD-10 Code")) + split_codes(coded_row.get("OPCS-4 Code")):
        checks.append(search_classbrowser_code(code))
    return checks


def code_check_summary(checks):
    if not checks:
        return "No proposed codes to check"
    found = sum(1 for check in checks if check.get("found"))
    return f"{found}/{len(checks)} proposed codes found in NHS Classifications Browser"


def load_detail_rows():
    if not DEFAULT_DETAIL_OUTPUT.exists():
        return []
    with open(DEFAULT_DETAIL_OUTPUT, encoding="utf-8") as handle:
        return json.load(handle)


def patient_detail(sample_number):
    for row in load_detail_rows():
        if str(row.get("Sample Number", "")) == str(sample_number):
            return row
    return None


def load_feedback(sample_number=None):
    if not FEEDBACK_OUTPUT.exists():
        return []
    with open(FEEDBACK_OUTPUT, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if sample_number is None:
        return rows
    return [row for row in rows if str(row.get("Sample Number", "")) == str(sample_number)]


def append_feedback(feedback):
    ensure_dirs()
    write_header = not FEEDBACK_OUTPUT.exists()
    with open(FEEDBACK_OUTPUT, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FEEDBACK_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(feedback)


def render_feedback_history(sample_number):
    feedback_rows = load_feedback(sample_number)
    if not feedback_rows:
        return '<p style="font-size:0.875rem;color:#425563;margin:0;">No coder feedback recorded for this patient yet.</p>'

    items = []
    for item in reversed(feedback_rows[-5:]):
        code_text = (
            f"ICD-10: {item.get('Agent ICD-10 Code', '')} → "
            f"{item.get('Corrected ICD-10 Code', '') or item.get('Agent ICD-10 Code', '')}  "
            f"OPCS-4: {item.get('Agent OPCS-4 Code', '')} → "
            f"{item.get('Corrected OPCS-4 Code', '') or item.get('Agent OPCS-4 Code', '')}"
        )
        meta_parts = [f"Coder: {html.escape(item.get('Coder ID', '') or 'not provided')}"]
        if item.get("Comments"):
            meta_parts.append(html.escape(item.get("Comments", "")))
        items.append(f"""
          <div class="nhsuk-feedback-item">
            <strong>{html.escape(item.get("Decision", ""))}</strong>
            &nbsp;&middot;&nbsp;
            <span style="color:#425563;">{html.escape(item.get("Timestamp", ""))}</span>
            <div class="nhsuk-feedback-item__codes">{html.escape(code_text)}</div>
            <div class="nhsuk-feedback-item__meta">{" &nbsp;&middot;&nbsp; ".join(meta_parts)}</div>
          </div>""")
    return "".join(items)


def render_patient_detail(sample_number, status=None, error=False, username=None, user_role=None):
    row = patient_detail(sample_number)
    if not row:
        body = f"""
        <div class="nhsuk-main-wrapper">
          <div class="nhsuk-width-container">
            <a class="nhsuk-back-link" href="/app">Back to app</a>
            <h1>Patient not found</h1>
            <p>No detail record exists for patient {html.escape(str(sample_number))}. Run the coding process first.</p>
            <a class="nhsuk-button nhsuk-button--secondary" href="/app">Back to app</a>
          </div>
        </div>"""
        return page_template("Patient not found", body, username=username, user_role=user_role)

    banner_html = ""
    if status:
        banner_type = "nhsuk-notification-banner--error" if error else "nhsuk-notification-banner--success"
        banner_title = "Error" if error else "Success"
        banner_html = f"""
        <div class="nhsuk-notification-banner {banner_type}" role="alert">
          <div class="nhsuk-notification-banner__header">
            <h2 class="nhsuk-notification-banner__title">{banner_title}</h2>
          </div>
          <div class="nhsuk-notification-banner__content">
            <p>{status}</p>
          </div>
        </div>"""

    browser = row.get("Classification Browser Check", {})
    checked = bool(browser.get("checked"))
    browser_badge = (
        '<span class="nhsuk-tag nhsuk-tag--green">Checked</span>'
        if checked else
        '<span class="nhsuk-tag nhsuk-tag--yellow">Check attempted</span>'
    )

    icd_codes = [c.strip() for c in str(row.get("ICD-10 Code", "")).split(";") if c.strip()]
    opcs_codes = [c.strip() for c in str(row.get("OPCS-4 Code", "")).split(";") if c.strip()]
    icd_html = " ".join(f'<span class="nhsuk-code-tag">{html.escape(c)}</span>' for c in icd_codes) or "—"
    opcs_html = " ".join(f'<span class="nhsuk-code-tag">{html.escape(c)}</span>' for c in opcs_codes) or "—"

    conf = str(row.get("Confidence", ""))
    try:
        conf_v = float(conf)
        conf_tag_cls = "nhsuk-tag--green" if conf_v >= 0.90 else "nhsuk-tag--yellow" if conf_v >= 0.80 else "nhsuk-tag--red"
    except ValueError:
        conf_tag_cls = "nhsuk-tag--grey"
    conf_badge = f'<span class="nhsuk-tag {conf_tag_cls}">{html.escape(conf)}</span>'

    rev = str(row.get("Human Review Required", ""))
    rev_badge = f'<span class="nhsuk-tag {"nhsuk-tag--yellow" if rev == "Yes" else "nhsuk-tag--green"}">{html.escape(rev)}</span>'

    dl_rows = [
        ("Sample number", html.escape(str(row.get("Sample Number", "")))),
        ("Source workbook", html.escape(str(row.get("Source Workbook", "")))),
        ("Source worksheet", html.escape(str(row.get("Source Worksheet", "")))),
        ("Source row", html.escape(str(row.get("Source Row", "")))),
        ("Source columns", html.escape(str(row.get("Source Columns", "")))),
        ("ICD-10 suggestion", icd_html),
        ("ICD-10 description", html.escape(str(row.get("ICD-10 Description", "")))),
        ("OPCS-4 suggestion", opcs_html),
        ("OPCS-4 description", html.escape(str(row.get("OPCS-4 Description", "")))),
        ("Confidence", conf_badge),
        ("Human review required", rev_badge),
        ("Coding rules applied", html.escape(str(row.get("Coding Rules Applied", "")))),
        ("Per-code browser checks", html.escape(str(row.get("ClassBrowser Code Check Summary", "")))),
        ("Classification Browser", html.escape(str(browser.get("status", "")))),
        ("Browser checked at", html.escape(str(browser.get("checked_at", "")))),
    ]
    summary_html = "".join(
        f'<div class="nhsuk-summary-list__row">'
        f'<div class="nhsuk-summary-list__key">{label}</div>'
        f'<div class="nhsuk-summary-list__value">{value}</div>'
        f'</div>'
        for label, value in dl_rows
    )

    code_checks = row.get("ClassBrowser Code Checks", [])
    check_items = "".join(f"""
      <div class="nhsuk-feedback-item">
        <strong class="nhsuk-code-tag" style="font-size:0.9rem;">{html.escape(c.get("code",""))}</strong>
        &nbsp;
        <span style="font-size:0.875rem;color:#425563;">{html.escape(c.get("classification",""))}</span>
        <div style="font-size:0.875rem;margin:4px 0 2px;">{html.escape(c.get("status",""))}</div>
        <div class="nhsuk-feedback-item__meta">
          Book: {html.escape(c.get("book_version",""))} &nbsp;&middot;&nbsp; Matches: {html.escape(str(c.get("match_count","")))}
          {(" &nbsp;&middot;&nbsp; " + html.escape(c.get("first_match",""))) if c.get("first_match") else ""}
        </div>
      </div>""" for c in code_checks
    ) or '<p style="font-size:0.875rem;color:#425563;margin:0;">No per-code checks recorded.</p>'

    body = f"""
    <div class="nhsuk-main-wrapper">
      <div class="nhsuk-width-container">
        {banner_html}
        <a class="nhsuk-back-link" href="/app">Back to app</a>
        <h1>Patient {html.escape(str(row.get("Sample Number", sample_number)))}</h1>
        <p style="color:#425563;margin-bottom:32px;">
          Full coding evidence and provenance from the latest run.
          &nbsp;{browser_badge}
        </p>
        <div class="nhsuk-grid-row nhsuk-grid-row--two-thirds-one-third">
          <div>
            <div class="nhsuk-card">
              <div class="nhsuk-card__content">
                <h2>Coding record</h2>
                <div class="nhsuk-summary-list">{summary_html}</div>
              </div>
            </div>
            <div class="nhsuk-card">
              <div class="nhsuk-card__content">
                <h2>Per-code Classifications Browser checks</h2>
                {check_items}
              </div>
            </div>
            <div class="nhsuk-card">
              <div class="nhsuk-card__content">
                <h2>Full patient evidence</h2>
                <div class="nhsuk-evidence-box">{html.escape(row.get("Finding", ""))}</div>
              </div>
            </div>
            <div class="nhsuk-card">
              <div class="nhsuk-card__content">
                <h2>Agent rationale</h2>
                <div class="nhsuk-evidence-box">{html.escape(row.get("LLM Reasoning", ""))}</div>
              </div>
            </div>
          </div>
          <div>
            <div class="nhsuk-card">
              <div class="nhsuk-card__content">
                <h2>Classifications Browser</h2>
                <p>{browser_badge}</p>
                <p style="font-size:0.875rem;color:#425563;">
                  Each proposed code is searched in the NHS England Classifications Browser
                  using the ICD-10 or OPCS-4 book for the episode date.
                </p>
                <a class="nhsuk-button nhsuk-button--secondary nhsuk-button--sm"
                   href="{html.escape(browser.get('url', CLASSIFICATION_BROWSER_URL))}"
                   target="_blank" rel="noopener">
                  Open Classifications Browser
                </a>
              </div>
            </div>
            <div class="nhsuk-card">
              <div class="nhsuk-card__content">
                <h2>Coder feedback</h2>
                <form action="/feedback" method="post">
                  <input type="hidden" name="sample_number" value="{html.escape(str(row.get("Sample Number", sample_number)))}">
                  <input type="hidden" name="agent_icd10" value="{html.escape(str(row.get("ICD-10 Code", "")))}">
                  <input type="hidden" name="agent_opcs4" value="{html.escape(str(row.get("OPCS-4 Code", "")))}">
                  <div class="nhsuk-form-group">
                    <label class="nhsuk-label" for="decision">Decision</label>
                    <select class="nhsuk-select" id="decision" name="decision">
                      <option value="Accepted">Accept agent coding</option>
                      <option value="Amended">Amend coding</option>
                      <option value="Rejected">Reject coding</option>
                      <option value="Needs senior review">Needs senior review</option>
                    </select>
                  </div>
                  <div class="nhsuk-form-group">
                    <label class="nhsuk-label" for="coder_id">Coder ID</label>
                    <span class="nhsuk-hint">Optional</span>
                    <input class="nhsuk-input" id="coder_id" type="text" name="coder_id">
                  </div>
                  <div class="nhsuk-form-group">
                    <label class="nhsuk-label" for="corrected_icd10">Corrected ICD-10</label>
                    <input class="nhsuk-input" id="corrected_icd10" type="text" name="corrected_icd10"
                      value="{html.escape(str(row.get("ICD-10 Code", "")))}">
                  </div>
                  <div class="nhsuk-form-group">
                    <label class="nhsuk-label" for="corrected_opcs4">Corrected OPCS-4</label>
                    <input class="nhsuk-input" id="corrected_opcs4" type="text" name="corrected_opcs4"
                      value="{html.escape(str(row.get("OPCS-4 Code", "")))}">
                  </div>
                  <div class="nhsuk-form-group">
                    <label class="nhsuk-label" for="comments">Notes</label>
                    <textarea class="nhsuk-textarea" id="comments" name="comments" rows="4"
                      placeholder="Record why codes were accepted, amended, or rejected."></textarea>
                  </div>
                  <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;">
                    <button type="submit" class="nhsuk-button" style="margin-bottom:0;">Save feedback</button>
                    <a class="nhsuk-button nhsuk-button--secondary nhsuk-button--sm" href="/download-feedback">Download CSV</a>
                  </div>
                </form>
                <div style="margin-top:24px;">
                  <h3 style="font-size:1rem;margin-bottom:8px;">Feedback history</h3>
                  {render_feedback_history(row.get("Sample Number", sample_number))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>"""
    return page_template(f"Patient {sample_number}", body, username=username, user_role=user_role)


def render_preview(csv_path=DEFAULT_OUTPUT):
    headers, rows = read_preview(csv_path)
    if not rows:
        return """
        <div class="nhsuk-card">
          <div class="nhsuk-card__content">
            <h2>Output preview</h2>
            <p style="color:#425563;margin:0;">Run the process to see results here.</p>
          </div>
        </div>"""

    preferred = ["Sample Number", "ICD-10 Code", "OPCS-4 Code", "Confidence", "Human Review Required", "Finding", "Source Row"]
    visible = [h for h in preferred if h in headers]
    head_html = "".join(f'<th class="nhsuk-table__header">{html.escape(h)}</th>' for h in visible)
    row_html = []
    for row in rows:
        cells = []
        for h in visible:
            v = row.get(h, "")
            if h in ("ICD-10 Code", "OPCS-4 Code"):
                tags = " ".join(f'<span class="nhsuk-code-tag">{html.escape(c.strip())}</span>' for c in v.split(";") if c.strip())
                cells.append(f'<td class="nhsuk-table__cell">{tags or "—"}</td>')
            elif h == "Confidence":
                try:
                    cv = float(v)
                    tag_cls = "nhsuk-tag--green" if cv >= 0.90 else "nhsuk-tag--yellow" if cv >= 0.80 else "nhsuk-tag--red"
                except ValueError:
                    tag_cls = "nhsuk-tag--grey"
                cells.append(f'<td class="nhsuk-table__cell"><span class="nhsuk-tag {tag_cls}">{html.escape(v)}</span></td>')
            elif h == "Human Review Required":
                tag_cls = "nhsuk-tag--yellow" if v == "Yes" else "nhsuk-tag--green"
                cells.append(f'<td class="nhsuk-table__cell"><span class="nhsuk-tag {tag_cls}">{html.escape(v)}</span></td>')
            elif h == "Sample Number":
                cells.append(f'<td class="nhsuk-table__cell"><a href="/patient/{html.escape(v)}">{html.escape(v)}</a></td>')
            elif h == "Finding":
                excerpt = v[:100] + "…" if len(v) > 100 else v
                cells.append(f'<td class="nhsuk-table__cell nhsuk-table__cell--truncate">{html.escape(excerpt)}</td>')
            else:
                cells.append(f'<td class="nhsuk-table__cell">{html.escape(v)}</td>')
        row_html.append(f'<tr class="nhsuk-table__row">{"".join(cells)}</tr>')

    return f"""
    <div class="nhsuk-card">
      <div class="nhsuk-card__content">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:16px;flex-wrap:wrap;">
          <h2 style="margin:0;">Output preview
            <span style="font-weight:400;font-size:0.9375rem;color:#425563;">&mdash; first {len(rows)} rows</span>
          </h2>
          <a class="nhsuk-button nhsuk-button--secondary nhsuk-button--sm hidden" href="/download" data-download-link style="margin:0;">
            Download CSV
          </a>
        </div>
        <div class="nhsuk-table-responsive">
          <table class="nhsuk-table">
            <thead class="nhsuk-table__head">
              <tr class="nhsuk-table__row">{head_html}</tr>
            </thead>
            <tbody class="nhsuk-table__body">{"".join(row_html)}</tbody>
          </table>
        </div>
      </div>
    </div>"""


def render_index(status=None, error=False, username=None, user_role=None):
    banner_html = ""
    if status:
        banner_type = "nhsuk-notification-banner--error" if error else "nhsuk-notification-banner--success"
        banner_title = "Error" if error else "Success"
        banner_html = f"""
        <div class="nhsuk-notification-banner {banner_type}" role="alert">
          <div class="nhsuk-notification-banner__header">
            <h2 class="nhsuk-notification-banner__title">{banner_title}</h2>
          </div>
          <div class="nhsuk-notification-banner__content">
            <p>{status}</p>
          </div>
        </div>"""

    default_exists = "available" if WORKBOOK_FILE.exists() else "missing"

    body = f"""
    <div class="nhsuk-main-wrapper">
      <div class="nhsuk-width-container">
        {banner_html}
        <h1>Endoscopy coding run</h1>
        <p class="nhsuk-lede-text">
          Assign ICD-10 and OPCS-4 codes from the sample workbook, or upload your own .xlsm file.
        </p>

        <div class="nhsuk-grid-row nhsuk-grid-row--two-thirds-one-third">
          <div>
            <div class="nhsuk-card">
              <div class="nhsuk-card__content">
                <h2>Run process</h2>
                <form action="/run" method="post" enctype="multipart/form-data" data-run-form>

                  <div class="nhsuk-form-group">
                    <label class="nhsuk-label">Workbook source</label>
                    <div class="nhsuk-radios__item">
                      <input class="nhsuk-radios__input" type="radio" id="source-sample"
                        name="source" value="sample" checked>
                      <label class="nhsuk-radios__label" for="source-sample">
                        Use sample workbook
                      </label>
                    </div>
                    <div class="nhsuk-radios__conditional">
                      <p class="nhsuk-hint" style="margin:0;">
                        {html.escape(str(WORKBOOK_FILE))} &mdash; {default_exists}
                      </p>
                    </div>
                    <div class="nhsuk-radios__item">
                      <input class="nhsuk-radios__input" type="radio" id="source-upload"
                        name="source" value="upload">
                      <label class="nhsuk-radios__label" for="source-upload">
                        Upload .xlsm workbook
                      </label>
                    </div>
                    <div class="nhsuk-radios__conditional">
                      <div class="nhsuk-form-group" style="margin-bottom:0;">
                        <label class="nhsuk-label" for="workbook-file">Select file</label>
                        <input class="nhsuk-input" id="workbook-file" type="file"
                          name="workbook" accept=".xlsm,.xlsx"
                          style="height:auto;padding:8px;">
                      </div>
                    </div>
                  </div>

                  <div class="nhsuk-form-group">
                    <label class="nhsuk-label" for="worksheet">Worksheet name</label>
                    <input class="nhsuk-input" id="worksheet" type="text"
                      name="worksheet" value="{html.escape(WORKSHEET_NAME)}"
                      style="max-width:300px;">
                  </div>

                  <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;">
                    <button type="submit" class="nhsuk-button" data-run-button>
                      Run clinical coding
                    </button>
                    <a class="nhsuk-button nhsuk-button--secondary hidden" href="/download"
                      data-download-link style="margin-bottom:8px;">
                      Download CSV
                    </a>
                  </div>
                </form>
                <p class="nhsuk-hint" style="margin-top:8px;">
                  Macros are not executed. Workbook, worksheet, row, and column provenance
                  are captured for every episode.
                </p>
              </div>
            </div>

            <div class="nhsuk-card hidden" data-stream-panel>
              <div class="nhsuk-card__content">
                <h3 data-stream-status>Waiting to start&hellip;</h3>
                <div class="nhsuk-progress-bar">
                  <div class="nhsuk-progress-bar__fill" data-progress-fill></div>
                </div>
                <ul class="nhsuk-stream-list" data-stream-list></ul>
              </div>
            </div>

            <div class="nhsuk-card" style="border:none;padding:0;background:none;margin-bottom:24px;">
              <img src="/static/endoscopy-recovery-area.jpg"
                alt="Endoscopy recovery area"
                style="width:100%;display:block;border:1px solid #d8dde0;">
              <p class="nhsuk-hint" style="margin:8px 0 0;">Clinical environment reference image.</p>
            </div>
          </div>

          <div>
            {render_preview()}
          </div>
        </div>
      </div>
    </div>

    <script>
    (function() {{
      const form = document.querySelector("[data-run-form]");
      const runBtn = document.querySelector("[data-run-button]");
      const streamPanel = document.querySelector("[data-stream-panel]");
      const streamStatus = document.querySelector("[data-stream-status]");
      const progressFill = document.querySelector("[data-progress-fill]");
      const streamList = document.querySelector("[data-stream-list]");
      const downloadLinks = document.querySelectorAll("[data-download-link]");

      if (!form) return;

      form.addEventListener("submit", function(e) {{
        e.preventDefault();
        streamPanel.classList.remove("hidden");
        runBtn.disabled = true;
        runBtn.textContent = "Running…";
        streamList.innerHTML = "";
        progressFill.style.width = "0%";

        const fd = new FormData(form);
        fetch("/run-stream", {{ method: "POST", body: fd }})
          .then(function(res) {{
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            function pump() {{
              return reader.read().then(function({{ done, value }}) {{
                if (done) return;
                buffer += decoder.decode(value, {{ stream: true }});
                let lines = buffer.split("\\n");
                buffer = lines.pop();
                lines.forEach(function(line) {{
                  if (!line.trim()) return;
                  try {{
                    const evt = JSON.parse(line);
                    handleEvent(evt);
                  }} catch(e) {{}}
                }});
                return pump();
              }});
            }}
            return pump();
          }})
          .catch(function(err) {{
            streamStatus.textContent = "Connection error: " + err.message;
            runBtn.disabled = false;
            runBtn.textContent = "Run clinical coding";
          }});
      }});

      function handleEvent(evt) {{
        if (evt.type === "start") {{
          streamStatus.textContent = "Processing " + evt.total + " records from " + evt.workbook + "…";
        }} else if (evt.type === "patient") {{
          progressFill.style.width = evt.percent + "%";
          streamStatus.textContent = evt.percent + "% — Patient " + evt.sample_number;
          const li = document.createElement("li");
          li.className = "nhsuk-stream-list__item";
          const conf = parseFloat(evt.confidence);
          const tagCls = conf >= 0.90 ? "nhsuk-tag--green" : conf >= 0.80 ? "nhsuk-tag--yellow" : "nhsuk-tag--red";
          li.innerHTML =
            "<span class=\\"nhsuk-tag " + tagCls + "\\">" + escHtml(evt.confidence) + "</span>" +
            "<span><a href=\\"" + escHtml(evt.detail_url) + "\\">" +
              "Patient " + escHtml(String(evt.sample_number)) +
            "</a> &mdash; ICD-10: " + escHtml(evt.icd10) +
            " &nbsp; OPCS-4: " + escHtml(evt.opcs4) + "</span>";
          streamList.appendChild(li);
          streamList.scrollTop = streamList.scrollHeight;
        }} else if (evt.type === "complete") {{
          progressFill.style.width = "100%";
          streamStatus.textContent = "Complete — " + evt.rows_processed + " records coded.";
          runBtn.disabled = false;
          runBtn.textContent = "Run clinical coding";
          downloadLinks.forEach(function(l) {{ l.classList.remove("hidden"); }});
        }} else if (evt.type === "error") {{
          streamStatus.textContent = "Error: " + evt.message;
          runBtn.disabled = false;
          runBtn.textContent = "Run clinical coding";
        }}
      }}

      function escHtml(s) {{
        return String(s)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;");
      }}
    }})();
    </script>"""
    return page_template("NHS Clinical Coder — Run", body, username=username, user_role=user_role)


def save_upload(form):
    item = form["workbook"] if "workbook" in form else None
    if item is None or not getattr(item, "filename", ""):
        raise ValueError("Choose an .xlsm workbook to upload.")

    source_name = Path(item.filename).name
    suffix = Path(source_name).suffix.lower()
    if suffix not in {".xlsm", ".xlsx"}:
        raise ValueError("Uploaded workbook must be an .xlsm or .xlsx file.")

    target = UPLOAD_DIR / f"{int(time.time())}_{source_name}"
    with open(target, "wb") as out:
        shutil.copyfileobj(item.file, out)
    return target


class AppHandler(BaseHTTPRequestHandler):

    def get_session_user(self):
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            name, _, value = part.strip().partition("=")
            if name.strip() == SESSION_COOKIE:
                return SESSIONS.get(value.strip())
        return None

    def send_redirect(self, location, status=HTTPStatus.FOUND):
        self.send_response(status)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def require_auth(self):
        session = self.get_session_user()
        if not session:
            self.send_redirect("/login")
        return session

    def send_html(self, html_text, status=HTTPStatus.OK):
        payload = html_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)
        session = self.get_session_user()

        if parsed.path == "/":
            if session:
                self.send_redirect("/app")
            else:
                self.send_html(render_landing())
            return

        if parsed.path == "/login":
            if session:
                self.send_redirect("/app")
            else:
                self.send_html(render_login())
            return

        if parsed.path == "/logout":
            cookie_header = self.headers.get("Cookie", "")
            for part in cookie_header.split(";"):
                name, _, value = part.strip().partition("=")
                if name.strip() == SESSION_COOKIE:
                    SESSIONS.pop(value.strip(), None)
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", f"{SESSION_COOKIE}=; Max-Age=0; Path=/; HttpOnly")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if parsed.path == "/app":
            session = self.require_auth()
            if not session:
                return
            self.send_html(render_index(username=session["name"], user_role=session["role"]))
            return

        if parsed.path.startswith("/patient/"):
            session = self.require_auth()
            if not session:
                return
            sample_number = parsed.path.removeprefix("/patient/")
            self.send_html(render_patient_detail(
                sample_number,
                username=session["name"],
                user_role=session["role"],
            ))
            return

        if parsed.path.startswith("/static/"):
            self.send_static(parsed.path)
            return

        if parsed.path == "/download":
            session = self.require_auth()
            if not session:
                return
            self.send_download()
            return

        if parsed.path == "/download-feedback":
            session = self.require_auth()
            if not session:
                return
            self.send_feedback_download()
            return

        if parsed.path == "/health":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Page not found")

    def send_static(self, request_path):
        relative_path = request_path.removeprefix("/static/").lstrip("/")
        static_path = (STATIC_DIR / relative_path).resolve()
        if STATIC_DIR.resolve() not in static_path.parents or not static_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Asset not found")
            return

        payload = static_path.read_bytes()
        content_type = mimetypes.guess_type(static_path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/login":
            self.handle_login()
            return

        if parsed.path == "/run-stream":
            session = self.require_auth()
            if not session:
                self.write_stream_event({"type": "error", "message": "Session expired. Please sign in again."})
                return
            self.stream_run()
            return

        if parsed.path == "/feedback":
            session = self.require_auth()
            if not session:
                return
            self.save_feedback(session)
            return

        if parsed.path != "/run":
            self.send_error(HTTPStatus.NOT_FOUND, "Page not found")
            return

        session = self.require_auth()
        if not session:
            return

        ensure_dirs()
        try:
            form = FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                    "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
                },
            )
            source = form.getfirst("source", "sample")
            worksheet = form.getfirst("worksheet", WORKSHEET_NAME).strip() or WORKSHEET_NAME
            workbook_path = save_upload(form) if source == "upload" else WORKBOOK_FILE
            browser_check = check_classifications_browser()

            result = run_coding_process(
                workbook_path=workbook_path,
                output_file=DEFAULT_OUTPUT,
                worksheet_name=worksheet,
            )
            detail_rows = []
            with open(DEFAULT_OUTPUT, newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    code_checks = classbrowser_checks_for_row(row)
                    row["ClassBrowser Code Checks"] = code_checks
                    row["ClassBrowser Code Check Summary"] = code_check_summary(code_checks)
                    row["Classification Browser Check"] = browser_check
                    detail_rows.append(row)
            with open(DEFAULT_OUTPUT, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
                writer.writeheader()
                for row in detail_rows:
                    writer.writerow({field: row.get(field, "") for field in FIELDNAMES})
            with open(DEFAULT_DETAIL_OUTPUT, "w", encoding="utf-8") as handle:
                json.dump(detail_rows, handle, ensure_ascii=False, indent=2)

            status_msg = (
                f"Processed <strong>{result['rows_processed']}</strong> workbook rows from "
                f"<strong>{html.escape(Path(result['workbook_file']).name)}</strong>. "
                f"Output written to <strong>{html.escape(Path(result['output_file']).name)}</strong>."
            )
            self.send_html(render_index(status=status_msg, username=session["name"], user_role=session["role"]))
        except Exception as exc:
            self.send_html(
                render_index(status=html.escape(str(exc)), error=True, username=session["name"], user_role=session["role"]),
                HTTPStatus.BAD_REQUEST,
            )

    def handle_login(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        params = parse_qs(body)
        username = params.get("username", [""])[0].strip()
        password = params.get("password", [""])[0]

        user = USERS.get(username)
        if not user or user["password"] != password:
            self.send_html(render_login(error="Username or password is incorrect. Please try again."))
            return

        token = secrets.token_hex(32)
        SESSIONS[token] = {"username": username, "name": user["name"], "role": user["role"]}
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", "/app")
        self.send_header("Set-Cookie", f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def save_feedback(self, session):
        ensure_dirs()
        sample_number = ""
        try:
            form = FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                    "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
                },
            )
            sample_number = form.getfirst("sample_number", "").strip()
            if not sample_number:
                raise ValueError("Missing patient sample number.")

            feedback = {
                "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "Sample Number": sample_number,
                "Decision": form.getfirst("decision", "Amended").strip(),
                "Agent ICD-10 Code": form.getfirst("agent_icd10", "").strip(),
                "Corrected ICD-10 Code": form.getfirst("corrected_icd10", "").strip(),
                "Agent OPCS-4 Code": form.getfirst("agent_opcs4", "").strip(),
                "Corrected OPCS-4 Code": form.getfirst("corrected_opcs4", "").strip(),
                "Coder ID": form.getfirst("coder_id", "").strip(),
                "Comments": form.getfirst("comments", "").strip(),
            }
            append_feedback(feedback)
            self.send_html(render_patient_detail(
                sample_number,
                status="Coder feedback saved.",
                username=session["name"],
                user_role=session["role"],
            ))
        except Exception as exc:
            self.send_html(
                render_patient_detail(sample_number, status=html.escape(str(exc)), error=True,
                                      username=session["name"], user_role=session["role"]),
                HTTPStatus.BAD_REQUEST,
            )

    def parse_run_form(self):
        form = FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            },
        )
        source = form.getfirst("source", "sample")
        worksheet = form.getfirst("worksheet", WORKSHEET_NAME).strip() or WORKSHEET_NAME
        workbook_path = save_upload(form) if source == "upload" else WORKBOOK_FILE
        return workbook_path, worksheet

    def write_stream_event(self, event):
        payload = json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n"
        self.wfile.write(payload)
        self.wfile.flush()

    def stream_run(self):
        ensure_dirs()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            workbook_path, worksheet = self.parse_run_form()
            browser_check = check_classifications_browser()
            records = parse_xlsm_records(Path(workbook_path), worksheet)
            total = len(records)

            self.write_stream_event({
                "type": "start",
                "total": total,
                "workbook": Path(workbook_path).name,
                "worksheet": worksheet,
                "classification_browser_status": browser_check["status"],
                "classification_browser_checked_at": browser_check["checked_at"],
            })

            detail_rows = []
            with open(DEFAULT_OUTPUT, "w", encoding="utf-8", newline="") as out:
                writer = csv.DictWriter(out, fieldnames=FIELDNAMES)
                writer.writeheader()

                for index, record in enumerate(records, start=1):
                    coded_row = code_record(record)
                    code_checks = classbrowser_checks_for_row(coded_row)
                    coded_row["ClassBrowser Code Check Summary"] = code_check_summary(code_checks)
                    detail_row = dict(coded_row)
                    detail_row["Classification Browser Check"] = browser_check
                    detail_row["ClassBrowser Code Checks"] = code_checks
                    detail_rows.append(detail_row)
                    writer.writerow(coded_row)
                    out.flush()

                    self.write_stream_event({
                        "type": "patient",
                        "index": index,
                        "total": total,
                        "percent": round((index / total) * 100, 1) if total else 100,
                        "sample_number": coded_row["Sample Number"],
                        "source_row": coded_row["Source Row"],
                        "icd10": coded_row["ICD-10 Code"],
                        "opcs4": coded_row["OPCS-4 Code"],
                        "confidence": coded_row["Confidence"],
                        "review_required": coded_row["Human Review Required"],
                        "finding": coded_row["Finding"],
                        "classification_browser_status": browser_check["status"],
                        "code_check_summary": coded_row["ClassBrowser Code Check Summary"],
                        "detail_url": f"/patient/{coded_row['Sample Number']}",
                    })
                    time.sleep(0.01)

            with open(DEFAULT_DETAIL_OUTPUT, "w", encoding="utf-8") as handle:
                json.dump(detail_rows, handle, ensure_ascii=False, indent=2)

            self.write_stream_event({
                "type": "complete",
                "rows_processed": total,
                "output_file": DEFAULT_OUTPUT.name,
                "download_url": "/download",
            })
        except Exception as exc:
            self.write_stream_event({"type": "error", "message": str(exc)})

    def send_download(self):
        if not DEFAULT_OUTPUT.exists():
            self.send_html(render_index(status="No CSV output exists yet. Run the process first.", error=True), HTTPStatus.NOT_FOUND)
            return
        payload = DEFAULT_OUTPUT.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f"attachment; filename={DEFAULT_OUTPUT.name}")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_feedback_download(self):
        if not FEEDBACK_OUTPUT.exists():
            self.send_html(render_index(status="No feedback CSV exists yet. Save coder feedback first.", error=True), HTTPStatus.NOT_FOUND)
            return
        payload = FEEDBACK_OUTPUT.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f"attachment; filename={FEEDBACK_OUTPUT.name}")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


def main():
    ensure_dirs()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Serving NHS Clinical Coder Test App at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
