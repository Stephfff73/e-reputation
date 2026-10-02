# -*- coding: utf-8 -*-
"""Revue hebdomadaire de l'écoute client in'li — V4
Base : audit DPIEC mis à jour au 30/09/2026.
V4.1 : collecte Google fiabilisée (Cloud : profil jetable, Chromium auto-installé, diagnostic).
Les 19 lignes de l'édition correspondent aux nouveaux verbatims qualifiés depuis le 08/04/2026.
"""
from pathlib import Path
import base64, html, os, re, shutil, subprocess, sys, tempfile, time, traceback
from datetime import datetime
import pandas as pd
import streamlit as st

# Diagnostic Playwright : on distingue l'absence du module de l'absence de Chromium.
PLAYWRIGHT_AVAILABLE = False
PLAYWRIGHT_IMPORT_ERROR = ""
PlaywrightError = Exception   # remplacé par la vraie classe si Playwright est importable
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
    PLAYWRIGHT_AVAILABLE = True
except Exception as _playwright_exc:
    PLAYWRIGHT_IMPORT_ERROR = str(_playwright_exc)

def playwright_status():
    """Retourne (etat, message) sans lancer de navigateur si possible."""
    if not PLAYWRIGHT_AVAILABLE:
        return ("missing_package", "Le module Python Playwright n'est pas installé dans l'environnement utilisé par Streamlit.")
    try:
        with sync_playwright() as p:
            browser_type = p.chromium
            executable = browser_type.executable_path
            if not executable or not Path(executable).exists():
                return ("missing_browser", f"Chromium Playwright est absent. Chemin attendu : {executable or 'non déterminé'}")
        return ("ok", "Playwright et Chromium sont disponibles.")
    except Exception as exc:
        msg = str(exc)
        if "Executable doesn't exist" in msg or "executable doesn't exist" in msg or "browserType.launch" in msg:
            return ("missing_browser", "Playwright est installé mais le navigateur Chromium n'est pas installé.")
        return ("error", f"Diagnostic Playwright : {msg}")

# Détection de Streamlit Community Cloud (le code y est monté dans /mount/src).
IS_CLOUD = Path("/mount/src").exists()
BASE_DIR = Path(__file__).resolve().parent


@st.cache_resource(show_spinner="Installation de Chromium (première exécution, 1 à 2 minutes)…")
def ensure_chromium():
    """Télécharge Chromium pour Playwright, une seule fois par déploiement.
    Retourne (code_retour, journal)."""
    try:
        r = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=900,
        )
        return r.returncode, (r.stdout + r.stderr)[-1200:]
    except Exception as exc:
        return 1, str(exc)


PINK="#E82473"; TEAL="#269A87"; BRUNSWICK="#00594E"; AMARANTE="#B90745"; BORDEAUX="#9C0C35"; AMBER="#E3A21A"; RED="#D64550"
AUDIT_PHASES=['Recherche et candidature', 'Visite et sélection', 'Signature et entrée', 'Vie quotidienne et SAV', 'Gestion financière et charges', 'Départ et restitution']
ROWS=[{'phase': 'Recherche et candidature', 'categorie': 'Candidature / digital', 'date': '15 mai 2026', 'auteur': 'Jean-Claude B.', 'sentiment': 'Négatif', 'urgence': 'Haute', 'resume': 'Complexité du dossier et parcours décourageant', 'verbatim': 'La complexité pour créer un dossier locataire est hallucinante. […] Tout semble fait pour décourager les locataires de postuler aux biens qui s’affichent.', 'source': 'Trustpilot'}, {'phase': 'Recherche et candidature', 'categorie': 'Éligibilité / revenus', 'date': '2 sept. 2026', 'auteur': 'Mila A.', 'sentiment': 'Négatif', 'urgence': 'Haute', 'resume': 'Calcul des revenus jugé incompréhensible', 'verbatim': 'Je ne comprends pas comment il calcule nos revenus : un loyer de 862, des revenus à 2 600 net par mois, on me répond “revenu insuffisant”. J’aimerais comprendre le calcul.', 'source': 'Trustpilot'}, {'phase': 'Recherche et candidature', 'categorie': 'Application / ergonomie', 'date': '26 août 2026', 'auteur': 'Thomas O.', 'sentiment': 'Négatif', 'urgence': 'Haute', 'resume': 'Application jugée difficile à utiliser pour compléter le dossier', 'verbatim': 'L’application est nullissime, impossible de rentrer les chiffres ou de compléter correctement son dossier, aucune ergonomie. En 2026 c’est intolérable.', 'source': 'Trustpilot'}, {'phase': 'Recherche et candidature', 'categorie': 'Données / confiance', 'date': '20 sept. 2026', 'auteur': 'Bernard T.', 'sentiment': 'Négatif', 'urgence': 'Moyenne', 'resume': 'Allégation non vérifiée sur l’usage des données personnelles', 'verbatim': 'Entreprise qui se borne à récupérer des informations sensibles et privées […] pour les revendre à des tiers. (allégation non vérifiée)', 'source': 'Trustpilot'}, {'phase': 'Visite et sélection', 'categorie': 'Annulation de visite', 'date': '1er août 2026', 'auteur': 'Clement N.', 'sentiment': 'Négatif', 'urgence': 'Critique', 'resume': 'Rendez-vous annulé quelques minutes avant la visite', 'verbatim': 'A 17h27 nous recevons un message de inli pour dire que le rdv est annulé. On n’annule pas un rdv 3 min avant l’heure ! Plus jamais je refais une visite avec votre agence. (Livry-Gargan)', 'source': 'Trustpilot'}, {'phase': 'Visite et sélection', 'categorie': 'Organisation de visite', 'date': '30 juil. 2026', 'auteur': 'Vicky J.', 'sentiment': 'Négatif', 'urgence': 'Haute', 'resume': 'Mauvaises clés et remplaçant du gardien non informé', 'verbatim': 'Le prestataire mandaté ne disposait pas des bonnes clés […] ma candidature a donc été annulée. Lors de la seconde visite, le gardien était en congés et son remplaçant n’était pas informé.', 'source': 'Trustpilot'}, {'phase': 'Visite et sélection', 'categorie': 'Information candidat', 'date': '14 août 2026', 'auteur': 'Dialika D.', 'sentiment': 'Négatif', 'urgence': 'Haute', 'resume': 'Candidature close sans information du gestionnaire', 'verbatim': 'Le gestionnaire de mon dossier ne m’a jamais appelé pour m’informer que ma candidature est close. J’ai perdu une journée et demie de salaire.', 'source': 'Trustpilot'}, {'phase': 'Vie quotidienne et SAV', 'categorie': 'Qualité de service / signal positif', 'date': '24 août 2026', 'auteur': 'Anissa S.', 'sentiment': 'Positif', 'urgence': 'Faible', 'resume': 'Signal positif sur le traitement des réclamations depuis une nouvelle gestion', 'verbatim': 'Depuis la nouvelle gestion de nos appartements, toutes les réclamations sont traitées dans les plus brefs délais. Agence à l’écoute via leur service internet.', 'source': 'Trustpilot'}, {'phase': 'Vie quotidienne et SAV', 'categorie': 'Relation de proximité / signal positif', 'date': '7 mai 2026', 'auteur': 'Pape Mamadou C.', 'sentiment': 'Positif', 'urgence': 'Faible', 'resume': 'Satisfaction exprimée pour la prise en charge, avec remerciement du gardien', 'verbatim': 'Je tenais vraiment à remercier Inli pour la bonne prise en charge des locataires. Je suis très satisfait. (remercie aussi le gardien)', 'source': 'Trustpilot'}, {'phase': 'Vie quotidienne et SAV', 'categorie': 'Chauffage / eau chaude', 'date': '30 mai 2026', 'auteur': 'Leonor M.', 'sentiment': 'Négatif', 'urgence': 'Critique', 'resume': 'Panne récurrente de chauffage et d’eau chaude en hiver', 'verbatim': 'Tous les ans en novembre/décembre c’est la même chose, on n’a pas d’eau chaude le soir, on les appelle mais ils ne répondent jamais, le chauffage n’est jamais allumé.', 'source': 'Trustpilot'}, {'phase': 'Vie quotidienne et SAV', 'categorie': 'Humidité / moisissure', 'date': '26 août 2026', 'auteur': 'Le Belliqueux', 'sentiment': 'Négatif', 'urgence': 'Critique', 'resume': 'Moisissure non traitée malgré de nombreuses relances', 'verbatim': 'Plusieurs mois avec de la moisissure dans l’appart malgré énormément de relances. Zéro intervention sérieuse, et aujourd’hui j’ai des problèmes de santé à cause de ça. (Sud-Ouest)', 'source': 'Trustpilot'}, {'phase': 'Vie quotidienne et SAV', 'categorie': 'Téléphone / quittance', 'date': '24 juil. 2026', 'auteur': 'Barto P.', 'sentiment': 'Négatif', 'urgence': 'Haute', 'resume': 'Attente téléphonique et transfert sans réponse pour une demande simple', 'verbatim': 'Plus de 15 minutes d’attente, transféré vers un autre service qui ne répond jamais, l’appel est coupé. Tout ça pour une simple demande de quittance de loyer.', 'source': 'Trustpilot'}, {'phase': 'Vie quotidienne et SAV', 'categorie': 'Maintenance / clôture', 'date': '18 juin 2026', 'auteur': 'Sarrah', 'sentiment': 'Négatif', 'urgence': 'Haute', 'resume': 'Problème de clôture non résolu depuis plus de deux ans', 'verbatim': 'Plus de 2 ans que je signale un problème de clôture/grillage, sans qu’aucune solution sérieuse ne soit apportée. Aucun contact de la gestionnaire depuis la signature du bail. (PACA)', 'source': 'Trustpilot'}, {'phase': 'Vie quotidienne et SAV', 'categorie': 'Réactivité / parties communes', 'date': '18 sept. 2026', 'auteur': 'Lily', 'sentiment': 'Négatif', 'urgence': 'Haute', 'resume': 'Absence de réponse et qualité de ménage des communs', 'verbatim': 'Plus personne ne répond aux mails, le ménage dans les communs c’est une catastrophe, la personne sur site s’en tape royalement.', 'source': 'Trustpilot'}, {'phase': 'Vie quotidienne et SAV', 'categorie': 'Travaux / finition', 'date': '6 mai 2026', 'auteur': 'Christiane', 'sentiment': 'Négatif', 'urgence': 'Moyenne', 'resume': 'Travaux de VELUX non terminés et absence de store', 'verbatim': 'Changement des VELUX […] sans store alors que nous en avions avant. Installation non terminée, j’attends depuis 2 semaines.', 'source': 'Trustpilot'}, {'phase': 'Gestion financière et charges', 'categorie': 'Loyer / charges', 'date': '26 août 2026', 'auteur': 'Rachid T.', 'sentiment': 'Négatif', 'urgence': 'Haute', 'resume': 'Hausse du loyer et régularisations de charges élevées', 'verbatim': 'Le loyer augmente tous les ans : +20% en 4 ans (de 1 017 à 1 255 €). Des régules de charges chaque année d’un montant exorbitant, entre 1 200 et 2 000 € par an.', 'source': 'Trustpilot'}, {'phase': 'Gestion financière et charges', 'categorie': 'Régularisation / information', 'date': '15 juin 2026', 'auteur': 'Morgan M.', 'sentiment': 'Négatif', 'urgence': 'Haute', 'resume': 'Régularisation des charges jugée rare et nécessitant des relances', 'verbatim': 'Une régularisation des charges très rarement effectuée. Il faut leur parler de commission départementale de conciliation pour avoir une réponse plus précise.', 'source': 'Trustpilot'}, {'phase': 'Départ et restitution', 'categorie': 'Dépôt de garantie', 'date': '22 juin 2026', 'auteur': 'Geoffrey S.', 'sentiment': 'Négatif', 'urgence': 'Critique', 'resume': 'Multiples appels après état des lieux et absence de justificatif', 'verbatim': 'Après mon état des lieux de sortie du 2 avril 2026, j’ai dû multiplier les appels. Un chèque aurait été envoyé le 26 mai, sans qu’aucun justificatif ne me soit communiqué.', 'source': 'Trustpilot'}, {'phase': 'Départ et restitution', 'categorie': 'État des lieux de sortie', 'date': '9 juil. 2026', 'auteur': 'Sylvie D.', 'sentiment': 'Négatif', 'urgence': 'Haute', 'resume': 'Rendez-vous de sortie impossible à obtenir malgré un recommandé', 'verbatim': 'Courrier de résiliation en recommandé dès mai […] toujours impossible d’obtenir un rendez-vous pour l’état des lieux de sortie. À chaque appel : “Le responsable va vous rappeler.”', 'source': 'Trustpilot'}]

def esc(v): return html.escape(str(v), quote=True)

def color(i): return [PINK,TEAL,BRUNSWICK,AMARANTE,BORDEAUX,"#008080"][i % 6]

def df_demo(): return pd.DataFrame(ROWS)

def image_b64(path):
    try: return base64.b64encode(Path(path).read_bytes()).decode()
    except Exception: return ""


# -----------------------------------------------------------------------------
# Collecte automatique des avis Google Maps
# -----------------------------------------------------------------------------
GOOGLE_INLI_SEARCH_URL = "https://www.google.com/maps/search/?api=1&query=in%27li+5+Place+de+la+Pyramide+92800+Puteaux"
GOOGLE_REVIEW_STORE = BASE_DIR / "avis_google_inli.csv"
GOOGLE_PROFILE_DIR = Path(".google_maps_profile_inli")


def _first_text(card, selectors):
    for selector in selectors:
        try:
            loc = card.locator(selector).first
            if loc.count() and loc.is_visible():
                txt = loc.inner_text(timeout=1200).strip()
                if txt:
                    return txt
        except Exception:
            pass
    return ""


def _first_attr(card, selectors, attr):
    for selector in selectors:
        try:
            loc = card.locator(selector).first
            if loc.count():
                value = loc.get_attribute(attr, timeout=1200)
                if value:
                    return value.strip()
        except Exception:
            pass
    return ""


def _rating_from_card(card):
    candidates = []
    for selector in [
        '[role="img"][aria-label*="étoile"]',
        '[role="img"][aria-label*="star"]',
        '[aria-label*="étoile"]',
        '[aria-label*="star"]',
    ]:
        try:
            n = card.locator(selector).count()
            for i in range(min(n, 3)):
                a = card.locator(selector).nth(i).get_attribute("aria-label") or ""
                m = re.search(r"([1-5])", a)
                if m:
                    candidates.append(int(m.group(1)))
        except Exception:
            pass
    return candidates[0] if candidates else None


def _classify_google_review(rating, text):
    t = (text or "").lower()
    # Classification volontairement transparente et révisable : elle sert à
    # pré-classer les avis dans la revue ; elle ne remplace pas une analyse humaine.
    rules = [
        ("Recherche et candidature", ["dossier", "candidature", "postulé", "postule", "annonce", "revenu", "éligib", "site", "application", "appli", "visite"], "Candidature / digital"),
        ("Visite et sélection", ["visite", "rendez-vous", "rdv", "clé", "candidature", "commission", "sélection", "logement disponible"], "Visite / sélection"),
        ("Signature et entrée", ["bail", "signature", "état des lieux d'entrée", "emménagement", "emménag", "entrée dans les lieux", "clé", "boîte aux lettres", "chaudière à l'arrivée"], "Entrée dans les lieux"),
        ("Gestion financière et charges", ["loyer", "charge", "régularisation", "régule", "augmentation", "prélèvement", "facture", "quittance", "paiement", "dépôt de garantie"], "Loyer / charges / financier"),
        ("Départ et restitution", ["préavis", "résiliation", "sortie", "état des lieux de sortie", "restitution", "remboursement", "chèque", "dépôt de garantie rendu"], "Départ / restitution"),
        ("Vie quotidienne et SAV", ["travaux", "réparation", "sinistre", "dégât", "eau chaude", "chauffage", "moisissure", "humidité", "ascenseur", "gardien", "ménage", "réclamation", "service client", "téléphone", "mail", "maintenance", "panne"], "Vie quotidienne / SAV"),
    ]
    for phase, keywords, category in rules:
        if any(k in t for k in keywords):
            break
    else:
        phase, category = "Vie quotidienne et SAV", "Autre / à qualifier"

    if rating is not None:
        sentiment = "Négatif" if rating <= 2 else ("Positif" if rating >= 4 else "Neutre")
    else:
        sentiment = "Négatif" if any(k in t for k in ["nul", "honteux", "catastroph", "inadmissible", "aucune réponse", "jamais", "à fuir", "décevant", "problème"]) else "Positif"

    critical_words = ["insalubre", "moisissure", "fuite", "inondation", "plus d'eau chaude", "plus de chauffage", "danger", "santé", "urgence", "sinistre"]
    high_words = ["aucune réponse", "jamais de réponse", "des mois", "plusieurs mois", "impossible", "15 appels", "relance", "réclamation"]
    urgency = "Critique" if any(k in t for k in critical_words) else ("Haute" if sentiment == "Négatif" and any(k in t for k in high_words) else ("Haute" if sentiment == "Négatif" else "Faible"))
    return phase, category, sentiment, urgency


def scrape_google_reviews(max_reviews=100, headless=True, pause=1.1, compat=False):
    status, message = playwright_status()
    if status == "missing_package":
        raise RuntimeError("PLAYWRIGHT_PACKAGE_MISSING")
    if status == "missing_browser":
        raise RuntimeError("PLAYWRIGHT_BROWSER_MISSING")
    if status != "ok":
        raise RuntimeError(message)

    reviews = []
    crash = {"page": False}
    browser = None
    profile_dir = None
    if IS_CLOUD:
        # Cloud : pas d'écran, pas de profil persistant, options pour conteneur et
        # WebGL désactivé (Google Maps passe alors en rendu léger, bien moins gourmand en mémoire).
        headless = True
        launch_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-3d-apis",
            "--disable-software-rasterizer",
            "--disable-extensions",
            "--mute-audio",
            "--disable-blink-features=AutomationControlled",
        ]
        if compat:
            launch_args += ["--single-process", "--no-zygote"]
    else:
        GOOGLE_PROFILE_DIR.mkdir(exist_ok=True)
        profile_dir = str(GOOGLE_PROFILE_DIR)
        launch_args = ["--disable-blink-features=AutomationControlled"]

    with sync_playwright() as p:
        if IS_CLOUD:
            browser = p.chromium.launch(headless=True, args=launch_args)
            context = browser.new_context(locale="fr-FR", viewport={"width": 1024, "height": 768})
            # Allège la mémoire : les avis sont du texte.
            context.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in ("image", "media", "font")
                else route.continue_(),
            )
        else:
            context = p.chromium.launch_persistent_context(
                profile_dir,
                headless=headless,
                locale="fr-FR",
                viewport={"width": 1280, "height": 900},
                args=launch_args,
            )
        page = context.pages[0] if context.pages else context.new_page()
        page.on("crash", lambda *_: crash.__setitem__("page", True))
        try:
            page.goto(GOOGLE_INLI_SEARCH_URL, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(3500)
            if "/sorry/" in page.url or "recaptcha" in page.url.lower():
                raise RuntimeError("Google a affiché un contrôle anti-robot (captcha) : la collecte automatique est bloquée depuis ce serveur.")

            # Consentement Google si présent.
            for label in ["Tout accepter", "Accepter tout", "Accept all", "Tout refuser", "Reject all"]:
                try:
                    btn = page.get_by_role("button", name=label, exact=True).first
                    if btn.count() and btn.is_visible(timeout=1000):
                        btn.click(timeout=3000)
                        page.wait_for_timeout(1800)
                        break
                except Exception:
                    pass

            # Ouvre la première fiche correspondant à la recherche si nécessaire.
            try:
                place_link = page.locator('a[href*="/maps/place/"]').first
                if place_link.count() and place_link.is_visible(timeout=1500):
                    place_link.click(timeout=5000)
                    page.wait_for_timeout(3000)
            except Exception:
                pass

            # Ouvre l'onglet/bouton Avis.
            clicked_reviews = False
            for pattern in [r"^Avis$", r"Avis \(.*\)", r"avis"]:
                try:
                    loc = page.get_by_role("tab", name=re.compile(pattern, re.I)).first
                    if loc.count() and loc.is_visible(timeout=1200):
                        loc.click(timeout=5000)
                        clicked_reviews = True
                        break
                except Exception:
                    pass
                try:
                    loc = page.get_by_role("button", name=re.compile(pattern, re.I)).first
                    if loc.count() and loc.is_visible(timeout=1200):
                        loc.click(timeout=5000)
                        clicked_reviews = True
                        break
                except Exception:
                    pass
            if not clicked_reviews:
                # Certains rendus utilisent un lien "Avis".
                try:
                    loc = page.get_by_text(re.compile(r"^Avis$", re.I)).first
                    if loc.count():
                        loc.click(timeout=5000)
                        clicked_reviews = True
                except Exception:
                    pass
            page.wait_for_timeout(2500)

            # Tri par avis les plus récents lorsque Google le propose.
            for pattern in [r"Trier les avis", r"Trier", r"Sort reviews"]:
                try:
                    loc = page.get_by_role("button", name=re.compile(pattern, re.I)).first
                    if loc.count() and loc.is_visible(timeout=1000):
                        loc.click(timeout=3000)
                        page.wait_for_timeout(500)
                        break
                except Exception:
                    pass
            for pattern in [r"Les plus récents", r"Plus récents", r"Newest"]:
                try:
                    loc = page.get_by_text(re.compile(pattern, re.I)).first
                    if loc.count() and loc.is_visible(timeout=1000):
                        loc.click(timeout=3000)
                        page.wait_for_timeout(1800)
                        break
                except Exception:
                    pass

            # Le flux d'avis est virtualisé : on scrolle le conteneur et on
            # collecte les cartes déjà rendues à chaque passage.
            stagnant = 0
            previous_count = 0
            for _ in range(120):
                cards = page.locator('[data-review-id]')
                count = cards.count()
                for i in range(count):
                    card = cards.nth(i)
                    try:
                        review_id = card.get_attribute("data-review-id") or ""
                        if not review_id or any(r.get("review_id") == review_id for r in reviews):
                            continue
                        # Déplie le texte complet si un bouton "Plus" est présent.
                        for more in ["Plus", "More"]:
                            try:
                                b = card.get_by_text(more, exact=True).first
                                if b.count() and b.is_visible(timeout=300):
                                    b.click(timeout=700)
                                    page.wait_for_timeout(100)
                                    break
                            except Exception:
                                pass
                        author = _first_text(card, ['div[class*="d4r55"]', '[class*="TSUbDb"]', 'button[aria-label*="Profil"]'])
                        text_review = _first_text(card, ['span[class*="wiI7pd"]', '[data-expandable-section] span', 'div[class*="MyEned"]'])
                        date_google = _first_text(card, ['span[class*="rsqaWe"]', 'span[class*="DU9Pgb"]'])
                        rating = _rating_from_card(card)
                        photos = len(card.locator('button img').all()) if False else 0
                        if not author and not text_review:
                            continue
                        phase, category, sentiment, urgency = _classify_google_review(rating, text_review)
                        reviews.append({
                            "review_id": review_id,
                            "phase": phase,
                            "categorie": category,
                            "date": date_google or "",
                            "auteur": author or "Auteur Google",
                            "sentiment": sentiment,
                            "urgence": urgency,
                            "resume": (text_review[:120] + "…") if len(text_review) > 120 else text_review,
                            "verbatim": text_review,
                            "source": "Google",
                            "note": rating if rating is not None else "",
                            "collecte_le": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        })
                    except Exception:
                        continue

                if len(reviews) >= max_reviews:
                    break
                if count <= previous_count:
                    stagnant += 1
                else:
                    stagnant = 0
                previous_count = count
                if stagnant >= 8:
                    break
                # Scroll le feed Google Maps.
                try:
                    feed = page.locator('div[role="feed"]').first
                    if feed.count():
                        feed.evaluate("el => el.scrollTo(0, el.scrollHeight)")
                    else:
                        page.mouse.wheel(0, 2400)
                except Exception:
                    page.mouse.wheel(0, 2400)
                page.wait_for_timeout(int(pause * 1000))

            if not reviews:
                try:
                    titre = page.title()
                except Exception:
                    titre = "?"
                raise RuntimeError(
                    "Aucun avis lu. Page finale : " + page.url[:110] + " · titre : « " + titre[:60] + " ». "
                    "Causes probables : écran de consentement ou captcha Google, ou structure de Google Maps modifiée."
                )
        except PlaywrightError as exc:
            msg = str(exc).lower()
            # Trace complète dans les journaux : Manage app > logs
            print("[collecte Google] " + traceback.format_exc(), flush=True)
            if "closed" in msg or "crash" in msg or crash["page"]:
                frames = [f for f in traceback.extract_tb(exc.__traceback__)
                          if Path(f.filename).name == Path(__file__).name]
                where = (f"ligne {frames[-1].lineno} ({(frames[-1].line or '').strip()[:70]})") if frames else "inconnue"
                cause = ("la page Chromium a planté (crash du rendu, presque toujours un manque de mémoire)"
                         if crash["page"] else
                         "le navigateur a été fermé de l'extérieur (processus tué par le serveur, ou profil verrouillé)")
                raise RuntimeError(
                    f"Chromium s'est arrêté : {cause}. Étape : {where}. Détail : {str(exc)[:160]}"
                ) from exc
            raise
        finally:
            try:
                context.close()
            except Exception:
                pass
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
    return reviews[:max_reviews]


def load_google_history():
    if GOOGLE_REVIEW_STORE.exists():
        try:
            return pd.read_csv(GOOGLE_REVIEW_STORE, dtype=str).fillna("")
        except Exception:
            pass
    return pd.DataFrame()


def merge_google_reviews(scraped):
    old = load_google_history()
    new_df = pd.DataFrame(scraped)
    if new_df.empty:
        return old, new_df
    if not old.empty and "review_id" in old.columns:
        new_only = new_df[~new_df.review_id.isin(old.review_id)].copy()
        combined = pd.concat([old, new_df], ignore_index=True).drop_duplicates("review_id", keep="last")
    else:
        new_only = new_df.copy()
        combined = new_df.copy()
    combined.to_csv(GOOGLE_REVIEW_STORE, index=False, encoding="utf-8-sig")
    return combined, new_only

HEADER_LOGO_B64='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'
FOOTER_LOGO_B64='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'

st.set_page_config(page_title="La Voix des locataires — V4", page_icon="👂", layout="wide")
st.markdown("""<style>
.stApp{background:#F5F8F7}.block-container{max-width:1280px;padding-top:1rem}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#00594E,#B90745)} section[data-testid="stSidebar"] *{color:#fff!important}
.hero{border-radius:24px;overflow:hidden;background:#fff;border:1px solid #d8ebe7;box-shadow:0 20px 55px #00594e20}
.hero-visual{position:relative;line-height:0}.hero img{display:block;width:100%;height:auto}.hero-logo{position:absolute;left:28px;top:24px;width:145px;filter:drop-shadow(0 5px 12px rgba(0,0,0,.22))}.hero-visual:after{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,53,47,.34),rgba(0,53,47,0) 30%);pointer-events:none}.hero-copy{background:linear-gradient(120deg,#00594E,#007c73);padding:28px 32px;color:#fff}
.hero-copy h1{font-family:Georgia,serif!important;color:#fff!important;font-size:3rem!important;margin:.2rem 0 .5rem!important}
.card{background:#fff;border:1px solid #DDE7E5;border-radius:16px;padding:15px;margin-bottom:10px;box-shadow:0 5px 18px #17202108}
.small{font-size:.78rem;color:#657274}.app-footer{margin:38px 0 8px;background:#fff;border:1px solid #DDE7E5;border-top:5px solid #00594E;border-radius:18px;padding:24px;text-align:center;box-shadow:0 8px 25px #17202108}.app-footer-title{font-size:.86rem;font-weight:800;color:#00594E}.app-footer-logo{display:block;width:150px;margin:15px auto 0}.pill{display:inline-block;border-radius:999px;padding:4px 8px;font-size:.7rem;font-weight:800;margin-right:4px;background:#edf2f1}
</style>""", unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = df_demo()
    # Avis Google déjà enregistrés (avis_google_inli.csv, versionné avec le script) :
    # ils s'affichent même si la collecte en direct échoue.
    _hist = load_google_history()
    if not _hist.empty:
        st.session_state.df = pd.concat([st.session_state.df, _hist], ignore_index=True)

with st.sidebar:
    st.markdown('## 👂 La Voix des locataires')
    st.caption('V4 · Audit MAJ 30/09/2026 · Google automatisé')

    st.markdown('### ⭐ Avis Google')
    google_n = st.slider('Nombre d’avis Google à rechercher', min_value=20, max_value=300, value=(40 if IS_CLOUD else 100), step=20)
    google_visible = st.checkbox('Afficher le navigateur pendant la collecte', value=False, disabled=IS_CLOUD, help='À utiliser surtout lors de la première connexion si Google affiche un écran de consentement. Indisponible sur le Cloud (pas d’écran).')
    compat = st.checkbox('Mode compatibilité Chromium (single-process)', value=False, disabled=not IS_CLOUD, help='À essayer sur le Cloud si Chromium s’arrête en cours de collecte.')
    auto_google = st.checkbox('Collecte automatique au démarrage', value=(not IS_CLOUD), help='Une collecte est exécutée une seule fois par session Streamlit. Un historique local permet ensuite de ne conserver que les nouveaux avis.')
    collect_google = st.button('🔄 Récupérer les nouveaux avis Google', use_container_width=True)

    should_collect = collect_google or (auto_google and not st.session_state.get('google_auto_done', False))
    if should_collect:
        # On marque la tentative AVANT de lancer la collecte : sinon chaque interaction
        # (curseur, case à cocher…) relance le script et empile des Chromium orphelins.
        st.session_state.google_auto_done = True

        status, status_message = playwright_status()
        if status == "missing_browser":
            code, log = ensure_chromium()
            if code != 0:
                ensure_chromium.clear()      # ne pas mémoriser un échec
            status, status_message = playwright_status()
            if status == "missing_browser":
                st.warning("🟠 Chromium n'a pas pu être installé automatiquement.")
                st.code(log or "aucun journal", language="bash")

        if status == "missing_package":
            st.error("🔴 Playwright n'est pas installé dans l'environnement Python utilisé par Streamlit.")
            st.code("python3 -m pip install -r requirements.txt", language="bash")
            st.caption(f"Détail technique : {PLAYWRIGHT_IMPORT_ERROR}")
        elif status == "missing_browser":
            st.code("python3 -m playwright install chromium", language="bash")
            st.caption("Après l'installation, relancez Streamlit puis cliquez sur « Récupérer les nouveaux avis Google ».")
        elif status != "ok":
            st.error(f"🔴 {status_message}")
        else:
            with st.spinner('Connexion à Google Maps et récupération des avis…'):
                try:
                    scraped = scrape_google_reviews(max_reviews=google_n, headless=not google_visible, compat=compat)
                    combined, new_only = merge_google_reviews(scraped)
                    st.session_state.google_history = combined
                    if not new_only.empty:
                        st.success(f'{len(new_only)} nouvel(aux) avis Google détecté(s).')
                        base = st.session_state.df
                        add = new_only
                        # Dédoublonnage par review_id uniquement sur les avis Google
                        # (drop_duplicates sur des NaN fusionnerait les verbatims Trustpilot).
                        if 'review_id' in base.columns:
                            deja = set(base['review_id'].dropna().astype(str))
                            add = new_only[~new_only['review_id'].astype(str).isin(deja)]
                        st.session_state.df = pd.concat([base, add], ignore_index=True)
                    else:
                        st.info(f'{len(scraped)} avis lus ; aucun nouvel avis depuis la dernière collecte.')
                except Exception as e:
                    st.error(f'Collecte Google impossible : {e}')

    if IS_CLOUD:
        st.caption('Mode Cloud : navigateur sans interface. Les avis enregistrés dans avis_google_inli.csv (dépôt) sont chargés au démarrage ; les nouveaux ne survivent pas à un redémarrage.')
    if GOOGLE_REVIEW_STORE.exists():
        try:
            hist = load_google_history()
            st.caption(f'Historique local Google : {len(hist)} avis')
        except Exception:
            pass

    st.divider()
    uploaded=st.file_uploader('Importer un CSV complémentaire',type=['csv'])
    if uploaded is not None:
        try:
            st.session_state.df=pd.read_csv(uploaded,sep=None,engine='python')
            st.success('CSV chargé.')
        except Exception as e:
            st.error(f'Erreur CSV : {e}')
    st.divider(); st.markdown('### Filtres')
    phase=st.selectbox('Étape du parcours',['Toutes']+AUDIT_PHASES)
    urg=st.multiselect('Priorité',['Critique','Haute','Moyenne','Faible'],default=['Critique','Haute','Moyenne','Faible'])
    sent=st.multiselect('Sentiment',['Négatif','Neutre','Positif'],default=['Négatif','Neutre','Positif'])

work=st.session_state.df.copy()
for col in ['phase','urgence','sentiment','source']:
    if col not in work.columns:
        work[col] = 'À qualifier'
if phase!='Toutes': work=work[work.phase==phase]
if urg: work=work[work.urgence.isin(urg)]
if sent: work=work[work.sentiment.isin(sent)]

_VISUEL = 'visuel_header_inli_immobilier_satisfaction_v3.png'
img=''
for _p in (BASE_DIR / _VISUEL, BASE_DIR / 'assets' / _VISUEL, Path('/mnt/data') / _VISUEL):
    img = image_b64(_p)
    if img:
        break
hero_img=f"<img src='data:image/png;base64,{img}' alt='Architecture résidentielle et satisfaction locataire'>" if img else ''
st.markdown(f"<div class='hero'><div class='hero-visual'>{hero_img}<img class='hero-logo' src='data:image/png;base64,{HEADER_LOGO_B64}' alt='in’li'></div><div class='hero-copy'><div style='font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;font-weight:800;color:#baf2e8'>in’li · écoute clients · revue hebdomadaire</div><h1>La Voix des locataires</h1><p style='margin:0;color:#e6f8f4'>Édition 2 · audit DPIEC mis à jour au 30 septembre 2026 · 19 nouveaux verbatims qualifiés</p></div></div>",unsafe_allow_html=True)

cols=st.columns(4)
metrics=[(len(st.session_state.df),'verbatims chargés'),(int((st.session_state.df.source=='Google').sum()) if 'source' in st.session_state.df.columns else 0,'avis Google'),(int((st.session_state.df.sentiment=='Négatif').sum()),'négatifs'),(int((st.session_state.df.sentiment=='Positif').sum()),'positifs')]
for c,(v,l) in zip(cols,metrics): c.metric(l,v)

st.markdown('## Parcours client / locataire')
cols=st.columns(6)
for i,p in enumerate(AUDIT_PHASES):
    n=int((st.session_state.df.phase==p).sum())
    cols[i].markdown(f"<div class='card'><b style='color:{color(i)}'>{i+1:02d}</b><br><strong>{esc(p)}</strong><div class='small'>{n} nouveau(x) verbatim</div></div>",unsafe_allow_html=True)

st.markdown('## Verbatims · audit + avis Google')
for _,r in work.iterrows():
    badge='background:#e8f7f3;color:#087568' if r.sentiment=='Positif' else ('background:#fde4e7;color:#a72e39' if r.urgence=='Critique' else 'background:#fff0d1;color:#956500')
    st.markdown(f"<div class='card'><span class='pill' style='{badge}'>{esc(r.urgence)}</span><span class='pill'>{esc(r.categorie)}</span><div class='small'>{esc(r.source)} · {esc(r.auteur)} · {esc(r.date)} · {esc(r.phase)}</div><div style='font-weight:700;margin:8px 0 4px'>{esc(r.resume)}</div><p style='font-family:Georgia,serif;line-height:1.55;margin-bottom:0'>“{esc(r.verbatim)}”</p></div>",unsafe_allow_html=True)

st.markdown(f"<footer class='app-footer'><div class='app-footer-title'><b>in’li</b> · Revue hebdomadaire de l’écoute client</div><img class='app-footer-logo' src='data:image/png;base64,{FOOTER_LOGO_B64}' alt='in’li'></footer>",unsafe_allow_html=True)

csv=st.session_state.df.to_csv(index=False).encode('utf-8-sig')
st.download_button('⬇️ Télécharger les avis / verbatims (CSV)',data=csv,file_name='avis_inli_audit_et_google.csv',mime='text/csv',use_container_width=True)
