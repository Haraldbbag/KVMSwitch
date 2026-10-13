# KVM Switch

Home-Assistant-Integration, die eine USB-Matrix (z. B. SC&T HKM02B, je Empfänger eine `select`-Entität) mit einem Blackmagic Videohub (je Ausgang ein `media_player`, z. B. über `smartvideohub`) koppelt. Wird in einem Raum eine USB-Quelle gewählt, schaltet die Integration auf Wunsch die Monitore des Raums mit.

## Installation

1. HACS → Benutzerdefinierte Repositories → `Haraldbbag/kvmswitch`, Kategorie *Integration*.
2. Installieren, Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → **KVM Switch**.
4. USB-Empfänger (Select-Entitäten) und Videohub-Ausgänge (Media Player) auswählen. Unter „Ignorierte Quellen" stehen Quellnamen, die keine echten Sender sind (Standard: `Leer`).

## Entitäten

Alle Einstellungen werden sofort gespeichert (HA-Storage), es gibt keinen Speichern-Button.

| Seite | Entität | Zweck |
|---|---|---|
| Raumnamen | `text.kvmswitch_raum{1-9}_name` | Name des Raums |
| Räume | `select.kvmswitch_raum{n}_usb` | USB-Empfänger des Raums |
| Räume | `text.kvmswitch_raum{n}_monitor{1-4}_name` | Bezeichnung des Monitors, z. B. „Monitor Links" |
| Räume | `select.kvmswitch_raum{n}_monitor{1-4}_ausgang` | Videohub-Ausgang des Monitors |
| Quellen | `select.kvmswitch_quelle_<sender>_eingang{1-4}` | Videohub-Eingänge eines USB-Senders |
| Haupt | `select.kvmswitch_raum{n}_quelle` | Quelle für den Raum wählen |
| Haupt | `switch.kvmswitch_raum{n}_monitore` | Monitore mitschalten (an) oder nur USB (aus) |

Die Sender-Liste wird aus den Optionen der USB-Empfänger gelernt. Taucht ein neuer Sender auf, lädt die Integration sich neu und legt dessen Eingangs-Dropdowns an.

## Schaltlogik

Bei Auswahl einer Quelle in `select.kvmswitch_raum{n}_quelle`:

1. Der USB-Empfänger des Raums wird auf die Quelle geschaltet.
2. Ist „Monitore mitschalten" an, werden die belegten Monitor-Ausgänge des Raums der Reihe nach mit den belegten Eingängen des Senders verbunden. Mehr Monitore als Eingänge: Die übrigen Monitore bleiben unverändert. Mehr Eingänge als Monitore: Die übrigen Eingänge werden ignoriert.

Die Monitore werden nur beim Umschalten über diese Integration mitgeschaltet, nicht wenn die USB-Matrix auf anderem Weg umgeschaltet wird.
