# Changelog

## 1.3.1
- When the calendar server rejects an event, the full iCalendar data is written to the log
- A mail the server keeps rejecting (HTTP 4xx/500) is skipped after 3 attempts instead of blocking all later mails

## 1.3.0
- New option `delete_processed`: deletes valid, processed invitations from the mailbox

## 1.2.0
- Renamed to Calendar Courier, English as the default language (German translation included)

## 1.1.0
- Install and update directly from GitHub
- Harmless CalDAV warnings are no longer logged

## 1.0.2
- Events are stored via plain GET/PUT/DELETE (no REPORT query anymore)
- Calendar URL is checked on startup; found calendars are listed in the log
- Mails are never skipped because of server or connection errors

## 1.0.1
- Build fix: base image defined in the Dockerfile (new Home Assistant build system)

## 1.0.0
- Initial release
