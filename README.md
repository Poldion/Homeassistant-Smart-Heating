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
| 2 | Alle Personen/Tracker länger als *Abwesenheits-Verzögerung* nicht zu Hause | **Abwesenheitstemperatur** |
| 3 | Eine Tür länger als *Tür-offen-Verzögerung* offen | **Absenktemperatur** |
| 4 | Bewegung erkannt oder innerhalb der *Nachlaufzeit* | **Komforttemperatur** |
| 5 | sonst | **Absenktemperatur** |

Weitere Details:

- **Nachlaufzeit:** Fällt ein Bewegungsmelder kurz auf „keine Bewegung“ zurück,
  bleibt die Komforttemperatur trotzdem bis zum Ende der Nachlaufzeit aktiv.
- **Tür:** Kurzes Öffnen wird ignoriert. Erst nach der eingestellten Zeit
  wird abgesenkt. Ist die Tür wieder zu und es gibt Bewegung, geht es zurück
  auf Komfort.
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
