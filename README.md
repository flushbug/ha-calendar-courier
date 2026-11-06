# 📬📅 Kalenderbote

Ein Home-Assistant-Add-on, das Termineinladungen aus einem Postfach automatisch in einen
CalDAV-Kalender (z. B. Nextcloud) einträgt – inklusive Verschiebungen und Absagen.

Gedacht für einen Familienkalender: Jeder pflegt seinen eigenen Kalender (z. B. Microsoft 365)
und lädt einfach die Familienadresse zu gemeinsamen Terminen ein. Der Kalenderbote nimmt die
Einladung an und hält den Familienkalender aktuell, der dann z. B. auf einem Display in
Home Assistant angezeigt wird.

## Installation
[![Repository zu Home Assistant hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FFlushbug%2Fha-kalenderbote)

Oder manuell: **Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories** und
`https://github.com/Flushbug/ha-kalenderbote` hinzufügen. Danach „Kalenderbote“ installieren.

Updates erscheinen automatisch in Home Assistant, sobald die Version in
`kalenderbote/config.yaml` erhöht wurde.

Details zur Einrichtung: [kalenderbote/DOCS.md](kalenderbote/DOCS.md)

## Lizenz
MIT
