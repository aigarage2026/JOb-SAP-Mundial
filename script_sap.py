import os
import pandas as pd
import google.generativeai as genai
from jobspy import scrape_jobs
from datetime import datetime
import resend

# --- CONFIGURAÇÕES FIXAS ---
RESEND_API_KEY = "re_iXRxD3Bb_Mv9mbFiG4KM9EzCanNG9yzuR"
DESTINATARIO = "Ribeiro_rogerio_r@hotmail.com" # Atualizado conforme solicitado
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

SEARCH_TERMS = [
    "SAP SD",
    "SAP OTC",
    "SAP Project Manager",
    "SAP Product Manager",
    "SAP Localization Brazil",
    "SAP Tax Reform",
    "SAP Latam Expert",
    "SAP Global Leader"
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
        resultado = response.text.upper()
        return "APROVADA" in resultado
    except Exception as e:
        print(f"Erro na chamada da IA: {e}")
        return False

def buscar_e_enviar():
    vagas_finais = []
    
    # Aumentei para 72h e 20 resultados para facilitar o teste inicial
    for termo in SEARCH_TERMS:
        print(f"\n--- 🔍 Iniciando busca para: {termo} ---")
        try:
            jobs = scrape_jobs(
                site_name=["linkedin", "indeed"], 
                search_term=termo, 
                location="Remote", 
                results_wanted=20, 
                hours_old=72 
            )
            
            print(f"Encontradas {len(jobs)} vagas brutas para este termo.")

            for _, job in jobs.iterrows():
                titulo = job['title']
                empresa = job['company']
                
                print(f"🧐 Analisando: {titulo} na {empresa}...")
                
                if analise_ia_vaga(titulo, job.get('description', '')):
                    print(f"  ✅ APROVADA pela IA!")
                    vagas_finais.append({
                        'Título': titulo, 
                        'Empresa': empresa, 
                        'Link': job['job_url']
                    })
                else:
                    print(f"  ❌ Reprovada pelo filtro.")
                    
        except Exception as e:
            print(f"Erro ao buscar no site: {e}")

    if vagas_finais:
        # Remover duplicatas de links
        vagas_unicas = {v['Link']: v for v in vagas_finais}.values()
        print(f"\n📧 Enviando e-mail com {len(vagas_unicas)} vagas aprovadas...")
        
        html = "<h2>Vagas SAP do Dia</h2>" + "".join([
            f"<p><b>{v['Título']}</b> ({v['Empresa']})<br><a href='{v['Link']}'>Link da Vaga</a></p><hr>" 
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
            print(f"❌ Erro ao enviar e-mail pelo Resend: {e}")
    else:
        print("\nℹ️ Nenhuma vaga passou pelos filtros da IA hoje.")

if __name__ == "__main__":
    if not GEMINI_KEY:
        print("❌ ERRO: A GEMINI_API_KEY não foi encontrada nos Secrets do GitHub.")
    else:
        buscar_e_enviar()
