# infrastructure/config/legal.py
"""
Bedrijfsgegevens van de Indiqa-aanbieder zelf (niet van een hovenier-tenant).
Gebruikt in de Algemene Voorwaarden en de Verwerkersovereenkomst.

LET OP: onderstaande waarden zijn placeholders. Vul ze in met de echte
gegevens van de entiteit waaronder Indiqa wordt verkocht voordat een
betalende klant zich hierop kan beroepen, en laat de teksten door een
jurist controleren.
"""

INDIQA_BEDRIJFSNAAM      = "[bedrijfsnaam Indiqa-aanbieder]"
INDIQA_KVK                = "[KVK-nummer]"
INDIQA_VESTIGINGSPLAATS   = "[vestigingsplaats]"
INDIQA_ADRES              = "[straat, postcode en plaats]"
INDIQA_CONTACT_EMAIL      = "info@indiqa.nl"

HOSTING_PARTIJ            = "[hostingpartij, bijv. Hetzner Online GmbH — Duitsland]"
EMAIL_PARTIJ              = "Brevo SAS — Frankrijk (EU)"

# Versiedatum van de juridische documenten. Wordt getoond in de teksten en
# vastgelegd bij elke acceptatie, zodat later te herleiden is welke versie
# een klant heeft geaccepteerd.
TERMS_VERSION = "2026-07-20"
