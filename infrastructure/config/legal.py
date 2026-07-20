# infrastructure/config/legal.py
"""
Bedrijfsgegevens van de Indiqa-aanbieder zelf (niet van een hovenier-tenant).
Gebruikt in de Algemene Voorwaarden en de Verwerkersovereenkomst.

Indiqa wordt vooralsnog verkocht onder de bestaande Veldman Hoveniers-
inschrijving (nog geen aparte KVK-registratie voor Indiqa). Zodra dat
wel gebeurt, deze gegevens bijwerken en TERMS_VERSION ophogen — bestaande
klanten hebben dan de oude versie geaccepteerd, nieuwe klanten de nieuwe.

LET OP: laat de teksten sowieso door een jurist controleren voordat je
hier commercieel op leunt.
"""

INDIQA_BEDRIJFSNAAM      = "Veldman Hoveniers"
INDIQA_KVK                = "76946320"
INDIQA_VESTIGINGSPLAATS   = "Balkbrug"
INDIQA_ADRES              = "Boslaan 27, 7707 AX Balkbrug"
INDIQA_CONTACT_EMAIL      = "info@indiqa.nl"

HOSTING_PARTIJ            = "Hetzner Online GmbH — Finland (HEL1-DC8)"
EMAIL_PARTIJ              = "Brevo SAS — Frankrijk (EU)"

# Versiedatum van de juridische documenten. Wordt getoond in de teksten en
# vastgelegd bij elke acceptatie, zodat later te herleiden is welke versie
# een klant heeft geaccepteerd.
TERMS_VERSION = "2026-07-20"
