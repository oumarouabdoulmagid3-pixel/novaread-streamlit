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
import urllib.parse

# =========================================================================
# === 1. CONFIGURATION & STYLE ===
# =========================================================================

st.set_page_config(page_title="NovaReader AI", page_icon="💎", layout="wide")

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F4F7F6; color: #2C3E50; }
    .main-header { background: linear-gradient(135deg, #00AEEF 0%, #0077b6 100%); padding: 2rem; border-radius: 0 0 20px 20px; color: white; text-align: center; margin-bottom: 2rem; box-shadow: 0 4px 15px rgba(0, 174, 239, 0.3); }
    .main-header h1 { color: white !important; font-weight: 700; letter-spacing: -1px; }
    .stTextInput > div > div > input { border-radius: 12px; border: 1px solid #E0E0E0; padding: 10px 15px; }
    [data-testid="stFileUploader"] { background-color: white; padding: 20px; border-radius: 15px; border: 1px dashed #00AEEF; }
    
    .stButton > button { width: 100%; background: linear-gradient(90deg, #00AEEF 0%, #0077b6 100%); color: white; font-weight: 600; border: none; padding: 0.75rem 1.5rem; border-radius: 12px; transition: all 0.3s ease; text-transform: uppercase; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 174, 239, 0.6); color: white !important; }
    
    .opp-card { background: white; border-radius: 16px; padding: 24px; margin-bottom: 20px; border: 1px solid #F0F0F0; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05); transition: all 0.3s ease; position: relative; overflow: hidden; }
    .opp-card:hover { transform: translateY(-5px); border-color: #00AEEF; }
    .opp-card::before { content: ''; position: absolute; top: 0; left: 0; width: 6px; height: 100%; background: #00AEEF; }
    .opp-badge { background-color: #E3F8FF; color: #0077b6; padding: 5px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; display: inline-block; margin-bottom: 10px; }
    .opp-title { font-size: 1.1rem; font-weight: 700; color: #1A202C; margin-bottom: 8px; line-height: 1.4; }
    .opp-meta { font-size: 0.85rem; color: #718096; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
    .section-title { color: #00AEEF; font-size: 0.9rem; font-weight: 700; text-transform: uppercase; margin-top: 12px; margin-bottom: 4px; letter-spacing: 0.5px; }
    .section-content { font-size: 0.95rem; color: #4A5568; line-height: 1.5; }
    
    .whatsapp-btn { display: inline-flex; align-items: center; justify-content: center; background-color: #25D366; color: white !important; padding: 10px 20px; border-radius: 50px; text-decoration: none; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease; border: 1px solid #25D366; }
    .whatsapp-btn:hover { background-color: #128C7E; transform: scale(1.05); }
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
model = genai.GenerativeModel("gemini-2.5-flash")

DEFAULT_RECEIVER_EMAIL = "daouda.hamadou@novatech.ne"
DEFAULT_WHATSAPP_NUMBER = "+227 91 01 22 12"

# --- LE CERVEAU STRATÉGIQUE ---
NOVATECH_CONTEXT = """
CONTEXTE ENTREPRISE : NOVATECH Solutions Technologiques (Niamey, Niger).
NOS EXPERTISES CLÉS :
1. Réseaux & Télécoms (Fibre optique, VSAT, Installation LAN/WAN).
2. Énergie (Solaire, Onduleurs, Électricité bâtiment).
3. Développement (Web, Mobile, Logiciels sur mesure).
4. Sécurité Électronique (Vidéosurveillance, Contrôle d'accès).
5. Cloud & Data Center.
6. Formation & Consulting IT.
"""

if "receiver_email" not in st.session_state:
    st.session_state["receiver_email"] = DEFAULT_RECEIVER_EMAIL
if "whatsapp_number" not in st.session_state:
    st.session_state["whatsapp_number"] = DEFAULT_WHATSAPP_NUMBER
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
if "last_uploaded_pdf_name" not in st.session_state:
    st.session_state["last_uploaded_pdf_name"] = None
if "auto_email_sent" not in st.session_state:
    st.session_state["auto_email_sent"] = False

# --- FONCTIONS CORE ---


def clean_markdown_formatting(text):
    if isinstance(text, list):
        text = " ".join([str(x) for x in text])
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(\d+\.)\s", r"<br/>\1 ", text)
    text = re.sub(r"(\n|\s)\*\s", r"<br/>- ", text)
    return text.strip()


def clean_for_audio(text):
    if not text:
        return ""
    t = text
    t = t.replace("**", "").replace("*", "")
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("-", ",")
    return t.strip()


def analyze_entire_pdf(pdf_path, progress_bar):
    """Analyse avec PROMPT STRATÉGIQUE RENFORCÉ."""

    progress_bar.progress(10, text="Envoi du journal au serveur IA...")
    uploaded_file = genai.upload_file(pdf_path, mime_type="application/pdf")

    dots = 0
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(1)
        uploaded_file = genai.get_file(uploaded_file.name)
        dots = (dots + 1) % 4
        progress_bar.progress(30, text=f"Lecture intelligente du document{'.' * dots}")

    if uploaded_file.state.name == "FAILED":
        return []

    progress_bar.progress(60, text="Élaboration de la stratégie pour chaque offre...")

    # --- PROMPT CLÉ : C'EST ICI QUE L'IA DEVIENT INTELLIGENTE ---
    prompt = f"""
    Tu es le Directeur Technique et Stratégique de NOVATECH.
    {NOVATECH_CONTEXT}
    
    TA MISSION :
    1. Analyse ce journal entier.
    2. Repère TOUS les Appels d'Offres où Novatech peut postuler (même partiellement).
    3. Pour chaque offre, Rédige une "Suggestion Stratégique" (Bénéfice Directeur).
    
    RÈGLE POUR LA "SUGGESTION STRATÉGIQUE" :
    - Ne dis PAS : "C'est une bonne opportunité". C'est inutile.
    - DIS PLUTÔT : "Utiliser notre expertise [Expertise X] pour le lot 1 et notre expertise [Expertise Y] pour le lot 2."
    - Explique COMMENT nos domaines (Réseau, Solaire, Dev, Sécurité...) s'appliquent ici.
    - Si c'est du BTP, cherche la partie "Câblage" ou "Électricité" pour nous placer.

    Format JSON attendu :
    [
      {{
        "titre": "Titre complet de l'AO",
        "secteur": "Secteur principal",
        "date_limite": "Date ou 'Non spécifié'",
        "conditions": "Conditions clés (CA, agrément...)",
        "Bénéfice Directeur": "La stratégie concrète : Quel domaine Novatech activer ?",
        "Mise en Oeuvre": "Action technique immédiate (ex: Contacter le partenaire X, Acheter le dossier...)"
      }}
    ]
    Si rien trouvé : []
    """

    try:
        response = model.generate_content(
            [prompt, uploaded_file],
            generation_config={"response_mime_type": "application/json"},
        )
        uploaded_file.delete()
        progress_bar.progress(90, text="Finalisation du rapport...")
        return json.loads(response.text)
    except Exception as e:
        print(f"Erreur API : {e}")
        return []


def generate_script(all_opportunities):
    script_parts = [
        "Bonjour Monsieur le Directeur. Voici les opportunités et ma suggestion stratégique pour chacune."
    ]
    for idx, o in enumerate(all_opportunities):
        titre = clean_for_audio(o.get("titre", ""))
        date = clean_for_audio(o.get("date_limite", ""))
        cond = clean_for_audio(o.get("conditions", "Conditions standards"))
        # Ici l'IA va lire la stratégie concrète (ex: "Utilisons notre pôle solaire...")
        strat = clean_for_audio(o.get("Bénéfice Directeur", "Stratégie à définir"))
        action = clean_for_audio(o.get("Mise en Oeuvre", "Action standard"))

        script_parts.append(f"Opportunité {idx+1}: {titre}.")
        script_parts.append(f"Date limite: {date}.")
        script_parts.append(f"Conditions: {cond}.")
        script_parts.append(f"Suggestion Stratégique: {strat}.")
        script_parts.append(f"Action requise: {action}.")
        script_parts.append("Suivante.")

    script_parts.append("Fin du briefing. Le détail est dans le PDF.")
    return " ".join(script_parts)


@st.cache_data(show_spinner=False)
def generate_audio(text):
    if not text:
        return None
    try:
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
        styles.add(
            ParagraphStyle(
                name="NovaTitle",
                parent=styles["Heading1"],
                textColor=colors.HexColor("#00AEEF"),
            )
        )

        elements = [
            Paragraph(
                "<b>Rapport Veille Stratégique Novatech</b>", styles["NovaTitle"]
            ),
            Spacer(1, 12),
        ]
        for o in all_ops:
            titre = clean_markdown_formatting(o.get("titre", ""))
            secteur = o.get("secteur", "")
            date = o.get("date_limite", "")
            cond = clean_markdown_formatting(o.get("conditions", ""))
            gain = clean_markdown_formatting(o.get("Bénéfice Directeur", ""))
            action = clean_markdown_formatting(o.get("Mise en Oeuvre", ""))

            elements.append(Paragraph(f"<b>📌 {titre}</b>", styles["Heading2"]))
            elements.append(
                Paragraph(f"<i>Secteur: {secteur} | Date: {date}</i>", styles["Normal"])
            )
            elements.append(Spacer(1, 5))
            elements.append(
                Paragraph(f"<b>📋 Conditions d'accès:</b><br/>{cond}", styles["Normal"])
            )
            elements.append(Spacer(1, 5))
            # Mise en valeur de la stratégie
            elements.append(
                Paragraph(
                    f"<b>💎 SUGGESTION STRATÉGIQUE (Expertises à activer):</b><br/>{gain}",
                    styles["Normal"],
                )
            )
            elements.append(Spacer(1, 5))
            elements.append(
                Paragraph(f"<b>🚀 Mise en Oeuvre:</b><br/>{action}", styles["Normal"])
            )
            elements.append(Spacer(1, 15))
            elements.append(Paragraph("_" * 50, styles["Normal"]))
            elements.append(Spacer(1, 15))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    except:
        return None


def send_email_pro(host, port, sender, passw, receiver, sub, all_opportunities, pdf):
    try:
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = receiver
        msg["Subject"] = sub

        list_items = ""
        for o in all_opportunities:
            titre = clean_markdown_formatting(o.get("titre", ""))
            date = o.get("date_limite", "")
            list_items += f"<li><b>{titre}</b> (DL: {date})</li>"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #00AEEF;">💎 Nouvelles Opportunités Détectées</h2>
            <p>Bonjour Monsieur le Directeur,</p>
            <p>L'IA a identifié des appels d'offres correspondant à nos expertises :</p>
            <ul>{list_items}</ul>
            <p><b>Note :</b> Le briefing AUDIO (avec suggestions stratégiques) est prêt pour WhatsApp.</p>
            <p>Veuillez trouver ci-joint le <b>Rapport PDF détaillé</b>.</p>
            <p>Cordialement,<br>NovaReader AI</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))
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
        return True, "Envoyé (PDF uniquement)"
    except Exception as e:
        return False, str(e)


def display_modern_card(opp):
    t = clean_markdown_formatting(opp.get("titre", "")).replace("<br/>", " ")
    c = clean_markdown_formatting(opp.get("conditions", "")).replace("<br/>", "<br>")
    b = clean_markdown_formatting(opp.get("Bénéfice Directeur", "")).replace(
        "<br/>", "<br>"
    )
    m = clean_markdown_formatting(opp.get("Mise en Oeuvre", "")).replace(
        "<br/>", "<br>"
    )

    html = f"""
    <div class="opp-card">
        <span class="opp-badge">{opp.get('secteur','Autre')}</span>
        <div class="opp-title">{t}</div>
        <div class="opp-meta">
            <span>📅 Limite: <b>{opp.get('date_limite','?')}</b></span>
        </div>
        <div class="section-title">📋 Conditions</div>
        <div class="section-content">{c}</div>
        <div class="section-title">💎 Suggestion Stratégique (Expertises)</div>
        <div class="section-content">{b}</div>
        <div class="section-title">🚀 Mise en Œuvre</div>
        <div class="section-content">{m}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# =========================================================================
# === INTERFACE UTILISATEUR ===
# =========================================================================

st.markdown(
    """<div class="main-header"><h1>💎 NovaReader AI</h1><p>L'intelligence artificielle au service de la stratégie Novatech</p></div>""",
    unsafe_allow_html=True,
)

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
        st.session_state["whatsapp_number"] = DEFAULT_WHATSAPP_NUMBER
        st.session_state["last_uploaded_pdf_name"] = uploaded_pdf.name
        st.rerun()

with col_right:
    st.markdown("### 🔐 Envoi & Contacts")
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
        "Email du DG (Pour le PDF)", value=st.session_state["receiver_email"]
    )
    st.session_state["receiver_email"] = rec_email
    wa_num = st.text_input(
        "Numéro WhatsApp DG",
        value=st.session_state["whatsapp_number"],
        placeholder="+227 00 00 00 00",
    )
    st.session_state["whatsapp_number"] = wa_num

st.markdown("<br>", unsafe_allow_html=True)

if not st.session_state["analyse_completee"]:
    col_btn_1, col_btn_2, col_btn_3 = st.columns([1, 2, 1])
    with col_btn_2:
        btn_start = st.button(
            "✨ LANCER L'ANALYSE (OPTIMISÉE)", disabled=not uploaded_pdf
        )

    if btn_start and uploaded_pdf:
        status_container = st.status("⚙️ Initialisation...", expanded=True)
        try:
            # 1. DECRYPTAGE
            pwd = man_pass
            if mode == "IA (Automatique)" and file_pass:
                status_container.update(
                    label="🔑 Recherche du mot de passe...", state="running"
                )
                img = convert_from_bytes(file_pass.getvalue())[0]
                pwd = model.generate_content(
                    [
                        "Trouve le code à 4 chiffres après 'Votre code:'. Réponds JUSTE le code.",
                        img,
                    ]
                ).text.strip()

            if not pwd or len(pwd) != 4:
                status_container.update(label="❌ Erreur code", state="error")
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
                path_decrypted = tmp.name

            # 2. ANALYSE
            status_container.update(
                label="🧠 Envoi à Gemini (Analyse Globale)...", state="running"
            )
            progress_bar = st.progress(0, text="Démarrage de l'analyse...")

            ops = analyze_entire_pdf(path_decrypted, progress_bar)
            os.remove(path_decrypted)

            progress_bar.progress(100, text="Analyse terminée !")

            # 3. GENERATION FINALE
            if ops:
                status_container.update(
                    label="📝 Génération des rapports...", state="running"
                )
                scr = generate_script(ops)
                aud = generate_audio(scr)
                pdf = generate_pdf_report(ops)

                st.session_state.update(
                    {
                        "all_opportunities": ops,
                        "script_content": scr,
                        "audio_file_bytes": aud,
                        "pdf_bytes": pdf,
                        "analyse_completee": True,
                    }
                )

                if pdf and not st.session_state["auto_email_sent"]:
                    sub = f"Veille Stratégique - {pd.Timestamp.now().strftime('%d/%m')}"
                    ok, msg = send_email_pro(
                        SMTP_HOST,
                        SMTP_PORT,
                        SMTP_SENDER,
                        SMTP_PASSWORD,
                        rec_email,
                        sub,
                        ops,
                        pdf,
                    )
                    if ok:
                        st.session_state["auto_email_sent"] = True

                status_container.update(
                    label="✅ Terminé avec succès !", state="complete", expanded=False
                )
                st.rerun()
            else:
                status_container.update(
                    label="⚠️ Aucune opportunité détectée.", state="complete"
                )

        except Exception as e:
            st.error(f"Erreur critique: {e}")

# =========================================================================
# === DASHBOARD DE RÉSULTATS ===
# =========================================================================

if st.session_state["analyse_completee"]:
    st.divider()
    k1, k2, k3 = st.columns(3)
    k1.metric("Opportunités", len(st.session_state["all_opportunities"]))
    k2.metric("Mode", "Analyse Globale (1 requête)")
    k3.metric(
        "Email PDF", "Envoyé ✅" if st.session_state["auto_email_sent"] else "Échec"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    tab_cards, tab_wa, tab_data = st.tabs(
        ["✨ VUE GALERIE", "🎙️ BRIEFING WHATSAPP", "📊 DONNÉES & PDF"]
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

    with tab_wa:
        st.markdown("### 🚀 Envoi WhatsApp Web")
        if st.session_state["audio_file_bytes"]:
            st.audio(st.session_state["audio_file_bytes"])

        c1, c2 = st.columns(2)
        phone = st.session_state["whatsapp_number"].replace(" ", "")
        msg_wa = f"Bonjour DG. Briefing audio du {pd.Timestamp.now().strftime('%d/%m')} ci-joint."
        url_wa = f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(msg_wa)}"

        with c1:
            if st.session_state["audio_file_bytes"]:
                st.download_button(
                    "1️⃣ Télécharger MP3 (Pour envoi)",
                    st.session_state["audio_file_bytes"],
                    "briefing.mp3",
                    "audio/mp3",
                    use_container_width=True,
                )
        with c2:
            st.markdown(
                f'<a href="{url_wa}" target="_blank" class="whatsapp-btn">2️⃣ Ouvrir WhatsApp Web</a>',
                unsafe_allow_html=True,
            )

    with tab_data:
        if st.session_state["pdf_bytes"]:
            st.download_button(
                "⬇️ Télécharger le Rapport PDF",
                st.session_state["pdf_bytes"],
                "rapport.pdf",
                "application/pdf",
                use_container_width=True,
            )
            st.markdown("---")

        df = pd.DataFrame(st.session_state["all_opportunities"])
        if not df.empty:
            for c in ["titre", "conditions", "Bénéfice Directeur", "Mise en Oeuvre"]:
                if c in df.columns:
                    df[c] = df[c].apply(lambda x: re.sub(r"<[^>]+>", "", str(x)))
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Export CSV", df.to_csv().encode("utf-8"), "data.csv", "text/csv"
            )
