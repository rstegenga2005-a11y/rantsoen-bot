#!/usr/bin/env python3
import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)

RANTSOENEN = {
    "hendrik": {
        "naam": "Melkkoeien \u2014 Hendrik",
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
        "naam": "Melkkoeien \u2014 Meile",
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
        "naam": "Droogstaande koeien",
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

ALIASSEN = {
    "hendrik": "hendrik", "henk": "hendrik", "h": "hendrik",
    "meile":   "meile",   "m":    "meile",
    "droog":   "droog",   "droge":"droog",   "d": "droog",
}

def fmt(n):
    return f"{round(n):,}".replace(",", ".")

def bereken(sleutel, totaal_kg, extra_kg=0, stal1=None):
    r = RANTSOENEN[sleutel]
    basis = sum(k for _, k in r["ing"])
    factor = (totaal_kg + extra_kg) / basis if basis > 0 else 0

    lopend = 0
    regels = []
    for naam, b in r["ing"]:
        adj = b * factor
        lopend += adj
        regels.append(
            f"*{naam}*\n"
            f"`{fmt(adj)} kg`  \u2192  totaal `{fmt(lopend)} kg`"
        )

    totaal = totaal_kg + extra_kg
    subtitel = f"_{fmt(totaal_kg)} kg"
    if extra_kg > 0:
        subtitel += f" + {fmt(extra_kg)} kg kalveren"
    subtitel += "_"

    tekst = (
        f"\U0001f33e *{r['naam']}*\n"
        f"{subtitel}\n"
        f"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        + "\n\n".join(regels)
        + f"\n\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
        f"\U0001f4e6 *Totaal:  {fmt(totaal)} kg*"
    )

    if r["split"] and stal1 is not None:
        stal2 = max(0, round(totaal) - stal1)
        tekst += (
            f"\n\n\U0001f3d7 *Verdeling stallen*\n"
            f"Stal 1 \u2192 `{fmt(stal1)} kg`\n"
            f"Stal 2 \u2192 `{fmt(stal2)} kg`"
        )

    return tekst

HELP = (
    "\U0001f33e *Rantsoen Bot*\n\n"
    "Stuur de stal en het totaal kg:\n\n"
    "`hendrik 7500`\n"
    "`meile 10000`\n"
    "`meile 10000 extra 400`  \u2190 kalveren\n"
    "`droog 3000`\n"
    "`droog 3000 stal1 1200`  \u2190 verdeling\n\n"
    "Korte namen werken ook: `h` `m` `d`\n\n"
    "Stuur `help` voor dit bericht."
)

def parse(tekst):
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
    stal1 = None
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
                stal1 = int(delen[i + 1].replace(".", "").replace(",", ""))
            except ValueError:
                pass
            i += 2
        else:
            i += 1
    return sleutel, totaal_kg, extra_kg, stal1

async def verwerk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    tekst = update.message.text.strip()
    if tekst.lower() in ("help", "/help", "/start"):
        await update.message.reply_text(HELP, parse_mode="Markdown")
        return
    resultaat = parse(tekst)
    if resultaat is None:
        eerste = tekst.lower().split()[0] if tekst.strip() else ""
        if eerste in ALIASSEN:
            await update.message.reply_text(
                "\u26a0\ufe0f Voorbeeld: `hendrik 7500`\nStuur `help` voor alle opties.",
                parse_mode="Markdown"
            )
        return
    sleutel, totaal_kg, extra_kg, stal1 = resultaat
    try:
        antwoord = bereken(sleutel, totaal_kg, extra_kg, stal1)
        await update.message.reply_text(antwoord, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"\u26a0\ufe0f Fout: {e}")

def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        print("Stel TELEGRAM_TOKEN in als omgevingsvariabele.")
        return
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, verwerk))
    app.add_handler(MessageHandler(filters.COMMAND, verwerk))
    print("Bot gestart...")
    app.run_polling()

if __name__ == "__main__":
    main()
