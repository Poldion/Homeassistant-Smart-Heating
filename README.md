# Smart Heating – Home Assistant Blueprint

Ein Automations-Blueprint, der die Heizung pro Raum anhand von **Bewegung**,
**Türstatus**, **Anwesenheit** und **Bettsensor** steuert.

[![Blueprint importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fpoldion%2Fhomeassistant-smart-heating%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fsmart_heating%2Froom_heating.yaml)

Benötigt Home Assistant **2024.10** oder neuer.

## Mehrere Räume

Blueprint-Eingaben sind in Home Assistant fest, eine dynamische Raumliste ist
dort nicht möglich. Deshalb legst du **pro Raum eine Automation** aus diesem
Blueprint an (*Einstellungen → Automationen → Blueprints → „Smart Heating –
Raumsteuerung“ → Automation erstellen*). Jede Raum-Automation bekommt eigene
Thermostate, Bewegungsmelder, Türsensoren und Temperaturen.

Anwesenheit und Bettsensor wählst du in jeder Raum-Automation gleich aus.
So wird bei Abwesenheit oder im Nachtmodus das ganze Haus abgesenkt.

## Logik

Bei jedem relevanten Ereignis wird der Sollzustand des Raums neu berechnet.
Die erste zutreffende Regel gewinnt:

| Priorität | Bedingung | Ergebnis |
|---|---|---|
| 1 | Bett im Zeitfenster länger als *Einschlaf-Verzögerung* belegt | Heizung **aus** oder **Nachttemperatur** |
| 2 | Keine Person länger als *Abwesenheits-Verzögerung* in einer der *Zuhause-Zonen* | **Abwesenheitstemperatur** |
| 3 | Eine Tür länger als *Tür-offen-Verzögerung* offen | **Absenktemperatur** |
| 4 | Bewegung erkannt oder innerhalb der *Nachlaufzeit* | **Komforttemperatur** |
| 5 | sonst | **Absenktemperatur** |

Weitere Details:

- **Nachlaufzeit:** Fällt ein Bewegungsmelder kurz auf „keine Bewegung“ zurück,
  bleibt die Komforttemperatur trotzdem bis zum Ende der Nachlaufzeit aktiv.
- **Tür:** Kurzes Öffnen wird ignoriert. Erst nach der eingestellten Zeit
  wird abgesenkt. Ist die Tür wieder zu und es gibt Bewegung, geht es zurück
  auf Komfort.
- **Zuhause-Zonen:** Du wählst, welche Zonen als „zu Hause“ zählen (Standard:
  `zone.home`). Legst du z. B. eine Zone „Umgebung“ mit 2–3 km Radius an und
  wählst sie aus, senkt kurzes Einkaufen nichts ab. Geprüft wird per GPS-Abstand
  zum Zonenmittelpunkt. So zählen auch verschachtelte Zonen (z. B. „Supermarkt“
  innerhalb von „Umgebung“), die Home Assistant selbst nicht mitzählt. Der Zustand
  `home` gilt immer als zu Hause (z. B. für reine WLAN-Tracker ohne GPS).
  Die Abwesenheits-Verzögerung zählt ab dem Verlassen der letzten Zone.
  Kommt jemand zurück in eine Zone, wird sofort wieder normal geregelt.
- **Bett-Zeitfenster:** Der Nachtmodus greift nur im eingestellten Zeitfenster
  (z. B. 21:00–09:00). Ein Mittagsschlaf schaltet also nichts ab. Beginn = Ende
  bedeutet „immer“. Bei Fensterbeginn bzw. -ende wird neu ausgewertet.
- **Aufsteh-Verzögerung:** Kurzes Aufstehen (Toilette) beendet den Nachtmodus
  nicht sofort.
- **Mehrere Betten:** Optional startet der Nachtmodus erst, wenn *alle* Betten
  belegt sind.
- **Freigabe-Schalter:** Optional, z. B. ein `input_boolean.heizperiode`. Ist er
  aus, lässt die Automation die Thermostate in Ruhe.
- Thermostate werden nur angesprochen, wenn sich der Sollwert ändert. Ein
  ausgeschaltetes Thermostat wird mit dem gewählten HVAC-Modus (Standard
  `heat`) wieder eingeschaltet.
- Unbekannte oder nicht verfügbare Anwesenheitszustände gelten als „zu Hause“.
  Bei einem Ausfall wird also nicht versehentlich abgesenkt.

## Tests

Die Tests starten eine echte Home-Assistant-Testinstanz und spielen die
Szenarien mit simulierter Zeit durch:

```bash
pip install -r requirements_test.txt
pytest
```
