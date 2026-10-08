from fastapi import FastAPI, Request, HTTPException
from datetime import datetime
import json
import os
import urllib.request
import urllib.error

app = FastAPI()

CLIENTES_FILE = "clientes.json"

def carregar_clientes():
    if not os.path.exists(CLIENTES_FILE):
        return {}
    try:
        with open(CLIENTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

stats_data = {
    "total_verificacoes": 0,
    "total_experiencias_enviadas": 0,
    "ultima_conexao": None,
    "ips_conectados": set(),
    "historico_conexoes": []
}

@app.post("/api/v1/verificar-licenca")
async def verificar_licenca(request: Request):
    try:
        dados = await request.json()
    except Exception:
        dados = {}
    
    usuario = dados.get("usuario") or dados.get("Usuario") or "Desconhecido"
    senha = dados.get("senha") or dados.get("Senha") or ""
    licenca = dados.get("licenca") or dados.get("Licenca") or ""
    
    # Validação flexível e direta para o administrador
    autorizado = False
    if str(usuario).strip() == "Adm_adm" and str(senha).strip() == "09870987" and str(licenca).strip() == "PROD-ADM-2026":
        autorizado = True
    else:
        clientes = carregar_clientes()
        if clientes and usuario in clientes:
            if clientes[usuario].get("senha") == senha and clientes[usuario].get("licenca") == licenca:
                autorizado = True

    if not autorizado:
        print(f"AVISO: Tentativa de acesso negado para usuário: {usuario} com dados: {dados}")
        raise HTTPException(status_code=401, detail="Licença inválida ou credenciais incorretas.")

    ip_cliente = request.client.forwarded_for or request.client.host
    
    cidade_origem = "Desconhecida"
    pais_origem = "Desconhecido"
    try:
        url = f"https://ipapi.co/{ip_cliente}/json/"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            geo_resposta = json.loads(response.read().decode())
            if "city" in geo_resposta:
                cidade_origem = geo_resposta.get("city", "Desconhecida")
                pais_origem = geo_resposta.get("country_name", "Desconhecido")
    except Exception:
        pass

    stats_data["total_verificacoes"] += 1
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stats_data["ultima_conexao"] = agora
    stats_data["ips_conectados"].add(ip_cliente)
    
    stats_data["historico_conexoes"].append({
        "usuario": usuario,
        "ip": ip_cliente,
        "cidade": cidade_origem,
        "pais": pais_origem,
        "data_hora": agora
    })
    
    if len(stats_data["historico_conexoes"]) > 50:
        stats_data["historico_conexoes"].pop(0)

    print(f"INFO: TradingServer - Licença autorizada para: {usuario} | IP: {ip_cliente} | Local: {cidade_origem}, {pais_origem}")

    return {
        "status": "sucesso", 
        "mensagem": "Licença validada com sucesso",
        "localizacao": f"{cidade_origem}, {pais_origem}"
    }

@app.post("/api/v1/experiencia")
async def registrar_experiencia(request: Request):
    try:
        dados = await request.json()
    except Exception:
        dados = {}
    stats_data["total_experiencias_enviadas"] += 1
    return {"status": "registrado", "mensagem": "Experiência absorvida."}

@app.get("/api/v1/stats")
def obter_estatisticas():
    return {
        "status": "online",
        "total_verificacoes_licenca": stats_data["total_verificacoes"],
        "total_experiencias_recebidas": stats_data["total_experiencias_enviadas"],
        "ultima_conexao": stats_data["ultima_conexao"],
        "total_ips_unicos_conectados": len(stats_data["ips_conectados"]),
        "ultimas_conexoes": stats_data["historico_conexoes"]
    }
