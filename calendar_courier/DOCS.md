# Calendar Courier

Calendar Courier reads meeting invitations from a dedicated mailbox and adds them to a
CalDAV calendar (e.g. Nextcloud). Reschedules and cancellations sent from Outlook or any
other calendar app are applied automatically. Only events the shared calendar was invited
to end up there – private events stay private.

## Setup
1. Create a Nextcloud user (e.g. `family`) with a calendar and generate an app password.
2. Set up a mailbox for the shared address with IMAP password login
   (Outlook.com / Microsoft 365 mailboxes don't work, they only allow OAuth).
3. Fill in the options. Put your own addresses into `allowed_senders`.
4. Start the add-on and check the log.

In Nextcloud you find the calendar URL under Calendar → ⋯ → "Copy internal link",
e.g. `https://cloud.example.com/remote.php/dav/calendars/family/family/`.
If the URL is wrong, the add-on lists all calendars it can find in the log on startup.

## Behaviour
| Mail from the organizer | Result in the shared calendar |
|---|---|
| New invitation | Event is created (attendance "accepted") |
| Updated invitation | Event is updated, older mails are ignored |
| Cancellation | Event is deleted |
| Cancellation of one occurrence | Only that occurrence is removed |

No reply is sent to the organizer. Only the organizer of an event can change or cancel it.

## Options
| Option | Meaning |
|---|---|
| `imap_host`, `imap_port` | Mail server of the mailbox (port usually 993) |
| `imap_user`, `imap_password` | Mailbox credentials |
| `imap_folder` | Folder where invitations arrive (default `INBOX`) |
| `processed_folder` | Optional: move processed mails here |
| `caldav_url` | URL of the target calendar |
| `caldav_user`, `caldav_password` | CalDAV credentials (an app password is recommended) |
| `allowed_senders` | Only invitations from these senders are accepted |
| `poll_interval` | Polling interval in seconds |
| `log_level` | `debug`, `info`, `warning` or `error` |
