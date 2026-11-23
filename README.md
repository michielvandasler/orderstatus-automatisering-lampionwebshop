# Lampionwebshop orderstatus-automatisering

Zet in CCV Shop ([lampionwebshop.nl](https://www.lampionwebshop.nl)) automatisch elke order met status **"Nieuw" (1)** die **betaald** is en **maximaal 32 dagen** oud is, over op **"In behandeling" (2)**. Oudere orders worden overgeslagen.

Draait via GitHub Actions (openbare repository = onbeperkt gratis Actions-minuten). Bij de statuswijziging wordt de klant niet gemaild (de API-standaard `mail: false` blijft).

## Eenmalige installatie

1. Deze repository staat op **Public**: daarmee zijn de Actions-minuten onbeperkt gratis.
2. Koppel het environment: *Settings → Environments → New environment* → naam `orderstatus-automatisering`.
3. Voeg onder dit environment toe (*Environment secrets* en *Environment variables*):
   - Secrets: `CCV_API_KEY` = je API key uit CCV Shop (Mijn Webshop → Instellingen → API gegevens) en `CCV_API_SECRET` = je API secret. De API key heeft lees- en schrijfrechten op orders nodig.
   - Variable: `CCV_SHOP_URL` = `https://www.lampionwebshop.nl`
4. **Dry-run (gedaan):** ga naar *Actions → Orderstatus automatisering → Run workflow* en vink **dry_run** aan. Het script toont dan alleen welke orders op "In behandeling" gezet zouden worden, zonder iets te wijzigen en zonder mail te versturen.
5. **Schema:** het script draait automatisch om de 10 minuten (6× per uur). De frequentie pas je aan, zie tabel hieronder.

## Schema aanpassen

Pas de cron-regel in `.github/workflows/update-order-status.yml` aan. Elke run rekent minimaal 1 minuut als de repository privé staat; openbaar is het onbeperkt gratis:

| Interval | Cron | Runs/dag | Minuten/maand |
|---|---|---|---|
| Elke 5 minuten | `*/5 * * * *` | 288 | ± 8.700 |
| Elke 10 minuten (standaard hier) | `*/10 * * * *` | 144 | ± 4.400 |
| Elke 15 minuten | `*/15 * * * *` | 96 | ± 2.900 |
| Elk uur | `5 * * * *` | 24 | ± 730 |

Let op: GitHub zet schedules automatisch uit na 60 dagen zonder commits in de repository; een commit reset dit.

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
