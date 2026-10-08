from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from datetime import datetime
import json
import os
import urllib.request
import threading

app = FastAPI()

CLIENTES_FILE = "clientes.json"

# ============================================================

# CLIENTES

# ============================================================

def carregar_clientes():
if not os.path.exists(CLIENTES_FILE):
return {}

```
try:
    with open(CLIENTES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
except Exception:
    return {}
```

# ============================================================

# ESTATISTICAS

# ============================================================

stats_data = {
"total_verificacoes": 0,
"total_experiencias_enviadas": 0,
"ultima_conexao": None,
"ips_conectados": set(),
"historico_conexoes": []
}

stats_lock = threading.Lock()

# ============================================================

# IP DO CLIENTE

# ============================================================

def obter_ip_cliente(request: Request):

```
ip_bruto = request.headers.get("x-forwarded-for")

if not ip_bruto and request.client:
    ip_bruto = request.client.host

ip_cliente = "Desconhecido"

if ip_bruto:

    lista_ips = [
        ip.strip()
        for ip in ip_bruto.split(",")
        if ip.strip()
    ]

    redes_privadas = (
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
    )

    for ip in lista_ips:

        if not ip.startswith(redes_privadas):
            ip_cliente = ip
            break

    if (
        ip_cliente == "Desconhecido"
        and lista_ips
    ):
        ip_cliente = lista_ips[0]

return ip_cliente
```

# ============================================================

# GEOLOCALIZACAO

# ============================================================

def obter_geolocalizacao(ip_cliente):

```
pais = "Desconhecido"
cidade = "Desconhecida"
bairro = "Desconhecido"

latitude = None
longitude = None

if ip_cliente == "Desconhecido":
    return (
        pais,
        cidade,
        bairro,
        latitude,
        longitude
    )

try:

    url = (
        "http://ip-api.com/json/"
        + ip_cliente
        + "?fields=status,country,city,district,lat,lon"
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TradingServer/1.0"
        }
    )

    with urllib.request.urlopen(
        req,
        timeout=3
    ) as response:

        conteudo = response.read().decode(
            "utf-8",
            errors="replace"
        )

        resultado = json.loads(conteudo)

    if resultado.get("status") == "success":

        pais = (
            resultado.get("country")
            or "Desconhecido"
        )

        cidade = (
            resultado.get("city")
            or "Desconhecida"
        )

        bairro = (
            resultado.get("district")
            or "Desconhecido"
        )

        try:
            latitude = float(
                resultado.get("lat")
            )
        except (
            TypeError,
            ValueError
        ):
            latitude = None

        try:
            longitude = float(
                resultado.get("lon")
            )
        except (
            TypeError,
            ValueError
        ):
            longitude = None

except Exception as erro:

    print(
        "AVISO: Falha na geolocalizacao do IP "
        + str(ip_cliente)
        + ": "
        + str(erro)
    )

return (
    pais,
    cidade,
    bairro,
    latitude,
    longitude
)
```

# ============================================================

# DADOS DA REQUISICAO

# ============================================================

async def obter_dados_requisicao(request: Request):

```
dados = {}

if request.query_params:
    dados = dict(request.query_params)

if not dados:

    try:
        dados = await request.json()

        if not isinstance(dados, dict):
            dados = {}

    except Exception:
        pass

if not dados:

    try:
        formulario = await request.form()
        dados = dict(formulario)

    except Exception:
        pass

return dados
```

# ============================================================

# VERIFICACAO DE LICENCA

#

# ESTA ROTA FOI MANTIDA:

# /api/v1/verificar-licenca

# ============================================================

@app.api_route(
"/api/v1/verificar-licenca",
methods=["GET", "POST"]
)
async def verificar_licenca(request: Request):

```
dados = await obter_dados_requisicao(request)

usuario = (
    dados.get("usuario")
    or dados.get("Usuario")
    or dados.get("user")
    or "Adm_adm"
)

autorizado = True

ip_cliente = obter_ip_cliente(request)

(
    pais_origem,
    cidade_origem,
    bairro_origem,
    latitude,
    longitude
) = obter_geolocalizacao(ip_cliente)

agora = datetime.now().strftime(
    "%Y-%m-%d %H:%M:%S"
)

registro = {
    "usuario": usuario,
    "ip": ip_cliente,
    "pais": pais_origem,
    "cidade": cidade_origem,
    "bairro": bairro_origem,
    "latitude": latitude,
    "longitude": longitude,
    "data_hora": agora
}

with stats_lock:

    stats_data[
        "total_verificacoes"
    ] += 1

    stats_data[
        "ultima_conexao"
    ] = agora

    stats_data[
        "ips_conectados"
    ].add(ip_cliente)

    stats_data[
        "historico_conexoes"
    ].append(registro)

    if len(
        stats_data[
            "historico_conexoes"
        ]
    ) > 50:

        stats_data[
            "historico_conexoes"
        ].pop(0)

print(
    "INFO: TradingServer - "
    "Licenca autorizada para: "
    + str(usuario)
    + " | IP: "
    + str(ip_cliente)
    + " | Local: "
    + str(pais_origem)
    + ", "
    + str(cidade_origem)
    + ", "
    + str(bairro_origem)
    + " | Coordenadas: "
    + str(latitude)
    + ", "
    + str(longitude)
)

return {
    "status": "sucesso",
    "mensagem": "Licenca validada com sucesso",
    "localizacao": (
        str(pais_origem)
        + ", "
        + str(cidade_origem)
        + " - Bairro: "
        + str(bairro_origem)
    )
}
```

# ============================================================

# EXPERIENCIA

#

# ESTA ROTA FOI MANTIDA:

# /api/v1/experiencia

# ============================================================

@app.api_route(
"/api/v1/experiencia",
methods=["GET", "POST"]
)
async def registrar_experiencia(request: Request):

```
with stats_lock:

    stats_data[
        "total_experiencias_enviadas"
    ] += 1

return {
    "status": "registrado",
    "mensagem": "Experiencia absorvida."
}
```

# ============================================================

# STATS

#

# ESTA ROTA FOI MANTIDA:

# /api/v1/stats

# ============================================================

@app.get("/api/v1/stats")
def obter_estatisticas():

```
with stats_lock:

    historico = list(
        stats_data[
            "historico_conexoes"
        ]
    )

    return {
        "status": "online",
        "total_verificacoes_licenca":
            stats_data[
                "total_verificacoes"
            ],
        "total_experiencias_recebidas":
            stats_data[
                "total_experiencias_enviadas"
            ],
        "ultima_conexao":
            stats_data[
                "ultima_conexao"
            ],
        "total_ips_unicos_conectados":
            len(
                stats_data[
                    "ips_conectados"
                ]
            ),
        "ultimas_conexoes":
            historico
    }
```

# ============================================================

# DASHBOARD

# ============================================================

DASHBOARD_HTML = """

<!DOCTYPE html>

<html lang="pt-BR">

<head>

<meta charset="UTF-8">

<meta
name="viewport"
content="width=device-width, initial-scale=1.0"

>

<title>TradingServer - Dashboard</title>

<link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #07111f;
    color: #e8f1ff;
    font-family: Arial, Helvetica, sans-serif;
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
        repeat(
            auto-fit,
            minmax(210px, 1fr)
        );

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

    border-bottom:
        1px solid #1d3552;

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

    border-bottom:
        1px solid #172b44;
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

.status-message {
    padding: 20px;

    color: #8ca6c5;

    text-align: center;
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
VERIFICACOES DE LICENCA
</div>

<div
    class="card-value"
    id="totalVerificacoes"
>
0
</div>

</div>

<div class="card">

<div class="card-title">
EXPERIENCIAS RECEBIDAS
</div>

<div
    class="card-value"
    id="totalExperiencias"
>
0
</div>

</div>

<div class="card">

<div class="card-title">
IPS UNICOS
</div>

<div
    class="card-value"
    id="totalIps"
>
0
</div>

</div>

<div class="card">

<div class="card-title">
ULTIMA CONEXAO
</div>

<div
    class="card-value"
    id="ultimaConexao"
    style="font-size:16px;"
>
—
</div>

</div>

</div>

<div class="layout">

<div class="panel">

<div class="panel-header">
🌎 Mapa mundial de conexoes
</div>

<div id="map"></div>

</div>

<div class="panel">

<div class="panel-header">
📡 Ultimas conexoes
</div>

<div
    class="connections"
    id="connections"
>
<div class="status-message">
Carregando...
</div>
</div>

</div>

</div>

<div class="footer">
TradingServer • Atualizacao automatica
</div>

</div>

<script
src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
></script>

<script>

const mapa = L.map("map").setView(
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
).addTo(mapa);


let marcadores = [];


function limparMarcadores() {

    marcadores.forEach(
        function(marcador) {

            mapa.removeLayer(
                marcador
            );

        }
    );

    marcadores = [];
}


function escaparHTML(valor) {

    if (
        valor === null ||
        valor === undefined
    ) {
        return "";
    }

    return String(valor)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


async function atualizarDashboard() {

    try {

        const resposta =
            await fetch(
                "/api/v1/stats",
                {
                    cache: "no-store"
                }
            );


        if (!resposta.ok) {

            throw new Error(
                "HTTP " +
                resposta.status
            );

        }


        const dados =
            await resposta.json();


        document.getElementById(
            "totalVerificacoes"
        ).textContent =
            dados.total_verificacoes_licenca || 0;


        document.getElementById(
            "totalExperiencias"
        ).textContent =
            dados.total_experiencias_recebidas || 0;


        document.getElementById(
            "totalIps"
        ).textContent =
            dados.total_ips_unicos_conectados || 0;


        document.getElementById(
            "ultimaConexao"
        ).textContent =
            dados.ultima_conexao || "—";


        limparMarcadores();


        const conexoes =
            dados.ultimas_conexoes || [];


        const container =
            document.getElementById(
                "connections"
            );


        container.innerHTML = "";


        if (conexoes.length === 0) {

            container.innerHTML =
                '<div class="status-message">' +
                'Nenhuma conexao registrada.' +
                '</div>';

            return;
        }


        const recentes =
            [...conexoes].reverse();


        recentes.forEach(
            function(item) {

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


                const conexao =
                    document.createElement(
                        "div"
                    );


                conexao.className =
                    "connection";


                conexao.innerHTML =

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


                container.appendChild(
                    conexao
                );


                const latitude =
                    Number(
                        item.latitude
                    );


                const longitude =
                    Number(
                        item.longitude
                    );


                if (
                    Number.isFinite(
                        latitude
                    ) &&
                    Number.isFinite(
                        longitude
                    ) &&
                    latitude >= -90 &&
                    latitude <= 90 &&
                    longitude >= -180 &&
                    longitude <= 180
                ) {

                    const marcador =
                        L.marker(
                            [
                                latitude,
                                longitude
                            ]
                        ).addTo(
                            mapa
                        );


                    marcador.bindPopup(

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

                        dataHora

                    );


                    marcadores.push(
                        marcador
                    );
                }

            }
        );

    }

    catch (erro) {

        console.error(
            "Erro no dashboard:",
            erro
        );

        document.getElementById(
            "connections"
        ).innerHTML =
            '<div class="status-message">' +
            'Nao foi possivel atualizar os dados.' +
            '</div>';
    }
}


atualizarDashboard();


setInterval(
    atualizarDashboard,
    10000
);

</script>

</body>

</html>
"""

# ============================================================

# PAGINA PRINCIPAL

# ============================================================

@app.get(
"/",
response_class=HTMLResponse
)
def pagina_principal():

```
return HTMLResponse(
    content=DASHBOARD_HTML
)
```
