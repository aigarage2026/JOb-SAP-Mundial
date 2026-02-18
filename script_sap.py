import os
import pandas as pd
import google.generativeai as genai
from jobspy import scrape_jobs
from datetime import datetime
import resend
import time

# --- CONFIGURAÇÕES ---
RESEND_API_KEY = "re_iXRxD3Bb_Mv9mbFiG4KM9EzCanNG9yzuR"
DESTINATARIO = "Ribeiro_rogerio_r@hotmail.com"
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

SEARCH_TERMS = [
    "SAP SD", "SAP OTC", "SAP Project Manager", 
    "SAP Product Manager", "SAP Localization Brazil", 
    "SAP Tax Reform", "SAP Latam", "SAP Global Leader"
]

# Inicialização com modelo estável
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    # Mudamos para o modelo mais estável para evitar o erro 404
    model = genai.GenerativeModel('gemini-pro') 

resend.api_key = RESEND_API_KEY

def analise_ia_vaga(titulo, descricao):
    # Tratamento para descrições vazias (o erro NoneType/float que deu no seu log)
    if not descricao or not isinstance(descricao, str):
        descricao = "Descrição não disponível."

    prompt = (
        f"Analise a vaga SAP: '{titulo}'. Descrição: {descricao[:400]}. "
        "Responda APENAS 'APROVADA' se for da área SAP e Remota. "
        "Caso contrário, responda 'REPROVADA'."
    )
    try:
        response = model.generate_content(prompt)
        return "APROVADA" in response.text.upper()
    except Exception as e:
        print(f"DEBUG IA: {e}")
        return True # Se a IA falhar, aprovamos para você não perder a chance

def buscar_e_enviar():
    vagas_aprovadas = []
    
    for termo in SEARCH_TERMS:
        print(f"\n--- 🔎 Buscando: {termo} ---")
        try:
            jobs = scrape_jobs(
                site_name=["linkedin", "indeed"],
                search_term=termo,
                location="Remote",
                results_wanted=15,
                hours_old=72, 
                country_preference_usa=True
            )
            
            if jobs.empty:
                continue

            for _, job in jobs.iterrows():
                titulo = str(job.get('title', 'Sem Título'))
                empresa = str(job.get('company', 'Empresa não informada'))
                # Proteção contra erro de 'float' ou 'None' na descrição
                descricao_vaga = job.get('description', '')
                
                print(f"🧐 Analisando: {titulo} na {empresa}...")
                
                if analise_ia_vaga(titulo, descricao_vaga):
                    print(f"  ✅ APROVADA!")
                    vagas_aprovadas.append({
                        'Título': titulo,
                        'Empresa': empresa,
                        'Link': job.get('job_url', '#')
                    })
                time.sleep(1) # Evita sobrecarga na API
                
        except Exception as e:
            print(f"DEBUG BUSCA: Erro no termo {termo}: {e}")

    if vagas_aprovadas:
        vagas_unicas = {v['Link']: v for v in vagas_aprovadas}.values()
        print(f"📧 Enviando e-mail com {len(vagas_unicas)} vagas...")
        
        html = "<h2>Vagas SAP Localizadas</h2>" + "".join([
            f"<p><b>{v['Título']}</b> - {v['Empresa']}<br><a href='{v['Link']}'>Ver Vaga</a></p><hr>" 
            for v in vagas_unicas
        ])
        
        try:
            resend.Emails.send({
                "from": "SAP_Agent <onboarding@resend.dev>",
                "to": DESTINATARIO,
                "subject": "Vagas de SAP no mundo",
                "html": html
            })
            print("✅ E-mail enviado com sucesso!")
        except Exception as e:
            print(f"❌ ERRO RESEND: {e}")
    else:
        print("ℹ️ Nenhuma vaga aprovada hoje.")

if __name__ == "__main__":
    if not GEMINI_KEY:
        print("❌ ERRO: GEMINI_API_KEY não configurada!")
    else:
        buscar_e_enviar()
