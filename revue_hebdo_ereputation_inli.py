# -*- coding: utf-8 -*-
"""
Revue hebdomadaire E-réputation in'li — Streamlit + générateur HTML
====================================================================
Objectif : transformer des avis issus du portail d'annonces, de l'application,
de Google et des espaces sociaux en une revue hebdomadaire orientée
« écoute client » et « réactivité opérationnelle ».

L'application fonctionne immédiatement en MODE DÉMONSTRATION avec un jeu
représentatif construit à partir du document « Analyse E-Reputation in'li -
Septembre 2026 » fourni avec le projet. Elle accepte ensuite un CSV pour
remplacer les données de démonstration.

CSV attendu (séparateur ; ou ,) :
source,canal,date,auteur,note,categorie,parcours,sentiment,urgence,resume,verbatim,url
"Google","Fiche Google","2026-09-24","Anonyme",1,"Maintenance","Vie dans le logement","Négatif","Critique","Dégât des eaux non résolu","...",""

Lancer :
    pip install streamlit pandas
    streamlit run revue_hebdo_ereputation_inli.py
"""

from __future__ import annotations

import base64
import html
import io
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# Identité visuelle
# -----------------------------------------------------------------------------
PINK = "#E82473"
TEAL = "#269A87"
BRUNSWICK = "#00594E"
AMARANTE = "#B90745"
BORDEAUX = "#9C0C35"
BLUE = "#008080"
KEPPEL = "#00AF98"
CYAN = "#008984"
INK = "#172021"
MUTED = "#657274"
LINE = "#E3E9E8"
CANVAS = "#F5F8F7"
WHITE = "#FFFFFF"
AMBER = "#E3A21A"
RED = "#D64550"
GREEN = "#2E8B57"

PALETTE = [PINK, TEAL, BRUNSWICK, AMARANTE, BORDEAUX, BLUE, KEPPEL, CYAN]

CATEGORIES = [
    "Candidature & dossier",
    "Attribution & acceptation",
    "Entrée & état des lieux",
    "Logement & maintenance",
    "Charges, loyer & paiement",
    "Relation de proximité",
    "Information & réactivité",
    "Sortie du logement",
    "Portail d'annonces & digital",
    "Autre / à qualifier",
]

PARCOURS = [
    "Recherche / candidature",
    "Attribution / acceptation",
    "Entrée dans le logement",
    "Vie dans le logement",
    "Gestion / incidents",
    "Paiement / charges",
    "Relation locataire",
    "Sortie du logement",
    "Parcours digital",
]

# -----------------------------------------------------------------------------
# Jeu de démonstration : informations quantitatives et verbatims visibles dans
# le PDF utilisateur + qualification éditoriale destinée à la maquette.
# -----------------------------------------------------------------------------
DEMO_ROWS = [
    {"source":"Google","canal":"Affichage naturel","date":"2026-09-24","auteur":"Anonyme","note":1,"categorie":"Attribution & acceptation","parcours":"Attribution / acceptation","sentiment":"Négatif","urgence":"Haute","resume":"Frustration autour de l'acceptation d'un dossier et du délai de traitement.","verbatim":"Après plusieurs semaines, la candidature reste sans réponse claire.","url":""},
    {"source":"Google","canal":"Affichage naturel","date":"2026-09-23","auteur":"Anonyme","note":1,"categorie":"Logement & maintenance","parcours":"Gestion / incidents","sentiment":"Négatif","urgence":"Critique","resume":"Dégât des eaux signalé, avec perception d'une aggravation faute de résolution rapide.","verbatim":"J'ai signalé un dégât des eaux chez moi depuis 1 mois. La fuite s'aggrave.","url":""},
    {"source":"Google","canal":"Affichage naturel","date":"2026-09-22","auteur":"Anonyme","note":1,"categorie":"Charges, loyer & paiement","parcours":"Paiement / charges","sentiment":"Négatif","urgence":"Haute","resume":"Réclamation concernant le montant ou la compréhension d'une charge / d'un paiement.","verbatim":"Le paiement et les montants demandés sont difficiles à comprendre.","url":""},
    {"source":"Google","canal":"Affichage naturel","date":"2026-09-21","auteur":"Anonyme","note":1,"categorie":"Logement & maintenance","parcours":"Vie dans le logement","sentiment":"Négatif","urgence":"Critique","resume":"Absence d'eau chaude ou de chauffage et sentiment de manque d'assistance.","verbatim":"Nous nous retrouvons souvent sans eau chaude ni chauffage.","url":""},
    {"source":"Google","canal":"Affichage naturel","date":"2026-09-20","auteur":"Anonyme","note":1,"categorie":"Relation de proximité","parcours":"Relation locataire","sentiment":"Négatif","urgence":"Haute","resume":"Perception d'une gestion insuffisante et d'une faible présence auprès des locataires.","verbatim":"La gestion est devenue quasi inexistante.","url":""},
    {"source":"Google","canal":"Affichage naturel","date":"2026-09-19","auteur":"Anonyme","note":1,"categorie":"Relation de proximité","parcours":"Relation locataire","sentiment":"Négatif","urgence":"Haute","resume":"Critique de la qualité de la relation client et de la considération perçue.","verbatim":"Service client nul. Aucune considération pour les locataires.","url":""},
    {"source":"Google Play","canal":"Appli in'li.fr","date":"2026-09-26","auteur":"Utilisateur","note":2,"categorie":"Portail d'annonces & digital","parcours":"Parcours digital","sentiment":"Négatif","urgence":"Moyenne","resume":"Avis défavorable sur l'expérience applicative.","verbatim":"L'expérience dans l'application pourrait être plus simple et plus fluide.","url":""},
    {"source":"Google Play","canal":"Appli in'li.fr","date":"2026-09-25","auteur":"Utilisateur","note":3,"categorie":"Portail d'annonces & digital","parcours":"Parcours digital","sentiment":"Neutre","urgence":"Faible","resume":"Avis mitigé sur l'application et son usage.","verbatim":"Application utile mais perfectible.","url":""},
    {"source":"Facebook","canal":"Groupe d'échange in'li","date":"2026-09-24","auteur":"Membre","note":"","categorie":"Attribution & acceptation","parcours":"Attribution / acceptation","sentiment":"Négatif","urgence":"Haute","resume":"Question sur la suite donnée après acceptation d'un dossier.","verbatim":"Comment se passe la suite après que in'li retienne notre dossier ?","url":""},
    {"source":"Facebook","canal":"Groupes locataires","date":"2026-09-23","auteur":"Membre","note":"","categorie":"Entrée & état des lieux","parcours":"Entrée dans le logement","sentiment":"Neutre","urgence":"Moyenne","resume":"Question sur l'état des lieux et les démarches associées.","verbatim":"J'ai fait l'état des lieux dans l'appartement.","url":""},
    {"source":"Facebook","canal":"Groupes locataires","date":"2026-09-22","auteur":"Membre","note":"","categorie":"Charges, loyer & paiement","parcours":"Paiement / charges","sentiment":"Négatif","urgence":"Haute","resume":"Question sur un loyer proratisé et son paiement.","verbatim":"Loyer proratisé : 627,59 € — comment procéder ?","url":""},
    {"source":"Facebook","canal":"Groupes locataires","date":"2026-09-21","auteur":"Membre","note":"","categorie":"Information & réactivité","parcours":"Relation locataire","sentiment":"Négatif","urgence":"Haute","resume":"Demande d'information et de délai après dépôt de pièces complémentaires.","verbatim":"Une fois les documents demandés envoyés, quand aurons-nous une réponse ?","url":""},
    {"source":"Google","canal":"Fiche Google in'li","date":"2026-09-20","auteur":"Anonyme","note":1,"categorie":"Logement & maintenance","parcours":"Gestion / incidents","sentiment":"Négatif","urgence":"Critique","resume":"Difficultés persistantes sur le chauffage ou l'eau chaude.","verbatim":"Plus d'un mois et demi sans eau chaude.","url":""},
    {"source":"Google","canal":"Fiche Google in'li","date":"2026-09-19","auteur":"Anonyme","note":1,"categorie":"Relation de proximité","parcours":"Relation locataire","sentiment":"Négatif","urgence":"Haute","resume":"Insatisfaction durable vis-à-vis de la gestion d'une résidence.","verbatim":"La situation est devenue insupportable.","url":""},
    {"source":"Google","canal":"Fiche Google in'li","date":"2026-09-18","auteur":"Anonyme","note":1,"categorie":"Logement & maintenance","parcours":"Vie dans le logement","sentiment":"Négatif","urgence":"Critique","resume":"Problèmes techniques récurrents et difficulté à obtenir de l'aide.","verbatim":"Impossible d'avoir quelqu'un qui nous aide.","url":""},
    {"source":"Google","canal":"Fiche Google in'li","date":"2026-09-17","auteur":"Anonyme","note":1,"categorie":"Relation de proximité","parcours":"Relation locataire","sentiment":"Négatif","urgence":"Haute","resume":"Perception d'un défaut de gestion dans la durée.","verbatim":"Je constate malheureusement que la gestion est quasiment inexistante.","url":""},
    {"source":"Google","canal":"Affichage naturel","date":"2026-09-16","auteur":"Anonyme","note":1,"categorie":"Attribution & acceptation","parcours":"Recherche / candidature","sentiment":"Négatif","urgence":"Haute","resume":"Incompréhension face à une candidature jugée injustement refusée.","verbatim":"Nous vivons une injustice totale après avoir visité un appartement.","url":""},
    {"source":"Google","canal":"Affichage naturel","date":"2026-09-15","auteur":"Anonyme","note":1,"categorie":"Portail d'annonces & digital","parcours":"Recherche / candidature","sentiment":"Négatif","urgence":"Moyenne","resume":"Expérience de recherche / candidature jugée peu transparente.","verbatim":"Le système paraît trop opaque.","url":""},
    {"source":"Google Play","canal":"Appli in'li.fr","date":"2026-09-14","auteur":"Utilisateur","note":4,"categorie":"Portail d'annonces & digital","parcours":"Parcours digital","sentiment":"Positif","urgence":"Faible","resume":"Retour favorable sur l'utilité de l'application.","verbatim":"Application utile pour suivre sa recherche.","url":""},
]


def demo_dataframe() -> pd.DataFrame:
    df = pd.DataFrame(DEMO_ROWS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["note_num"] = pd.to_numeric(df["note"], errors="coerce")
    return df


def clean_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "rating":"note", "stars":"note", "review":"verbatim", "texte":"verbatim",
        "summary":"resume", "résumé":"resume", "category":"categorie",
        "rubrique":"categorie", "channel":"canal", "platform":"source",
        "sentiment_client":"sentiment", "priority":"urgence", "parcours_client":"parcours",
    }
    df = df.copy()
    df.columns = [re.sub(r"\s+", "_", str(c).strip().lower()) for c in df.columns]
    df = df.rename(columns={k:v for k,v in aliases.items() if k in df.columns})
    for col in ["source","canal","auteur","categorie","parcours","sentiment","urgence","resume","verbatim","url"]:
        if col not in df.columns:
            df[col] = ""
    if "date" not in df.columns:
        df["date"] = pd.Timestamp.today().normalize()
    if "note" not in df.columns:
        df["note"] = ""
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["note_num"] = pd.to_numeric(df["note"], errors="coerce")
    return df


def filtered_data(df, sources, sentiments, categories, urgencies):
    out = df.copy()
    if sources:
        out = out[out["source"].isin(sources)]
    if sentiments:
        out = out[out["sentiment"].isin(sentiments)]
    if categories:
        out = out[out["categorie"].isin(categories)]
    if urgencies:
        out = out[out["urgence"].isin(urgencies)]
    return out


def stats(df):
    n = len(df)
    rated = df["note_num"].dropna()
    avg = float(rated.mean()) if not rated.empty else None
    neg = int((df["sentiment"] == "Négatif").sum())
    critical = int((df["urgence"] == "Critique").sum())
    high = int((df["urgence"] == "Haute").sum())
    return {"volume":n, "avg":avg, "neg":neg, "critical":critical, "high":high}


def top_categories(df, limit=6):
    return df["categorie"].value_counts().head(limit)


def badge_class(value):
    return {"Critique":"critical", "Haute":"high", "Moyenne":"medium", "Faible":"low"}.get(value, "neutral")


def sentiment_class(value):
    return {"Négatif":"negative", "Neutre":"neutral", "Positif":"positive"}.get(value, "neutral")


def theme_color(i):
    return PALETTE[i % len(PALETTE)]


def pct(part, total):
    return 0 if not total else round(part / total * 100)


def html_escape(value):
    return html.escape(clean_text(value))


# -----------------------------------------------------------------------------
# Génération HTML autonome
# -----------------------------------------------------------------------------
def generer_html(df: pd.DataFrame, semaine: str, titre: str = "La Revue Hebdomadaire de l'Écoute Client") -> str:
    df = normalize_columns(df)
    s = stats(df)
    avg = f"{s['avg']:.1f}" if s["avg"] is not None else "—"
    neg_pct = pct(s["neg"], s["volume"])
    cat_counts = top_categories(df, 10)

    category_cards = ""
    for i, (cat, count) in enumerate(cat_counts.items()):
        color = theme_color(i)
        category_cards += f"""
        <div class='cat-card' style='--accent:{color}'>
          <div class='cat-index'>{i+1:02d}</div>
          <div class='cat-main'><strong>{html_escape(cat)}</strong><span>{count} signal(s) · {pct(count, s['volume'])}%</span><div class='bar'><i style='width:{pct(count, cat_counts.max())}%'></i></div></div>
        </div>"""

    urgent = df[df["urgence"].isin(["Critique", "Haute"])].copy()
    urgent = urgent.sort_values(by=["urgence", "date"], ascending=[True, False])
    urgent_cards = ""
    for _, r in urgent.head(8).iterrows():
        urgent_cards += f"""
        <article class='signal-card'>
          <div class='signal-top'><span class='badge {badge_class(r['urgence'])}'>{html_escape(r['urgence'])}</span><span class='source'>{html_escape(r['source'])} · {html_escape(r['canal'])}</span></div>
          <h3>{html_escape(r['resume'])}</h3>
          <p class='quote'>“{html_escape(r['verbatim'])}”</p>
          <div class='signal-meta'><span>{html_escape(r['categorie'])}</span><span>{html_escape(r['parcours'])}</span></div>
        </article>"""
    if not urgent_cards:
        urgent_cards = "<div class='empty'>Aucun signal prioritaire dans la sélection.</div>"

    review_cards = ""
    for _, r in df.sort_values("date", ascending=False).head(18).iterrows():
        note = f"{int(r['note_num'])}/5" if pd.notna(r["note_num"]) else "—"
        review_cards += f"""
        <article class='review-card'>
          <div class='review-head'><span class='channel'>{html_escape(r['source'])}</span><span class='date'>{r['date'].strftime('%d/%m/%Y') if pd.notna(r['date']) else ''}</span></div>
          <div class='review-title'><span class='stars'>{'★' * int(r['note_num']) if pd.notna(r['note_num']) else '•'}</span><span class='note'>{note}</span><span class='badge {sentiment_class(r['sentiment'])}'>{html_escape(r['sentiment'])}</span></div>
          <h3>{html_escape(r['resume'])}</h3>
          <p>“{html_escape(r['verbatim'])}”</p>
          <div class='review-foot'><span>{html_escape(r['categorie'])}</span><span>{html_escape(r['parcours'])}</span><span class='badge {badge_class(r['urgence'])}'>{html_escape(r['urgence'])}</span></div>
        </article>"""

    action_rows = ""
    actions = [
        ("01", "Accusé de réception", "Prévoir un signal de prise en charge lorsqu'un avis décrit un incident ou une attente de réponse.", PINK),
        ("02", "Qualification rapide", "Rattacher chaque avis à une étape du parcours et à une cause opérationnelle avant consolidation.", TEAL),
        ("03", "Boucle de retour", "Identifier les sujets récurrents qui méritent un retour vers les équipes et, lorsque possible, vers le client.", BLUE),
    ]
    for num, title2, body, color in actions:
        action_rows += f"<div class='action'><b style='color:{color}'>{num}</b><div><strong>{title2}</strong><p>{body}</p></div></div>"

    data_json = df.fillna("").to_dict(orient="records")
    data_json = json.dumps(data_json, ensure_ascii=False, default=str).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang='fr'>
<head>
<meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{html_escape(titre)} — {html_escape(semaine)}</title>
<style>
:root{{--pink:{PINK};--teal:{TEAL};--brunswick:{BRUNSWICK};--amarante:{AMARANTE};--bordeaux:{BORDEAUX};--blue:{BLUE};--keppel:{KEPPEL};--cyan:{CYAN};--ink:{INK};--muted:{MUTED};--line:{LINE};--canvas:{CANVAS};--white:#fff;--amber:{AMBER};--red:{RED};--green:{GREEN}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--canvas);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}} .page{{max-width:1180px;margin:auto;padding:24px}}
.cover{{border-radius:26px;overflow:hidden;background:linear-gradient(135deg,var(--brunswick),#007d78 55%,var(--teal));color:white;box-shadow:0 22px 60px #00594e24}} .cover-top{{height:10px;background:linear-gradient(90deg,var(--pink) 0 18%,white 18% 20%,var(--pink) 20% 38%,white 38% 40%,var(--pink) 40% 100%)}} .cover-body{{padding:42px 46px 38px;display:grid;grid-template-columns:1.6fr .8fr;gap:34px}} .eyebrow{{text-transform:uppercase;letter-spacing:.13em;font-size:.75rem;font-weight:800;opacity:.78}} h1{{font-family:Georgia,serif;font-size:clamp(2.6rem,5vw,4.6rem);line-height:.96;margin:12px 0;color:#fff}} .subtitle{{font-size:1.1rem;max-width:680px;line-height:1.55;opacity:.9}} .cover-note{{margin-top:25px;border-left:4px solid var(--pink);padding-left:15px;font-family:Georgia,serif;font-style:italic;font-size:1.03rem}} .week{{align-self:center;background:#ffffff16;border:1px solid #ffffff2e;border-radius:22px;padding:25px}} .week strong{{font-size:2.4rem;display:block}} .week span{{opacity:.8}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}} .kpi{{background:white;border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 8px 24px #1720210b}} .kpi .n{{font-size:2rem;font-weight:850}} .kpi .l{{color:var(--muted);font-size:.85rem;margin-top:4px}} .kpi.pink{{border-top:4px solid var(--pink)}} .kpi.teal{{border-top:4px solid var(--teal)}} .kpi.amber{{border-top:4px solid var(--amber)}} .kpi.red{{border-top:4px solid var(--red)}}
.section{{margin:30px 0}} .section-head{{display:flex;justify-content:space-between;align-items:end;gap:16px;margin-bottom:14px}} .overline{{font-size:.72rem;text-transform:uppercase;letter-spacing:.13em;color:var(--teal);font-weight:850}} h2{{font-family:Georgia,serif;font-size:2rem;margin:4px 0}} .section-desc{{color:var(--muted);margin:0;max-width:760px}}
.categories{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}} .cat-card{{display:flex;gap:14px;align-items:center;background:#fff;border:1px solid var(--line);border-left:5px solid var(--accent);border-radius:16px;padding:14px 16px}} .cat-index{{font-weight:900;color:var(--accent);font-size:1.1rem}} .cat-main{{flex:1}} .cat-main strong{{display:block}} .cat-main span{{font-size:.78rem;color:var(--muted)}} .bar{{height:5px;background:#edf1f0;border-radius:999px;margin-top:8px;overflow:hidden}} .bar i{{display:block;height:100%;background:var(--accent);border-radius:999px}}
.split{{display:grid;grid-template-columns:1.15fr .85fr;gap:18px}} .panel{{background:#fff;border:1px solid var(--line);border-radius:20px;padding:20px}} .signal-card{{padding:15px 0;border-bottom:1px solid var(--line)}} .signal-card:last-child{{border-bottom:0}} .signal-top,.review-head,.review-foot{{display:flex;justify-content:space-between;gap:10px;align-items:center}} .source,.date{{color:var(--muted);font-size:.75rem}} .signal-card h3,.review-card h3{{font-size:1rem;margin:9px 0 7px}} .quote{{margin:0;color:#435052;font-family:Georgia,serif;line-height:1.5}} .signal-meta,.review-foot{{font-size:.72rem;color:var(--muted);margin-top:10px;display:flex;gap:8px;flex-wrap:wrap}}
.badge{{display:inline-flex;align-items:center;border-radius:999px;padding:5px 9px;font-size:.68rem;font-weight:800;background:#eef2f1;color:#3e4b4d}} .badge.critical{{background:#fde4e7;color:#a72e39}} .badge.high{{background:#fff0d1;color:#9b6900}} .badge.medium{{background:#e7f5f2;color:#087568}} .badge.low,.badge.positive{{background:#e5f5ea;color:#277746}} .badge.negative{{background:#fde7eb;color:#ae3150}} .badge.neutral{{background:#edf1f3;color:#5c696c}}
.reviews{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}} .review-card{{background:white;border:1px solid var(--line);border-radius:18px;padding:17px;box-shadow:0 7px 22px #17202108}} .channel{{font-size:.75rem;font-weight:850;color:var(--teal)}} .review-title{{display:flex;gap:7px;align-items:center;margin-top:12px}} .stars{{color:var(--amber);letter-spacing:1px}} .note{{font-weight:850;font-size:.78rem}} .review-card h3{{line-height:1.25}} .review-card p{{color:#4b585a;font-family:Georgia,serif;line-height:1.45;margin:0}}
.actions{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}} .action{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:18px;display:flex;gap:13px}} .action>b{{font-size:1.4rem}} .action strong{{display:block}} .action p{{margin:5px 0 0;color:var(--muted);font-size:.82rem;line-height:1.45}}
.footer{{margin-top:40px;border-radius:20px;background:var(--brunswick);color:#fff;padding:24px;display:flex;justify-content:space-between;gap:20px;align-items:center}} .footer b{{color:var(--pink)}} .fine{{font-size:.75rem;opacity:.72}}
@media(max-width:900px){{.cover-body,.split{{grid-template-columns:1fr}}.kpis{{grid-template-columns:repeat(2,1fr)}}.reviews{{grid-template-columns:repeat(2,1fr)}}.actions{{grid-template-columns:1fr}}}} @media(max-width:620px){{.page{{padding:12px}}.cover-body{{padding:28px 24px}}.categories,.reviews,.kpis{{grid-template-columns:1fr}}h1{{font-size:2.8rem}}}}
</style></head><body>
<div class='page'>
<section class='cover'><div class='cover-top'></div><div class='cover-body'><div><div class='eyebrow'>in'li · écoute clients · veille hebdomadaire</div><h1>{html_escape(titre)}</h1><p class='subtitle'>Une lecture opérationnelle des avis et conversations pour détecter les irritants, suivre le parcours locataire et accélérer la réaction des équipes.</p><div class='cover-note'>« Écouter ne consiste pas seulement à recueillir un avis : il s'agit de transformer le signal en action. »</div></div><div class='week'><span>Édition</span><strong>{html_escape(semaine)}</strong><span>{s['volume']} signaux analysés · {len(cat_counts)} rubriques visibles</span></div></div></section>
<div class='kpis'><div class='kpi pink'><div class='n'>{s['volume']}</div><div class='l'>avis / conversations dans la sélection</div></div><div class='kpi teal'><div class='n'>{avg}<small>/5</small></div><div class='l'>note moyenne des avis notés</div></div><div class='kpi amber'><div class='n'>{neg_pct}%</div><div class='l'>signaux classés négatifs</div></div><div class='kpi red'><div class='n'>{s['critical'] + s['high']}</div><div class='l'>signaux à traiter en priorité</div></div></div>
<section class='section'><div class='section-head'><div><div class='overline'>01 · Cartographie</div><h2>Les irritants du parcours</h2><p class='section-desc'>Une classification orientée parcours client / locataire pour passer d'une liste d'avis à une lecture des sujets récurrents.</p></div></div><div class='categories'>{category_cards}</div></section>
<section class='section split'><div class='panel'><div class='overline'>02 · Vigilance</div><h2>Signaux prioritaires</h2><p class='section-desc'>Les verbatims associés à une urgence « haute » ou « critique » dans la maquette.</p>{urgent_cards}</div><div class='panel'><div class='overline'>03 · Pistes de réaction</div><h2>Du signal à l'action</h2><p class='section-desc'>La revue peut devenir un rituel hebdomadaire de qualification et de bouclage.</p><div class='actions'>{action_rows}</div></div></section>
<section class='section'><div class='section-head'><div><div class='overline'>04 · Revue</div><h2>Les avis de la semaine</h2><p class='section-desc'>Recherche, tri et qualification peuvent être ajoutés à partir du même jeu de données.</p></div></div><div class='reviews'>{review_cards}</div></section>
<footer class='footer'><div><b>in'li</b> · Revue hebdomadaire de l'écoute client</div><div class='fine'>Document de démonstration · données issues du support « Analyse E-Reputation in'li — Septembre 2026 » et qualifications de maquette.</div></footer>
</div>
<script>window.EREP_DATA={data_json};</script></body></html>"""


# -----------------------------------------------------------------------------
# Streamlit
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Écoute clients in'li — Revue hebdo", page_icon="👂", layout="wide")

st.markdown(f"""
<style>
.stApp{{background:{CANVAS}}}
section[data-testid="stSidebar"]{{background:linear-gradient(180deg,{BRUNSWICK} 0%,#003f3c 100%)}}
section[data-testid="stSidebar"] *{{color:#fff!important}}
.block-container{{max-width:1280px;padding-top:1.1rem}}
.hero{{background:linear-gradient(135deg,{BRUNSWICK},{TEAL});border-radius:24px;padding:28px 32px;color:#fff;box-shadow:0 18px 50px #00594e20;border-top:7px solid {PINK}}}
.hero h1{{font-family:Georgia,serif!important;color:#fff!important;font-size:3.3rem!important;line-height:1!important;margin:.2rem 0 .6rem!important}}
.hero p{{font-size:1.05rem;max-width:850px;opacity:.9}}
.kpi{{background:#fff;border:1px solid {LINE};border-radius:18px;padding:18px 20px;min-height:115px;box-shadow:0 8px 25px #1720210b}}
.kpi b{{font-size:2rem;color:{INK}}}.kpi span{{display:block;color:{MUTED};font-size:.8rem;margin-top:5px}}
.section-title{{font-family:Georgia,serif;font-size:1.8rem;font-weight:700;color:{INK};margin:25px 0 8px}}
.card{{background:#fff;border:1px solid {LINE};border-radius:16px;padding:15px;margin-bottom:10px}}
.pill{{display:inline-block;border-radius:999px;padding:4px 8px;font-size:.7rem;font-weight:800;margin-right:4px;background:#edf2f1}}
.small{{font-size:.78rem;color:{MUTED}}}
div[data-testid="stDataFrame"]{{border-radius:16px;overflow:hidden}}
</style>
""", unsafe_allow_html=True)

if "df" not in st.session_state:
    st.session_state.df = demo_dataframe()

with st.sidebar:
    st.markdown("## 👂 Écoute clients")
    st.caption("Revue hebdomadaire E-réputation in'li")
    st.divider()
    st.markdown("### Données")
    uploaded = st.file_uploader("Importer un CSV d'avis", type=["csv"], help="Colonnes recommandées : source, canal, date, note, categorie, parcours, sentiment, urgence, resume, verbatim, url")
    if uploaded is not None:
        try:
            raw = uploaded.read()
            try:
                imported = pd.read_csv(io.BytesIO(raw), sep=None, engine="python")
            except Exception:
                imported = pd.read_csv(io.BytesIO(raw), sep=";")
            st.session_state.df = normalize_columns(imported)
            st.success(f"{len(st.session_state.df)} lignes importées")
        except Exception as exc:
            st.error(f"Import impossible : {exc}")
    if st.button("↺ Revenir aux données de démonstration", use_container_width=True):
        st.session_state.df = demo_dataframe()
        st.rerun()
    st.divider()
    edition_date = st.date_input("Date de l'édition", value=date(2026, 9, 30))
    semaine = f"Semaine du {(edition_date - timedelta(days=6)).strftime('%d/%m/%Y')} au {edition_date.strftime('%d/%m/%Y')}"
    st.markdown("### Filtres")
    df0 = normalize_columns(st.session_state.df)
    sources = st.multiselect("Canal / source", sorted(df0.source.dropna().unique()), default=[])
    sentiments = st.multiselect("Sentiment", sorted(df0.sentiment.dropna().unique()), default=[])
    categories = st.multiselect("Rubrique", sorted(df0.categorie.dropna().unique()), default=[])
    urgencies = st.multiselect("Priorité", ["Critique","Haute","Moyenne","Faible"], default=[])

st.markdown(f"""
<div class='hero'>
<div style='font-size:.72rem;text-transform:uppercase;letter-spacing:.14em;font-weight:800;opacity:.75'>in'li · veille & écoute clients</div>
<h1>La Revue Hebdomadaire<br>de l'Écoute Client</h1>
<p>Portail d'annonces · application · fiche Google · Google Play · groupes d'échanges — une lecture orientée irritants, parcours locataire et réactivité.</p>
</div>
""", unsafe_allow_html=True)

work = filtered_data(df0, sources, sentiments, categories, urgencies)
s = stats(work)
avg = f"{s['avg']:.1f}/5" if s['avg'] is not None else "—"

cols = st.columns(4)
for col, value, label, color in zip(cols, [s["volume"], avg, s["neg"], s["critical"]+s["high"]], ["Signaux analysés","Note moyenne","Signaux négatifs","Priorités hautes / critiques"], [PINK,TEAL,AMBER,RED]):
    with col:
        st.markdown(f"<div class='kpi' style='border-top:4px solid {color}'><b>{value}</b><span>{label}</span></div>", unsafe_allow_html=True)

st.markdown("<div class='section-title'>Cartographie du parcours client / locataire</div>", unsafe_allow_html=True)
cat_counts = work.categorie.value_counts()
chart = cat_counts.rename("Signaux").to_frame()
st.bar_chart(chart, height=300)

c1, c2 = st.columns([1.2, 1])
with c1:
    st.markdown("<div class='section-title'>Signaux prioritaires</div>", unsafe_allow_html=True)
    urgent = work[work.urgence.isin(["Critique","Haute"])].sort_values("date", ascending=False)
    for _, r in urgent.head(7).iterrows():
        note = f" · {int(r.note_num)}/5" if pd.notna(r.note_num) else ""
        st.markdown(f"<div class='card'><b>{html_escape(r.resume)}</b><div class='small'>{html_escape(r.source)} · {html_escape(r.categorie)} · {html_escape(r.parcours)}{note}</div><p style='margin:.55rem 0;font-family:Georgia,serif'>“{html_escape(r.verbatim)}”</p><span class='pill' style='background:{'#fde4e7' if r.urgence=='Critique' else '#fff0d1'}'>{html_escape(r.urgence)}</span><span class='pill'>{html_escape(r.sentiment)}</span></div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='section-title'>10 rubriques observées</div>", unsafe_allow_html=True)
    source_categories = ["logement", "chauffage", "état des lieux", "immeuble", "gardien", "caution", "eau chaude", "mise en demeure", "VMC", "astreinte"]
    st.markdown(" ".join([f"<span class='pill'>{x}</span>" for x in source_categories]), unsafe_allow_html=True)
    st.info("Ces rubriques sont celles explicitement visibles dans le support de septembre 2026. Elles peuvent être remplacées par une taxonomie complète du parcours client / locataire.")

st.markdown("<div class='section-title'>Revue des avis</div>", unsafe_allow_html=True)
show = work.sort_values("date", ascending=False).copy()
show["Date"] = show["date"].dt.strftime("%d/%m/%Y")
show["Note"] = show["note_num"].apply(lambda x: f"{int(x)}/5" if pd.notna(x) else "—")
view = show[["Date","source","canal","categorie","parcours","sentiment","urgence","Note","resume"]].rename(columns={"source":"Source","canal":"Canal","categorie":"Rubrique","parcours":"Parcours","sentiment":"Sentiment","urgence":"Priorité","resume":"Synthèse"})
st.dataframe(view, use_container_width=True, hide_index=True)

st.divider()
col1, col2 = st.columns(2)
with col1:
    st.download_button("⬇️ Télécharger la revue HTML", data=generer_html(work, semaine), file_name=f"revue_hebdo_ereputation_inli_{edition_date:%Y%m%d}.html", mime="text/html", use_container_width=True)
with col2:
    csv = work.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Télécharger les données filtrées", data=csv, file_name=f"avis_inli_{edition_date:%Y%m%d}.csv", mime="text/csv", use_container_width=True)

with st.expander("ℹ️ Méthode et règles de qualification"):
    st.markdown("""
**Principe :** un avis devient un signal exploitable lorsqu'il est rattaché à une source, une étape du parcours, une rubrique et un niveau d'urgence.

- **Critique** : incident sensible ou risque de rupture de service / situation nécessitant une vérification rapide.
- **Haute** : attente de réponse, dysfonctionnement ou irritant récurrent susceptible de générer plusieurs sollicitations.
- **Moyenne** : sujet à suivre ou à documenter.
- **Faible** : information, remarque isolée ou signal positif.

La qualification présentée dans le mode démonstration est une **maquette éditoriale** ; elle ne remplace pas une analyse métier ni une règle de décision validée par les équipes.
""")
