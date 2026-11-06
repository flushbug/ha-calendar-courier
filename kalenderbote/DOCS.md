# Kalenderbote

Der Kalenderbote liest Termineinladungen aus einem eigenen Postfach und trägt sie in
einen CalDAV-Kalender (z. B. Nextcloud) ein. Verschiebungen und Absagen aus Outlook
werden automatisch nachgezogen. So landen auf dem Wohnzimmer-Display nur die Termine,
zu denen ihr den Familienkalender eingeladen habt – private Termine bleiben privat.

## Einrichtung
1. In Nextcloud einen Benutzer (z. B. `familie`) mit einem Kalender anlegen und ein
   App-Passwort erzeugen.
2. Ein Postfach mit IMAP-Zugang per Passwort für die Familienadresse einrichten
   (Outlook.com/Microsoft 365 funktionieren nicht, da dort nur OAuth erlaubt ist).
3. Die Optionen ausfüllen. Bei `allowed_senders` eure eigenen Adressen eintragen.
4. Add-on starten und im Log prüfen.

Die Kalender-URL findest du in Nextcloud unter Kalender → ⋯ → „Interne Adresse kopieren“,
z. B. `https://cloud.example.de/remote.php/dav/calendars/familie/familie/`.
Ist die URL falsch, listet das Add-on beim Start alle gefundenen Kalender im Log auf.

## Verhalten
| Mail aus Outlook | Ergebnis im Familienkalender |
|---|---|
| Neue Einladung | Termin wird angelegt (Teilnahme „angenommen“) |
| Geänderte Einladung | Termin wird aktualisiert, ältere Mails werden ignoriert |
| Absage | Termin wird gelöscht |
| Absage eines Serientermins | nur dieser eine Termin entfällt |

Es wird keine Antwort an den Organisator gesendet. Ändern oder absagen kann nur, wer den
Termin angelegt hat.

## Optionen
| Option | Bedeutung |
|---|---|
| `imap_host`, `imap_port` | Mailserver des Familien-Postfachs (Port meist 993) |
| `imap_user`, `imap_password` | Zugangsdaten des Postfachs |
| `imap_folder` | Ordner, in dem die Einladungen ankommen (Standard `INBOX`) |
| `processed_folder` | optional: verarbeitete Mails hierhin verschieben |
| `caldav_url` | URL des Zielkalenders |
| `caldav_user`, `caldav_password` | CalDAV-Zugang (am besten App-Passwort) |
| `allowed_senders` | nur Einladungen dieser Absender werden übernommen |
| `poll_interval` | Abfrageintervall in Sekunden |
| `log_level` | `debug`, `info`, `warning` oder `error` |
