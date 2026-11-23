# Lampionwebshop orderstatus-automatisering

Zet in CCV Shop ([lampionwebshop.nl](https://www.lampionwebshop.nl)) automatisch elke order met status **"Nieuw" (1)** die **betaald** is en **maximaal 32 dagen** oud is, over op **"In behandeling" (2)**. Oudere orders worden overgeslagen.

Draait via GitHub Actions (gratis). Bij de statuswijziging wordt de klant niet gemaild (de API-standaard `mail: false` blijft).

## Eenmalige installatie

1. Zet deze repository op GitHub als **Private**.
2. Koppel het environment: *Settings → Environments → New environment* → naam `orderstatus-automatisering`.
3. Voeg onder dit environment toe (*Environment secrets* en *Environment variables*):
   - Secrets: `CCV_API_KEY` = je API key uit CCV Shop (Mijn Webshop → Instellingen → API gegevens) en `CCV_API_SECRET` = je API secret. De API key heeft lees- en schrijfrechten op orders nodig.
   - Variable: `CCV_SHOP_URL` = `https://www.lampionwebshop.nl`
4. **Eerst testen (dry-run):** ga naar *Actions → Orderstatus automatisering → Run workflow* en vink **dry_run** aan. Het script toont dan alleen welke orders op "In behandeling" gezet zouden worden, zonder iets te wijzigen en zonder mail te versturen.
5. **Daarna activeren:** verwijder in `.github/workflows/update-order-status.yml` de `#` bij de regels `# schedule:` en `#   - cron: "*/5 * * * *"` en commit. Het schema draait dan elke 5 minuten (12× per uur).

## Schema aanpassen

Pas de cron-regel in `.github/workflows/update-order-status.yml` aan. Op een gratis privérepo heb je 2.000 Actions-minuten per maand; elke run rekent minimaal 1 minuut:

| Interval | Cron | Runs/dag | Minuten/maand |
|---|---|---|---|
| Elke 5 minuten (standaard hier) | `*/5 * * * *` | 288 | ± 8.700 |
| Elke 15 minuten | `*/15 * * * *` | 96 | ± 2.900 |
| Elk uur | `5 * * * *` | 24 | ± 730 |

Let op: bij elke 5 of 15 minuten kom je boven de 2.000 gratis minuten per maand uit. Wil je binnen het gratis pakket blijven, kies dan het bare schema per uur. GitHub zet schedules ook automatisch uit na 60 dagen zonder commits in de repository.

## Regels

| Instelling | Waarde |
|---|---|
| Van status | 1 (Nieuw) |
| Naar status | 2 (In proces / In behandeling) |
| Voorwaarde | `paid = true` én `create_date` binnen 32 dagen |
| Filtermethode | Server-side: `status`, `min_create_date` (formaat `Y-m-d`); betaald-filter client-side op `paid` |
| E-mail naar klant | Nee (`mail` blijft op de API-standaard `false`) |
| API-limieten | Ophalen 150/min, patchen 100/min (script vertraagt automatisch) |

## Lokaal testen

```bash
CCV_SHOP_URL=https://www.lampionwebshop.nl CCV_API_KEY=... CCV_API_SECRET=... DRY_RUN=true python update_order_status.py
```

Het script gebruikt alleen de Python-standaardbibliotheek; geen dependencies.
