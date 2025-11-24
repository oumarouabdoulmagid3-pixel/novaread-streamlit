import streamlit as st
import os
import google.generativeai as genai
from pdf2image import convert_from_bytes
import tempfile
import json
import pandas as pd
import requests
from gtts import gTTS
import PyPDF2

# --- IMPORTS POUR L'EXPORT ---
import io
import urllib.parse

# --- NOUVELLE LIBRAIRIE POUR PDF ---
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# --- IMPORTS EMAIL AUTOMATIQUE ---
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# =========================================================================
# === CONFIGURATION GLOBALE & LECTURE DES SECRETS ===
# =========================================================================

# Valeurs par défaut si les secrets ne sont pas trouvés
API_KEY = os.environ.get("GOOGLE_API_KEY", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = 465
SMTP_SENDER = os.environ.get("SMTP_SENDER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    SMTP_HOST = st.secrets["SMTP_HOST"]
    # Assurez-vous que le port est traité comme un entier
    SMTP_PORT = int(st.secrets["SMTP_PORT"])
    SMTP_SENDER = st.secrets["SMTP_SENDER"]
    SMTP_PASSWORD = st.secrets["SMTP_PASSWORD"]
except KeyError:
    # Affiche l'erreur si une ou plusieurs clés sont manquantes
    if not API_KEY or not SMTP_HOST or not SMTP_SENDER or not SMTP_PASSWORD:
        st.error(
            "🔑 ERREUR DE CONFIGURATION : Clé API ou identifiants SMTP non trouvés. Configurez correctement .streamlit/secrets.toml"
        )
        st.stop()
    # Sinon, utilise le fallback basé sur les variables d'environnement (si définies)


# Vérification finale des clés lues
if not API_KEY:
    st.error("🔑 ERREUR DE CONFIGURATION : Clé API Gemini non trouvée.")
    st.stop()
if not all([SMTP_HOST, SMTP_SENDER, SMTP_PASSWORD]):
    st.error(
        "📧 ERREUR DE CONFIGURATION SMTP : Les identifiants (HOST, SENDER, PASSWORD) ne sont pas configurés."
    )
    st.stop()

# Initialisation de Gemini
os.environ["GOOGLE_API_KEY"] = API_KEY
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash-lite")


# === CONFIGURATION EMAIL DESTINATAIRE PAR DÉFAUT & GESTION D'ÉTAT ===
DEFAULT_RECEIVER_EMAIL = "daouda.hamadou@novatech.ne"
# DEFAULT_RECEIVER_EMAIL = "oumarouabdoulmagid3@gmail.com"

# --- MODIFICATION D'ÉTAT : INITIALISATION ---
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
# --- FIN MODIFICATION D'ÉTAT ---


st.set_page_config(
    page_title="NovaReader - Veille Stratégique", page_icon="🚀", layout="wide"
)

# --- CSS PERSONNALISÉ (DESIGN FINAL - CLAIR & MODERNE) ---
st.markdown(
    """
<style>
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


# --- FONCTIONS GEMINI ---


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


# --- FONCTIONS GENERATION DE CONTENU (Script/Audio/PDF) ---


def generate_script(all_opportunities):
    """Rédige le script vocal pour le DG."""
    text_for_script = json.dumps(all_opportunities, ensure_ascii=False)

    script_prompt = f"""
    Agis comme un secrétaire de direction efficace.
    Voici les opportunités JSON trouvées : {text_for_script}.
    
    Rédige un briefing vocal concis, professionnel et structuré pour le Directeur de NOVATECH.
    
    Le texte doit être optimisé pour un DISCORS ORAL, sans utiliser de caractères spéciaux, de listes à puces (*, -) ou de symboles. Utilise des phrases complètes et des transitions fluides.
    
    Structure ton rapport en deux parties claires :
    1. Priorité Numérique : Détaille d'abord et avec emphase toutes les opportunités du secteur Numérique, Informatique et Télécommunications, en citant la date limite et les conditions de soumission pour chaque point trouvé.
    2. Autres Secteurs : Mentionne ensuite, de manière plus brève, les opportunités trouvées dans les autres secteurs (Santé, Éducation, Agriculture, etc.).

    Commence par "Monsieur le Directeur, voici le point de veille stratégique du Sahel de ce jour."
    Termine par : "Vous trouverez le rapport détaillé complet, au format PDF, dans le mail ci-joint, ainsi que les détails de soumission de chaque appel d'offres dans l'onglet 'Vue Cartes' de l'application."
    """
    script = model.generate_content(script_prompt).text
    return script


@st.cache_data(show_spinner=False)
def generate_audio(text):
    """Génère l'audio en utilisant gTTS (Cloud TTS, compatible Windows/Linux)."""
    if not text.strip():
        return None

    st.info(
        "🎙️ Synthèse vocale de haute qualité (gTTS) en cours... (Nécessite Internet)"
    )
    temp_path = None

    try:
        tts = gTTS(text=text, lang="fr", timeout=10)

        # Utilisation de tempfile pour l'écriture
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
    """Crée un rapport PDF détaillé à partir des opportunités."""
    if not all_opportunities:
        return None

    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=letter, title="Rapport de Veille Novatech"
        )
        styles = getSampleStyleSheet()
        flowables = []

        # Title
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
            flowables.append(
                Paragraph(
                    f"<font size='14'><b>Titre :</b> {opp['titre']}</font>",
                    styles["Heading2"],
                )
            )
            flowables.append(
                Paragraph(f"<b>Secteur :</b> {opp['secteur']}", styles["Normal"])
            )
            flowables.append(
                Paragraph(
                    f"<b>Date Limite :</b> {opp['date_limite']}", styles["Normal"]
                )
            )
            flowables.append(
                Paragraph(f"<b>Page Source :</b> {opp['page']}", styles["Normal"])
            )
            flowables.append(
                Paragraph(f"<b>Conditions :</b> {opp['conditions']}", styles["Normal"])
            )
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


# --- FONCTION D'ENVOI EMAIL (PRO) ---
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

        # Attachement du Corps du mail (texte)
        msg.attach(MIMEText(body, "plain"))

        if audio_bytes:
            # Attachement Audio
            part_audio = MIMEBase("application", "octet-stream")
            part_audio.set_payload(audio_bytes)
            encoders.encode_base64(part_audio)
            part_audio.add_header(
                "Content-Disposition", 'attachment; filename="briefing_audio.mp3"'
            )
            msg.attach(part_audio)

        if pdf_bytes:
            # Attachement PDF
            part_pdf = MIMEBase("application", "octet-stream")
            part_pdf.set_payload(pdf_bytes)
            encoders.encode_base64(part_pdf)
            # Nom de fichier incluant la date
            pdf_filename = (
                f"rapport_detaille_veille_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf"
            )
            part_pdf.add_header(
                "Content-Disposition", f'attachment; filename="{pdf_filename}"'
            )
            msg.attach(part_pdf)

        # Connexion SMTP Sécurisée (SSL) sur le port 465
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(sender, password)
            server.send_message(msg)

        return True, "✅ Email envoyé avec succès (Audio et PDF joints) !"
    except Exception as e:
        return (
            False,
            f"❌ Erreur d'envoi : {str(e)} (Vérifiez l'hôte '{smtp_host}' et le mot de passe).",
        )


# --- INTERFACE PRINCIPALE ---

# Header
st.markdown(
    "<h1 style='text-align: center; color: #212529;'>🚀 NOVATECH • Veille Stratégique</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #555;'><i>Analysez Le Sahel en un clic avec l'IA</i></p>",
    unsafe_allow_html=True,
)

st.markdown("---")

# Zone d'upload et mot de passe alignée
col_pdf, col_password_mode = st.columns([1.5, 1])

# --- Colonne 1 : Journal PDF et Email Destinataire ---
with col_pdf:
    st.subheader("Configuration des Fichiers et du Destinataire")
    uploaded_pdf = st.file_uploader(
        "📥 1. Le Journal (PDF chiffré)", type="pdf", key="pdf_uploader"
    )

    # --- MODIFICATION D'ÉTAT : RÉINITIALISATION SI NOUVEAU FICHIER ---
    # Si l'utilisateur charge un nouveau PDF, on réinitialise l'état pour forcer une nouvelle analyse.
    if (
        uploaded_pdf
        and st.session_state.get("last_uploaded_pdf_name") != uploaded_pdf.name
    ):
        st.session_state["analyse_completee"] = False
        st.session_state["num_pages_analyzed"] = 0
        st.session_state["last_uploaded_pdf_name"] = uploaded_pdf.name
    elif uploaded_pdf is None:
        # Si le fichier est effacé par l'utilisateur, réinitialiser l'état
        st.session_state["analyse_completee"] = False
        st.session_state["num_pages_analyzed"] = 0
        st.session_state["last_uploaded_pdf_name"] = None
    # --- FIN MODIFICATION D'ÉTAT ---

    # CHAMP EMAIL
    st.text_input(
        "📧 3. Email du Destinataire (DG)",
        value=st.session_state["receiver_email"],
        key="receiver_email_input",
        placeholder="exemple@novatech.ne",
        # Mise à jour de l'état Streamlit lors de la saisie
        on_change=lambda: st.session_state.__setitem__(
            "receiver_email", st.session_state["receiver_email_input"]
        ),
    )
    st.caption(f"L'expéditeur est configuré sur: **{SMTP_SENDER}**")

# --- Colonne 2 : Choix du Mode Mot de Passe ---
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

# Condition de lancement et bouton (MAINTENANT TOUJOURS VISIBLE)
col_a, col_b, col_c = st.columns([1, 2, 1])
with col_b:
    start_btn = st.button(
        "✨ Lancer l'analyse IA (Déchiffrement + Veille)",
        use_container_width=True,
        type="primary",
        disabled=st.session_state[
            "analyse_completee"
        ],  # Désactiver si analyse déjà faite
    )

# ---------------------------------------------------------------------------------------------------------------------
# === BLOC DE TRAITEMENT (Exécuté uniquement si le bouton est cliqué ET si l'analyse n'est pas déjà complète) ===
# ---------------------------------------------------------------------------------------------------------------------

if (
    start_btn
    and not st.session_state["analyse_completee"]
    and uploaded_pdf is not None
    and (uploaded_password_file is not None or manual_password)
):

    # Vérification simple de l'email avant de lancer
    if "@" not in st.session_state["receiver_email"]:
        st.error("❌ Veuillez saisir une adresse email de destinataire valide.")
        st.stop()

    # --- R.A.Z des messages d'erreur précédents ---
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
                        f"Erreur de conversion du PDF du mot de passe en image: {e}. Vérifiez l'installation de Poppler."
                    )
                    status.update(
                        label="❌ Échec de l'analyse.",
                        state="error",
                        expanded=False,
                    )
                    st.stop()

                password_prompt = """
                Analyse l'image de ce document d'avertissement. 
                Trouve le code à quatre (04) caractères qui est spécifié après la phrase 'Votre code:'. 
                Réponds UNIQUEMENT avec ce code, sans aucun texte supplémentaire, explication, guillemet ou ponctuation. 
                Si le code n'est pas trouvé, réponds 'ERREUR'.
                """

                try:
                    response = model.generate_content(
                        [password_prompt, password_page_image]
                    )
                    password_content = response.text.strip()
                except Exception as e:
                    st.error(
                        f"Erreur lors de l'appel à Gemini pour le mot de passe: {e}"
                    )
                    password_content = "ERREUR"

                if (
                    not password_content
                    or password_content == "ERREUR"
                    or len(password_content) != 4
                ):
                    st.error(
                        f"❌ Impossible d'obtenir le mot de passe via Gemini. Réponse reçue: {password_content}"
                    )
                    status.update(
                        label="❌ Échec de l'analyse.",
                        state="error",
                        expanded=False,
                    )
                    st.stop()

                st.write(f"✅ Mot de passe extrait par Gemini : ['{password_content}']")
                status.update(
                    label="✅ Mot de passe extrait.",
                    state="complete",
                    expanded=False,
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
                        label="❌ Échec de l'analyse.",
                        state="error",
                        expanded=False,
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
            label="⚙️ Conversion et Analyse en cours...",
            state="running",
            expanded=True,
        )

        # 3. CONVERSION EN IMAGES & ANALYSE GEMINI
        st.write("📄 Conversion du PDF en images...")
        try:
            images = convert_from_bytes(open(decrypted_pdf_path, "rb").read())
            # --- SAUVEGARDE DU NOMBRE DE PAGES DANS L'ÉTAT ---
            st.session_state["num_pages_analyzed"] = len(images)
            # -------------------------------------------------
        except Exception as e:
            st.error(
                f"Erreur Poppler ou de conversion : {e}. Veuillez vérifier l'installation de Poppler."
            )
            st.stop()

        st.write(
            f"👀 {len(images)} pages détectées. L'IA de Gemini commence l'analyse visuelle..."
        )
        progress_bar = st.progress(0)

        all_opportunities = []

        with st.expander("🔍 Aperçu des pages analysées", expanded=False):
            st.write("Les pages sont affichées ici au fur et à mesure de l'analyse.")
            page_cols = st.columns(4)

        for i, page_image in enumerate(images):
            with page_cols[i % 4]:
                st.image(page_image, caption=f"Page {i+1}", use_container_width=True)

            opps = analyze_page_structured(page_image)

            if opps:
                for op in opps:
                    op["page"] = i + 1
                    all_opportunities.append(op)

            progress_bar.progress((i + 1) / len(images))

        # 4. RÉSULTATS (Génération et Sauvegarde dans l'état)
        if all_opportunities:

            # 4.1. Génération du Script
            with st.spinner("1/4 - Rédaction du script audio par l'IA..."):
                script_content = generate_script(all_opportunities)

            # 4.2. Génération de l'Audio
            with st.spinner("2/4 - Génération du fichier audio MP3..."):
                audio_file_bytes = generate_audio(script_content)

            # 4.3. Génération du PDF
            with st.spinner("3/4 - Génération du rapport détaillé PDF..."):
                pdf_bytes = generate_pdf_report(all_opportunities)

            # --- SAUVEGARDE DANS SESSION STATE ---
            st.session_state["analyse_completee"] = True
            st.session_state["all_opportunities"] = all_opportunities
            st.session_state["script_content"] = script_content
            st.session_state["audio_file_bytes"] = audio_file_bytes
            st.session_state["pdf_bytes"] = pdf_bytes
            # --- FIN SAUVEGARDE ---

            status.update(
                label="✅ Analyse terminée et résultats sauvegardés !",
                state="complete",
                expanded=False,
            )

            # Forcer le rafraîchissement pour afficher les résultats persistants immédiatement
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
        st.stop()

    finally:
        # Nettoyage du fichier temporaire déchiffré
        if (
            decrypted_pdf_path
            and isinstance(decrypted_pdf_path, str)
            and os.path.exists(decrypted_pdf_path)
        ):
            os.remove(decrypted_pdf_path)

# ---------------------------------------------------------------------------------------------------------------------
# === BLOC D'AFFICHAGE PERSISTANT DES RÉSULTATS (TOUJOURS EXÉCUTÉ SI ANALYSE TERMINÉE) ===
# ---------------------------------------------------------------------------------------------------------------------

if st.session_state["analyse_completee"]:

    # Récupération des données de l'état
    all_opportunities = st.session_state["all_opportunities"]
    script_content = st.session_state["script_content"]
    audio_file_bytes = st.session_state["audio_file_bytes"]
    pdf_bytes = st.session_state["pdf_bytes"]
    receiver_email = st.session_state["receiver_email"]

    # 1. Envoi automatique
    st.divider()
    st.subheader("🤖 Récapitulatif et Envoi Automatique")

    subject = f"Veille Novatech - {pd.Timestamp.now().strftime('%d/%m/%Y')}"

    col_email_info, col_email_btn = st.columns([3, 1])
    col_email_info.info(
        f"Le rapport (Audio et PDF) a été envoyé à : **{receiver_email}**."
    )

    if col_email_btn.button(
        "🔄 Renvoyer l'Email (si nécessaire)", use_container_width=True
    ):
        if audio_file_bytes and pdf_bytes and receiver_email:
            # Création du corps du mail
            body_list = [f"- {o.get('titre')}" for o in all_opportunities]
            body = (
                f"Bonjour Monsieur le Directeur,\n\nListe des opportunités du jour :\n\n"
                + "\n".join(body_list)
                + f"\n\nLe rapport détaillé (Audio et PDF) est en pièces jointes.\n\nCordialement,\nAbdoul Magid Kanoma\nNovaReader AI"
            )

            with st.spinner(
                f"Envoi de l'Email automatique à **{receiver_email}** en cours..."
            ):
                ok, msg = send_email_pro(
                    SMTP_HOST,
                    SMTP_PORT,
                    SMTP_SENDER,
                    SMTP_PASSWORD,
                    receiver_email,
                    subject,
                    body,
                    audio_file_bytes,  # <-- AUDIO
                    pdf_bytes,  # <-- PDF
                )
                if ok:
                    st.success(msg)
                    st.balloons()
                else:
                    st.error(msg)
        else:
            st.error(
                "❌ Envoi automatique impossible : Audio, PDF ou Email destinataire manquant ou invalide. Vérifiez l'erreur de génération PDF."
            )

    # 2. Indicateurs Clés de Performance
    st.divider()
    kpi1, kpi2, kpi3 = st.columns(3)

    kpi1.metric("Pages Analysées", st.session_state["num_pages_analyzed"])
    kpi2.metric("Opportunités Trouvées", len(all_opportunities))

    if all_opportunities:
        sectors = [op["secteur"] for op in all_opportunities]
        top_sector = pd.Series(sectors).mode()[0] if sectors else "N/A"
    else:
        top_sector = "N/A"
    kpi3.metric("Secteur Majeur", top_sector)

    st.divider()

    # --- NOUVEAU BLOC AVEC ONGLETS (st.tabs) ---
    st.subheader("📋 Résultats de la Veille")

    tab_cards, tab_audio, tab_table = st.tabs(
        ["🖼️ Vue Cartes", "🎙️ Rapport Audio", "📊 Tableau Détails"]
    )

    # --- 1. Onglet Vue Cartes ---
    with tab_cards:
        st.markdown("### 🗺️ Opportunités Détaillées (Cartes)")
        for opp in all_opportunities:
            st.markdown(
                f"""
                <div class="opp-card">
                    <p class="opp-sector">Secteur : {opp['secteur']}</p>
                    <p class="opp-title">{opp['titre']}</p>
                    <p class="opp-date">Date Limite : {opp['date_limite']}</p>
                    <small>Conditions : {opp['conditions']}</small><br>
                    <small>Source : Page {opp['page']}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # --- 2. Onglet Rapport Audio ---
    with tab_audio:
        st.markdown("### 🎙️ Aperçu du Briefing Vocal et PDF")

        # Affichage du Script
        with st.expander("Lire le script détaillé"):
            st.write(script_content)

        # Affichage de l'Audio
        if audio_file_bytes:
            st.audio(audio_file_bytes, format="audio/mp3")
        else:
            st.warning("Aucun audio disponible (échec de la génération).")

        st.markdown("---")

        # Bouton de Téléchargement PDF
        st.subheader("📤 Action Immédiate (Téléchargement PDF)")

        if pdf_bytes:
            st.download_button(
                label="📄 Télécharger le Rapport Détaillé (PDF)",
                data=pdf_bytes,
                file_name=f"Rapport_Detaille_Veille_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
        else:
            st.button(
                "📄 Télécharger le Rapport Détaillé (PDF)",
                disabled=True,
                use_container_width=True,
            )

    # --- 3. Onglet Tableau Détails ---
    with tab_table:
        st.markdown("### 📊 Données Brutes (Tableau)")
        st.dataframe(
            pd.DataFrame(all_opportunities), use_container_width=True, hide_index=True
        )
    # -------------------------------------------------
    # --- FIN NOUVEAU BLOC AVEC ONGLETS ---
    # -------------------------------------------------
