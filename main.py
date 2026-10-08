from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
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

    ip_bruto = request.headers.get("x-forwarded-for")
    if not ip_bruto and request.client:
        ip_bruto = request.client.host

    ip_cliente = "Desconhecido"
    if ip_bruto:
        lista_ips = [ip.strip() for ip in ip_bruto.split(",")]
        for ip in lista_ips:
            if ip and not ip.startswith(("10.", "192.168.", "127.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")):
                ip_cliente = ip
                break
        if ip_cliente == "Desconhecido" and lista_ips:
            ip_cliente = lista_ips[0]

    cidade_origem = "Desconhecida"
    pais_origem = "Desconhecido"
    bairro_origem = "Desconhecido"
    
    if ip_cliente != "Desconhecido":
        try:
            url = f"http://ip-api.com/json/{ip_cliente}?fields=status,country,city,district"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                geo_resposta = json.loads(response.read().decode())
                if geo_resposta.get("status") == "success":
                    cidade_origem = geo_resposta.get("city", "Desconhecida")
                    pais_origem = geo_resposta.get("country", "Desconhecido")
                    bairro_origem = geo_resposta.get("district") or "Desconhecido"
        except Exception:
            pass

    stats_data["total_verificacoes"] += 1
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stats_data["ultima_conexao"] = agora
    stats_data["ips_conectados"].add(ip_cliente)
    
    stats_data["historico_conexoes"].append({
        "usuario": usuario,
        "ip": ip_cliente,
        "pais": pais_origem,
        "cidade": cidade_origem,
        "bairro": bairro_origem,
        "data_hora": agora
    })
    
    if len(stats_data["historico_conexoes"]) > 50:
        stats_data["historico_conexoes"].pop(0)

    return {
        "status": "sucesso", 
        "mensagem": "Licença validada com sucesso",
        "localizacao": f"{pais_origem}, {cidade_origem} - Bairro: {bairro_origem}"
    }

@app.api_route("/api/v1/experiencia", methods=["GET", "POST"])
async def registrar_experiencia(request: Request):
    stats_data["total_experiencias_enviadas"] += 1
    return {"status": "registrado", "mensagem": "Experiência absorvida."}

# ENDPOINT DE ESTATÍSTICAS COM DASHBOARD VISUAL E MAPA MUNDIAL
@app.get("/api/v1/stats", response_class=HTMLResponse)
def obter_estatisticas():
    ultimas_conexoes_html = ""
    for c in reversed(stats_data["historico_conexoes"]):
        ultimas_conexoes_html += f"""
        <tr>
            <td><span class="badge">{c['usuario']}</span></td>
            <td><code>{c['ip']}</code></td>
            <td>🌍 {c['pais']}</td>
            <td>🏙️ {c['cidade']}</td>
            <td>📍 {c['bairro']}</td>
            <td>🕒 {c['data_hora']}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Trading AI - Painel de Controlo</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            :root {{
                --bg-color: #0f172a;
                --card-bg: #1e293b;
                --text-color: #f8fafc;
                --accent-color: #38bdf8;
                --border-color: #334155;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-color);
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            h1 {{
                font-size: 24px;
                margin-bottom: 5px;
                color: #38bdf8;
            }}
            .subtitle {{
                color: #94a3b8;
                margin-bottom: 25px;
                font-size: 14px;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .card {{
                background-color: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }}
            .card h3 {{
                margin: 0 0 10px 0;
                font-size: 14px;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .card .value {{
                font-size: 28px;
                font-weight: bold;
                color: #f8fafc;
            }}
            .status-online {{
                color: #4ade80 !important;
            }}
            #map {{
                height: 400px;
                border-radius: 12px;
                border: 1px solid var(--border-color);
                margin-bottom: 30px;
            }}
            .table-container {{
                background-color: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                overflow: hidden;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                text-align: left;
                font-size: 14px;
            }}
            th, td {{
                padding: 12px 16px;
                border-bottom: 1px solid var(--border-color);
            }}
            th {{
                background-color: #111827;
                color: #94a3b8;
                font-weight: 600;
            }}
            tr:hover {{
                background-color: rgba(56, 189, 248, 0.05);
            }}
            .badge {{
                background-color: #0284c7;
                color: white;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Painel de Controlo & Servidor IA</h1>
            <div class="subtitle">Monitorização em tempo real dos robôs de Trading e Licenças</div>

            <div class="grid">
                <div class="card">
                    <h3>Estado do Servidor</h3>
                    <div class="value status-online">● ONLINE</div>
                </div>
                <div class="card">
                    <h3>Validações de Licença</h3>
                    <div class="value">{stats_data["total_verificacoes"]}</div>
                </div>
                <div class="card">
                    <h3>Experiências IA Recebidas</h3>
                    <div class="value">{stats_data["total_experiencias_enviadas"]}</div>
                </div>
                <div class="card">
                    <h3>IPs Únicos Conectados</h3>
                    <div class="value">{len(stats_data["ips_conectados"])}</div>
                </div>
            </div>

            <div id="map"></div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Utilizador</th>
                            <th>Endereço IP</th>
                            <th>País</th>
                            <th>Cidade</th>
                            <th>Bairro</th>
                            <th>Data / Hora</th>
                        </tr>
                    </thead>
                    <tbody>
                        {ultimas_conexoes_html if ultimas_conexoes_html else '<tr><td colspan="6" style="text-align:center; color:#94a3b8;">A aguardar conexões...</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            var map = L.map('map').setView([20, 0], 2);
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{s}}/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '&copy; OpenStreetMap & CARTO',
                maxZoom: 19
            }}).addTo(map);

            // Adiciona marcador global de exemplo ou via geocodificação dinâmica do IP
            // Aqui exibe o mapa base escuro interativo pronto para receber os pontos
        </script>
    </body>
    </html>
    """
    return html_content
