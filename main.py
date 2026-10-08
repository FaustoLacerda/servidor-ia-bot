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
    lat = -22.9056
    lon = -47.0608
    
    if ip_cliente != "Desconhecido":
        try:
            url = f"http://ip-api.com/json/{ip_cliente}?fields=status,country,city,district,lat,lon"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                geo_resposta = json.loads(response.read().decode())
                if geo_resposta.get("status") == "success":
                    cidade_origem = geo_resposta.get("city", "Desconhecida")
                    pais_origem = geo_resposta.get("country", "Desconhecido")
                    bairro_origem = geo_resposta.get("district") or "Desconhecido"
                    lat = geo_resposta.get("lat", -22.9056)
                    lon = geo_resposta.get("lon", -47.0608)
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
        "lat": lat,
        "lon": lon,
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

# DASHBOARD PROFISSIONAL COMPLETO (DARK MODE FUTURISTA)
@app.get("/api/v1/stats", response_class=HTMLResponse)
def obter_estatisticas():
    ultimas_conexoes_html = ""
    marcadores_js = ""
    
    centro_lat = -22.9056
    centro_lon = -47.0608
    zoom = 4

    if stats_data["historico_conexoes"]:
        ultima = stats_data["historico_conexoes"][-1]
        centro_lat = ultima["lat"]
        centro_lon = ultima["lon"]
        zoom = 6

    for c in reversed(stats_data["historico_conexoes"]):
        ultimas_conexoes_html += f"""
        <tr>
            <td>🌍 {c['pais']}</td>
            <td>🏙️ {c['cidade']} - {c['bairro']}</td>
            <td><span class="status-dot"></span> <span style="color:#4ade80;">Online</span></td>
            <td>{c['data_hora']}</td>
        </tr>
        """
        marcadores_js += f"""
        L.marker([{c['lat']}, {c['lon']}]).addTo(map)
            .bindPopup("<b>Utilizador:</b> {c['usuario']}<br><b>Local:</b> {c['cidade']}, {c['pais']}<br><b>IP:</b> {c['ip']}");
        """

    total_verif = stats_data["total_verificacoes"]
    total_exp = stats_data["total_experiencias_enviadas"]
    total_ips = len(stats_data["ips_conectados"])
    ultima_conn = stats_data["ultima_conexao"] or "Nenhuma"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Servidor IA - Painel de Monitoramento</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
        <style>
            :root {{
                --bg-main: #070d1b;
                --bg-sidebar: #0b1329;
                --card-bg: #111c38;
                --border-color: #1e294b;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --accent-blue: #38bdf8;
                --accent-green: #4ade80;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: var(--bg-main);
                color: var(--text-main);
                margin: 0;
                display: flex;
                height: 100vh;
                overflow: hidden;
            }}
            /* Sidebar */
            aside {{
                width: 240px;
                background-color: var(--bg-sidebar);
                border-right: 1px solid var(--border-color);
                display: flex;
                flex-direction: column;
                padding: 20px;
            }}
            .logo-area {{
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 30px;
            }}
            .logo-area i {{
                font-size: 24px;
                color: var(--accent-blue);
            }}
            .logo-area h2 {{
                font-size: 18px;
                margin: 0;
                color: #fff;
            }}
            .menu-item {{
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px 15px;
                color: var(--text-muted);
                text-decoration: none;
                border-radius: 8px;
                margin-bottom: 5px;
                font-size: 14px;
                transition: 0.2s;
            }}
            .menu-item.active, .menu-item:hover {{
                background-color: rgba(56, 189, 248, 0.1);
                color: var(--accent-blue);
            }}
            /* Main Content */
            .main-container {{
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow-y: auto;
            }}
            header {{
                background-color: var(--bg-sidebar);
                border-bottom: 1px solid var(--border-color);
                padding: 15px 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .header-title h1 {{
                margin: 0;
                font-size: 20px;
                color: #fff;
            }}
            .header-title p {{
                margin: 2px 0 0 0;
                font-size: 12px;
                color: var(--text-muted);
            }}
            .header-right {{
                display: flex;
                align-items: center;
                gap: 20px;
            }}
            .badge-online {{
                background-color: rgba(74, 222, 128, 0.1);
                color: var(--accent-green);
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 8px;
                border: 1px solid rgba(74, 222, 128, 0.2);
            }}
            .badge-online::before {{
                content: '';
                width: 8px;
                height: 8px;
                background-color: var(--accent-green);
                border-radius: 50%;
                box-shadow: 0 0 8px var(--accent-green);
            }}
            .content {{
                padding: 25px 30px;
                display: flex;
                flex-direction: column;
                gap: 25px;
            }}
            /* Cards Grid */
            .cards-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
            }}
            .stat-card {{
                background-color: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 20px;
                position: relative;
                overflow: hidden;
            }}
            .stat-card h3 {{
                margin: 0 0 8px 0;
                font-size: 13px;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .stat-card .value {{
                font-size: 26px;
                font-weight: bold;
                color: #fff;
            }}
            .stat-card i {{
                position: absolute;
                right: 20px;
                top: 20px;
                font-size: 24px;
                color: rgba(56, 189, 248, 0.2);
            }}
            /* Dashboard Center Grid */
            .dashboard-grid {{
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
            }}
            .panel {{
                background-color: var(--card-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 20px;
                display: flex;
                flex-direction: column;
            }}
            .panel h2 {{
                margin: 0 0 15px 0;
                font-size: 16px;
                color: #fff;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            #map {{
                height: 380px;
                border-radius: 8px;
                border: 1px solid var(--border-color);
            }}
            /* Tables */
            .table-wrapper {{
                overflow-x: auto;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                text-align: left;
                font-size: 13px;
            }}
            th, td {{
                padding: 12px 15px;
                border-bottom: 1px solid var(--border-color);
            }}
            th {{
                color: var(--text-muted);
                font-weight: 600;
                background-color: rgba(0,0,0,0.2);
            }}
            .status-dot {{
                height: 8px;
                width: 8px;
                background-color: #4ade80;
                border-radius: 50%;
                display: inline-block;
            }}
            .progress-bar-container {{
                background-color: var(--border-color);
                border-radius: 4px;
                height: 8px;
                width: 100%;
                margin-top: 8px;
                overflow: hidden;
            }}
            .progress-bar {{
                background-color: var(--accent-blue);
                height: 100%;
                width: 100%;
            }}
            footer {{
                text-align: center;
                padding: 15px;
                color: var(--text-muted);
                font-size: 12px;
                border-top: 1px solid var(--border-color);
                background-color: var(--bg-sidebar);
            }}
        </style>
    </head>
    <body>
        <aside>
            <div class="logo-area">
                <i class="fa-solid fa-robot"></i>
                <h2>SERVIDOR IA</h2>
            </div>
            <a href="#" class="menu-item active"><i class="fa-solid fa-chart-pie"></i> Visão Geral</a>
            <a href="#" class="menu-item"><i class="fa-solid fa-globe"></i> Mapa Mundial</a>
            <a href="#" class="menu-item"><i class="fa-solid fa-network-wired"></i> Conexões</a>
            <a href="#" class="menu-item"><i class="fa-solid fa-sliders"></i> Estatísticas</a>
        </aside>

        <div class="main-container">
            <header>
                <div class="header-title">
                    <h1>Painel de Monitoramento</h1>
                    <p>Gestão de Licenças e Robôs em Tempo Real</p>
                </div>
                <div class="header-right">
                    <div class="badge-online">ONLINE</div>
                    <div style="font-size: 12px; color: var(--text-muted);">
                        <i class="fa-regular fa-clock"></i> {ultima_conn}
                    </div>
                </div>
            </header>

            <div class="content">
                <div class="cards-grid">
                    <div class="stat-card">
                        <h3>Licenças Ativas</h3>
                        <div class="value">{total_verif}</div>
                        <i class="fa-solid fa-shield-halved"></i>
                    </div>
                    <div class="stat-card">
                        <h3>Experiências Recebidas</h3>
                        <div class="value">{total_exp}</div>
                        <i class="fa-solid fa-flask"></i>
                    </div>
                    <div class="stat-card">
                        <h3>IPs Únicos Conectados</h3>
                        <div class="value">{total_ips}</div>
                        <i class="fa-solid fa-users"></i>
                    </div>
                    <div class="stat-card">
                        <h3>Status do Servidor</h3>
                        <div class="value" style="color: var(--accent-green); font-size: 22px; padding-top: 4px;">OPERACIONAL</div>
                        <i class="fa-solid fa-server"></i>
                    </div>
                </div>

                <div class="dashboard-grid">
                    <div class="panel">
                        <h2><i class="fa-solid fa-earth-americas" style="color: var(--accent-blue);"></i> Conexões no Mundo</h2>
                        <div id="map"></div>
                    </div>
                    
                    <div class="panel">
                        <h2><i class="fa-solid fa-chart-bar" style="color: var(--accent-blue);"></i> Distribuição por País</h2>
                        <div style="margin-top: 10px;">
                            <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 5px;">
                                <span>🇧🇷 Brasil</span>
                                <span style="font-weight: bold;">100%</span>
                            </div>
                            <div class="progress-bar-container">
                                <div class="progress-bar"></div>
                            </div>
                        </div>
                        <div style="margin-top: 25px;">
                            <h3 style="font-size: 13px; color: var(--text-muted); margin-bottom: 10px; text-transform: uppercase;">Versão da API</h3>
                            <div style="background: rgba(56, 189, 248, 0.05); border: 1px solid var(--border-color); padding: 12px; border-radius: 8px; font-size: 14px; display: flex; justify-content: space-between; align-items: center;">
                                <span>API v1.0 (FastAPI)</span>
                                <span style="color: var(--accent-green); font-weight: bold;">Estável</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="panel">
                    <h2><i class="fa-solid fa-clock-rotate-left" style="color: var(--accent-blue);"></i> Conexões Recentes</h2>
                    <div class="table-wrapper">
                        <table>
                            <thead>
                                <tr>
                                    <th>País</th>
                                    <th>Localização</th>
                                    <th>Status</th>
                                    <th>Horário</th>
                                </tr>
                            </thead>
                            <tbody>
                                {ultimas_conexoes_html if ultimas_conexoes_html else '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">A aguardar conexões...</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <footer>
                Servidor IA - Monitor Global de Conexões &copy; 2026
            </footer>
        </div>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            var map = L.map('map', {{ zoomControl: false }}).setView([{centro_lat}, {centro_lon}], {zoom});
            L.control.zoom({{ position: 'bottomright' }}).addTo(map);
            
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{s}}/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '&copy; OpenStreetMap & CARTO',
                maxZoom: 19
            }}).addTo(map);

            {marcadores_js}
        </script>
    </body>
    </html>
    """
    return html_content
