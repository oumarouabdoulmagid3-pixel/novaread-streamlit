import google.generativeai as genai
import os

# Remplace par ta clé API (celle qui commence par AIza)
api_key = "AIzaSyAY4NqDYCpBAebXi3Qb-KMLXBPpuTfvPH0" 

genai.configure(api_key=api_key)

print("--- Liste des modèles disponibles ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Erreur : {e}")