#!/usr/bin/env python3
"""Calendar Courier – iMIP invitations to CalDAV.

Reads meeting invitations (iMIP, RFC 6047) from an IMAP mailbox and
mirrors them into a CalDAV calendar:
  REQUEST  -> create or update the event (only if SEQUENCE is not older)
  CANCEL   -> delete the event or a single occurrence of a series
"""

import email
import hashlib
import re
import email.policy
import imaplib
import json
import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote
from email.utils import parseaddr

import caldav
from icalendar import Calendar

OPTIONS_FILE = "/data/options.json"
STATE_FILE = "/data/state.json"
SEARCH_DAYS = 30          # how far back mails are considered
STATE_KEEP_DAYS = 90      # how long processed mails are remembered
MAX_FAILURES = 3          # a broken mail is skipped after this many attempts
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

log = logging.getLogger("imip")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_state(state):
    cutoff = time.time() - STATE_KEEP_DAYS * 86400
    for key in [k for k, v in state.items() if v < cutoff]:
        del state[key]
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def addr(value):
    return str(value or "").lower().replace("mailto:", "").strip()


def seq(comp):
    try:
        return int(comp.get("SEQUENCE", 0))
    except (TypeError, ValueError):
        return 0


def rid_key(comp):
    """Comparable key of the RECURRENCE-ID (None = master event)."""
    rid = comp.get("RECURRENCE-ID")
    if rid is None:
        return None
    dt = rid.dt
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return dt.strftime("%Y%m%dT%H%M%S")
    return dt.strftime("%Y%m%d")


def prop_bytes(comp, name):
    value = comp.get(name)
    return value.to_ical() if value is not None else None


def series_changed(old, new):
    return (prop_bytes(old, "DTSTART") != prop_bytes(new, "DTSTART")
            or prop_bytes(old, "RRULE") != prop_bytes(new, "RRULE"))


def summary(comp):
    start = comp.get("DTSTART")
    return "'%s' (%s)" % (comp.get("SUMMARY", "untitled"),
                          start.dt if start is not None else "?")


def mark_accepted(comp, own_addr):
    """Marks the calendar's own attendee entry as accepted."""
    if "@" not in own_addr:
        return
    attendees = comp.get("ATTENDEE")
    if attendees is None:
        return
    if not isinstance(attendees, list):
        attendees = [attendees]
    for attendee in attendees:
        if addr(attendee) == own_addr:
            attendee.params["PARTSTAT"] = "ACCEPTED"
            attendee.params.pop("RSVP", None)


def new_calendar():
    cal = Calendar()
    cal.add("prodid", "-//Calendar Courier//EN")
    cal.add("version", "2.0")
    return cal


def imap_date(d):
    return "%02d-%s-%d" % (d.day, MONTHS[d.month - 1], d.year)


def extract_calendar(msg):
    """Returns the first iCalendar part with a METHOD (the actual invitation)."""
    for part in msg.walk():
        ctype = part.get_content_type()
        fname = (part.get_filename() or "").lower()
        if ctype not in ("text/calendar", "application/ics") and not fname.endswith(".ics"):
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        try:
            cal = Calendar.from_ical(payload)
        except Exception as err:  # noqa: BLE001
            log.warning("Unreadable iCalendar part: %s", err)
            continue
        if cal.get("METHOD"):
            return cal
    return None


# --------------------------------------------------------------------------
# CalDAV operations
# --------------------------------------------------------------------------

class CalendarError(RuntimeError):
    pass


class StoredEvent:
    def __init__(self, store, url, data):
        self.store, self.url, self.data = store, url, data

    def save(self):
        self.store.put_url(self.url, self.data)

    def delete(self):
        self.store.delete_url(self.url)


class CalStore:
    """Events are stored at <calendar-url>/<UID>.ics, so no REPORT query is
    needed, only plain GET/PUT/DELETE."""

    def __init__(self, client, url):
        self.client = client
        self.base = url if url.endswith("/") else url + "/"

    def url_for(self, uid):
        if re.fullmatch(r"[A-Za-z0-9._@-]{1,200}", uid):
            name = uid
        else:
            name = hashlib.sha1(uid.encode()).hexdigest()
        return self.base + quote(name) + ".ics"

    def _check(self, resp, what):
        if resp.status not in (200, 201, 204):
            raise CalendarError("%s failed: HTTP %s %s"
                                % (what, resp.status, str(resp.raw)[:300]))

    def get(self, uid):
        url = self.url_for(uid)
        resp = self.client.request(url, "GET")
        if resp.status == 404:
            return None
        self._check(resp, "Read")
        data = resp.raw if isinstance(resp.raw, str) else resp.raw.decode()
        return StoredEvent(self, url, data)

    def put(self, uid, ical):
        self.put_url(self.url_for(uid), ical)

    def put_url(self, url, ical):
        resp = self.client.put(url, ical.encode(),
                               {"Content-Type": "text/calendar; charset=utf-8"})
        self._check(resp, "Save")

    def delete_url(self, url):
        resp = self.client.delete(url)
        if resp.status != 404:
            self._check(resp, "Delete")


def check_calendar(client, url):
    """Checks on startup that the URL is a calendar; otherwise logs hints."""
    try:
        comps = caldav.Calendar(client=client, url=url).get_supported_components()
        if "VEVENT" in comps:
            return True
    except Exception as err:  # noqa: BLE001
        log.debug("Calendar check: %s", err)
    log.error("caldav_url is not a calendar: %s", url)
    try:
        for cal in client.principal().calendars():
            log.error("  Found calendar: %s  ->  %s", cal.name, cal.url)
        log.error("Please use one of the URLs above as caldav_url.")
    except Exception as err:  # noqa: BLE001
        log.error("Could not list calendars: %s", err)
    return False


def find_event(calendar, uid):
    return calendar.get(uid)


def apply_request(calendar, uid, comps, tzs, own_addr):
    for comp in comps:
        mark_accepted(comp, own_addr)

    existing = find_event(calendar, uid)
    if existing is None:
        cal = new_calendar()
        for tz in tzs:
            cal.add_component(tz)
        for comp in comps:
            cal.add_component(comp)
        calendar.put(uid, cal.to_ical().decode())
        log.info("Created: %s", summary(comps[0]))
        return

    stored = Calendar.from_ical(existing.data)
    stored.pop("METHOD", None)
    changed = False

    for inc in comps:  # master event comes first (see process_message)
        key = rid_key(inc)
        events = [c for c in stored.subcomponents if c.name == "VEVENT"]
        cur = next((e for e in events if rid_key(e) == key), None)

        if cur is not None and seq(inc) < seq(cur):
            log.info("Ignored outdated invitation: %s", summary(inc))
            continue

        if key is None and cur is not None and series_changed(cur, inc):
            # series pattern changed -> old exceptions are invalid (Outlook drops them too)
            stored.subcomponents = [c for c in stored.subcomponents
                                    if not (c.name == "VEVENT" and rid_key(c) is not None)]

        if cur is not None and any(c is cur for c in stored.subcomponents):
            idx = next(i for i, c in enumerate(stored.subcomponents) if c is cur)
            stored.subcomponents[idx] = inc
        else:
            stored.add_component(inc)
        changed = True
        log.info("Updated: %s", summary(inc))

    known_tz = {str(c.get("TZID")) for c in stored.subcomponents if c.name == "VTIMEZONE"}
    for tz in tzs:
        if str(tz.get("TZID")) not in known_tz:
            stored.subcomponents.insert(0, tz)
            changed = True

    if changed:
        existing.data = stored.to_ical().decode()
        existing.save()


def apply_cancel(calendar, uid, comps):
    existing = find_event(calendar, uid)
    if existing is None:
        log.info("Cancellation for unknown event %s – nothing to do", uid)
        return

    if any(rid_key(c) is None for c in comps):
        existing.delete()
        log.info("Deleted: %s", summary(comps[0]))
        return

    stored = Calendar.from_ical(existing.data)
    stored.pop("METHOD", None)
    master = next((c for c in stored.subcomponents
                   if c.name == "VEVENT" and rid_key(c) is None), None)

    for comp in comps:
        key = rid_key(comp)
        stored.subcomponents = [c for c in stored.subcomponents
                                if not (c.name == "VEVENT" and rid_key(c) == key)]
        if master is not None:
            master.add("EXDATE", comp["RECURRENCE-ID"].dt)
        log.info("Occurrence cancelled: %s", summary(comp))

    if not any(c.name == "VEVENT" for c in stored.subcomponents):
        existing.delete()
    else:
        existing.data = stored.to_ical().decode()
        existing.save()


# --------------------------------------------------------------------------
# Mail processing
# --------------------------------------------------------------------------

def process_message(raw, calendar, opts):
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    sender = addr(parseaddr(str(msg.get("From", "")))[1])
    cal = extract_calendar(msg)
    if cal is None:
        log.debug("Mail from %s contains no invitation", sender)
        return

    method = str(cal.get("METHOD")).upper()
    tzs = [c for c in cal.subcomponents if c.name == "VTIMEZONE"]
    allowed = {addr(a) for a in opts.get("allowed_senders") or []}
    own_addr = addr(opts.get("imap_user"))

    by_uid = {}
    for comp in cal.subcomponents:
        if comp.name == "VEVENT" and comp.get("UID"):
            by_uid.setdefault(str(comp.get("UID")), []).append(comp)

    for uid, comps in by_uid.items():
        if allowed and sender not in allowed:
            log.warning("Invitation from %s not allowed – ignored", sender)
            continue
        comps.sort(key=lambda c: rid_key(c) is not None)  # master event first

        if method in ("REQUEST", "PUBLISH", "ADD"):
            active, cancelled = [], []
            for comp in comps:
                (cancelled if str(comp.get("STATUS", "")).upper() == "CANCELLED"
                 else active).append(comp)
            if active:
                apply_request(calendar, uid, active, tzs, own_addr)
            if cancelled:
                apply_cancel(calendar, uid, cancelled)
        elif method == "CANCEL":
            apply_cancel(calendar, uid, comps)
        else:
            log.debug("Method %s ignored (%s)", method, uid)


def run_once(opts, state, failures):
    client = caldav.DAVClient(url=opts["caldav_url"],
                              username=opts["caldav_user"],
                              password=opts["caldav_password"])
    if not check_calendar(client, opts["caldav_url"]):
        return
    calendar = CalStore(client, opts["caldav_url"])

    folder = opts.get("imap_folder") or "INBOX"
    processed = opts.get("processed_folder")
    imap = imaplib.IMAP4_SSL(opts["imap_host"], int(opts.get("imap_port", 993)))
    try:
        imap.login(opts["imap_user"], opts["imap_password"])
        typ, _ = imap.select('"%s"' % folder)
        if typ != "OK":
            raise RuntimeError("Folder %s not found" % folder)
        uidvalidity = (imap.response("UIDVALIDITY")[1] or [b"0"])[0].decode()

        since = imap_date(date.today() - timedelta(days=SEARCH_DAYS))
        _, data = imap.uid("SEARCH", None, "SINCE", since)
        moved = False

        for uid in (data[0] or b"").split():
            key = "%s:%s:%s" % (folder, uidvalidity, uid.decode())
            if key in state:
                continue
            _, msgdata = imap.uid("FETCH", uid, "(BODY.PEEK[])")
            raw = next((p[1] for p in msgdata if isinstance(p, tuple)), None)
            if raw is None:
                continue
            try:
                process_message(raw, calendar, opts)
            except (CalendarError, caldav.lib.error.DAVError, OSError):
                # server/connection problem: never skip the mail, retry later
                log.exception("Calendar server error for mail %s – retrying next run", key)
                break
            except Exception:  # noqa: BLE001
                failures[key] = failures.get(key, 0) + 1
                log.exception("Error processing mail %s (attempt %d)", key, failures[key])
                if failures[key] < MAX_FAILURES:
                    break  # keep order, retry next run
                log.error("Skipping mail %s after %d failed attempts", key, MAX_FAILURES)

            state[key] = time.time()
            save_state(state)
            imap.uid("STORE", uid, "+FLAGS", "(\\Seen)")
            if processed:
                typ, _ = imap.uid("COPY", uid, '"%s"' % processed)
                if typ == "OK":
                    imap.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
                    moved = True
                else:
                    log.warning("Moving to %s failed", processed)

        if moved:
            imap.expunge()
    finally:
        try:
            imap.logout()
        except Exception:  # noqa: BLE001
            pass


def main():
    opts = load_json(OPTIONS_FILE, {})
    logging.basicConfig(
        level=getattr(logging, str(opts.get("log_level", "info")).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    # caldav logs harmless deviations (e.g. HTML body on 404) as warnings
    logging.getLogger("caldav").setLevel(logging.ERROR)
    if not opts.get("allowed_senders"):
        log.warning("No allowed senders configured – EVERY invitation will be accepted!")

    state = load_json(STATE_FILE, {})
    failures = {}
    interval = int(opts.get("poll_interval", 120))
    log.info("Calendar Courier started, interval %ss", interval)

    while True:
        try:
            run_once(opts, state, failures)
        except Exception:  # noqa: BLE001
            log.exception("Run failed")
        time.sleep(interval)


if __name__ == "__main__":
    main()
