# AZ-204-PREP-ANKI

Interactive Anki flashcards for the **Microsoft Azure Developer Associate (AZ-204)** exam.

## What's Inside

~519 interactive quiz cards across 14 domains, covering all AZ-204 exam topics.

### Card Types

| Type | Description |
|------|-------------|
| **Single-choice** | Classic 1-of-4 multiple choice |
| **Multi-select** | Pick N correct answers (checkboxes) |
| **Ordering** | Arrange steps in the correct order |
| **Code hot-area** | Click on the line(s) with errors |

### Domains

| # | Domain | Cards |
|---|--------|-------|
| 01 | App Service | ~45 |
| 02 | Azure Functions | ~45 |
| 03 | Blob Storage | ~30 |
| 04 | Cosmos DB | ~30 |
| 05 | Containers & AKS | ~45 |
| 06 | Authentication | ~35 |
| 07 | Secure Solutions | ~36 |
| 08 | API Management | ~30 |
| 09 | Event Solutions | ~30 |
| 10 | Message Solutions | ~30 |
| 11 | Caching | ~28 |
| 12 | CDN | ~25 |
| 13 | Monitoring | ~35 |
| — | Cross-domain | ~27 |

## Prerequisites

1. [Anki](https://apps.ankiweb.net/) installed and running
2. [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on installed
3. Python 3.8+

## How to Use

Push all cards to Anki:

```bash
python3 scripts/push-to-anki.py source/*/rich-cards-v2.json
```

Push a single domain:

```bash
python3 scripts/push-to-anki.py source/01-app-service/rich-cards-v2.json
```

Delete a subdeck:

```bash
python3 scripts/push-to-anki.py --delete-deck "AZ-204-PREP-ANKI::01-App Service"
```

## Deck Structure

```
AZ-204-PREP-ANKI
├── 01-App Service
├── 02-Functions
├── 03-Blob Storage
├── 04-Cosmos DB
├── 05-Containers
├── 06-Authentication
├── 07-Secure Solutions
├── 08-API Management
├── 09-Event Solutions
├── 10-Message Solutions
├── 11-Caching
├── 12-CDN
├── 13-Monitoring
└── (cross-domain cards in parent deck)
```

## Resources

- [AZ-204 Exam Page](https://learn.microsoft.com/en-us/credentials/certifications/azure-developer/)
- [Microsoft Learn — AZ-204 Path](https://learn.microsoft.com/en-us/training/paths/create-azure-app-service-web-apps/)
- [Azure Documentation](https://learn.microsoft.com/en-us/azure/)
