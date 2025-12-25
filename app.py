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
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import re
import time

# =========================================================================
# === 1. CONFIGURATION & STYLE (INCHANGÉ - VOTRE STYLE PRÉSERVÉ) ===
# =========================================================================

st.set_page_config(page_title="NovaReader AI", page_icon="💎", layout="wide")

st.markdown(
    """
<style>
    /* IMPORT DE POLICE MODERNE */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #F4F7F6;
        color: #2C3E50;
    }

    /* HEADER STYLISÉ */
    .main-header {
        background: linear-gradient(135deg, #00AEEF 0%, #0077b6 100%);
        padding: 2rem;
        border-radius: 0 0 20px 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0, 174, 239, 0.3);
    }
    .main-header h1 {
        color: white !important;
        font-weight: 700;
        letter-spacing: -1px;
    }
    .main-header p {
        opacity: 0.9;
        font-size: 1.1rem;
    }

    /* INPUTS & FILE UPLOADER (STYLE GLASS) */
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 1px solid #E0E0E0;
        padding: 10px 15px;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
    }
    .stTextInput > div > div > input:focus {
        border-color: #00AEEF;
        box-shadow: 0 0 0 2px rgba(0, 174, 239, 0.2);
    }
    [data-testid="stFileUploader"] {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        border: 1px dashed #00AEEF;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }

    /* BOUTON D'ACTION PRINCIPAL */
    .stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #00AEEF 0%, #0077b6 100%);
        color: white;
        font-weight: 600;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 15px rgba(0, 174, 239, 0.4);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 174, 239, 0.6);
        color: white !important;
    }
    .stButton > button:disabled {
        background: #BDC3C7;
        box-shadow: none;
        cursor: not-allowed;
    }

    /* CARTE D'OPPORTUNITÉ (DESIGN MODERNE) */
    .opp-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        border: 1px solid #F0F0F0;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .opp-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        border-color: #00AEEF;
    }
    .opp-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 6px;
        height: 100%;
        background: #00AEEF;
    }
    .opp-badge {
        background-color: #E3F8FF;
        color: #0077b6;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        display: inline-block;
        margin-bottom: 10px;
    }
    .opp-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1A202C;
        margin-bottom: 8px;
        line-height: 1.4;
    }
    .opp-meta {
        font-size: 0.85rem;
        color: #718096;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .section-title {
        color: #00AEEF;
        font-size: 0.9rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-top: 12px;
        margin-bottom: 4px;
        letter-spacing: 0.5px;
    }
    .section-content {
        font-size: 0.95rem;
        color: #4A5568;
        line-height: 1.5;
    }

    /* CUSTOM TABS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: white;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        padding: 0 20px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .stTabs [aria-selected="true"] {
        background-color: #00AEEF !important;
        color: white !important;
        border-color: #00AEEF !important;
    }

</style>
""",
    unsafe_allow_html=True,
)

# =========================================================================
# === LOGIQUE METIER ===
# =========================================================================

API_KEY = os.environ.get("GOOGLE_API_KEY", "")
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    SMTP_HOST = st.secrets["SMTP_HOST"]
    SMTP_PORT = int(st.secrets["SMTP_PORT"])
    SMTP_SENDER = st.secrets["SMTP_SENDER"]
    SMTP_PASSWORD = st.secrets["SMTP_PASSWORD"]
except KeyError:
    pass

if not API_KEY:
    st.error("🔑 ERREUR API : Clé manquante.")
    st.stop()

os.environ["GOOGLE_API_KEY"] = API_KEY
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash-lite")

DEFAULT_RECEIVER_EMAIL = "daouda.hamadou@novatech.ne"

NOVATECH_CONTEXT = """
CONTEXTE ENTREPRISE : NOVATECH Solutions Technologiques (Niamey, Niger).
Expertises : Réseaux, Télécoms, Cloud, Cybersécurité, Dév Web/Mobile, IA, Énergie, Électronique, Formation.
Objectif : Identifier des appels d'offres où ces expertises donnent un avantage concurrentiel.
"""

# --- ETAT ---
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

# --- FONCTIONS CORE (AMÉLIORÉES) ---


def clean_markdown_formatting(text):
    """Nettoyage pour affichage HTML/PDF (garde le gras en HTML)"""
    if isinstance(text, list):
        text = " ".join([str(x) for x in text])
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    # Convertit le gras Markdown en HTML pour Streamlit/PDF
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Gère les listes numérotées
    text = re.sub(r"(\d+\.)\s", r"<br/>\1 ", text)
    # Gère les puces
    text = re.sub(r"(\n|\s)\*\s", r"<br/>- ", text)
    return text.strip()


def clean_for_audio(text):
    """Nettoyage STRICT pour l'audio (supprime TOUTES les balises et étoiles)"""
    if not isinstance(text, str):
        return ""
    # Supprime les astérisques de gras
    text = text.replace("**", "").replace("*", "")
    # Supprime les balises HTML éventuelles
    text = re.sub(r"<[^>]+>", "", text)
    # Remplace les tirets de liste par des virgules pour la fluidité
    text = text.replace("- ", ", ").replace("  ", " ")
    return text.strip()


def analyze_page_structured(image):
    prompt = f"""
    Tu es un analyste stratégique pour NOVATECH. Contexte : {NOVATECH_CONTEXT}
    
    Tâche : Analyse cette page de journal. Si tu trouves des Appels d'Offres (Numérique, Énergie, BTP, Santé, Éducation), extrais-les.
    
    Pour chaque offre, rédige une section 'profit_dg' expliquant spécifiquement comment NOVATECH peut gagner ce marché grâce à ses expertises.
    
    Réponds UNIQUEMENT au format JSON :
    [
      {{
        "titre": "Titre complet",
        "secteur": "Secteur",
        "date_limite": "JJ/MM/AAAA",
        "conditions": "Résumé des conditions d'admissibilité",
        "profit_dg": "Argumentaire stratégique pour le DG (Pourquoi nous ?)",
        "mise_en_oeuvre": "Actions techniques immédiates pour répondre"
      }}
    ]
    Si rien, renvoie : []
    """
    try:
        response = model.generate_content(
            [prompt, image],
            generation_config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text)
    except:
        return []


def generate_script(all_opportunities):
    """Génère un script narratif fluide pour le DG."""
    script_parts = [
        "Bonjour Monsieur le Directeur. Voici le point de veille stratégique du jour."
    ]

    for idx, opp in enumerate(all_opportunities):
        # Nettoyage spécifique audio ici
        titre = clean_for_audio(opp.get("titre", ""))
        date = clean_for_audio(opp.get("date_limite", "non spécifiée"))
        cond = clean_for_audio(opp.get("conditions", "standard"))
        profit = clean_for_audio(opp.get("profit_dg", ""))

        script_parts.append(f"Opportunité numéro {idx+1} : {titre}.")
        script_parts.append(f"La date limite est le {date}.")
        script_parts.append(f"Concernant les conditions : {cond}.")
        script_parts.append(f"Voici l'intérêt stratégique pour Novatech : {profit}.")
        script_parts.append("Passons à la suivante.")

    script_parts.append(
        "Vous trouverez les détails de mise en œuvre dans le rapport PDF ci-joint. Bonne journée."
    )
    return " ".join(script_parts)


@st.cache_data(show_spinner=False)
def generate_audio(text):
    if not text:
        return None
    try:
        # Le texte arrive ici DÉJÀ nettoyé par generate_script -> clean_for_audio
        tts = gTTS(text=text, lang="fr", tld="fr")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            return open(fp.name, "rb").read()
    except:
        return None


def generate_pdf_report(all_ops):
    if not all_ops:
        return None
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()

        # Styles personnalisés pour le PDF
        title_style = ParagraphStyle(
            "NovaTitle",
            parent=styles["Title"],
            textColor=colors.HexColor("#00AEEF"),
            spaceAfter=20,
        )
        heading_style = ParagraphStyle(
            "NovaHeading",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#2C3E50"),
            spaceBefore=15,
        )
        normal_style = styles["Normal"]

        elements = [
            Paragraph("<b>Rapport de Veille Stratégique - NOVATECH</b>", title_style),
            Spacer(1, 12),
        ]

        for o in all_ops:
            titre = clean_markdown_formatting(o.get("titre", ""))
            secteur = o.get("secteur", "")
            profit = clean_markdown_formatting(o.get("profit_dg", ""))
            action = clean_markdown_formatting(o.get("mise_en_oeuvre", ""))

            # Bloc Titre
            elements.append(Paragraph(f"📌 {titre}", heading_style))
            elements.append(
                Paragraph(
                    f"<b>Secteur :</b> {secteur} | <b>Date Limite :</b> {o.get('date_limite','?')}",
                    normal_style,
                )
            )
            elements.append(Spacer(1, 5))

            # Bloc Stratégie
            elements.append(
                Paragraph(
                    f"<b>💡 IDÉE STRATÉGIQUE POUR LE DG :</b><br/>{profit}",
                    normal_style,
                )
            )
            elements.append(Spacer(1, 5))

            # Bloc Action
            elements.append(
                Paragraph(f"<b>🚀 MISE EN ŒUVRE :</b><br/>{action}", normal_style)
            )
            elements.append(Spacer(1, 15))
            # Ligne de séparation
            elements.append(Paragraph("_" * 60, normal_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    except:
        return None


def send_email_pro(
    host, port, sender, passw, receiver, sub, all_opportunities, audio, pdf
):
    try:
        # Création de la liste HTML des titres uniquement
        list_html = ""
        for o in all_opportunities:
            titre = clean_markdown_formatting(o.get("titre", "Offre"))
            list_html += f"<li><b>{titre}</b> (DL: {o.get('date_limite','?')})</li>"

        html_body = f"""
        <html>
            <body style="font-family: Arial, color: #333;">
                <h2 style="color: #00AEEF;">💎 NovaReader : Nouvelles Opportunités</h2>
                <p>Bonjour Monsieur le Directeur,</p>
                <p>Voici les offres identifiées ce jour :</p>
                <ul style="background: #f4f7f6; padding: 15px; border-left: 4px solid #00AEEF;">
                    {list_html}
                </ul>
                <p>Veuillez trouver ci-joint :</p>
                <ul>
                    <li>🔊 <b>Le briefing audio</b> (Stratégie & Conditions)</li>
                    <li>📄 <b>Le rapport PDF</b> (Détails & Mise en œuvre)</li>
                </ul>
                <p>Cordialement,<br>Votre Agent IA</p>
            </body>
        </html>
        """

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = receiver
        msg["Subject"] = sub
        msg.attach(MIMEText(html_body, "html"))  # Envoi en HTML

        if audio:
            p = MIMEBase("application", "octet-stream")
            p.set_payload(audio)
            encoders.encode_base64(p)
            p.add_header(
                "Content-Disposition", 'attachment; filename="briefing_strategique.mp3"'
            )
            msg.attach(p)
        if pdf:
            p = MIMEBase("application", "octet-stream")
            p.set_payload(pdf)
            encoders.encode_base64(p)
            p.add_header(
                "Content-Disposition", 'attachment; filename="rapport_analyse.pdf"'
            )
            msg.attach(p)

        with smtplib.SMTP_SSL(host, port) as s:
            s.login(sender, passw)
            s.send_message(msg)
        return True, "Envoyé"
    except Exception as e:
        return False, str(e)


def display_modern_card(opp):
    # Nettoyage HTML pour l'affichage carte
    t = clean_markdown_formatting(opp.get("titre", "")).replace("<br/>", " ")
    # On utilise profit_dg ici comme demandé
    b = clean_markdown_formatting(opp.get("profit_dg", "")).replace("<br/>", "<br>")
    m = clean_markdown_formatting(opp.get("mise_en_oeuvre", "")).replace(
        "<br/>", "<br>"
    )

    html = f"""
    <div class="opp-card">
        <span class="opp-badge">{opp.get('secteur','Autre')}</span>
        <div class="opp-title">{t}</div>
        <div class="opp-meta">
            <span>📅 Limite: <b>{opp.get('date_limite','?')}</b></span>
            <span>📄 Page {opp.get('page','?')}</span>
        </div>
        <div class="section-title">💎 Idée Stratégique (Usage Novatech)</div>
        <div class="section-content">{b}</div>
        <div class="section-title">🚀 Mise en Œuvre Technique</div>
        <div class="section-content">{m}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# =========================================================================
# === INTERFACE UTILISATEUR (INCHANGÉE - VOTRE STYLE) ===
# =========================================================================

# HEADER
st.markdown(
    """
<div class="main-header">
    <h1>💎 NovaReader AI</h1>
    <p>L'intelligence artificielle au service de la stratégie Novatech</p>
</div>
""",
    unsafe_allow_html=True,
)

# SECTION CONFIGURATION
col_left, col_right = st.columns([1.5, 1], gap="large")

with col_left:
    st.markdown("### 📥 Importation du Journal")
    uploaded_pdf = st.file_uploader(
        "Déposez le fichier PDF ici (crypté ou non)", type="pdf"
    )

    if (
        uploaded_pdf
        and st.session_state.get("last_uploaded_pdf_name") != uploaded_pdf.name
    ):
        st.session_state.clear()
        st.session_state["receiver_email"] = DEFAULT_RECEIVER_EMAIL
        st.session_state["last_uploaded_pdf_name"] = uploaded_pdf.name
        st.rerun()

with col_right:
    st.markdown("### 🔐 Sécurité & Envoi")
    mode = st.radio(
        "Méthode de déchiffrement", ["IA (Automatique)", "Code Manuel"], horizontal=True
    )

    if mode == "Code Manuel":
        man_pass = st.text_input(
            "Code PIN (4 chiffres)", type="password", placeholder="Ex: 1234"
        )
        file_pass = None
    else:
        file_pass = st.file_uploader("Fichier contenant le code", type="pdf")
        man_pass = None

    rec_email = st.text_input(
        "Email du Destinataire (DG)", value=st.session_state["receiver_email"]
    )
    st.session_state["receiver_email"] = rec_email

st.markdown("<br>", unsafe_allow_html=True)

# BOUTON D'ACTION
if not st.session_state["analyse_completee"]:
    col_btn_1, col_btn_2, col_btn_3 = st.columns([1, 2, 1])
    with col_btn_2:
        btn_start = st.button(
            "✨ LANCER L'ANALYSE STRATÉGIQUE", disabled=not uploaded_pdf
        )

    # LOGIQUE DE TRAITEMENT
    if btn_start and uploaded_pdf:
        status_container = st.status(
            "⚙️ Initialisation des moteurs IA...", expanded=True
        )
        try:
            # 1. DECRYPTAGE
            pwd = man_pass
            if mode == "IA (Automatique)" and file_pass:
                status_container.update(
                    label="🔑 L'IA cherche le mot de passe...", state="running"
                )
                img = convert_from_bytes(file_pass.getvalue())[0]
                pwd = model.generate_content(
                    [
                        "Trouve le code à 4 chiffres après 'Votre code:'. Réponds JUSTE le code.",
                        img,
                    ]
                ).text.strip()

            if not pwd or len(pwd) != 4:
                status_container.update(
                    label="❌ Erreur de mot de passe", state="error"
                )
                st.error("Le code doit faire 4 caractères.")
                st.stop()

            status_container.update(label="🔓 Déchiffrement du PDF...", state="running")
            reader = PyPDF2.PdfReader(uploaded_pdf)
            if reader.is_encrypted:
                reader.decrypt(pwd)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                writer = PyPDF2.PdfWriter()
                for p in reader.pages:
                    writer.add_page(p)
                writer.write(tmp)
                path = tmp.name

            # 2. ANALYSE
            status_container.update(
                label="🧠 Analyse Cognitive en cours...", state="running"
            )
            images = convert_from_bytes(open(path, "rb").read())
            st.session_state["num_pages_analyzed"] = len(images)
            os.remove(path)

            ops = []
            progress_bar = st.progress(0)

            for i, img in enumerate(images):
                # time.sleep(2) # Décommenter si limite de quota
                res = analyze_page_structured(img)
                if res:
                    for o in res:
                        o["page"] = i + 1
                        # Sécurisation des clés si l'IA oublie
                        if "profit_dg" not in o:
                            o["profit_dg"] = "Analyse manquante"
                        if "mise_en_oeuvre" not in o:
                            o["mise_en_oeuvre"] = "Voir détails"
                        ops.append(o)
                progress_bar.progress((i + 1) / len(images))

            # 3. GENERATION FINALE
            if ops:
                status_container.update(
                    label="📝 Rédaction du briefing DG...", state="running"
                )
                scr = generate_script(ops)  # Script nettoyé
                aud = generate_audio(scr)
                pdf = generate_pdf_report(ops)  # PDF Stylé

                st.session_state.update(
                    {
                        "all_opportunities": ops,
                        "script_content": scr,
                        "audio_file_bytes": aud,
                        "pdf_bytes": pdf,
                        "analyse_completee": True,
                    }
                )

                # ENVOI EMAIL
                if aud and pdf and not st.session_state["auto_email_sent"]:
                    sub = f"Veille Stratégique - {pd.Timestamp.now().strftime('%d/%m')}"
                    # Envoi avec la nouvelle fonction HTML
                    ok, msg = send_email_pro(
                        SMTP_HOST,
                        SMTP_PORT,
                        SMTP_SENDER,
                        SMTP_PASSWORD,
                        rec_email,
                        sub,
                        ops,  # On passe la liste des opportunités
                        aud,
                        pdf,
                    )
                    if ok:
                        st.session_state["auto_email_sent"] = True

                status_container.update(
                    label="✅ Mission accomplie !", state="complete", expanded=False
                )
                st.rerun()
            else:
                status_container.update(
                    label="⚠️ Aucune opportunité détectée ce jour.", state="complete"
                )

        except Exception as e:
            st.error(f"Erreur critique: {e}")

# =========================================================================
# === DASHBOARD DE RÉSULTATS ===
# =========================================================================

if st.session_state["analyse_completee"]:
    st.divider()

    # KPIs
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Opportunités Trouvées", len(st.session_state["all_opportunities"]))
    kpi2.metric("Pages Analysées", st.session_state["num_pages_analyzed"])
    kpi3.metric(
        "Statut Email",
        "Envoyé ✅" if st.session_state["auto_email_sent"] else "En attente ⏳",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ONGLETS MODERNES
    tab_cards, tab_media, tab_data = st.tabs(
        ["✨ VUE GALERIE", "🎙️ BRIEFING & EXPORT", "📊 DONNÉES BRUTES"]
    )

    with tab_cards:
        ops = st.session_state["all_opportunities"]
        if ops:
            cols = st.columns(3)
            for i, op in enumerate(ops):
                with cols[i % 3]:
                    display_modern_card(op)
        else:
            st.info("Rien à afficher.")

    with tab_media:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("### 🎧 Briefing Audio")
            if st.session_state["audio_file_bytes"]:
                st.audio(st.session_state["audio_file_bytes"])
                st.download_button(
                    "⬇️ Télécharger MP3",
                    st.session_state["audio_file_bytes"],
                    "briefing.mp3",
                    "audio/mp3",
                    use_container_width=True,
                )
        with c2:
            st.markdown("### 📄 Rapport PDF")
            if st.session_state["pdf_bytes"]:
                st.markdown("Le rapport contient l'analyse détaillée pour le Comex.")
                st.download_button(
                    "⬇️ Télécharger PDF",
                    st.session_state["pdf_bytes"],
                    "rapport.pdf",
                    "application/pdf",
                    use_container_width=True,
                )

        st.markdown("---")
        st.markdown("### 📝 Script Transcrit")
        st.code(st.session_state["script_content"], language="text")

    with tab_data:
        df = pd.DataFrame(st.session_state["all_opportunities"])
        if not df.empty:
            cols_to_clean = ["titre", "conditions", "profit_dg", "mise_en_oeuvre"]
            for c in cols_to_clean:
                if c in df.columns:
                    df[c] = df[c].apply(lambda x: re.sub(r"<[^>]+>", "", str(x)))
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Export CSV", df.to_csv().encode("utf-8"), "data.csv", "text/csv"
            )
