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

# Termos otimizados com a palavra Remote
SEARCH_TERMS = [
    "SAP SD Remote", "SAP OTC Remote", "SAP Project Manager Remote", 
    "SAP Product Manager Remote", "SAP Localization Brazil Remote", 
    "SAP Tax Reform Remote", "SAP Latam Remote", "SAP Global Leader Remote"
]

# Inicialização com modelo estável
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-pro') 

resend.api_key = RESEND_API_KEY

def analise_ia_vaga(titulo, descricao):
    if not descricao or not isinstance(descricao, str):
        descricao = "Descrição não disponível."

    # Prompt ultra-focado em Trabalho Remoto Global
    prompt = (
        f"Analise a vaga SAP: '{titulo}'. Descrição: {descricao[:500]}. "
        "Critério de Aprovação: A vaga deve ser 100% REMOTA (Work from home/Remote/Anywhere). "
        "Se a vaga mencionar modelo Híbrido, Escritório ou Cidade específica para presença física, responda 'REPROVADA'. "
        "Responda APENAS 'APROVADA' ou 'REPROVADA'."
    )
    try:
        response = model.generate_content(prompt)
        return "APROVADA" in response.text.upper()
    except Exception as e:
        print(f"DEBUG IA: {e}")
        return False # Em caso de dúvida sobre ser remoto, não enviamos

def buscar_e_enviar():
    vagas_aprovadas = []
    
    for termo in SEARCH_TERMS:
        print(f"\n--- 🔎 Buscando Remoto: {termo} ---")
        try:
            # Filtro de localização definido como Remote e parâmetro is_remote=True
            jobs = scrape_jobs(
                site_name=["linkedin", "indeed"],
                search_term=termo,
                location="Remote",
                is_remote=True, # Força a busca apenas por vagas marcadas como remotas
                results_wanted=15,
                hours_old=72, 
                country_preference_usa=True
            )
            
            if jobs.empty:
                print(f"Nenhuma vaga nova encontrada para {termo}")
                continue

            for _, job in jobs.iterrows():
                titulo = str(job.get('title', 'Sem Título'))
                empresa = str(job.get('company', 'Empresa não informada'))
                descricao_vaga = job.get('description', '')
                
                print(f"🧐 Analisando Remoto: {titulo} na {empresa}...")
                
                if analise_ia_vaga(titulo, descricao_vaga):
                    print(f"  ✅ APROVADA (100% Remota)!")
                    vagas_aprovadas.append({
                        'Título': titulo,
                        'Empresa': empresa,
                        'Link': job.get('job_url', '#')
                    })
                else:
                    print(f"  ❌ Descartada (Não é 100% remota ou perfil errado).")
                
                time.sleep(1) # Respeita o limite da API
                
        except Exception as e:
            print(f"DEBUG BUSCA: Erro no termo {termo}: {e}")

    if vagas_aprovadas:
        # Remover duplicatas de links
        vagas_unicas = {v['Link']: v for v in vagas_aprovadas}.values()
        print(f"📧 Enviando e-mail com {len(vagas_unicas)} vagas aprovadas...")
        
        html = "<h2>Vagas SAP 100% Remotas Localizadas</h2>" + "".join([
            f"<p><b>{v['Título']}</b> - {v['Empresa']}<br><a href='{v['Link']}'>Ver Vaga</a></p><hr>" 
            for v in vagas_unicas
        ])
        
        try:
            resend.Emails.send({
                "from": "SAP_Agent <onboarding@resend.dev>",
                "to": DESTINATARIO,
                "subject": "Vagas de SAP no mundo - 100% Remoto",
                "html": html
            })
            print("✅ E-mail enviado com sucesso!")
        except Exception as e:
            print(f"❌ ERRO RESEND: {e}")
    else:
        print("ℹ️ Nenhuma vaga 100% remota aprovada hoje.")

if __name__ == "__main__":
    if not GEMINI_KEY:
        print("❌ ERRO: GEMINI_API_KEY não configurada nos Secrets do GitHub!")
    else:
        buscar_e_enviar()
