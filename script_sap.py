import os
import pandas as pd
import google.generativeai as genai
from jobspy import scrape_jobs
from datetime import datetime
import resend
import time

# --- CONFIGURAÇÕES ---
RESEND_API_KEY = "re_iXRxD3Bb_Mv9mbFiG4KM9EzCanNG9yzuR"
DESTINATARIO = "aigarage2026@gmail.com"
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

SEARCH_TERMS = [
    "SAP SD Remote", "SAP OTC Remote", "SAP Project Manager Remote", 
    "SAP Product Manager Remote", "SAP Localization Brazil Remote", 
    "SAP Tax Reform Remote", "SAP Latam Remote", "SAP Global Leader Remote"
]

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest') 

resend.api_key = RESEND_API_KEY

def analise_ia_vaga(titulo, descricao):
    if not descricao or not isinstance(descricao, str):
        descricao = "Descrição não disponível."

    # PROMPT COM KILL SWITCH (REGRAS DE EXCLUSÃO)
    prompt = (
        f"Analise a vaga SAP: '{titulo}'. Descrição: {descricao[:700]}. "
        "REGRAS DE EXCLUSÃO (KILL SWITCH): "
        "Responda 'REPROVADA' se a descrição mencionar: "
        "- US Citizen Only ou US Citizenship required "
        "- Green Card required / Permanent Resident "
        "- No C2C / No Corp-to-Corp "
        "- Must reside in the US / No offshore "
        "- Modelo Híbrido ou Presencial. "
        "\nCaso a vaga seja 100% REMOTA, aceite contractors globais e seja da área SAP, responda 'APROVADA'. "
        "Responda APENAS 'APROVADA' ou 'REPROVADA'."
    )
    
    try:
        response = model.generate_content(prompt)
        return "APROVADA" in response.text.upper()
    except Exception as e:
        print(f"⚠️ Alerta IA: {e}")
        # Em caso de erro técnico na IA, aprovamos para análise manual do usuário
        return True 

def buscar_e_enviar():
    vagas_aprovadas = []
    
    for termo in SEARCH_TERMS:
        print(f"\n--- 🔎 Buscando: {termo} ---")
        try:
            jobs = scrape_jobs(
                site_name=["linkedin", "indeed"],
                search_term=termo,
                location="Remote",
                is_remote=True,
                results_wanted=20,
                hours_old=72, 
                country_preference_usa=True
            )
            
            if jobs.empty:
                continue

            for _, job in jobs.iterrows():
                titulo = str(job.get('title', 'Sem Título'))
                empresa = str(job.get('company', 'Empresa não informada'))
                descricao_vaga = job.get('description', '')
                
                print(f"🧐 Analisando: {titulo} na {empresa}...")
                
                if analise_ia_vaga(titulo, descricao_vaga):
                    print(f"  ✅ APROVADA!")
                    vagas_aprovadas.append({
                        'Título': titulo,
                        'Empresa': empresa,
                        'Link': job.get('job_url', '#')
                    })
                else:
                    print(f"  ❌ REPROVADA (Kill Switch: Restrição de Cidadania/Local/Vínculo).")
                
                time.sleep(1) 
                
        except Exception as e:
            print(f"❌ Erro na busca do termo {termo}: {e}")

    if vagas_aprovadas:
        vagas_unicas = {v['Link']: v for v in vagas_aprovadas}.values()
        print(f"📧 Enviando e-mail com {len(vagas_unicas)} vagas filtradas...")
        
        html = f"<h2>Relatório SAP Global Remote - {datetime.now().strftime('%d/%m/%Y')}</h2>"
        html += "<p style='color: gray;'>Filtros: Sem restrição de cidadania US, 100% Remoto, SAP Funcional/Gestão.</p><hr>"
        html += "".join([
            f"<div style='margin-bottom:15px;'><b>{v['Título']}</b> - {v['Empresa']}<br>"
            f"<a href='{v['Link']}'>Clique aqui para ver a vaga</a></div><hr>" 
            for v in vagas_unicas
        ])
        
        try:
            resend.Emails.send({
                "from": "SAP_Agent <onboarding@resend.dev>",
                "to": DESTINATARIO,
                "subject": "🎯 Vagas SAP (Global Remote Only)",
                "html": html
            })
            print(f"✅ E-mail enviado com sucesso para {DESTINATARIO}!")
        except Exception as e:
            print(f"❌ ERRO NO RESEND: {e}")
    else:
        print("ℹ️ Nenhuma vaga compatível com os critérios (Kill Switch ativado para a maioria).")

if __name__ == "__main__":
    if not GEMINI_KEY:
        print("❌ ERRO: GEMINI_API_KEY não encontrada nos Secrets do GitHub.")
    else:
        buscar_e_enviar()
