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
from fpdf import FPDF 
import urllib.parse
# -----------------------------

# =========================================================================
# === CONFIGURATION GLOBALE ===
# =========================================================================
# Configuration de la clé API (Utilisez st.secrets() pour la sécurité en ligne)
API_KEY = "AIzaSyAY4NqDYCpBAebXi3Qb-KMLXBPpuTfvPH0" # Remplacez ceci par une clé sécurisée si possible
os.environ["GOOGLE_API_KEY"] = API_KEY 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-lite') 


st.set_page_config(page_title="NovaReader - Veille Stratégique", page_icon="🚀", layout="wide")

# --- CSS PERSONNALISÉ (DESIGN FINAL - CLAIR & MODERNE) ---
st.markdown("""
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
    
    /* Bouton WhatsApp - Lien stylisé en vert */
    .whatsapp-button {
        background-color: #25d366 !important; 
        color: white !important;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-size: 16px;
        font-weight: bold;
        text-align: center;
        text-decoration: none;
        display: block; /* Important pour prendre toute la largeur */
        line-height: 1.5;
    }
    .whatsapp-button:hover {
        background-color: #128c7e !important; 
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
""", unsafe_allow_html=True)


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
        response = model.generate_content([prompt, image], generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception:
        return []

# --- FONCTIONS EXPORT ET TTS ---

@st.cache_data(show_spinner=False)
def generate_audio(text):
    """Génère l'audio en utilisant gTTS (Cloud TTS, compatible Windows/Linux)."""
    if not text.strip(): 
        return None
    
    st.info("🎙️ Synthèse vocale de haute qualité (gTTS) en cours... (Nécessite Internet)")
    temp_path = None
    
    try:
        tts = gTTS(text=text, lang='fr', timeout=10) 
        
        # Utilisation de tempfile pour l'écriture
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp: 
            temp_path = fp.name
        tts.save(temp_path)
        
        st.success("✅ Fichier audio généré avec succès en format MP3 !")
        
        with open(temp_path, "rb") as f:
            audio_bytes = f.read()
            
        return audio_bytes
        
    except Exception as e:
        st.error(f"Erreur de Synthèse Vocale gTTS : {e}. Cause probable: Connexion instable ou bloquée.")
        return None
        
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)



def generate_pdf_report(script, all_opportunities):
    """Crée un rapport PDF dans un buffer mémoire en utilisant les polices standard (Helvetica)."""
    
    # 1. Utiliser la classe FPDF standard
    class PDF(FPDF):
        def header(self):
            # Utilisation de la police standard nativement chargée
            self.set_font('Helvetica', 'B', 15) 
            self.cell(0, 10, 'Rapport de Veille Stratégique NOVATECH', 0, 1, 'C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8) 
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
            
    pdf = PDF('P', 'mm', 'A4')
    # ATTENTION : L'appel pdf.add_font(...) a été supprimé pour éviter la FileNotFoundError.
    
    pdf.add_page()
    
    # --- Section 1: Briefing Textuel ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Helvetica', 'B', 14) 
    pdf.cell(0, 10, '1. Briefing Vocal (Texte Intégral)', 1, 1, 'L', 1)
    
    pdf.set_font('Helvetica', size=11)
    clean_script = script.replace('\n', ' ') 
    pdf.multi_cell(0, 7, clean_script) 
    pdf.ln(10)

    # --- Section 2: Détails des Opportunités ---
    pdf.set_font('Helvetica', 'B', 14) 
    pdf.cell(0, 10, '2. Détails des Opportunités Trouvées', 1, 1, 'L', 1)
    pdf.ln(5)

    if not all_opportunities:
        pdf.set_font('Helvetica', size=12) 
        pdf.cell(0, 10, 'Aucune opportunité pertinente n\'a été trouvée.', 0, 1)
    else:
        for opp in all_opportunities:
            pdf.set_font('Helvetica', 'B', 12) 
            pdf.set_text_color(141, 47, 47) 
            pdf.multi_cell(0, 6, opp['titre'])
            
            pdf.set_text_color(0, 0, 0) 
            pdf.set_font('Helvetica', 'I', 10) 
            pdf.cell(40, 5, f"Secteur: {opp['secteur']}", 0, 0)
            pdf.cell(50, 5, f"Deadline: {opp['date_limite']}", 0, 0)
            pdf.cell(0, 5, f"Page: {opp['page']}", 0, 1)
            
            pdf.set_font('Helvetica', size=10) 
            pdf.multi_cell(0, 5, f"Conditions: {opp['conditions']}")
            pdf.ln(3)

    # Sauvegarde dans un buffer
    pdf_output = pdf.output(dest='S').encode('latin-1') 
    return pdf_output


def generate_whatsapp_link(number, all_opportunities):
    """Génère un lien "Click-to-Chat" pour WhatsApp avec résumé."""
    clean_number = "".join(filter(str.isdigit, number))
    
    # Logique pour ajouter le préfixe +227
    if not clean_number.startswith("227") and not clean_number.startswith("00227"):
        clean_number = "227" + clean_number.lstrip('0')
    
    # Création du corps du message
    if not all_opportunities:
        text = "Rapport de Veille Novatech : Aucune opportunité pertinente trouvée aujourd'hui."
    else:
        opportunities_summary = [f"• {opp['titre']} ({opp['secteur']}) - Deadline: {opp['date_limite']}" for opp in all_opportunities]
        summary_text = "\n".join(opportunities_summary)
        
        text = (
            "Monsieur le Directeur,\n\n"
            "Voici le résumé des opportunités trouvées dans le journal 'Le Sahel' :\n\n"
            f"{summary_text}\n\n"
            "Le rapport vocal et le PDF complet sont disponibles sur l'application NovaReader."
        )
    
    # Encodage de l'URL
    encoded_text = urllib.parse.quote(text)
    
    whatsapp_url = f"https://wa.me/{clean_number}?text={encoded_text}"
    
    return whatsapp_url, clean_number

# --- LOGIQUE D'AFFICHAGE DU RAPPORT AUDIO/ACTION ---

def display_audio_report(all_opportunities):
    """Contient la logique d'affichage et de génération audio/PDF/WhatsApp."""
    st.subheader("🎙️ Briefing du Directeur")
    
    text_for_script = json.dumps(all_opportunities, ensure_ascii=False)
    
    # 1. Génération du Script
    with st.spinner("Rédaction du script audio par l'IA..."):
        
        script_prompt = f"""
        Agis comme un secrétaire de direction efficace.
        Voici les opportunités JSON trouvées : {text_for_script}.
        
        Rédige un briefing vocal concis, professionnel et structuré pour le Directeur de NOVATECH.
        
        Le texte doit être optimisé pour un DISCORS ORAL, sans utiliser de caractères spéciaux, de listes à puces (*, -) ou de symboles. Utilise des phrases complètes et des transitions fluides.
        
        Structure ton rapport en deux parties claires :
        1. Priorité Numérique : Détaille d'abord et avec emphase toutes les opportunités du secteur Numérique, Informatique et Télécommunications, en citant la date limite et les conditions de soumission pour chaque point trouvé.
        2. Autres Secteurs : Mentionne ensuite, de manière plus brève, les opportunités trouvées dans les autres secteurs (Santé, Éducation, Agriculture, etc.).

        Commence par "Monsieur le Directeur, voici le point de veille stratégique du Sahel de ce jour."
        Termine par : "Vous trouverez le tableau de bord complet ainsi que les détails de soumission de chaque appel d'offres dans l'onglet 'Vue Cartes' de l'application."
        """
        script = model.generate_content(script_prompt).text
    
    with st.expander("Lire le script détaillé"):
        st.write(script)
    
    # 2. Génération de l'Audio
    if script.strip():
        audio_file_bytes = generate_audio(script) 
        if audio_file_bytes:
            st.audio(audio_file_bytes, format='audio/mp3') 
        else:
            st.error("Impossible de générer l'audio.")
    else:
        st.warning("Aucun script généré pour l'audio.")

    st.markdown("---")
    st.subheader("📤 Actions Immédiates (Un Seul Clic)")
    
    # --- Configuration Numéro de Téléphone ---
    whatsapp_number = st.text_input(
        "📱 Numéro WhatsApp du destinataire (+227XXXXXXXX)",
        value="+227 95464196",
        key="whatsapp_target_number"
    )

    col_pdf_dl, col_whatsapp_send = st.columns(2)
    
    # 3. Bouton de Téléchargement PDF
    with col_pdf_dl:
        if script.strip():
            pdf_bytes = generate_pdf_report(script, all_opportunities)
            
            st.download_button(
                label="📄 Télécharger le Rapport PDF",
                data=pdf_bytes,
                file_name=f"Rapport_Veille_Sahel_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
        else:
            st.button("📄 Télécharger le Rapport PDF", disabled=True, use_container_width=True)

    # 4. Lien d'Envoi WhatsApp (Simule l'automatisme)
    with col_whatsapp_send:
        whatsapp_url, clean_number = generate_whatsapp_link(whatsapp_number, all_opportunities)
        
        st.markdown(
            f"""
            <a href="{whatsapp_url}" target="_blank" class="whatsapp-button">
                🚀 Envoyer le Résumé WhatsApp (Cliquez)
            </a>
            <div style='text-align: center; margin-top: 5px; font-size: 11px; color: #7f8c8d;'>
                (Ouvre WhatsApp Web/App pour confirmation)
            </div>
            """,
            unsafe_allow_html=True
        )

# --- INTERFACE PRINCIPALE ---

# Header
st.markdown("<h1 style='text-align: center; color: #212529;'>🚀 NOVATECH • Veille Stratégique</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'><i>Analysez Le Sahel en un clic avec l'IA</i></p>", unsafe_allow_html=True)

st.markdown("---")

# Zone d'upload et mot de passe alignée
col_pdf, col_password_mode = st.columns([1.5, 1])

# --- Colonne 1 : Journal PDF ---
with col_pdf:
    st.markdown('<div style="height: 30px;"></div>', unsafe_allow_html=True)
    st.subheader("Charger les Fichiers et le Mot de Passe")
    uploaded_pdf = st.file_uploader("📥 1. Le Journal (PDF chiffré)", type="pdf")

# --- Colonne 2 : Choix du Mode Mot de Passe ---
with col_password_mode:
    
    password_mode = st.radio(
        "🔑 2. Comment fournir le Mot de Passe ?",
        options=["Fichier PDF par l'IA", "Saisie directe (4 caractères)"],
        index=0,
        horizontal=False,
        key="password_mode_select"
    )

    uploaded_password_file = None
    manual_password = None

    if password_mode == "Fichier PDF par l'IA":
        uploaded_password_file = st.file_uploader(
            "📁 Charger le Fichier PDF contenant le code", 
            type="pdf"
        )
    else:
        st.markdown("🤫 **Saisir le Mot de Passe (4 caractères)**") 
        manual_password = st.text_input(
            label="", 
            type="password",
            placeholder="Entrez le code ici..."
        )
    
# Condition de lancement 
if uploaded_pdf is not None and (uploaded_password_file is not None or manual_password):
    
    col_a, col_b, col_c = st.columns([1,2,1])
    with col_b:
        start_btn = st.button("✨ Lancer l'analyse IA (Déchiffrement + Veille)", use_container_width=True, type="primary")

    if start_btn:
        
        decrypted_pdf_path = None 
        password_content = None 

        try:
            # 1. DÉTERMINATION DU MOT DE PASSE 
            
            if password_mode == "Saisie directe (4 caractères)":
                password_content = manual_password.strip()
                if not (password_content and len(password_content) == 4):
                    st.error("❌ Le mot de passe saisi manuellement doit contenir exactement 4 caractères.")
                    st.stop()
                st.info(f"✅ Mot de passe saisi manuellement : ['{password_content}']")
                
            elif password_mode == "Fichier PDF par l'IA" and uploaded_password_file is not None:
                
                with st.status("🔑 L'IA de Gemini extrait le mot de passe du PDF...", expanded=True) as status:
                    
                    try:
                        password_pdf_bytes = uploaded_password_file.getvalue()
                        password_page_image = convert_from_bytes(password_pdf_bytes, first_page=1, last_page=1)[0]
                    except Exception as e:
                        st.error(f"Erreur de conversion du PDF du mot de passe en image: {e}. Vérifiez l'installation de Poppler.")
                        status.update(label="❌ Échec de l'analyse.", state="error", expanded=False)
                        st.stop()
                        
                    password_prompt = """
                    Analyse l'image de ce document d'avertissement. 
                    Trouve le code à quatre (04) caractères qui est spécifié après la phrase 'Votre code:'. 
                    Réponds UNIQUEMENT avec ce code, sans aucun texte supplémentaire, explication, guillemet ou ponctuation. 
                    Si le code n'est pas trouvé, réponds 'ERREUR'.
                    """
                    
                    try:
                        response = model.generate_content([password_prompt, password_page_image])
                        password_content = response.text.strip()
                    except Exception as e:
                        st.error(f"Erreur lors de l'appel à Gemini pour le mot de passe: {e}")
                        password_content = "ERREUR" 

                    if not password_content or password_content == "ERREUR" or len(password_content) != 4:
                        st.error(f"❌ Impossible d'obtenir le mot de passe via Gemini. Réponse reçue: {password_content}")
                        status.update(label="❌ Échec de l'analyse.", state="error", expanded=False)
                        st.stop()

                    st.write(f"✅ Mot de passe extrait par Gemini : ['{password_content}']")
                    status.update(label="✅ Mot de passe extrait.", state="complete", expanded=False)

            if not password_content:
                st.error("❌ Le mot de passe n'a pas pu être déterminé. Veuillez vérifier vos entrées.")
                st.stop()

            # 2. DÉCHIFFREMENT DU JOURNAL PDF
            with st.status("🔒 Déchiffrement du Journal PDF en cours...", expanded=True) as status:
                pdf_reader = PyPDF2.PdfReader(uploaded_pdf)
                
                if pdf_reader.is_encrypted:
                    if pdf_reader.decrypt(password_content):
                        st.write("✅ Journal PDF déchiffré avec succès. Préparation pour la conversion...")
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_decrypted_pdf:
                            pdf_writer = PyPDF2.PdfWriter()
                            for page_num in range(len(pdf_reader.pages)):
                                pdf_writer.add_page(pdf_reader.pages[page_num])
                            pdf_writer.write(temp_decrypted_pdf)
                            decrypted_pdf_path = temp_decrypted_pdf.name
                            
                    else:
                        st.error("❌ Échec du déchiffrement. Mot de passe incorrect.")
                        status.update(label="❌ Échec de l'analyse.", state="error", expanded=False)
                        st.stop()
                else:
                    st.warning("Le Journal PDF n'est pas chiffré. L'analyse continue...")
                    uploaded_pdf.seek(0) 
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_decrypted_pdf:
                        temp_decrypted_pdf.write(uploaded_pdf.getvalue())
                        decrypted_pdf_path = temp_decrypted_pdf.name 

            status.update(label="⚙️ Conversion et Analyse en cours...", state="running", expanded=True)
            
            # 3. CONVERSION EN IMAGES & ANALYSE GEMINI
            st.write("📄 Conversion du PDF en images...")
            try:
                images = convert_from_bytes(open(decrypted_pdf_path, 'rb').read())
            except Exception as e:
                st.error(f"Erreur Poppler ou de conversion : {e}. Veuillez vérifier l'installation de Poppler.")
                st.stop()
            
            st.write(f"👀 {len(images)} pages détectées. L'IA de Gemini commence l'analyse visuelle...")
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
                        op['page'] = i + 1 
                        all_opportunities.append(op)
                
                progress_bar.progress((i + 1) / len(images))
            
            status.update(label="✅ Analyse terminée !", state="complete", expanded=False)

        except Exception as e:
            st.error(f"Une erreur inattendue est survenue durant le traitement : {e}")
            st.exception(e)
            st.stop()
            
        finally:
            if decrypted_pdf_path and isinstance(decrypted_pdf_path, str) and os.path.exists(decrypted_pdf_path):
                os.remove(decrypted_pdf_path)

        
        # 4. RÉSULTATS (AFFICHAGE)
        if all_opportunities:
            st.divider()
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Pages Analysées", len(images))
            kpi2.metric("Opportunités Trouvées", len(all_opportunities))
            
            if all_opportunities:
                sectors = [op['secteur'] for op in all_opportunities]
                top_sector = pd.Series(sectors).mode()[0] if sectors else "N/A"
            else:
                top_sector = "N/A"
            kpi3.metric("Secteur Majeur", top_sector)
            st.divider()

            tab_visuel, tab_audio, tab_data = st.tabs(["📱 Vue Cartes", "🎧 Rapport Audio", "📊 Tableau Détails"])
            
            # --- ONGLET 1 : CARTES ---
            with tab_visuel:
                st.subheader("Opportunités Filtrées et Triées")
                
                df_opps = pd.DataFrame(all_opportunities)
                
                def parse_date(date_str):
                    if date_str == "Non spécifiée" or pd.isna(date_str): return pd.NaT 
                    try: return pd.to_datetime(date_str, format='%d/%m/%Y', errors='coerce')
                    except: return pd.NaT
                        
                df_opps['date_dt'] = df_opps['date_limite'].apply(parse_date)
                
                col_filter, col_sort = st.columns([2, 1])
                unique_sectors = sorted(df_opps['secteur'].unique())
                selected_sectors = col_filter.multiselect(
                    "Filtre par Secteur", options=unique_sectors, default=unique_sectors, placeholder="Sélectionnez un ou plusieurs secteurs"
                )
                
                sort_option = col_sort.radio(
                    "Trier par Date Limite", options=["Date la plus proche", "Date la plus lointaine", "Par défaut"], index=0, horizontal=True
                )
                
                filtered_df = df_opps[df_opps['secteur'].isin(selected_sectors)]
                
                if sort_option == "Date la plus proche":
                    final_df = filtered_df.sort_values(by='date_dt', ascending=True, na_position='last')
                elif sort_option == "Date la plus lointaine":
                    final_df = filtered_df.sort_values(by='date_dt', ascending=False, na_position='last')
                else:
                    final_df = filtered_df
                
                
                if final_df.empty:
                    st.warning("Aucune opportunité ne correspond aux filtres sélectionnés.")
                else:
                    st.info(f"Affiche **{len(final_df)}** opportunités sur **{len(df_opps)}** au total.")
                    
                    rows = st.columns(2)
                    for idx, item in final_df.iterrows(): 
                        with rows[idx % 2]:
                            html_card = f"""
                            <div class="opp-card">
                                <div class="opp-title">{item['titre']}</div>
                                <div class="opp-sector">{item['secteur']}</div>
                                <div style="margin-top: 10px;">
                                    <span class="opp-date">📅 Date Limite: {item['date_limite']}</span>
                                    <br>
                                    <small style="color: #7f8c8d;">ℹ️ {item['conditions']}</small>
                                    <br>
                                    <small style="color: #95a5a6;">📄 Page {item['page']}</small>
                                </div>
                            </div>
                            """
                            st.markdown(html_card, unsafe_allow_html=True)


            # --- ONGLET 2 : AUDIO, PDF & WHATSAPP ---
            with tab_audio:
                display_audio_report(all_opportunities)


            # --- ONGLET 3 : DATA (TABLEAU) ---
            with tab_data:
                st.subheader("Base de données des Opportunités")
                df_display = pd.DataFrame(all_opportunities)
                st.dataframe(
                    df_display, 
                    column_config={
                        "titre": "Objet de l'appel", "date_limite": "Deadline",
                        "secteur": st.column_config.TextColumn("Secteur", help="Domaine d'activité"),
                        "conditions": "Conditions / Détails de Soumission", "page": "Page Source"
                    },
                    use_container_width=True, hide_index=True
                )

        else:
            st.warning("Aucune opportunité pertinente trouvée aujourd'hui. Vous pouvez consulter l'édition d'hier !")
            
elif uploaded_pdf is not None or (uploaded_password_file is not None or (manual_password and len(manual_password) == 4)):
      st.warning("Veuillez charger **le Journal PDF** ET fournir **le Mot de Passe** (par fichier ou par saisie) pour commencer l'analyse.")