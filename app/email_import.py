"""Log applications and rejections from Gmail into the tracker.

Reads "thank you for applying" and "unfortunately..." emails over IMAP (read-only, so nothing
is marked as read), works out the organization and role, and:

    - adds an application (status Applied, follow-up in 10 days) for each new confirmation
    - marks the matching application "Rejected by Org" for each rejection, adding the
      application first if it was never logged

Each email is handled once: its Message-ID is recorded in the email_imports table.

Needs GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env (a Gmail app password, from Google
Account > Security > 2-Step Verification > App passwords). Everything stays on this computer.
"""
import email
import imaplib
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from email.header import decode_header, make_header
from email.policy import default as default_policy
from email.utils import parseaddr, parsedate_to_datetime

FOLLOW_UP_DAYS = 10

# Gmail search for candidate emails; the classifier below makes the final call.
GMAIL_QUERY = ('subject:(application OR applying OR applied OR candidacy OR "your interest") '
               '-category:promotions -from:jobalerts-noreply@linkedin.com -from:jobs-noreply@linkedin.com')

REJECTION = re.compile(
    r"(unfortunately|regret to inform|not (?:to )?(?:proceed|move forward|moving forward)|"
    r"(?:won't|will not|unable to|not be able to) (?:be )?(?:move|moving|proceed|proceeding)(?: you)? forward|"
    r"decided to (?:move forward|proceed|pursue|go) with (?:another|other)|"
    r"no longer (?:being )?(?:considered|under consideration)|position has been filled|"
    r"(?:were|was|have) not (?:been )?selected|not a match at this time)", re.I)
CONFIRMATION = re.compile(
    r"(thank you for (?:applying|your (?:recent )?application|submitting)|thanks for applying|"
    r"(?:we(?:'ve| have)|has been) received(?: your application)?|application (?:received|confirmation|submitted)|"
    r"your application (?:to|for|has been|was) (?:sent|received|submitted|successfully)|we received your application)",
    re.I)
NOT_JOBS = re.compile(r"(security code|verification code|verify your|incomplete (?:job )?application|"
                      r"loan|credit|mortgage|apartment|lease|rental|visa application|passport|"
                      r"grant application|scholarship|admissions?|financial aid)", re.I)
JOB_CONTEXT = re.compile(r"\b(position|role|opening|candidacy|candidate|requisition|hiring team|recruit\w*|"
                         r"talent acquisition|job)\b", re.I)

_SUBJECT_PATTERNS = [
    # "Information about your application to Civis Analytics - Applied Data Scientist (Contract)"
    re.compile(r"application (?:to|with|at) (?P<org>.+?)\s+[-–|:]\s+(?P<role>.+)$", re.I),
    # "Application for Data Analyst I, Analytics Reporting - Khan Academy"
    re.compile(r"application for (?:the )?(?P<role>.+?)\s+[-–|]\s+(?P<org>[^-–|]+)$", re.I),
    # "Thank you for applying to Recidiviz", "... at RTI International", "your application was sent to X"
    re.compile(r"(?:applying|application|interest|sent)\s+(?:to|at|with|in)\s+(?:the\s+)?(?P<org>[^-–|:!,]+?)"
               r"(?:\s*[-–|:]\s*(?P<role>.+?))?[!.]?$", re.I),
    # "Data Analyst - Zearn"
    re.compile(r"^(?P<role>[^-–|]{3,80}?)\s+[-–|]\s+(?P<org>[^-–|]{2,60})$", re.I),
]
_BODY_ROLE = re.compile(
    r"(?:application|candidacy|applying|applied|interest)\s+(?:to|for|in)\s+(?:the\s+|our\s+)?"
    r"(?P<role>[A-Z][^.\n]{2,90}?)\s+(?:position|role|opening|job|posting)\b")
_BODY_ORG = re.compile(r"\b(?:opening|position|role) (?:at|with) (?P<org>[A-Z][\w&.' ]{1,60}?)[.,!]")
_GENERIC_SENDER = re.compile(r"(no-?reply|do-?not-?reply|careers?|jobs?|recruit\w*|talent|hiring|team|"
                             r"greenhouse|workday|lever|icims|ashby|smartrecruiters|notifications?|hr|people)",
                             re.I)
_GENERIC_WORDS = {"the", "of", "and", "for", "at", "inc", "llc", "co", "team", "careers", "university",
                  "college", "school", "institute", "foundation", "group", "international", "recruiting"}


@dataclass
class Message:
    message_id: str
    sent: date
    subject: str
    sender_name: str
    sender_address: str
    body: str


def classify(subject: str, body: str) -> str | None:
    """'rejection', 'confirmation', or None for anything that isn't about a job application."""
    text = f"{subject}\n{body}"
    if NOT_JOBS.search(subject) or not JOB_CONTEXT.search(text):
        return None
    if REJECTION.search(body):
        return "rejection"
    if CONFIRMATION.search(text):
        return "confirmation"
    return None


def _clean(text: str | None) -> str:
    text = re.sub(r"\s+", " ", text or "").strip(" -–|:!.,")
    return re.sub(r"^(?:fwd?|re):\s*", "", text, flags=re.I)


def extract(subject: str, body: str, sender_name: str = "") -> tuple[str | None, str | None]:
    """Best guess at (organization, role) from the subject, then the body, then the sender."""
    subject = _clean(re.sub(r"^(?:fwd?|re):\s*", "", subject or "", flags=re.I))
    subject = re.sub(r"^\w+,\s+", "", subject)  # "Deval, your application was sent to X"
    org = role = None
    for pattern in _SUBJECT_PATTERNS:
        m = pattern.search(subject)
        if m:
            org, role = _clean(m.group("org")), _clean(m.groupdict().get("role"))
            break
    if org and re.fullmatch(r"(?i)(?:you|us|our team|the team)", org):
        org = None
    if role and re.search(r"(?i)\b(remote|anywhere|usa|united states|hybrid)\b|,\s*[A-Z]{2}$", role):
        role = None  # "Thank you for applying at PNNL - Anywhere, USA": that's a location
    if not role:
        m = _BODY_ROLE.search(body or "")
        role = _clean(m.group("role")) if m else None
    if not org:
        m = _BODY_ORG.search(body or "")
        org = _clean(m.group("org")) if m else None
    if not org and sender_name and not _GENERIC_SENDER.search(sender_name):
        org = _clean(sender_name)
    return org or None, role or None


def _words(name: str | None) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (name or "").lower())) - _GENERIC_WORDS


def _decode(value: str | None) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except (ValueError, LookupError):
        return value or ""


def parse_raw(raw: bytes) -> Message:
    msg = email.message_from_bytes(raw, policy=default_policy)
    part = msg.get_body(preferencelist=("plain", "html"))
    body = part.get_content() if part is not None else ""
    if part is not None and part.get_content_type() == "text/html":
        body = re.sub(r"<[^>]+>", " ", body)
    name, address = parseaddr(_decode(msg.get("From")))
    try:
        sent = parsedate_to_datetime(msg.get("Date")).date()
    except (TypeError, ValueError):
        sent = date.today()
    return Message(message_id=(msg.get("Message-ID") or "").strip(), sent=sent, subject=_decode(msg.get("Subject")),
                   sender_name=name, sender_address=address, body=body)


def fetch_messages(address: str, password: str, days: int = 14) -> list[Message]:
    """Candidate emails from the last `days` days. Read-only; messages stay unread."""
    imap = imaplib.IMAP4_SSL("imap.gmail.com", timeout=60)
    try:
        imap.login(address, password)
        status, _ = imap.select('"[Gmail]/All Mail"', readonly=True)
        if status != "OK":
            imap.select("INBOX", readonly=True)
        query = f"{GMAIL_QUERY} newer_than:{int(days)}d"
        status, data = imap.search(None, "X-GM-RAW", f'"{query}"')
        ids = data[0].split() if status == "OK" and data and data[0] else []
        messages = []
        for msg_id in ids:
            status, parts = imap.fetch(msg_id, "(BODY.PEEK[])")
            for item in parts or []:
                if isinstance(item, tuple):
                    messages.append(parse_raw(item[1]))
        return messages
    finally:
        try:
            imap.logout()
        except Exception:  # already disconnected
            pass


def _ensure_table(db: sqlite3.Connection) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS email_imports (message_id TEXT PRIMARY KEY, processed_date TEXT)")


def _find_org(db: sqlite3.Connection, name: str):
    row = db.execute("SELECT id FROM orgs WHERE lower(name) = lower(?)", (name,)).fetchone()
    if row:
        return row[0]
    target = _words(name)
    if not target:
        return None
    for org_id, org_name in db.execute("SELECT id, name FROM orgs").fetchall():
        words = _words(org_name)
        if words and (words <= target or target <= words):
            return org_id
    return None


def _find_application(db: sqlite3.Connection, org_id: int, role: str | None):
    rows = db.execute("SELECT id, role_title, status FROM applications WHERE org_id = ? ORDER BY date_applied DESC",
                      (org_id,)).fetchall()
    if role:
        for app_id, title, status in rows:
            if _words(title) == _words(role) or _words(role) <= _words(title) or _words(title) <= _words(role):
                return app_id, status
    # Without a role, a single open application at that org is the one meant.
    open_rows = [r for r in rows if r[2] not in ("Rejected by Org", "Rejected Offer", "Accepted")]
    if not role and len(open_rows) == 1:
        return open_rows[0][0], open_rows[0][2]
    return None


def apply_messages(db: sqlite3.Connection, messages: list[Message], dry_run: bool = False,
                   own_address: str = "") -> list[str]:
    """Write what the emails show into the tracker. Returns one line per change, for display."""
    _ensure_table(db)
    done = {r[0] for r in db.execute("SELECT message_id FROM email_imports").fetchall()}
    changes = []
    for msg in sorted(messages, key=lambda m: m.sent):
        if msg.message_id and msg.message_id in done:
            continue
        mine = own_address and msg.sender_address.lower() == own_address.lower()
        kind = None if mine else classify(msg.subject, msg.body)  # skip emails you sent yourself
        org_name, role = extract(msg.subject, msg.body, msg.sender_name) if kind else (None, None)
        if kind and org_name:
            role_title = role or "Role not stated in email"
            org_id = _find_org(db, org_name)
            if org_id is None:
                changes.append(f"New organization: {org_name}")
                if not dry_run:
                    org_id = db.execute("INSERT INTO orgs (name, notes) VALUES (?, ?)",
                                        (org_name, f"Added from an application email on {msg.sent}.")).lastrowid
            found = _find_application(db, org_id, role) if org_id else None
            if kind == "confirmation" and not found:
                changes.append(f"Applied: {org_name} — {role_title} ({msg.sent})")
                if not dry_run:
                    db.execute(
                        "INSERT INTO applications (org_id, role_title, date_applied, status, follow_up_date, notes) "
                        "VALUES (?, ?, ?, 'Applied', ?, ?)",
                        (org_id, role_title, msg.sent.isoformat(),
                         (msg.sent + timedelta(days=FOLLOW_UP_DAYS)).isoformat(),
                         f"Logged from confirmation email: {msg.subject}"))
            elif kind == "rejection":
                if found and found[1] in ("Rejected by Org",):
                    pass
                elif found:
                    changes.append(f"Rejected: {org_name} — {role_title} ({msg.sent})")
                    if not dry_run:
                        db.execute("UPDATE applications SET status = 'Rejected by Org', follow_up_date = NULL, "
                                   "notes = trim(coalesce(notes, '') || ' Rejection email ' || ?) WHERE id = ?",
                                   (msg.sent.isoformat(), found[0]))
                else:
                    changes.append(f"Rejected (application not logged before): {org_name} — {role_title} ({msg.sent})")
                    if not dry_run:
                        db.execute(
                            "INSERT INTO applications (org_id, role_title, date_applied, status, notes) "
                            "VALUES (?, ?, ?, 'Rejected by Org', ?)",
                            (org_id, role_title, msg.sent.isoformat(),
                             f"Logged from rejection email: {msg.subject}. Date applied unknown; this is the rejection date."))
        if not dry_run and msg.message_id:
            db.execute("INSERT OR IGNORE INTO email_imports (message_id, processed_date) VALUES (?, ?)",
                       (msg.message_id, date.today().isoformat()))
    if not dry_run:
        db.commit()
    return changes


def run(db: sqlite3.Connection, days: int = 14, dry_run: bool = False) -> list[str]:
    address, password = os.environ.get("GMAIL_ADDRESS"), os.environ.get("GMAIL_APP_PASSWORD")
    if not address or not password:
        raise RuntimeError("Add GMAIL_ADDRESS and GMAIL_APP_PASSWORD to your .env to check email.")
    return apply_messages(db, fetch_messages(address, password, days), dry_run=dry_run, own_address=address)
