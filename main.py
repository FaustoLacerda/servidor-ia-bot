from fastapi import FastAPI, Request
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

@app.api_route("/api/v1/verificar-licenca", methods=["GET", "POST"])
async def verificar_licenca(request: Request):
    dados = {}
    
    if request.query_params:
        dados = dict(request.query_params)
    if not dados:
        try:
            dados = await request.json()
        except Exception:
            pass
    if not dados:
        try:
            form_data = await request.form()
            dados = dict(form_data)
        except Exception:
            pass
    
    usuario = dados.get("usuario") or dados.get("Usuario") or dados.get("user") or "Adm_adm"
    autorizado = True

    # Extrai o primeiro IP válido caso venha numa lista com vírgulas (ex: "45.71.124.41, 172.71...")
    ip_bruto = request.headers.get("x-forwarded-for")
    if not ip_bruto and request.client:
        ip_bruto = request.client.host
    
    if ip_bruto:
        ip_cliente = ip_bruto.split(",")[0].strip()
    else:
        ip_cliente = "Desconhecido"

    cidade_origem = "Desconhecida"
    pais_origem = "Desconhecido"
    
    if ip_cliente != "Desconhecido" and ip_cliente != "127.0.0.1" and ip_cliente != "localhost":
        try:
            # Usando ip-api.com que retorna dados detalhados de forma gratuita e rápida
            url = f"http://ip-api.com/json/{ip_cliente}?fields=status,country,city"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                geo_resposta = json.loads(response.read().decode())
                if geo_resposta.get("status") == "success":
                    cidade_origem = geo_resposta.get("city", "Desconhecida")
                    pais_origem = geo_resposta.get("country", "Desconhecido")
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

@app.api_route("/api/v1/experiencia", methods=["GET", "POST"])
async def registrar_experiencia(request: Request):
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
