```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from datetime import datetime
import json
import os
import urllib.request
import urllib.error
import threading

app = FastAPI()

CLIENTES_FILE = "clientes.json"

# ============================================================
# CLIENTES
# ============================================================

def carregar_clientes():
    if not os.path.exists(CLIENTES_FILE):
        return {}

    try:
        with open(CLIENTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ============================================================
# ESTATÍSTICAS
# ============================================================

stats_data = {
    "total_verificacoes": 0,
    "total_experiencias_enviadas": 0,
    "ultima_conexao": None,
    "ips_conectados": set(),
    "historico_conexoes": []
}

# Evita problemas caso o Render receba requisições simultâneas
stats_lock = threading.Lock()


# ============================================================
# IP
# ============================================================

def obter_ip_cliente(request: Request):
    """
    Mantém a lógica atual de identificação do IP,
    priorizando X-Forwarded-For usado pelo Render/proxy.
    """

    ip_bruto = request.headers.get("x-forwarded-for")

    if not ip_bruto and request.client:
        ip_bruto = request.client.host

    ip_cliente = "Desconhecido"

    if ip_bruto:
        lista_ips = [ip.strip() for ip in ip_bruto.split(",")]

        for ip in lista_ips:
            if ip and not ip.startswith((
                "10.",
                "192.168.",
                "127.",
                "172.16.",
                "172.17.",
                "172.18.",
                "172.19.",
                "172.20.",
                "172.21.",
                "172.22.",
                "172.23.",
                "172.24.",
                "172.25.",
                "172.26.",
                "172.27.",
                "172.28.",
                "172.29.",
                "172.30.",
                "172.31."
            )):
                ip_cliente = ip
                break

        if ip_cliente == "Desconhecido" and lista_ips:
            ip_cliente = lista_ips[0]

    return ip_cliente


# ============================================================
# GEOLOCALIZAÇÃO
# ============================================================

def obter_geolocalizacao(ip_cliente):
    """
    Consulta o ip-api.

    Além dos campos antigos:
        country
        city
        district

    agora também solicita:
        lat
        lon

    Se a consulta falhar, a API continua funcionando normalmente.
    """

    cidade_origem = "Desconhecida"
    pais_origem = "Desconhecido"
    bairro_origem = "Desconhecido"

    latitude = None
    longitude = None

    if ip_cliente == "Desconhecido":
        return (
            pais_origem,
            cidade_origem,
            bairro_origem,
            latitude,
            longitude
        )

    try:
        url = (
            f"http://ip-api.com/json/{ip_cliente}"
            "?fields=status,country,city,district,lat,lon"
        )

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(req, timeout=3) as response:
            geo_resposta = json.loads(
                response.read().decode("utf-8")
            )

        if geo_resposta.get("status") == "success":

            cidade_origem = (
                geo_resposta.get("city")
                or "Desconhecida"
            )

            pais_origem = (
                geo_resposta.get("country")
                or "Desconhecido"
            )

            bairro_origem = (
                geo_resposta.get("district")
                or "Desconhecido"
            )

            # Latitude
            try:
                if geo_resposta.get("lat") is not None:
                    latitude = float(geo_resposta["lat"])
            except (TypeError, ValueError):
                latitude = None

            # Longitude
            try:
                if geo_resposta.get("lon") is not None:
                    longitude = float(geo_resposta["lon"])
            except (TypeError, ValueError):
                longitude = None

    except Exception as erro:
        print(
            f"AVISO: Não foi possível obter geolocalização "
            f"do IP {ip_cliente}: {erro}"
        )

    return (
        pais_origem,
        cidade_origem,
        bairro_origem,
        latitude,
        longitude
    )


# ============================================================
# LER DADOS DA REQUISIÇÃO
# ============================================================

async def obter_dados_requisicao(request: Request):
    dados = {}

    # GET / query string
    if request.query_params:
        dados = dict(request.query_params)

    # JSON
    if not dados:
        try:
            dados = await request.json()
        except Exception:
            pass

    # Form
    if not dados:
        try:
            form_data = await request.form()
            dados = dict(form_data)
        except Exception:
            pass

    return dados


# ============================================================
# API EXISTENTE DO ROBÔ
# ============================================================

@app.api_route(
    "/api/v1/verificar-licenca",
    methods=["GET", "POST"]
)
async def verificar_licenca(request: Request):

    dados = await obter_dados_requisicao(request)

    # Mantido exatamente o padrão de compatibilidade atual
    usuario = (
        dados.get("usuario")
        or dados.get("Usuario")
        or dados.get("user")
        or "Adm_adm"
    )

    autorizado = True

    # --------------------------------------------------------
    # IP
    # --------------------------------------------------------

    ip_cliente = obter_ip_cliente(request)

    # --------------------------------------------------------
    # GEOLOCALIZAÇÃO
    # --------------------------------------------------------

    (
        pais_origem,
        cidade_origem,
        bairro_origem,
        latitude,
        longitude
    ) = obter_geolocalizacao(ip_cliente)

    # --------------------------------------------------------
    # ESTATÍSTICAS
    # --------------------------------------------------------

    agora = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    registro = {
        "usuario": usuario,
        "ip": ip_cliente,
        "pais": pais_origem,
        "cidade": cidade_origem,
        "bairro": bairro_origem,

        # NOVOS CAMPOS
        "latitude": latitude,
        "longitude": longitude,

        "data_hora": agora
    }

    with stats_lock:

        stats_data["total_verificacoes"] += 1

        stats_data["ultima_conexao"] = agora

        stats_data["ips_conectados"].add(ip_cliente)

        stats_data["historico_conexoes"].append(
            registro
        )

        # Mantém somente as 50 conexões mais recentes
        if len(stats_data["historico_conexoes"]) > 50:
            stats_data["historico_conexoes"].pop(0)

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    print(
        "INFO: TradingServer - "
        f"Licença autorizada para: {usuario} | "
        f"IP: {ip_cliente} | "
        f"Local: {pais_origem}, "
        f"{cidade_origem}, "
        f"{bairro_origem} | "
        f"Coordenadas: {latitude}, {longitude}"
    )

    # --------------------------------------------------------
    # RESPOSTA ORIGINAL
    # --------------------------------------------------------

    return {
        "status": "sucesso",
        "mensagem": "Licença validada com sucesso",
        "localizacao": (
            f"{pais_origem}, "
            f"{cidade_origem} - "
            f"Bairro: {bairro_origem}"
        )
    }


# ============================================================
# EXPERIÊNCIA — ROTA EXISTENTE
# ============================================================

@app.api_route(
    "/api/v1/experiencia",
    methods=["GET", "POST"]
)
async def registrar_experiencia(request: Request):

    with stats_lock:
        stats_data["total_experiencias_enviadas"] += 1

    return {
        "status": "registrado",
        "mensagem": "Experiência absorvida."
    }


# ============================================================
# STATS — ROTA EXISTENTE
# ============================================================

@app.get("/api/v1/stats")
def obter_estatisticas():

    with stats_lock:

        historico = list(
            stats_data["historico_conexoes"]
        )

        return {
            "status": "online",

            "total_verificacoes_licenca":
                stats_data["total_verificacoes"],

            "total_experiencias_recebidas":
                stats_data[
                    "total_experiencias_enviadas"
                ],

            "ultima_conexao":
                stats_data["ultima_conexao"],

            "total_ips_unicos_conectados":
                len(stats_data["ips_conectados"]),

            "ultimas_conexoes":
                historico
        }


# ============================================================
# DASHBOARD
# ============================================================

DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="pt-BR">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>TradingServer - Dashboard</title>

<link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
/>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #07111f;
    color: #e8f1ff;
    font-family:
        Arial,
        Helvetica,
        sans-serif;
}

header {
    background: #0b1728;
    border-bottom: 1px solid #1d3552;
    padding: 18px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.logo {
    font-size: 22px;
    font-weight: bold;
}

.online {
    color: #43e97b;
    font-weight: bold;
}

.container {
    padding: 20px;
}

.cards {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(210px, 1fr));

    gap: 15px;
    margin-bottom: 20px;
}

.card {
    background: #0d1b2e;
    border: 1px solid #1d3552;
    border-radius: 12px;
    padding: 18px;
}

.card-title {
    color: #8ca6c5;
    font-size: 13px;
    margin-bottom: 8px;
}

.card-value {
    font-size: 28px;
    font-weight: bold;
}

.layout {
    display: grid;

    grid-template-columns:
        minmax(0, 2fr)
        minmax(320px, 1fr);

    gap: 20px;
}

.panel {
    background: #0d1b2e;
    border: 1px solid #1d3552;
    border-radius: 12px;
    overflow: hidden;
}

.panel-header {
    padding: 15px 18px;
    border-bottom: 1px solid #1d3552;
    font-weight: bold;
}

#map {
    width: 100%;
    height: 560px;
}

.connections {
    max-height: 560px;
    overflow-y: auto;
}

.connection {
    padding: 14px 16px;
    border-bottom: 1px solid #172b44;
}

.connection-user {
    font-weight: bold;
    color: #ffffff;
}

.connection-location {
    margin-top: 5px;
    color: #9eb4cf;
    font-size: 13px;
}

.connection-ip {
    margin-top: 4px;
    color: #6f8aa8;
    font-size: 12px;
}

.connection-time {
    margin-top: 4px;
    color: #5f7894;
    font-size: 11px;
}

.badge {
    display: inline-block;
    margin-left: 7px;
    padding: 3px 7px;
    border-radius: 20px;
    background: #123c2b;
    color: #43e97b;
    font-size: 10px;
}

.footer {
    margin-top: 20px;
    color: #617995;
    font-size: 12px;
    text-align: center;
}

@media (max-width: 900px) {

    .layout {
        grid-template-columns: 1fr;
    }

    #map {
        height: 420px;
    }

}

</style>

</head>

<body>

<header>

    <div class="logo">
        🌎 TradingServer
    </div>

    <div class="online">
        ● ONLINE
    </div>

</header>


<div class="container">

    <div class="cards">

        <div class="card">

            <div class="card-title">
                VERIFICAÇÕES DE LICENÇA
            </div>

            <div
                class="card-value"
                id="totalVerificacoes">
                0
            </div>

        </div>


        <div class="card">

            <div class="card-title">
                EXPERIÊNCIAS RECEBIDAS
            </div>

            <div
                class="card-value"
                id="totalExperiencias">
                0
            </div>

        </div>


        <div class="card">

            <div class="card-title">
                IPs ÚNICOS
            </div>

            <div
                class="card-value"
                id="totalIps">
                0
            </div>

        </div>


        <div class="card">

            <div class="card-title">
                ÚLTIMA CONEXÃO
            </div>

            <div
                class="card-value"
                id="ultimaConexao"
                style="font-size:16px;">
                —
            </div>

        </div>

    </div>


    <div class="layout">


        <div class="panel">

            <div class="panel-header">
                🌎 Mapa mundial de conexões
            </div>

            <div id="map"></div>

        </div>


        <div class="panel">

            <div class="panel-header">
                📡 Últimas conexões
            </div>

            <div
                class="connections"
                id="connections">
            </div>

        </div>


    </div>


    <div class="footer">
        TradingServer • Dashboard atualizado automaticamente
    </div>

</div>


<script
    src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js">
</script>


<script>

const map = L.map("map").setView(
    [10, 0],
    2
);


L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom: 18,
        attribution:
            "&copy; OpenStreetMap contributors"
    }
).addTo(map);


let markers = [];


function limparMarcadores() {

    markers.forEach(function(marker) {
        map.removeLayer(marker);
    });

    markers = [];
}


function escaparHTML(valor) {

    if (valor === null ||
        valor === undefined) {
        return "";
    }

    return String(valor)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function atualizarDashboard() {

    fetch("/api/v1/stats")
        .then(function(response) {

            if (!response.ok) {
                throw new Error(
                    "Erro HTTP " + response.status
                );
            }

            return response.json();
        })

        .then(function(data) {

            document.getElementById(
                "totalVerificacoes"
            ).textContent =
                data.total_verificacoes_licenca || 0;


            document.getElementById(
                "totalExperiencias"
            ).textContent =
                data.total_experiencias_recebidas || 0;


            document.getElementById(
                "totalIps"
            ).textContent =
                data.total_ips_unicos_conectados || 0;


            document.getElementById(
                "ultimaConexao"
            ).textContent =
                data.ultima_conexao || "—";


            limparMarcadores();


            const lista =
                data.ultimas_conexoes || [];


            const container =
                document.getElementById(
                    "connections"
                );


            if (lista.length === 0) {

                container.innerHTML =
                    '<div class="connection">' +
                    'Nenhuma conexão registrada.' +
                    '</div>';

                return;
            }


            container.innerHTML = "";


            /*
             * Mostra as conexões mais recentes primeiro.
             */

            const listaReversa =
                [...lista].reverse();


            listaReversa.forEach(function(item) {

                const usuario =
                    escaparHTML(
                        item.usuario ||
                        "Desconhecido"
                    );


                const pais =
                    escaparHTML(
                        item.pais ||
                        "Desconhecido"
                    );


                const cidade =
                    escaparHTML(
                        item.cidade ||
                        "Desconhecida"
                    );


                const bairro =
                    escaparHTML(
                        item.bairro ||
                        "Desconhecido"
                    );


                const ip =
                    escaparHTML(
                        item.ip ||
                        "Desconhecido"
                    );


                const dataHora =
                    escaparHTML(
                        item.data_hora ||
                        ""
                    );


                const div =
                    document.createElement(
                        "div"
                    );

                div.className =
                    "connection";


                div.innerHTML =

                    '<div class="connection-user">' +

                    usuario +

                    '<span class="badge">' +
                    'CONECTADO' +
                    '</span>' +

                    '</div>' +

                    '<div class="connection-location">' +

                    pais +
                    " • " +
                    cidade +
                    " • " +
                    bairro +

                    '</div>' +

                    '<div class="connection-ip">' +

                    "IP: " +
                    ip +

                    '</div>' +

                    '<div class="connection-time">' +

                    dataHora +

                    '</div>';


                container.appendChild(div);


                /*
                 * MAPA
                 */

                const lat =
                    Number(item.latitude);


                const lon =
                    Number(item.longitude);


                if (
                    Number.isFinite(lat) &&
                    Number.isFinite(lon) &&
                    lat >= -90 &&
                    lat <= 90 &&
                    lon >= -180 &&
                    lon <= 180
                ) {

                    const marker =
                        L.marker([
                            lat,
                            lon
                        ]).addTo(map);


                    marker.bindPopup(

                        "<b>" +
                        usuario +
                        "</b><br>" +

                        pais +
                        "<br>" +

                        cidade +
                        "<br>" +

                        bairro +
                        "<br><br>" +

                        "IP: " +
                        ip +
                        "<br>" +

                        "Data: " +
                        dataHora

                    );


                    markers.push(marker);
                }

            });

        })

        .catch(function(error) {

            console.error(
                "Erro ao atualizar dashboard:",
                error
            );

        });

}


/*
 * Primeira atualização
 */

atualizarDashboard();


/*
 * Atualiza a cada 10 segundos
 */

setInterval(
    atualizarDashboard,
    10000
);

</script>

</body>

</html>
"""


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/", response_class=HTMLResponse)
def dashboard():

    return HTMLResponse(
        content=DASHBOARD_HTML
    )
```
