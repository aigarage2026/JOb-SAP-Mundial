import os
import pandas as pd
import google.generativeai as genai
from jobspy import scrape_jobs
from datetime import datetime
import resend

# --- CONFIGURAÇÕES FIXAS ---
RESEND_API_KEY = "re_iXRxD3Bb_Mv9mbFiG4KM9EzCanNG9yzuR"
DESTINATARIO = "S_Gianisella@hotmail.com"
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

SEARCH_TERMS = [
    "SAP SD OTC Remote Anywhere", 
    "SAP Project Manager Brazil Localization",
    "SAP Product Manager Tax Reform",
    "SAP Latam Expert Remote Contractor",
    "SAP Brazil Localization Global Leader"
]

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
resend.api_key = RESEND_API_KEY

def analise_ia_vaga(titulo, descricao):
    prompt = (
        f"Analise a vaga SAP: '{titulo}'. Descrição: {descricao[:500]}. "
        "Responda APENAS 'APROVADA' se for SD, OTC, Project/Product Manager ou Liderança, "
        "tiver foco em Localização Brasil/Latam/Tax Reform e aceitar Remote Anywhere. "
        "Caso contrário, responda 'REPROVADA'."
    )
    try:
        response = model.generate_content(prompt)
        return "APROVADA" in response.text.upper()
    except:
        return False

def buscar_e_enviar():
    vagas_finais = []
    for termo in SEARCH_TERMS:
        print(f"Buscando {termo}...")
        jobs = scrape_jobs(site_name=["linkedin", "indeed"], search_term=termo, location="Remote", results_wanted=10, hours_old=24)
        for _, job in jobs.iterrows():
            if analise_ia_vaga(job['title'], job.get('description', '')):
                vagas_finais.append({'Título': job['title'], 'Empresa': job['company'], 'Link': job['job_url']})
    
    if vagas_finais:
        # Remover duplicatas
        vagas_unicas = {v['Link']: v for v in vagas_finais}.values()
        html = "<h2>Vagas SAP do Dia</h2>" + "".join([f"<p><b>{v['Título']}</b> ({v['Empresa']})<br><a href='{v['Link']}'>Link</a></p>" for v in vagas_unicas])
        resend.Emails.send({"from": "SAP_Agent <onboarding@resend.dev>", "to": DESTINATARIO, "subject": "Vagas de SAP no mundo", "html": html})

if __name__ == "__main__":
    buscar_e_enviar()
