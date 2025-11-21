import streamlit as st
import os
import google.generativeai as genai
from pdf2image import convert_from_bytes
import tempfile
import json
import pandas as pd
import requests
import PyPDF2
# --- IMPORT CLOUD TTS ---
from gtts import gTTS
import io 

# =========================================================================
# === CONFIGURATION GLOBALE ===
# =========================================================================
# Votre clé API doit être mise à jour ici ou sécurisée via st.secrets
API_KEY = "AIzaSyAY4NqDYCpBAebXi3Qb-KMLXBPpuTfvPH0"
os.environ["GOOGLE_API_KEY"] = API_KEY 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-lite') 


st.set_page_config(page_title="NovaReader", page_icon="🚀", layout="wide")

# --- CSS PERSONNALISÉ (Identique) ---
st.markdown("""
<style>
    /* 1. PALETTE GLOBALE ET FOND */
    .stApp {
        background-color: #f8f9fa; /* Fond Blanc très très légèrement cassé */
        color: #212529; /* Texte général noir profond */
    }
    h1, h2, h3, h4, h5, h6 {
        color: #212529; /* Titres noir profond */
    }
    
    /* 2. COULEUR PRIMAIRE (Bordeaux/Rouille) */
    :root {
        --primary-color: #8d2f2f; 
        --secondary-color: #f1f3f5; /* Gris clair pour le fond des tags/secteurs */
    }

    /* 3. UPLOAD FILE & CONTENEURS PRINCIPAUX (CLARTÉ ET ALIGNEMENT) */
    
    /* Conteneur du fichier une fois uploadé */
    [data-testid="stUploadedFile"] {
        background-color: #e9ecef !important; /* Petit fond gris pour faire ressortir */
        border-radius: 5px;
        padding: 5px;
    }
    
    /* --- CORRECTION FINALE DU NOM DE FICHIER --- */
    /* Cible tous les textes et les petites icônes pour forcer le NOIR */
    [data-testid="stUploadedFile"] div, 
    [data-testid="stUploadedFile"] span,
    [data-testid="stUploadedFile"] small, 
    [data-testid="stUploadedFile"] svg {
        color: #000000 !important; /* Force le texte en noir */
        fill: #000000 !important; /* Force l'icône en noir */
    }
    
    /* Renforce l'affichage du nom du fichier */
    [data-testid="stUploadedFile"] div {
        font-weight: 600 !important;
    }
    /* --- FIN CORRECTION NOM FICHIER --- */


    /* 3. STYLE DE LA ZONE D'UPLOAD GÉNÉRALE */
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

    /* Correction du champ de saisie du mot de passe */
    [data-testid="stTextInput"] input {
        background-color: white !important; 
        color: #000000 !important; 
        border: 1px solid #ced4da; 
        border-radius: 5px;
    }
    /* Cible le texte du placeholder ("Entrez le code ici...") */
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
            
    /* 6. CORRECTION DIVERSES (LISIBILITÉ PARFAITE) */
    
    /* 6.1. Correction du texte des statuts, expanders et radio en NOIR sur fond clair */
    div[data-testid="stStatusContainer"] p,
    div[data-testid="stExpander"] p,
    div[data-testid="stRadio"] label p,
    div[data-testid="stTabs"] button,
    div[data-testid="stExpander"] button {
        color: #212529 !important; 
    }
    
    /* 6.2. Statut / Expander (Passage au BLANC pour un look épuré) */
    div[data-testid="stStatusContainer"] > div,
    div[data-testid="stExpander"] > div {
        background-color: #f1f3f5; /* Couleur secondaire, un gris très clair */
        border-radius: 10px;
        border: 1px solid #ced4da; /* Bordure légèrement plus visible */
    }
    
    /* 6.3. st.metric (KPI) - Lisibilité des valeurs */
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #8d2f2f !important; /* Couleur primaire (Bordeaux) pour les valeurs */
        font-weight: bold; 
    }
    /* 6.4. st.metric (KPI) - Correction Libellés */
    div[data-testid="stMetricLabel"] p {
        color: #000000 !important; /* Noir Pur pour les libellés */
        font-weight: bold !important;
    }

    /* 6.5. Correction des couleurs des icônes/éléments Streamlit */
    div[data-testid="stTabs"] svg {
        fill: #212529 !important; /* Icônes des onglets en noir */
    }
    div[data-testid="stRadio"] label:nth-child(1) span:first-child > div {
        background-color: #8d2f2f !important; /* Point radio en couleur primaire */
    }
    div[data-testid="stRadio"] label:nth-child(2) span:first-child > div {
        background-color: #212529 !important; /* Point radio en noir */
    }
    
    /* Cacher le menu hamburger et le footer de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# --- FONCTIONS ---

def analyze_page_structured(image):
    """Demande un JSON strict à l'IA avec le prompt DG mis à jour."""
    prompt = """
    Tu es un analyste de veille stratégique pour le secteur du Numérique.
    Analyse cette page du journal 'Le Sahel'.

    Ton objectif est d'identifier toutes les opportunités d'Appels d'Offres et de business pertinentes pour NOVATECH, en te concentrant sur les secteurs suivants au Niger, comme demandé par la Direction Générale :
    1. Numérique, Informatique, Télécommunications (Priorité absolue)
    2. Éducation
    3. Santé
    4. Agriculture
    5. Environnement
    6. Services E-administratifs, Gouvernance Électronique (E-Gouv)
    7. Infrastructures, BTP (si fortement lié à la technologie ou si un détail clé est présent).

    Réponds UNIQUEMENT au format JSON (liste d'objets). Si aucune opportunité pertinente n'est trouvée, renvoie une liste JSON vide [].
    Chaque objet doit inclure les clés suivantes : 
    "titre" : Le titre complet ou l'objet de l'appel d'offres.
    "secteur" : Le secteur le plus pertinent, choisi strictement dans la liste ci-dessus.
    "date_limite" : La date limite de dépôt de dossier (JJ/MM/AAAA) ou "Non spécifiée" si absente.
    "conditions" : Un résumé concis des conditions de soumission (ex: prix du dossier, lieu de dépôt, caution, pièces à fournir).
    """

    try:
        response = model.generate_content([prompt, image], generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        return []

# NOUVELLE FONCTION TTS BASÉE SUR LE CLOUD (gTTS)
@st.cache_data(show_spinner=False)
def generate_audio_cloud(text):
    """
    Génère l'audio en utilisant l'API Google Text-to-Speech (gTTS).
    Ceci est la solution la plus compatible pour le déploiement en ligne (Windows/Linux/Mac).
    """
    if not text.strip(): 
        return None
    
    st.info("🎙️ Synthèse vocale CLOUD (gTTS) en cours... Ceci garantit la compatibilité Windows/Linux.")
    
    try:
        # Création d'un objet gTTS en français (fr)
        tts = gTTS(text=text, lang='fr', tld='fr')
        
        # Utilisation d'un buffer mémoire (BytesIO) pour éviter d'écrire sur le disque
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        
        audio_bytes = fp.read()
            
        st.success("✅ Audio généré par Google Cloud TTS.")
        return audio_bytes
        
    except Exception as e:
        st.error(f"❌ Erreur de Synthèse Vocale CLOUD (gTTS) : {e}. Le service Google TTS est peut-être inaccessible.")
        return None


def display_audio_report(all_opportunities):
    """Contient la logique d'affichage et de génération audio dans l'onglet."""
    st.subheader("🎙️ Briefing du Directeur")
    
    text_for_script = json.dumps(all_opportunities, ensure_ascii=False)
    
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
    
    if script.strip():
        # Appel à la nouvelle fonction CLOUD
        audio_file_bytes = generate_audio_cloud(script) 
        if audio_file_bytes:
            st.audio(audio_file_bytes, format='audio/mp3') 
        else:
            st.error("Impossible de lire l'audio. Le service gTTS a échoué.")
    else:
        st.warning("Aucun script généré pour l'audio.")

# --- INTERFACE ---

# Header
st.markdown("<h1 style='text-align: center; color: #212529;'>🚀 NOVATECH • Veille Stratégique</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'><i>Analysez Le Sahel en un clic avec l'IA</i></p>", unsafe_allow_html=True)

st.markdown("---")

# Zone d'upload modifiée pour la flexibilité et l'alignement
col_pdf, col_password_mode = st.columns([1.5, 1])

# --- Colonne 1 : Journal PDF ---
with col_pdf:
    st.markdown('<div style="height: 30px;"></div>', unsafe_allow_html=True)
    st.subheader("Charger les Fichiers et le Mot de Passe")
    uploaded_pdf = st.file_uploader("📥 1. Le Journal (PDF chiffré)", type="pdf")

# --- Colonne 2 : Choix du Mode Mot de Passe (Optimisé pour l'alignement) ---
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
        # Correction de l'avertissement Streamlit pour le label vide
        st.markdown("🤫 **Saisir le Mot de Passe (4 caractères)**") 
        manual_password = st.text_input(
            label="Mot de passe du journal", # Label non vide pour l'accessibilité
            type="password",
            placeholder="Entrez le code ici...",
            label_visibility="hidden" # Le masque visuellement
        )
    
# Condition de lancement 
if uploaded_pdf is not None and (uploaded_password_file is not None or (manual_password and len(manual_password) == 4)):
    
    col_a, col_b, col_c = st.columns([1,2,1])
    with col_b:
        # Correction de l'ancienne syntaxe use_container_width
        start_btn = st.button("✨ Lancer l'analyse IA (Déchiffrement + Veille)", width='stretch', type="primary")

    if start_btn:
        
        decrypted_pdf_path = None 
        password_content = None 

        try:
            # 1. DÉTERMINATION DU MOT DE PASSE (LOGIQUE FLEXIBLE)
            
            if password_mode == "Saisie directe (4 caractères)":
                password_content = manual_password.strip()
                if not (password_content and len(password_content) == 4):
                    st.error("❌ Le mot de passe saisi manuellement doit contenir exactement 4 caractères.")
                    st.stop()
                st.info(f"✅ Mot de passe saisi manuellement : ['{password_content}']")
                
            elif password_mode == "Fichier PDF par l'IA" and uploaded_password_file is not None:
                
                # --- LOGIQUE D'EXTRACTION GEMINI ---
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

            # Vérification finale
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
                with open(decrypted_pdf_path, 'rb') as f:
                    images = convert_from_bytes(f.read())

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
            
            # --- ONGLET 1 : CARTES (MODERNE AVEC FILTRES) ---
            with tab_visuel:
                st.subheader("Opportunités Filtrées et Triées")
                
                df_opps = pd.DataFrame(all_opportunities)
                
                def parse_date(date_str):
                    if date_str == "Non spécifiée" or pd.isna(date_str):
                        return pd.NaT 
                    try:
                        return pd.to_datetime(date_str, format='%d/%m/%Y', errors='coerce')
                    except:
                        return pd.NaT
                        
                df_opps['date_dt'] = df_opps['date_limite'].apply(parse_date)
                
                col_filter, col_sort = st.columns([2, 1])
                
                unique_sectors = sorted(df_opps['secteur'].unique())
                selected_sectors = col_filter.multiselect(
                    "Filtre par Secteur",
                    options=unique_sectors,
                    default=unique_sectors,
                    placeholder="Sélectionnez un ou plusieurs secteurs"
                )
                
                sort_option = col_sort.radio(
                    "Trier par Date Limite",
                    options=["Date la plus proche", "Date la plus lointaine", "Par défaut"],
                    index=0,
                    horizontal=True
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


            # --- ONGLET 2 : AUDIO ---
            with tab_audio:
                display_audio_report(all_opportunities)


            # --- ONGLET 3 : DATA (TABLEAU) ---
            with tab_data:
                st.subheader("Base de données des Opportunités")
                df_display = pd.DataFrame(all_opportunities)
                st.dataframe(
                    df_display, 
                    column_config={
                        "titre": "Objet de l'appel",
                        "date_limite": "Deadline",
                        "secteur": st.column_config.TextColumn("Secteur", help="Domaine d'activité"),
                        "conditions": "Conditions / Détails de Soumission", 
                        "page": "Page Source"
                    },
                    width='stretch', 
                    hide_index=True
                )

        else:
            st.warning("Aucune opportunité pertinente trouvée aujourd'hui. L'analyse est terminée, mais le journal ne contenait pas d'appels d'offres pertinents pour NOVATECH.")
            
elif uploaded_pdf is not None or (uploaded_password_file is not None or (manual_password and len(manual_password) == 4)):
      st.warning("Veuillez charger **le Journal PDF** ET fournir **le Mot de Passe** (par fichier ou par saisie) pour commencer l'analyse.")