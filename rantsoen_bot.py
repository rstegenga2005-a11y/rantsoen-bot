#!/usr/bin/env python3
"""
Rantsoen Bot voor Telegram
==========================
Stuur in de groep bijv:
  hendrik 7500
  meile 10000
  meile 10500 extra 400
  droog 3000 stal1 1200

De bot rekent automatisch uit hoeveel van elk ingrediënt je nodig hebt.
"""

import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO
)

# ─── Rantsoenen (verhoudingen op basis van referentietotaal) ───────────
RANTSOENEN = {
    "hendrik": {
        "naam":  "Melkkoeien \u2014 Hendrik",
        "split": False,
        "ing": [
            ("KUIPER EASTEREIN ML",      570),
            ("Soja HP",                   267),
            ("Grote sleufsilo",          3640),
            ("Perspulp biet",             660),
            ("Snijmais Eijseiga leane",  2145),
            ("Water",                     825),
        ],
    },
    "meile": {
        "naam":  "Melkkoeien \u2014 Meile",
        "split": False,
        "ing": [
            ("KUIPER REAHUUS ML O",       755),
            ("Soja HP",                   364),
            ("Grote sleufsilo",          4963),
            ("Perspulp biet",             900),
            ("Snijmais Eijseiga leane",  2700),
            ("Water",                    1125),
        ],
    },
    "droog": {
        "naam":  "Droogstaande koeien",
        "split": True,
        "ing": [
            ("Grote sleufsilo 2025",     1354),
            ("Stro (Spaans gehamerd)",    588),
            ("Mais aankoop 2025",         974),
            ("DairyFit Droogstand",      30.6),
            ("Soja 48 gem. herkauwers",   184),
        ],
    },
}

# Korte namen die de bot herkent
ALIASSEN = {
    "hendrik": "hendrik", "henk": "hendrik", "h": "hendrik",
    "meile":   "meile",   "m":    "meile",
    "droog":   "droog",   "droge":"droog",   "d": "droog",
}

HELP = (
    "\U0001f33e *Rantsoen Bot \u2014 hoe werkt het?*\n\n"
    "Stuur de naam van de stal en het totaal aantal kg dat je wilt voeren:\n\n"
    "`hendrik 7500`\n"
    "`meile 10000`\n"
    "`droog 3000`\n\n"
    "Extra kuil voor kalveren bij Meile:\n"
    "`meile 10000 extra 400`\n\n"
    "Verdeling over stallen bij droge koeien:\n"
    "`droog 3000 stal1 1200`\n\n"
    "Kortere namen werken ook: `h`, `m`, `d`\n\n"
    "Stuur `help` voor dit bericht."
)


def fmt(n):
    """Getal netjes afronden — geen decimalen tenzij nodig."""
    r = round(n, 1)
    return str(int(r)) if r == int(r) else str(r)


def bereken(sleutel: str, totaal_kg: float, extra_kg: float = 0, stal1: int = None) -> str:
    """
    Rekent het rantsoen terug vanuit het gewenste totaal kg.
    De verhouding van de ingrediënten blijft altijd exact gelijk.
    Optioneel: extra_kg wordt proportioneel meegenomen (Meile / kalveren).
    Optioneel: stal1 geeft de verdeling voor droge koeien.
    """
    r = RANTSOENEN[sleutel]
    basis_totaal = sum(k for _, k in r["ing"])

    # Factor op basis van gewenst totaal (inclusief eventuele extra)
    gewenst = totaal_kg + extra_kg
    factor  = gewenst / basis_totaal if basis_totaal > 0 else 0

    # Ingrediënten berekenen
    max_len  = max(len(n) for n, _ in r["ing"])
    lopend   = 0
    regels   = []

    for naam, basis in r["ing"]:
        adj     = basis * factor
        lopend += adj
        pad_naam = naam.ljust(max_len)
        regels.append(
            f"  {pad_naam}  {fmt(adj):>6} kg  \u2192 {fmt(lopend):>7} kg"
        )

    lijn = "\u2500" * (max_len + 24)

    # Opbouw antwoord
    lines = [
        f"\U0001f33e *{r['naam']}*",
        f"_Totaal: {fmt(totaal_kg)} kg"
        + (f" + {fmt(extra_kg)} kg kalveren" if extra_kg > 0 else "") + "_",
        "",
        "```",
        f"  {'Ingrediënt':<{max_len}}  {'kg':>6}      {'Totaal':>8}",
        lijn,
    ]
    lines.extend(regels)
    lines += [
        lijn,
        f"  {'TOTAAL':<{max_len}}  {fmt(gewenst):>6} kg",
        "```",
    ]

    # Stalverdeling bij droge koeien
    if r["split"] and stal1 is not None:
        stal2 = max(0, round(gewenst) - stal1)
        lines += [
            "",
            "\U0001f3d7 *Verdeling stallen*",
            f"  Stal 1:  *{stal1} kg*",
            f"  Stal 2:  *{stal2} kg*",
        ]

    return "\n".join(lines)


def parse(tekst: str):
    """
    Verwerkt het ingestuurde bericht.
    Verwacht formaat:
      <stal> <totaal_kg> [extra <kg>] [stal1 <kg>]

    Voorbeelden:
      hendrik 7500
      meile 10000 extra 400
      droog 3000 stal1 1200
      d 3000 stal1 1200

    Geeft terug: (sleutel, totaal_kg, extra_kg, stal1) of None.
    """
    delen = tekst.lower().strip().split()
    if len(delen) < 2:
        return None

    sleutel = ALIASSEN.get(delen[0])
    if not sleutel:
        return None

    try:
        totaal_kg = float(delen[1].replace(",", "."))
    except ValueError:
        return None

    extra_kg = 0
    stal1    = None
    i = 2
    while i < len(delen):
        if delen[i] in ("extra", "kalveren") and i + 1 < len(delen):
            try:
                extra_kg = float(delen[i + 1].replace(",", "."))
            except ValueError:
                pass
            i += 2
        elif delen[i] in ("stal1", "stal") and i + 1 < len(delen):
            try:
                stal1 = int(delen[i + 1].replace(",", ""))
            except ValueError:
                pass
            i += 2
        else:
            i += 1

    return sleutel, totaal_kg, extra_kg, stal1


async def verwerk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verwerkt elk inkomend bericht in de groep (of privé)."""
    if not update.message or not update.message.text:
        return

    tekst = update.message.text.strip()

    # Help commando
    if tekst.lower() in ("help", "/help", "/start"):
        await update.message.reply_text(HELP, parse_mode="Markdown")
        return

    # Probeer te parsen
    resultaat = parse(tekst)
    if resultaat is None:
        # Alleen reageren als de eerste word een bekende stalnaam is
        eerste = tekst.lower().split()[0] if tekst.strip() else ""
        if eerste in ALIASSEN:
            await update.message.reply_text(
                "\u26a0\ufe0f Ik begrijp dit niet helemaal.\n\n"
                "Voorbeeld: `hendrik 7500` of `meile 10000 extra 400`\n"
                "Stuur `help` voor alle opties.",
                parse_mode="Markdown"
            )
        return

    sleutel, totaal_kg, extra_kg, stal1 = resultaat

    try:
        antwoord = bereken(sleutel, totaal_kg, extra_kg, stal1)
        await update.message.reply_text(antwoord, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"\u26a0\ufe0f Fout bij berekening: {e}")


def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("ERROR: Stel de omgevingsvariabele TELEGRAM_TOKEN in.")
        print("Voorbeeld: export TELEGRAM_TOKEN=123456:ABCdef...")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, verwerk))
    app.add_handler(MessageHandler(filters.COMMAND, verwerk))

    print("Bot is gestart en luistert naar berichten...")
    app.run_polling()


if __name__ == "__main__":
    main()
