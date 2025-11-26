import streamlit as st
import os
import google.generativeai as genai
from pdf2image import convert_from_bytes
import tempfile
import json
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from gtts import gTTS
import PyPDF2
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# =========================================================================
# === CONFIGURATION GLOBALE & LECTURE DES SECRETS (Inchangé) ===
# =========================================================================

API_KEY = os.environ.get("GOOGLE_API_KEY", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = 465
SMTP_SENDER = os.environ.get("SMTP_SENDER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    SMTP_HOST = st.secrets["SMTP_HOST"]
    SMTP_PORT = int(st.secrets["SMTP_PORT"])
    SMTP_SENDER = st.secrets["SMTP_SENDER"]
    SMTP_PASSWORD = st.secrets["SMTP_PASSWORD"]
except KeyError:
    if not API_KEY or not SMTP_HOST or not SMTP_SENDER or not SMTP_PASSWORD:
        st.error(
            "🔑 ERREUR DE CONFIGURATION : Clé API ou identifiants SMTP non trouvés. Configurez correctement .streamlit/secrets.toml"
        )
        st.stop()

if not API_KEY:
    st.error("🔑 ERREUR DE CONFIGURATION : Clé API Gemini non trouvée.")
    st.stop()
if not all([SMTP_HOST, SMTP_SENDER, SMTP_PASSWORD]):
    st.error(
        "📧 ERREUR DE CONFIGURATION SMTP : Les identifiants (HOST, SENDER, PASSWORD) ne sont pas configurés."
    )
    st.stop()

os.environ["GOOGLE_API_KEY"] = API_KEY
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash-lite")

DEFAULT_RECEIVER_EMAIL = "daouda.hamadou@novatech.ne"
NOVATECH_CONTEXT = """
NOVATECH est un Partenaire Technologique fiable et durable pour apporter des solutions innovantes et efficaces dans le Numérique, utilisant les technologies numériques dans les secteurs clés du développement.
Missions : Contribuer à la Transformation Numérique du Niger et de l'Afrique et Créer de la Valeur et de la Richesse Partagée.
Domaines d'expertise: RÉSEAUX INFORMATIQUES, TELECOMS, SERVEURS & CLOUD, CYBERSECURITE, LOGICIELS WEB & MOBILE, INTELLIGENCE ARTIFICIELLE (IA), ENERGIE, ELECTRONIQUE, Formations et Certifications IT, CONSULTING.
"""

# --- MODIFICATION D'ÉTAT : INITIALISATION (Inchangé) ---
if "receiver_email" not in st.session_state:
    st.session_state["receiver_email"] = DEFAULT_RECEIVER_EMAIL
if "analyse_completee" not in st.session_state:
    st.session_state["analyse_completee"] = False
if "all_opportunities" not in st.session_state:
    st.session_state["all_opportunities"] = []
if "script_content" not in st.session_state:
    st.session_state["script_content"] = ""
if "audio_file_bytes" not in st.session_state:
    st.session_state["audio_file_bytes"] = None
if "pdf_bytes" not in st.session_state:
    st.session_state["pdf_bytes"] = None
if "num_pages_analyzed" not in st.session_state:
    st.session_state["num_pages_analyzed"] = 0
if "last_uploaded_pdf_name" not in st.session_state:
    st.session_state["last_uploaded_pdf_name"] = None
if "auto_email_sent" not in st.session_state:
    st.session_state["auto_email_sent"] = False
# --- FIN MODIFICATION D'ÉTAT ---


st.set_page_config(
    page_title="NovaReader - Veille Stratégique Avancée", page_icon="🚀", layout="wide"
)

# --- CSS PERSONNALISÉ (Inchangé) ---
st.markdown(
    """
<style>
    /* ... (CSS omis pour la concision) ... */
    /* 1. PALETTE GLOBALE ET FOND */
    .stApp {
        background-color: #f8f9fa; 
        color: #212529; 
    }
    h1, h2, h3, h4, h5, h6 {
        color: #212529; 
    }
    
    /* 2. COULEUR PRIMAIRE (Bordeaux/Rouille) */
    :root {
        --primary-color: #8d2f2f; 
        --secondary-color: #f1f3f5; 
    }

    /* 3. UPLOAD FILE & CONTENEURS */
    [data-testid="stUploadedFile"] {
        background-color: #e9ecef !important; 
        border-radius: 5px;
        padding: 5px;
    }
    [data-testid="stUploadedFile"] * {
        color: #000000 !important; 
        fill: #000000 !important; 
    }
    [data-testid="stUploadedFile"] div {
        font-weight: 600 !important;
    }
    .stFileUploader {
        background-color: #f8f9fa; 
        border: 2px dashed #ced4da;
        border-radius: 10px;
        padding: 20px;
    }
    div[data-testid="stFileUploaderDropzone"] {
        background-color: var(--secondary-color) !important; 
        border: none; 
    }
    [data-testid="stTextInput"] input {
        background-color: white !important; 
        color: #000000 !important; 
        border: 1px solid #ced4da; 
        border-radius: 5px;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: #adb5bd !important;
    }

    /* 4. BOUTONS */
    .stButton>button {
        background-color: var(--primary-color); 
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #5d1f1f; 
    }
    
    /* 5. CARTES D'OPPORTUNITÉS */
    .opp-card {
        background-color: white; 
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15); 
        margin-bottom: 15px;
        border-left: 6px solid var(--primary-color); 
        transition: transform 0.2s ease-in-out;
    }
    .opp-card:hover {
        transform: translateY(-3px); 
    }
    .opp-title {
        font-weight: bold;
        font-size: 19px; 
        color: #212529; 
    }
    .opp-sector {
        display: inline-block;
        background-color: var(--secondary-color); 
        color: #34495e; 
        padding: 6px 12px;
        border-radius: 25px; 
        font-size: 13px;
        font-weight: bold;
    }
    .opp-date {
        color: var(--primary-color); 
        font-weight: bold;
        font-size: 15px;
    }
    small {
        color: #7f8c8d; 
    }
            
    /* 6. CORRECTION DIVERSES (Lisibilité) */
    div[data-testid="stStatusContainer"] p, div[data-testid="stExpander"] p,
    div[data-testid="stRadio"] label p, div[data-testid="stTabs"] button,
    div[data-testid="stExpander"] button {
        color: #212529 !important; 
    }
    div[data-testid="stStatusContainer"] > div,
    div[data-testid="stExpander"] > div {
        background-color: #f1f3f5; 
        border-radius: 10px;
        border: 1px solid #ced4da; 
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #8d2f2f !important; 
        font-weight: bold; 
    }
    div[data-testid="stMetricLabel"] p {
        color: #000000 !important; 
        font-weight: bold !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)


# --- FONCTIONS GEMINI (Inchangées) ---


def analyze_page_structured(image):
    """Demande un JSON strict à l'IA pour l'extraction des opportunités."""
    prompt = """
    Tu es un analyste de veille stratégique pour le secteur du Numérique.
    Analyse cette page du journal 'Le Sahel'.

    Ton objectif est d'identifier toutes les opportunités d'Appels d'Offres et de business pertinentes pour NOVATECH, en te concentrant sur les secteurs suivants au Niger :
    1. Numérique, Informatique, Télécommunications (Priorité absolue)
    2. Éducation
    3. Santé
    4. Agriculture
    5. Environnement
    6. Services E-administratifs, Gouvernance Électronique (E-Gouv)
    7. Infrastructures, BTP (si fortement lié à la technologie).

    Réponds UNIQUEMENT au format JSON (liste d'objets). Si aucune opportunité pertinente n'est trouvée, renvoie une liste JSON vide [].
    Chaque objet doit inclure les clés suivantes : 
    "titre" : Le titre complet ou l'objet de l'appel d'offres.
    "secteur" : Le secteur le plus pertinent, choisi strictement dans la liste ci-dessus.
    "date_limite" : La date limite de dépôt de dossier (JJ/MM/AAAA) ou "Non spécifiée" si absente.
    "conditions" : Un résumé concis des conditions de soumission.
    """

    try:
        response = model.generate_content(
            [prompt, image],
            generation_config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text)
    except Exception:
        return []


def create_strategic_prompt(opportunity_title, novatech_context, opportunity_sector):
    """Génère un prompt Gemini pour une analyse orientée Directeur (Bénéfice/Mise en Oeuvre)."""

    if (
        "Numérique" in opportunity_sector
        or "Informatique" in opportunity_sector
        or "Télécommunications" in opportunity_sector
    ):
        expertise_focus = (
            "RÉSEAUX INFORMATIQUES, TELECOMS, SERVEURS & CLOUD, CYBERSECURITE"
        )
    elif "Santé" in opportunity_sector or "Éducation" in opportunity_sector:
        expertise_focus = (
            "LOGICIELS WEB & MOBILE, CONSULTING, Formations et Certifications IT"
        )
    elif "Agriculture" in opportunity_sector or "Environnement" in opportunity_sector:
        expertise_focus = "INTELLIGENCE ARTIFICIELLE (IA), ELECTRONIQUE, ENERGIE"
    else:
        expertise_focus = "INTELLIGENCE ARTIFICIELLE (IA), CONSULTING"

    base_prompt = f"""
    En tant qu'analyste IA pour NOVATECH, votre mission est de rédiger une analyse stratégique pour M. le Directeur concernant l'opportunité d'Appel d'Offres suivante : '{opportunity_title}' (Secteur : {opportunity_sector}).

    CONTEXTE NOVATECH (pour garantir la pertinence de l'offre et l'angle d'attaque) :
    ---
    {novatech_context}
    Les expertises NOVATECH les plus pertinentes sont: {expertise_focus}.
    ---

    Pour cette opportunité spécifique, générez un résumé concis qui répond à deux questions essentielles pour la prise de décision du Directeur :

    1. **Bénéfice Directeur :** Expliquez en quoi M. le Directeur va concrètement en profiter (gain stratégique, réduction de coût, innovation, positionnement marché). (Titre: 'BÉNÉFICE DIRECTEUR')
    2. **Mise en Œuvre :** Expliquez comment il peut concrètement servir de cette opportunité (quelle expertise NOVATECH utiliser, actions à entreprendre, étapes clés pour l'implémentation du projet/soumission). (Titre: 'MISE EN ŒUVRE')

    Format de sortie requis (strictement du texte, avec les titres BÉNÉFICE DIRECTEUR: et MISE EN ŒUVRE: sur des lignes distinctes) :
    BÉNÉFICE DIRECTEUR: <Votre réponse ici>
    MISE EN ŒUVRE: <Votre réponse ici>
    """
    return base_prompt


def analyze_opportunity_strategically(
    opportunity_title, opportunity_sector, novatech_context
):
    """Analyse un Appels d'Offres dynamiquement pour le Directeur en structurant la réponse."""
    prompt = create_strategic_prompt(
        opportunity_title, novatech_context, opportunity_sector
    )

    try:
        response = model.generate_content(prompt)
        output_text = response.text
    except Exception as e:
        return {
            "Bénéfice Directeur": f"Erreur d'appel IA pour l'analyse: {e}",
            "Mise en Oeuvre": "Veuillez vérifier la clé API et la connexion.",
        }

    benefice = "Analyse IA non formatée correctement."
    mise_en_oeuvre = "Analyse IA non formatée correctement."
    try:
        if "BÉNÉFICE DIRECTEUR:" in output_text and "MISE EN ŒUVRE:" in output_text:
            parts = output_text.split("BÉNÉFICE DIRECTEUR:")
            if len(parts) > 1:
                benefice_part = parts[1]
                if "MISE EN ŒUVRE:" in benefice_part:
                    benefice = benefice_part.split("MISE EN ŒUVRE:")[0].strip()
                    mise_en_oeuvre = benefice_part.split("MISE EN ŒUVRE:")[1].strip()

    except Exception:
        pass

    benefice = benefice.replace("BÉNÉFICE DIRECTEUR:", "").strip()
    mise_en_oeuvre = mise_en_oeuvre.replace("MISE EN ŒUVRE:", "").strip()

    return {"Bénéfice Directeur": benefice, "Mise en Oeuvre": mise_en_oeuvre}


# --- FONCTIONS GENERATION DE CONTENU (Script/Audio/PDF/Email) ---


def clean_markdown_formatting(text):
    """Supprime les doubles astérisques (**) utilisés pour le gras du Markdown."""
    if isinstance(text, str):
        return text.replace("**", "")
    return text


def get_email_content(script_content, is_auto=False):
    """Génère le sujet et le corps de l'email."""
    tag = " (ENVOI AUTO)" if is_auto else ""
    subject = f"Veille Stratégique NOVATECH - Journal du {pd.Timestamp.now().strftime('%d/%m/%Y')} (via NovaReader{tag})"

    email_body = f"""
Bonjour Monsieur le Directeur,

Veuillez trouver ci-joint les documents de veille stratégique analysés par NovaReader :

1. Fichier Audio (briefing_audio.mp3) : Un résumé vocal concis des opportunités clés du jour.
2. Rapport Détaillé (rapport_strategique_veille_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf) : Le rapport complet avec l'analyse stratégique 'Bénéfice Directeur' et 'Mise en Œuvre' pour chaque opportunité.

Vous trouverez également le script complet du briefing ci-dessous :
---
{script_content}
---

Cordialement,

Votre Assistant IA
Novatech - Veille Stratégique
"""
    return subject, email_body


def generate_script(all_opportunities):
    """Rédige le script vocal pour le DG, basé sur les analyses stratégiques."""

    briefing_points = []
    for opp in all_opportunities:
        # On utilise le texte nettoyé ici pour l'email/audio
        cleaned_titre = clean_markdown_formatting(opp["titre"])
        cleaned_benefice = clean_markdown_formatting(opp["Bénéfice Directeur"])
        cleaned_oeuvre = clean_markdown_formatting(opp["Mise en Oeuvre"])

        briefing_points.append(
            f"Opportunité {cleaned_titre} (Secteur {opp['secteur']}). Date limite: {opp['date_limite']}. Le bénéfice stratégique pour NOVATECH est : {cleaned_benefice}. La mise en oeuvre concrète implique : {cleaned_oeuvre}."
        )

    text_for_script = "\n".join(briefing_points)

    script_prompt = f"""
    Agis comme un secrétaire de direction efficace.
    Voici le récapitulatif des opportunités de veille et leur analyse stratégique :
    
    {text_for_script}
    
    Rédige un briefing vocal concis, professionnel et structuré pour le Directeur de NOVATECH.
    
    Le texte doit être optimisé pour un DISCORS ORAL, sans utiliser de caractères spéciaux ou de listes. Utilise des phrases complètes et des transitions fluides.
    
    Structure ton rapport en deux parties claires :
    1. Introduction et synthèse des opportunités Numériques prioritaires.
    2. Détail pour chaque opportunité (Numérique et Autres), en citant le Bénéfice Directeur et une action clé de Mise en Œuvre.

    Commence par "Monsieur le Directeur, voici le point de veille stratégique du Sahel de ce jour."
    Termine par : "Vous trouverez le rapport détaillé complet, incluant l'analyse stratégique Bénéfice Directeur et Mise en Œuvre pour chaque opportunité, au format PDF, dans le mail ci-joint, ainsi que les détails complets dans l'onglet 'Vue Galerie' de l'application."
    """
    script = model.generate_content(script_prompt).text
    return clean_markdown_formatting(script)  # <-- Nettoyage final pour le script


@st.cache_data(show_spinner=False)
def generate_audio(text):
    """Génère l'audio en utilisant gTTS."""
    # (Logique gTTS inchangée)
    if not text.strip():
        return None

    st.info(
        "🎙️ Synthèse vocale de haute qualité (gTTS) en cours... (Nécessite Internet)"
    )
    temp_path = None

    try:
        tts = gTTS(text=text, lang="fr", timeout=10)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name
        tts.save(temp_path)

        st.success("✅ Fichier audio généré avec succès en format MP3 !")

        with open(temp_path, "rb") as f:
            audio_bytes = f.read()

        return audio_bytes

    except Exception as e:
        st.error(
            f"Erreur de Synthèse Vocale gTTS : {e}. Cause probable: Connexion instable ou bloquée."
        )
        return None

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def generate_pdf_report(all_opportunities):
    """Crée un rapport PDF détaillé à partir des opportunités. (MISE À JOUR)"""
    if not all_opportunities:
        return None

    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=letter, title="Rapport de Veille Stratégique Novatech"
        )
        styles = getSampleStyleSheet()
        flowables = []

        # Title (Inchangé)
        flowables.append(
            Paragraph(
                "<b>Rapport Détaillé de Veille Stratégique - Novatech</b>",
                styles["Title"],
            )
        )
        flowables.append(Spacer(1, 12))
        flowables.append(
            Paragraph(
                f"Date du Rapport : <b>{pd.Timestamp.now().strftime('%d/%m/%Y')}</b>",
                styles["Normal"],
            )
        )
        flowables.append(Spacer(1, 24))

        # Opportunities details
        for opp in all_opportunities:
            # Nettoyage des chaînes
            cleaned_titre = clean_markdown_formatting(opp["titre"])
            cleaned_conditions = clean_markdown_formatting(opp["conditions"])
            cleaned_benefice = clean_markdown_formatting(opp["Bénéfice Directeur"])
            cleaned_oeuvre = clean_markdown_formatting(opp["Mise en Oeuvre"])

            # Titre de l'opportunité
            flowables.append(
                Paragraph(
                    f"<font size='14'><b>OPPORTUNITÉ :</b> {cleaned_titre}</font>",  # Utilise le texte nettoyé
                    styles["Heading2"],
                )
            )
            flowables.append(
                Paragraph(f"<b>Secteur :</b> {opp['secteur']}", styles["Normal"])
            )
            flowables.append(
                Paragraph(
                    f"<b>Date Limite :</b> {opp['date_limite']} (Page {opp['page']})",
                    styles["Normal"],
                )
            )
            flowables.append(
                Paragraph(
                    f"<b>Conditions :</b> {cleaned_conditions}", styles["Normal"]
                )  # Utilise le texte nettoyé
            )
            flowables.append(Spacer(1, 6))

            # Bénéfice Directeur
            flowables.append(
                Paragraph(
                    f"<font color='#8d2f2f'><b>BÉNÉFICE DIRECTEUR:</b></font>",
                    styles["h3"],
                )
            )
            flowables.append(
                Paragraph(cleaned_benefice, styles["Normal"])
            )  # Utilise le texte nettoyé

            # Mise en Œuvre
            flowables.append(
                Paragraph(
                    f"<font color='#8d2f2f'><b>MISE EN ŒUVRE (Action Clé):</b></font>",
                    styles["h3"],
                )
            )
            flowables.append(
                Paragraph(cleaned_oeuvre, styles["Normal"])
            )  # Utilise le texte nettoyé

            flowables.append(Spacer(1, 18))

        doc.build(flowables)
        buffer.seek(0)
        st.success("✅ Fichier PDF généré avec succès !")
        return buffer.getvalue()

    except Exception as e:
        st.error(
            f"❌ Erreur lors de la génération du PDF (ReportLab) : {e}. Avez-vous installé 'reportlab' ?"
        )
        return None


# --- FONCTION D'ENVOI EMAIL (PRO) (Inchangée) ---
def send_email_pro(
    smtp_host,
    smtp_port,
    sender,
    password,
    receiver,
    subject,
    body,
    audio_bytes,
    pdf_bytes,
):
    """Envoie un email via un serveur SMTP Pro (Novatech) avec audio et PDF."""
    try:
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = receiver
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        if audio_bytes:
            part_audio = MIMEBase("application", "octet-stream")
            part_audio.set_payload(audio_bytes)
            encoders.encode_base64(part_audio)
            part_audio.add_header(
                "Content-Disposition", 'attachment; filename="briefing_audio.mp3"'
            )
            msg.attach(part_audio)

        if pdf_bytes:
            part_pdf = MIMEBase("application", "octet-stream")
            part_pdf.set_payload(pdf_bytes)
            encoders.encode_base64(part_pdf)
            pdf_filename = f"rapport_strategique_veille_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf"
            part_pdf.add_header(
                "Content-Disposition", f'attachment; filename="{pdf_filename}"'
            )
            msg.attach(part_pdf)

        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(sender, password)
            server.send_message(msg)

        return True, "✅ Email envoyé avec succès (Audio et PDF joints) !"
    except Exception as e:
        return (
            False,
            f"❌ Erreur d'envoi : {str(e)} (Vérifiez l'hôte '{smtp_host}' et le mot de passe).",
        )


# --- FONCTIONS DE VUE (Inchangées) ---


def display_opportunity_card(opp):
    """Affiche une opportunité dans un format de carte HTML/Markdown pour le style."""

    # Nettoyage des astérisques pour l'affichage de la carte
    cleaned_titre = clean_markdown_formatting(opp["titre"])
    cleaned_conditions = clean_markdown_formatting(opp["conditions"])
    cleaned_benefice = clean_markdown_formatting(opp["Bénéfice Directeur"])
    cleaned_oeuvre = clean_markdown_formatting(opp["Mise en Oeuvre"])

    html_content = f"""
    <div class="opp-card">
        <span class="opp-sector">📍 {opp['secteur']} (Page {opp['page']})</span>
        <p class="opp-title">{cleaned_titre}</p>
        <p class="opp-date">Date Limite: <b>{opp['date_limite']}</b></p>
        <small>Conditions: {cleaned_conditions[:100]}{'...' if len(cleaned_conditions) > 100 else ''}</small>
        <hr style="border-top: 1px solid #f1f3f5; margin: 10px 0;">
        <details>
            <summary>Analyse Stratégique</summary>
            <p style="font-size: 14px; margin-bottom: 5px;"><b>BÉNÉFICE DIRECTEUR:</b></p>
            <p style="font-size: 14px;">{cleaned_benefice}</p>
            <p style="font-size: 14px; margin-bottom: 5px;"><b>MISE EN ŒUVRE:</b></p>
            <p style="font-size: 14px;">{cleaned_oeuvre}</p>
        </details>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)


# --- INTERFACE PRINCIPALE (Inchangée) ---

st.markdown(
    "<h1 style='text-align: center; color: #212529;'>🚀 NOVATECH • Veille Stratégique Avancée</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #555;'><i>Analysez le journal, décryptez, et obtenez un briefing stratégique pour M. le Directeur.</i></p>",
    unsafe_allow_html=True,
)

st.markdown("---")

col_pdf, col_password_mode = st.columns([1.5, 1])

with col_pdf:
    st.subheader("Configuration des Fichiers et du Destinataire")
    uploaded_pdf = st.file_uploader(
        "📥 1. Le Journal (PDF chiffré)", type="pdf", key="pdf_uploader"
    )

    # Logique de réinitialisation d'état (Inchangée)
    if (
        uploaded_pdf
        and st.session_state.get("last_uploaded_pdf_name") != uploaded_pdf.name
    ) or (
        uploaded_pdf is None
        and st.session_state.get("last_uploaded_pdf_name") is not None
    ):
        st.session_state["analyse_completee"] = False
        st.session_state["num_pages_analyzed"] = 0
        st.session_state["auto_email_sent"] = False
        st.session_state["last_uploaded_pdf_name"] = (
            uploaded_pdf.name if uploaded_pdf else None
        )
        st.rerun()

    st.text_input(
        "📧 3. Email du Destinataire (DG)",
        value=st.session_state["receiver_email"],
        key="receiver_email_input",
        placeholder="exemple@novatech.ne",
        on_change=lambda: st.session_state.__setitem__(
            "receiver_email", st.session_state["receiver_email_input"]
        ),
    )
    st.caption(f"L'expéditeur est configuré sur: **{SMTP_SENDER}**")

with col_password_mode:
    st.subheader("Accès au Chiffrement")
    password_mode = st.radio(
        "🔑 2. Comment fournir le Mot de Passe ?",
        options=["Fichier PDF par l'IA", "Saisie directe (4 caractères)"],
        index=0,
        horizontal=False,
        key="password_mode_select",
    )
    uploaded_password_file = None
    manual_password = None

    if password_mode == "Fichier PDF par l'IA":
        uploaded_password_file = st.file_uploader(
            "📁 Charger le Fichier PDF contenant le code",
            type="pdf",
            key="password_uploader",
        )
    else:
        st.markdown("🤫 **Saisir le Mot de Passe (4 caractères)**")
        manual_password = st.text_input(
            label="",
            type="password",
            placeholder="Entrez le code ici...",
            key="manual_password_input",
        )

col_a, col_b, col_c = st.columns([1, 2, 1])
with col_b:
    start_btn = st.button(
        "✨ Lancer l'analyse IA (Déchiffrement + Veille Stratégique)",
        use_container_width=True,
        type="primary",
        disabled=st.session_state["analyse_completee"] or uploaded_pdf is None,
    )

# ---------------------------------------------------------------------------------------------------------------------
# === BLOC DE TRAITEMENT (Logique inchangée, utilise les fonctions de nettoyage) ===
# ---------------------------------------------------------------------------------------------------------------------

if (
    start_btn
    and not st.session_state["analyse_completee"]
    and uploaded_pdf is not None
    and (
        uploaded_password_file is not None
        or (password_mode == "Saisie directe (4 caractères)" and manual_password)
    )
):
    # (Logique de détermination du mot de passe et de déchiffrement inchangée)
    # (Logique de conversion en images & extraction des opportunités inchangée)
    # ...
    decrypted_pdf_path = None
    password_content = None

    try:
        # 1. DÉTERMINATION DU MOT DE PASSE
        if password_mode == "Saisie directe (4 caractères)":
            password_content = manual_password.strip()
            if not (password_content and len(password_content) == 4):
                st.error(
                    "❌ Le mot de passe saisi manuellement doit contenir exactement 4 caractères."
                )
                st.stop()
            st.info(f"✅ Mot de passe saisi manuellement : ['{password_content}']")

        elif (
            password_mode == "Fichier PDF par l'IA"
            and uploaded_password_file is not None
        ):
            with st.status(
                "🔑 L'IA de Gemini extrait le mot de passe du PDF...", expanded=True
            ) as status:
                try:
                    password_pdf_bytes = uploaded_password_file.getvalue()
                    password_page_image = convert_from_bytes(
                        password_pdf_bytes, first_page=1, last_page=1
                    )[0]
                except Exception as e:
                    st.error(
                        f"Erreur de conversion du PDF du mot de passe en image: {e}."
                    )
                    status.update(
                        label="❌ Échec de l'analyse.", state="error", expanded=False
                    )
                    st.stop()

                password_prompt = """
                Analyse l'image de ce document d'avertissement. 
                Trouve le code à quatre (04) caractères qui est spécifié après la phrase 'Votre code:'. 
                Réponds UNIQUEMENT avec ce code, sans aucun texte supplémentaire, explication, guillemet ou ponctuation. 
                Si le code n'est pas trouvé, réponds 'ERREUR'.
                """
                response = model.generate_content(
                    [password_prompt, password_page_image]
                )
                password_content = response.text.strip()

                if (
                    not password_content
                    or password_content == "ERREUR"
                    or len(password_content) != 4
                ):
                    st.error(
                        f"❌ Impossible d'obtenir le mot de passe via Gemini. Réponse reçue: {password_content}"
                    )
                    status.update(
                        label="❌ Échec de l'analyse.", state="error", expanded=False
                    )
                    st.stop()

                st.write(f"✅ Mot de passe extrait par Gemini : ['{password_content}']")
                status.update(
                    label="✅ Mot de passe extrait.", state="complete", expanded=False
                )

        if not password_content:
            st.error(
                "❌ Le mot de passe n'a pas pu être déterminé. Veuillez vérifier vos entrées."
            )
            st.stop()

        # 2. DÉCHIFFREMENT DU JOURNAL PDF
        with st.status(
            "🔒 Déchiffrement du Journal PDF en cours...", expanded=True
        ) as status:
            pdf_reader = PyPDF2.PdfReader(uploaded_pdf)

            if pdf_reader.is_encrypted:
                if pdf_reader.decrypt(password_content):
                    st.write(
                        "✅ Journal PDF déchiffré avec succès. Préparation pour la conversion..."
                    )
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".pdf"
                    ) as temp_decrypted_pdf:
                        pdf_writer = PyPDF2.PdfWriter()
                        for page_num in range(len(pdf_reader.pages)):
                            pdf_writer.add_page(pdf_reader.pages[page_num])
                        pdf_writer.write(temp_decrypted_pdf)
                        decrypted_pdf_path = temp_decrypted_pdf.name
                else:
                    st.error("❌ Échec du déchiffrement. Mot de passe incorrect.")
                    status.update(
                        label="❌ Échec de l'analyse.", state="error", expanded=False
                    )
                    st.stop()
            else:
                st.warning("Le Journal PDF n'est pas chiffré. L'analyse continue...")
                uploaded_pdf.seek(0)
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".pdf"
                ) as temp_decrypted_pdf:
                    temp_decrypted_pdf.write(uploaded_pdf.getvalue())
                    decrypted_pdf_path = temp_decrypted_pdf.name

        status.update(
            label="⚙️ Conversion et Analyse en cours...", state="running", expanded=True
        )

        # 3. CONVERSION EN IMAGES & EXTRACTION DES OPPORTUNITÉS
        st.write("📄 Conversion du PDF en images...")
        images = convert_from_bytes(open(decrypted_pdf_path, "rb").read())
        st.session_state["num_pages_analyzed"] = len(images)
        st.write(
            f"👀 {len(images)} pages détectées. L'IA de Gemini commence l'analyse visuelle..."
        )
        progress_bar = st.progress(0)

        all_opportunities = []
        with st.expander(
            "🔍 Aperçu des pages analysées et des opportunités extraites",
            expanded=False,
        ):
            page_cols = st.columns(4)

            for i, page_image in enumerate(images):
                with page_cols[i % 4]:
                    st.image(
                        page_image, caption=f"Page {i+1}", use_container_width=True
                    )

                # ÉTAPE A : EXTRACTION SIMPLE
                opps = analyze_page_structured(page_image)

                if opps:
                    for op in opps:
                        op["page"] = i + 1

                        # ÉTAPE B : ANALYSE STRATÉGIQUE
                        st.write(
                            f"🧠 Analyse stratégique de l'opportunité: {op['titre']}..."
                        )
                        strategic_analysis = analyze_opportunity_strategically(
                            op["titre"], op["secteur"], NOVATECH_CONTEXT
                        )
                        op["Bénéfice Directeur"] = strategic_analysis[
                            "Bénéfice Directeur"
                        ]
                        op["Mise en Oeuvre"] = strategic_analysis["Mise en Oeuvre"]

                        all_opportunities.append(op)

                progress_bar.progress((i + 1) / len(images))

        # 4. RÉSULTATS (Génération et Sauvegarde dans l'état)
        if all_opportunities:
            with st.spinner("1/3 - Rédaction du script audio stratégique..."):
                script_content = generate_script(
                    all_opportunities
                )  # Appelle la fonction nettoyée
            with st.spinner("2/3 - Génération du fichier audio MP3..."):
                audio_file_bytes = generate_audio(script_content)
            with st.spinner("3/3 - Génération du rapport détaillé PDF..."):
                pdf_bytes = generate_pdf_report(
                    all_opportunities
                )  # Appelle la fonction nettoyée

            # Sauvegarde des résultats
            st.session_state["analyse_completee"] = True
            st.session_state["all_opportunities"] = all_opportunities
            st.session_state["script_content"] = script_content
            st.session_state["audio_file_bytes"] = audio_file_bytes
            st.session_state["pdf_bytes"] = pdf_bytes
            st.session_state["num_pages_analyzed"] = len(images)

            # --- DÉBUT ENVOI AUTOMATIQUE (Logique inchangée) ---
            if (
                audio_file_bytes
                and pdf_bytes
                and not st.session_state["auto_email_sent"]
            ):
                st.write("📧 Déclenchement de l'envoi automatique de l'email...")
                receiver_email = st.session_state["receiver_email"]

                auto_subject, auto_email_body = get_email_content(
                    script_content, is_auto=True
                )

                success, message = send_email_pro(
                    SMTP_HOST,
                    SMTP_PORT,
                    SMTP_SENDER,
                    SMTP_PASSWORD,
                    receiver_email,
                    auto_subject,
                    auto_email_body,
                    audio_file_bytes,
                    pdf_bytes,
                )

                if success:
                    st.session_state["auto_email_sent"] = True
                    st.write(
                        f"🎉 **ENVOI AUTOMATIQUE RÉUSSI** à {receiver_email}. Message: {message}"
                    )
                    status_label = "✅ Analyse terminée et E-mail automatique envoyé !"
                else:
                    st.write(
                        f"❌ **ÉCHEC DE L'ENVOI AUTOMATIQUE** à {receiver_email}. Message: {message} (Veuillez vérifier les logs SMTP ou renvoyer manuellement)."
                    )
                    status_label = "⚠️ Analyse terminée. Échec de l'envoi automatique."
            else:
                status_label = (
                    "✅ Analyse stratégique terminée et résultats sauvegardés !"
                )
            # --- FIN ENVOI AUTOMATIQUE ---

            status.update(
                label=status_label,
                state="complete",
                expanded=False,
            )
            st.rerun()

        else:
            status.update(
                label="⚠️ Analyse terminée. Aucune opportunité pertinente trouvée.",
                state="warning",
                expanded=False,
            )

    except Exception as e:
        st.error(f"Une erreur inattendue est survenue durant le traitement : {e}")
        st.exception(e)

    finally:
        if (
            decrypted_pdf_path
            and isinstance(decrypted_pdf_path, str)
            and os.path.exists(decrypted_pdf_path)
        ):
            os.remove(decrypted_pdf_path)

# ---------------------------------------------------------------------------------------------------------------------
# === BLOC D'AFFICHAGE PERSISTANT DES RÉSULTATS (Inchangé) ===
# ---------------------------------------------------------------------------------------------------------------------

if st.session_state["analyse_completee"]:

    # (Métriques et Onglets inchangés)
    all_opportunities = st.session_state["all_opportunities"]
    script_content = st.session_state["script_content"]
    audio_file_bytes = st.session_state["audio_file_bytes"]
    pdf_bytes = st.session_state["pdf_bytes"]
    num_pages_analyzed = st.session_state["num_pages_analyzed"]

    st.markdown("## 📊 Récapitulatif de l'Analyse")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(
            label="JOURNAL ANALYSÉ", value=st.session_state["last_uploaded_pdf_name"]
        )
    with col_m2:
        st.metric(label="PAGES TRAITÉES", value=f"{num_pages_analyzed}")
    with col_m3:
        st.metric(label="OPPORTUNITÉS CLÉS", value=f"{len(all_opportunities)}")

    st.markdown("---")

    tab_galerie, tab_script_export, tab_table = st.tabs(
        ["✨ Vue Galerie (Détail)", "🎙️ Script Vocal & Export", "📋 Vue Tableau"]
    )

    with tab_galerie:
        st.markdown("### Toutes les Opportunités Analysées")

        if all_opportunities:
            cols_per_row = 3
            opportunity_iter = iter(all_opportunities)

            while True:
                current_cols = st.columns(cols_per_row)
                opportunities_in_row = []

                for _ in range(cols_per_row):
                    try:
                        opportunities_in_row.append(next(opportunity_iter))
                    except StopIteration:
                        break

                if not opportunities_in_row:
                    break

                for i, opp in enumerate(opportunities_in_row):
                    with current_cols[i]:
                        display_opportunity_card(opp)
        else:
            st.warning("Aucune opportunité n'a été trouvée pour analyse.")

    with tab_table:
        st.markdown("### Détail en Tableau (Exportable en CSV)")
        df = pd.DataFrame(all_opportunities)
        # Nettoyage des colonnes pour un affichage propre dans le tableau (optionnel)
        df["titre"] = df["titre"].apply(clean_markdown_formatting)
        df["conditions"] = df["conditions"].apply(clean_markdown_formatting)
        df["Bénéfice Directeur"] = df["Bénéfice Directeur"].apply(
            clean_markdown_formatting
        )
        df["Mise en Oeuvre"] = df["Mise en Oeuvre"].apply(clean_markdown_formatting)

        st.dataframe(
            df,
            use_container_width=True,
            column_order=[
                "titre",
                "secteur",
                "date_limite",
                "page",
                "conditions",
                "Bénéfice Directeur",
                "Mise en Oeuvre",
            ],
            hide_index=True,
        )

    with tab_script_export:
        st.markdown("### 🎙️ Briefing Vocal et Export")

        if st.session_state["auto_email_sent"]:
            st.success(
                "✅ **L'envoi automatique de l'email a été effectué avec succès.** Utilisez le bouton ci-dessous pour un renvoi."
            )
        else:
            st.warning(
                "⚠️ L'envoi automatique a échoué ou n'a pas été tenté. Veuillez utiliser le bouton ci-dessous."
            )

        st.info(
            "Ce briefing vocal a été rédigé par Gemini 2.5 pour une présentation directe à M. le Directeur, et optimisé pour la synthèse vocale."
        )

        if audio_file_bytes:
            st.audio(audio_file_bytes, format="audio/mp3", sample_rate=24000)

        st.markdown("#### Script Complet (pour référence):")
        st.code(script_content, language="markdown")

        col_dl_a, col_dl_p, col_dl_d = st.columns(3)
        with col_dl_a:
            if audio_file_bytes:
                st.download_button(
                    label="⬇️ Télécharger l'Audio MP3",
                    data=audio_file_bytes,
                    file_name="briefing_strategique_novatech.mp3",
                    mime="audio/mp3",
                    use_container_width=True,
                )
            else:
                st.button(
                    "Générer l'Audio (Échec de la génération précédente)",
                    disabled=True,
                    use_container_width=True,
                )

        with col_dl_p:
            if pdf_bytes:
                st.download_button(
                    label="⬇️ Télécharger le Rapport PDF",
                    data=pdf_bytes,
                    file_name=f"rapport_strategique_veille_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.button(
                    "Générer le PDF (Échec de la génération précédente)",
                    disabled=True,
                    use_container_width=True,
                )

        with col_dl_d:
            # Assurez-vous d'utiliser le DataFrame nettoyé pour le CSV aussi
            st.download_button(
                label="⬇️ Télécharger le Tableau CSV",
                data=df.to_csv().encode("utf-8"),
                file_name="opportunites_novatech.csv",
                mime="text/csv",
                use_container_width=True,
            )

        # ---------------------------------------------------------------------
        # --- ENVOI PAR EMAIL (RENVOI MANUEL) ---
        # ---------------------------------------------------------------------
        st.markdown("### 📧 Renvoi Manuel du Briefing au DG")

        send_email_btn = st.button(
            "🚀 Renvoyer le Briefing (Audio + PDF) par Email",
            key="send_email_button_manual",
            use_container_width=True,
            disabled=not (audio_file_bytes and pdf_bytes),
        )

        if send_email_btn:
            # Le script_content est déjà nettoyé ici
            subject, email_body = get_email_content(script_content, is_auto=False)

            with st.spinner("Envoi de l'email en cours..."):
                success, message = send_email_pro(
                    SMTP_HOST,
                    SMTP_PORT,
                    SMTP_SENDER,
                    SMTP_PASSWORD,
                    st.session_state["receiver_email"],
                    subject,
                    email_body,
                    audio_file_bytes,
                    pdf_bytes,
                )

            if success:
                st.success(message)
            else:
                st.error(message)
