"""Erzeugt die Abschnitte Kuehlschrank und Pokale fuer das Profil-README.

Namen und Texte stammen woertlich von der Späti-Seite (Objekt D in index.html),
gekuerzt nur durch Weglassen. Links auf oeffentliche Repos oder Live-Seiten, sonst auf den Späti.
Aufruf: python3 tools/sections.py README.md fridge|trophies  (ersetzt den Bereich zwischen den Markern)
"""
import sys

SPAETI = "https://spaeti.5.45.109.195.sslip.io"
GH = "https://github.com/sami-mag07/"

# (Bild-ID, Name, Text, Link oder None, Alt-Text) in Regalreihen zu je drei
FRIDGE = [
    [("searchify", "Searchify Eistee",
      "Mein Research-Agent: sucht parallel über mehrere Suchdienste und lässt kein Zitat durch, das in keiner Quelle steht.",
      GH + "searchify", "Eine Flasche Searchify Eistee mit blauem Ameisen-Etikett, die sich dreht"),
     ("emil", "Emil Cola",
      "Ein Orchestrator mit 9 Spezialisten. Sortiert Mails, plant Termine, ruft mich an. Läuft über WhatsApp.",
      None, "Eine Flasche Emil Cola mit weißem Etikett, die sich dreht"),
     ("redteam", "Red Team Shot",
      "Greift meine eigenen Apps an: Recon, Secret-Scan, Prompt-Injection gegen Emil, Retest nach jedem Fix.",
      None, "Eine schwarze Dose Red Team Shot mit rotem Fadenkreuz, die sich dreht")],
    [("orchestra", "Orchestra Limo",
      "Geschäftskarte bezahlt, eine Frage aufs Telefon, ein Tap und der Beleg liegt in der Steuerakte.",
      GH + "tapntax", "Eine Flasche Orchestra Limo mit weißem Etikett, die sich dreht"),
     ("stipendien", "Stipendien Saft",
      "Findet Stipendien, die wirklich passen. Das CRM dahinter läuft im Emil-Dashboard.",
      None, "Eine grüne Flasche Stipendien Saft mit Apfel auf dem Etikett, die sich dreht"),
     ("hub", "Hub Spezi",
      "Alle Hackathons, Aufgaben und Notizen von Malek und mir an einem Ort.",
      GH + "hub", "Eine lila-orange Dose Hub Spezi, die sich dreht")],
    [("followcam", "HooperGPT Energy",
      "Erkennt Spieler, Trikotnummern und Würfe aus dem Spielvideo. YOLO, Kalman-Filter, OCR.",
      None, "Eine schwarze Dose HooperGPT Energy mit orangem Basketball, die sich dreht"),
     ("courtside", "Courtside Iso",
      "Videoanalyse für Spiele, im August von Basketball auf Fußball erweitert.",
      None, "Eine Flasche Courtside Iso mit blau-gelbem Etikett, die sich dreht"),
     ("handball", "Handball Schorle",
      "Port von FollowCam auf Handball, getestet an einem kompletten Spiel.",
      None, "Eine blaue Dose Handball Schorle, die sich dreht")],
    [("beacon", "Beacon Tonic",
      "Krisen-Cockpit für einen Stromausfall. Zeigt, was zu tun ist, wenn nichts mehr geht.",
      None, "Eine Flasche Beacon Tonic mit Funkturm auf dem Etikett, die sich dreht"),
     ("parkit", "ParkIt Brause",
      "Zeigt, was Parken in Berlin gerade kostet, bevor du losfährst.",
      "https://parkit.5.45.109.195.sslip.io", "Eine pinke Dose ParkIt Brause, die sich dreht"),
     ("portfolio", "Portfolio Wasser",
      "Mein Portfolio als macOS Tahoe nachgebaut, mit Emil in der Notch.",
      "https://portfolio.5.45.109.195.sslip.io", "Eine Flasche Portfolio Wasser mit meinem Namen auf dem Etikett, die sich dreht")],
]

TROPHIES = [[
    ("trophy_code", "1. Platz CODE-Hackathon",
     "Mit Malek HooperGPT in einem Tag gebaut, damals hieß es noch FollowCam.",
     None, "Pokal des CODE-Hackathons: zwei weiße Code-Klammern auf einem Sockel mit der Eins, der sich dreht"),
    ("trophy_google", "2. Platz Google Accessibility Hackathon",
     "Mit Malek Doorway gebaut: zeigt Rollstuhlnutzern und blinden Menschen, welcher Eingang für sie funktioniert.",
     GH + "doorway", "Gläserner Preis des Google Accessibility Hackathons für den zweiten Platz, der sich dreht"),
    ("trophy_loewen", "2. Platz Schule der Löwen",
     "Mein erster Pitch allein und auf Deutsch. Vier Stimmen hinter Platz eins.",
     None, "Goldener Pokal von Schule der Löwen mit Schild 2. Platz, der sich dreht"),
]]
TROPHY_MORE = "Dazu 3. Platz beim OpenAI Hackathon, 3. Platz beim Cursor Hackathon und 4. Platz bei SummerUP von 120 Teams."


def cell(pid, name, text, link, alt):
    """Bild und Name sind ein einziger Link (ein Tab-Stopp). Ohne eigenes Repo oder Demo fuehrt er in den Späti.
    Das Bild ist dekorativ (alt leer), der Name im Link traegt die Bedeutung."""
    href = link or SPAETI
    return (f'<td align="center" valign="top" width="33%"><a href="{href}">'
            f'<img src="assets/drinks/{pid}.webp" width="180" alt=""><br><b>{name}</b></a><br><sub>{text}</sub></td>')


def table(rows):
    out = ["<table>"]
    for row in rows:
        out.append("<tr>" + "".join(cell(*c) for c in row) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def fridge():
    return "## Kühlschrank\n\n" + table(FRIDGE)


def trophies():
    return "## Pokale\n\n" + table(TROPHIES) + "\n\n" + TROPHY_MORE


def replace_between(text, start, end, body):
    a = text.index(start) + len(start)
    b = text.index(end)
    return text[:a] + "\n" + body + "\n" + text[b:]


if __name__ == "__main__":
    what = sys.argv[2]
    path = sys.argv[1]
    s = open(path, encoding="utf-8").read()
    if what == "fridge":
        s = replace_between(s, "<!-- kuehlschrank:start -->", "<!-- kuehlschrank:end -->", fridge())
    elif what == "trophies":
        s = replace_between(s, "<!-- pokale:start -->", "<!-- pokale:end -->", trophies())
    open(path, "w", encoding="utf-8").write(s)
