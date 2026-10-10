from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
random = __import__('random')
secrets = __import__('secrets')
smtplib = __import__('smtplib')

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import uvicorn

app = FastAPI(title="Quantum MT5 - Servidor & Licenciamento")

security = HTTPBasic()

ADMIN_USER = "Adm_Master"
ADMIN_PASS = "R@oyal0987"

DB_FILE = "dados_servidor.json"
RELATORIOS_FILE = "dados_relatorios.json"

# --- CONFIGURAÇÕES DE SMTP PARA ENVIO DE E-MAIL REAL ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "seu-email@gmail.com"  # Substitua pelo seu e-mail
SMTP_PASSWORD = "xxxx xxxx xxxx xxxx"  # Senha de App do Gmail

# Dicionário temporário para armazenar os códigos OTP gerados
otp_database = {}


def enviar_email_otp(to_email: str, code: str):
  try:
    msg = MIMEMultipart()
    msg["From"] = f"Quantum MT5 <{SMTP_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = f"{code} é o seu código de acesso - Quantum MT5"

    body_html = f"""
        <html>
            <body style="background-color: #080909; color: #f7f3eb; font-family: Arial, sans-serif; padding: 30px;">
                <div style="max-width: 500px; margin: auto; background-color: #101110; border: 1px solid #d7ad62; padding: 24px; border-radius: 6px;">
                    <h2 style="color: #f2d49a; margin-top: 0;">Quantum MT5</h2>
                    <p style="color: #bcb6aa;">O seu código de verificação para acesso ou cadastro na plataforma é:</p>
                    <div style="background-color: #161716; border: 1px dashed #d7ad62; padding: 16px; text-align: center; font-size: 28px; font-weight: bold; letter-spacing: 6px; color: #f2d49a; margin: 20px 0;">
                        {code}
                    </div>
                    <p style="font-size: 12px; color: #bcb6aa;">Se não solicitou este código, por favor ignore este e-mail.</p>
                </div>
            </body>
        </html>
        """
    msg.attach(MIMEText(body_html, "html"))

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SMTP_EMAIL, SMTP_PASSWORD)
    server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
    server.quit()
    return True
  except Exception as e:
    print(f"Erro ao enviar e-mail SMTP: {e}")
    return False


def carregar_relatorios():
  if os.path.exists(RELATORIOS_FILE):
    try:
      with open(RELATORIOS_FILE, "r", encoding="utf-8") as f:
        dados_carregados = json.load(f)
        if "Desconhecido" in dados_carregados:
          del dados_carregados["Desconhecido"]
        return dados_carregados
    except Exception:
      pass
  return {}


def salvar_relatorios():
  try:
    with open(RELATORIOS_FILE, "w", encoding="utf-8") as f:
      json.dump(relatorios_usuarios, f, ensure_ascii=False, indent=4)
  except Exception:
    pass


relatorios_usuarios = carregar_relatorios()


def carregar_dados():
  dados = {
      "total_verificacoes": 0,
      "total_experiencias_enviadas": 0,
      "ultima_conexao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "ips_conectados": set(),
      "conexoes_ativas": {},
  }

  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        carregado = json.load(f)
        dados["total_verificacoes"] = carregado.get("total_verificacoes", 0)
        dados["total_experiencias_enviadas"] = carregado.get(
            "total_experiencias_enviadas", 0
        )
        dados["ultima_conexao"] = carregado.get(
            "ultima_conexao", dados["ultima_conexao"]
        )
        dados["ips_conectados"] = set(carregado.get("ips_conectados", []))
        dados["conexoes_ativas"] = carregado.get("conexoes_ativas", {})
    except Exception:
      pass

  if not dados["conexoes_ativas"] and relatorios_usuarios:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for usr in relatorios_usuarios.keys():
      dados["conexoes_ativas"][usr] = {
          "usuario": usr,
          "ip": "127.0.0.1",
          "pais": "Brasil",
          "cidade": "Campinas",
          "regiao": "São Paulo",
          "localizacao": "Campinas - São Paulo",
          "lat": -22.9056,
          "lon": -47.0608,
          "data_hora": agora,
      }
    dados["total_verificacoes"] = max(
        dados["total_verificacoes"], len(relatorios_usuarios)
    )

  return dados


def salvar_dados():
  dados_para_salvar = stats_data.copy()
  dados_para_salvar["ips_conectados"] = list(stats_data["ips_conectados"])
  try:
    with open(DB_FILE, "w", encoding="utf-8") as f:
      json.dump(dados_para_salvar, f, ensure_ascii=False, indent=4)
  except Exception:
    pass


stats_data = carregar_dados()


def verificar_admin(credentials: HTTPBasicCredentials = Depends(security)):
  is_user_ok = secrets.compare_digest(credentials.username, ADMIN_USER)
  is_pass_ok = secrets.compare_digest(credentials.password, ADMIN_PASS)
  if not (is_user_ok and is_pass_ok):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Acesso negado. Credenciais de Administrador inválidas.",
        headers={"WWW-Authenticate": "Basic"},
    )
  return credentials.username


# --- ROTA RAIZ (Evita o erro 404 no Render) ---
@app.get("/", include_in_schema=False)
def raiz():
  return {
      "status": "online",
      "servidor": "Quantum MT5 Backend",
      "mensagem": "Servidor operando com sucesso. Acesse o painel em /api/v1/stats",
  }


# --- ROTAS DE AUTENTICAÇÃO POR E-MAIL (OTP) ---
@app.post("/api/v1/enviar-otp")
async def api_enviar_otp(request: Request):
  try:
    dados = await request.json()
  except Exception:
    dados = {}
  email = dados.get("email")
  if not email:
    raise HTTPException(status_code=400, detail="E-mail obrigatório.")

  codigo = f"{random.randint(100000, 999999)}"
  otp_database[email] = codigo

  enviado = enviar_email_otp(email, codigo)
  if not enviado:
    print(f"[Modo Fallback] Código OTP para {email}: {codigo}")

  return {
      "status": "sucesso",
      "mensagem": f"Código de verificação enviado para {email}",
  }


@app.post("/api/v1/verificar-otp")
async def api_verificar_otp(request: Request):
  try:
    dados = await request.json()
  except Exception:
    dados = {}
  email = dados.get("email")
  codigo = dados.get("codigo")

  if not email or not codigo:
    raise HTTPException(status_code=400, detail="Dados incompletos.")

  codigo_salvo = otp_database.get(email)
  if not codigo_salvo or codigo_salvo != codigo:
    raise HTTPException(
        status_code=400, detail="Código de verificação incorreto ou expirado."
    )

  del otp_database[email]
  return {"status": "sucesso", "mensagem": "E-mail validado com sucesso!"}


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

  usuario = (
      dados.get("usuario")
      or dados.get("Usuario")
      or dados.get("user")
      or "Adm_adm"
  )
  licenca = dados.get("licenca") or ""

  if licenca and licenca != "PROD-ADM-2026":
    raise HTTPException(
        status_code=401, detail="Chave de licença inválida ou expirada."
    )

  ip_bruto = request.headers.get("x-forwarded-for")
  if not ip_bruto and request.client:
    ip_bruto = request.client.host

  ip_cliente = ip_bruto.split(",")[0].strip() if ip_bruto else "Desconhecido"

  pais = "Brasil"
  cidade = "Campinas"
  regiao = "São Paulo"
  lat = -22.9056
  lon = -47.0608

  stats_data["total_verificacoes"] += 1
  agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  stats_data["ultima_conexao"] = agora
  stats_data["ips_conectados"].add(ip_cliente)

  localizacao_completa = f"{cidade} - {regiao}"

  stats_data["conexoes_ativas"][usuario] = {
      "usuario": usuario,
      "ip": ip_cliente,
      "pais": pais,
      "cidade": cidade,
      "regiao": regiao,
      "localizacao": localizacao_completa,
      "lat": lat,
      "lon": lon,
      "data_hora": agora,
  }

  if usuario not in relatorios_usuarios:
    relatorios_usuarios[usuario] = {
        "usuario": usuario,
        "lucro_total": 0.0,
        "prejuizo_total": 0.0,
        "operacoes_vencedoras": 0,
        "operacoes_perdedoras": 0,
        "banca_atual": 0.0,
        "saldo_creditos": 50.00,
        "comissao_devida": 0.0,
        "status_robo": "ATIVO",
        "ultima_atualizacao": agora,
    }
    salvar_relatorios()

  salvar_dados()

  user_info = relatorios_usuarios[usuario]
  return {
      "status": "sucesso",
      "mensagem": "Licença validada com sucesso",
      "saldo_creditos": user_info.get("saldo_creditos", 0.0),
      "localizacao": f"{pais}, {localizacao_completa}",
  }


@app.api_route("/api/v1/heartbeat", methods=["POST", "GET"])
async def heartbeat_robo(request: Request):
  dados = {}
  if request.query_params:
    dados = dict(request.query_params)
  if not dados:
    try:
      dados = await request.json()
    except Exception:
      pass

  usuario = dados.get("usuario") or dados.get("user") or "Robo_Ativo"

  ip_bruto = request.headers.get("x-forwarded-for")
  if not ip_bruto and request.client:
    ip_bruto = request.client.host
  ip_cliente = ip_bruto.split(",")[0].strip() if ip_bruto else "Desconhecido"

  agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  stats_data["ultima_conexao"] = agora

  if usuario not in relatorios_usuarios:
    relatorios_usuarios[usuario] = {
        "usuario": usuario,
        "lucro_total": 0.0,
        "prejuizo_total": 0.0,
        "operacoes_vencedoras": 0,
        "operacoes_perdedoras": 0,
        "banca_atual": 0.0,
        "saldo_creditos": 50.00,
        "comissao_devida": 0.0,
        "status_robo": "ATIVO",
        "ultima_atualizacao": agora,
    }
    salvar_relatorios()

  if usuario not in stats_data["conexoes_ativas"]:
    stats_data["conexoes_ativas"][usuario] = {
        "usuario": usuario,
        "ip": ip_cliente,
        "pais": "Brasil",
        "cidade": "Campinas",
        "regiao": "São Paulo",
        "localizacao": "Campinas - São Paulo",
        "lat": -22.9056,
        "lon": -47.0608,
        "data_hora": agora,
    }
  else:
    stats_data["conexoes_ativas"][usuario]["data_hora"] = agora

  salvar_dados()

  user_info = relatorios_usuarios[usuario]
  status_atual = user_info.get("status_robo", "ATIVO")

  return {
      "status": "online",
      "estado_robo": status_atual,
      "saldo_creditos": user_info.get("saldo_creditos", 0.0),
      "mensagem": "Heartbeat recebido",
  }


@app.api_route("/api/v1/experiencia", methods=["GET", "POST"])
async def registrar_experiencia(request: Request):
  stats_data["total_experiencias_enviadas"] += 1
  salvar_dados()
  return {"status": "registrado", "mensagem": "Experiência absorvida."}


@app.api_route("/api/v1/relatorio-usuario", methods=["POST"])
async def receber_relatorio_usuario(request: Request):
  try:
    dados = await request.json()
  except Exception:
    dados = {}

  licenca = dados.get("licenca") or ""
  senha = dados.get("senha") or ""
  usuario = dados.get("usuario") or ""

  if not usuario or licenca != "PROD-ADM-2026" or senha != "09870987":
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=(
            "Acesso negado. Credenciais ou licença inválidas para envio de"
            " relatórios."
        ),
    )

  lucro = float(dados.get("lucro", 0.0))
  banca = float(dados.get("banca", 0.0))

  vitorias = dados.get("vitorias")
  derrotas = dados.get("derrotas")
  lucro_total_acomp = dados.get("lucro_total")
  prejuizo_total_acomp = dados.get("prejuizo_total")

  if usuario not in relatorios_usuarios:
    relatorios_usuarios[usuario] = {
        "usuario": usuario,
        "lucro_total": 0.0,
        "prejuizo_total": 0.0,
        "operacoes_vencedoras": 0,
        "operacoes_perdedoras": 0,
        "banca_atual": banca,
        "saldo_creditos": 50.00,
        "comissao_devida": 0.0,
        "status_robo": "ATIVO",
        "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

  user_data = relatorios_usuarios[usuario]
  user_data["banca_atual"] = (
      banca if banca > 0 else user_data.get("banca_atual", 0.0)
  )
  user_data["ultima_atualizacao"] = datetime.now().strftime(
      "%Y-%m-%d %H:%M:%S"
  )

  if (
      vitorias is not None
      and derrotas is not None
      and lucro_total_acomp is not None
  ):
    user_data["operacoes_vencedoras"] = int(vitorias)
    user_data["operacoes_perdedoras"] = int(derrotas)
    user_data["lucro_total"] = float(lucro_total_acomp)
    user_data["prejuizo_total"] = float(prejuizo_total_acomp)
  else:
    if lucro >= 0:
      user_data["lucro_total"] += lucro
      if lucro > 0:
        user_data["operacoes_vencedoras"] += 1
    else:
      user_data["prejuizo_total"] += abs(lucro)
      user_data["operacoes_perdedoras"] += 1

  salvar_relatorios()
  return {
      "status": "sucesso",
      "mensagem": "Relatório processado com sucesso",
      "saldo_creditos_atual": user_data["saldo_creditos"],
      "status_robo": user_data["status_robo"],
  }


@app.post("/api/v1/admin/adicionar-credito")
async def adicionar_credito(request: Request, admin: str = Depends(verificar_admin)):
  try:
    dados = await request.json()
  except Exception:
    dados = {}

  usuario = dados.get("usuario")
  valor = float(dados.get("valor", 0.0))

  if not usuario or usuario not in relatorios_usuarios:
    raise HTTPException(status_code=404, detail="Utilizador não encontrado.")

  user_data = relatorios_usuarios[usuario]
  user_data["saldo_creditos"] = user_data.get("saldo_creditos", 0.0) + valor

  if user_data["saldo_creditos"] > 0 and user_data["status_robo"] == "BLOQUEADO":
    user_data["status_robo"] = "ATIVO"

  salvar_relatorios()
  return {
      "status": "sucesso",
      "mensagem": f"Créditos adicionados com sucesso para {usuario}.",
      "novo_saldo": user_data["saldo_creditos"],
  }


@app.get("/api/v1/stats", response_class=HTMLResponse)
def obter_estatisticas(admin: str = Depends(verificar_admin)):
  ultimas_conexoes_html = ""
  marcadores_js = ""
  linhas_relatorios_html = ""
  linhas_financeiro_html = ""

  centro_lat = -22.9056
  centro_lon = -47.0608

  lista_conexoes = list(stats_data["conexoes_ativas"].values())

  for c in lista_conexoes:
    usr = c["usuario"]
    if usr not in relatorios_usuarios:
      relatorios_usuarios[usr] = {
          "usuario": usr,
          "lucro_total": 0.0,
          "prejuizo_total": 0.0,
          "operacoes_vencedoras": 0,
          "operacoes_perdedoras": 0,
          "banca_atual": 0.0,
          "saldo_creditos": 50.00,
          "comissao_devida": 0.0,
          "status_robo": "ATIVO",
          "ultima_atualizacao": c["data_hora"],
      }
      salvar_relatorios()

  if lista_conexoes:
    ultima = lista_conexoes[-1]
    centro_lat = ultima["lat"]
    centro_lon = ultima["lon"]

  for c in reversed(lista_conexoes):
    try:
      dt_conn = datetime.strptime(c["data_hora"], "%Y-%m-%d %H:%M:%S")
      ativo = datetime.now() - dt_conn < timedelta(hours=72)
    except Exception:
      ativo = True

    status_cor = "#4ade80" if ativo else "#94a3b8"
    status_txt = "Online" if ativo else "Inativo"

    ultimas_conexoes_html += f"""
        <tr>
            <td>🌍 {c['pais']}</td>
            <td>🏙️ <b>{c['localizacao']}</b><br><small style="color:var(--text-muted);">IP: {c['ip']} | Utilizador: {c['usuario']}</small></td>
            <td><span class="status-dot" style="background-color: {status_cor};"></span> <span style="color:{status_cor};">{status_txt}</span></td>
            <td>{c['data_hora']}</td>
        </tr>
        """
    marcadores_js += f"""
        L.circleMarker([{c['lat']}, {c['lon']}], {{
            radius: 12,
            fillColor: "{status_cor}",
            color: "#ffffff",
            weight: 2,
            opacity: 1,
            fillOpacity: 0.95
        }}).addTo(map).bindPopup("<b>Utilizador:</b> {c['usuario']}<br><b>Local:</b> {c['localizacao']}, {c['pais']}<br><b>IP:</b> {c['ip']}");
        """

  for usr, info in relatorios_usuarios.items():
    lucro_liquido = info["lucro_total"] - info["prejuizo_total"]
    cor_lucro = "#4ade80" if lucro_liquido >= 0 else "#f87171"
    sinal = "+" if lucro_liquido >= 0 else ""

    saldo_cred = info.get("saldo_creditos", 50.0)
    comissao_gerada = info.get("comissao_devida", 0.0)
    status_robo = info.get("status_robo", "ATIVO")
    cor_status = "#4ade80" if status_robo == "ATIVO" else "#f87171"

    linhas_relatorios_html += f"""
        <tr>
            <td>👤 <b>{usr}</b></td>
            <td>💰 R$ {info['banca_atual']:.2f}</td>
            <td style="color: {cor_lucro}; font-weight: bold;">{sinal}R$ {lucro_liquido:.2f}</td>
            <td>✅ {info['operacoes_vencedoras']} / ❌ {info['operacoes_perdedoras']}</td>
            <td>{info['ultima_atualizacao']}</td>
        </tr>
        """

    linhas_financeiro_html += f"""
        <tr>
            <td>👤 <b>{usr}</b></td>
            <td>R$ {saldo_cred:.2f}</td>
            <td style="color: #38bdf8; font-weight: bold;">R$ {comissao_gerada:.2f}</td>
            <td><span style="color: {cor_status}; font-weight: bold;">{status_robo}</span></td>
            <td><button onclick="adicionarCredito('{usr}')" style="background:#38bdf8; color:#070d1b; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; font-weight:bold;">+ Adicionar Crédito</button></td>
        </tr>
        """

  total_verif = max(
      len(stats_data["conexoes_ativas"]), len(relatorios_usuarios)
  )
  total_exp = stats_data["total_experiencias_enviadas"]
  total_ips = max(len(stats_data["ips_conectados"]), 1)
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
                cursor: pointer;
            }}
            .menu-item.active, .menu-item:hover {{
                background-color: rgba(56, 189, 248, 0.1);
                color: var(--accent-blue);
            }}
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
            .tab-content {{
                display: none;
                flex-direction: column;
                gap: 25px;
            }}
            .tab-content.active {{
                display: flex;
            }}
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
            #map, #map-expanded {{
                height: 380px;
                width: 100%;
                border-radius: 8px;
                background-color: #070d1b;
                border: 1px solid var(--border-color);
            }}
            .leaflet-tile-pane {{
                filter: brightness(0.65) invert(1) contrast(2.8) hue-rotate(200deg) saturate(1.2);
            }}
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
            <div class="menu-item active" onclick="switchTab('visao-geral', this)"><i class="fa-solid fa-chart-pie"></i> Visão Geral</div>
            <div class="menu-item" onclick="switchTab('relatorios', this)"><i class="fa-solid fa-file-invoice-dollar"></i> Relatórios</div>
            <div class="menu-item" onclick="switchTab('financeiro', this)"><i class="fa-solid fa-wallet"></i> Financeiro & Créditos</div>
            <div class="menu-item" onclick="switchTab('mapa', this)"><i class="fa-solid fa-globe"></i> Mapa Mundial</div>
            <div class="menu-item" onclick="switchTab('conexoes', this)"><i class="fa-solid fa-network-wired"></i> Conexões</div>
        </aside>

        <main class="main-container">
            <header>
                <div class="header-title">
                    <h1 id="header-title-text">Painel de Monitoramento</h1>
                    <p id="header-subtitle-text">Gestão de Licenças e Créditos em Tempo Real (Admin: {admin})</p>
                </div>
                <div class="header-right">
                    <div class="badge-online">ONLINE</div>
                    <div style="font-size: 12px; color: var(--text-muted);">
                        <i class="fa-regular fa-clock"></i> {ultima_conn}
                    </div>
                </div>
            </header>

            <div class="content">
                <!-- ABA 1: VISÃO GERAL -->
                <div id="visao-geral" class="tab-content active">
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
                                    <span>API v3.9 (Sincronização de Histórico)</span>
                                    <span style="color: var(--accent-green); font-weight: bold;">Ativo</span>
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

                <!-- ABA 2: RELATÓRIOS -->
                <div id="relatorios" class="tab-content">
                    <div class="panel">
                        <h2><i class="fa-solid fa-file-invoice-dollar" style="color: var(--accent-blue);"></i> Relatório Confidencial de Desempenho por Utilizador</h2>
                        <div class="table-wrapper" style="margin-top: 10px;">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Utilizador</th>
                                        <th>Capital (Banca Atual)</th>
                                        <th>Lucro / Prejuízo Líquido</th>
                                        <th>Vitórias / Derrotas</th>
                                        <th>Última Atividade</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {linhas_relatorios_html if linhas_relatorios_html else '<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">Nenhum dado de relatório recebido ainda.</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- ABA 3: FINANCEIRO & CRÉDITOS -->
                <div id="financeiro" class="tab-content">
                    <div class="panel">
                        <h2><i class="fa-solid fa-wallet" style="color: var(--accent-blue);"></i> Controlo Financeiro, Carteira Pré-Paga e Comissão (5%)</h2>
                        <p style="color: var(--text-muted); font-size: 13px; margin-top: -5px; margin-bottom: 15px;">
                            Acompanhe o saldo pré-pago de cada cliente e o valor acumulado das comissões descontadas automaticamente a cada lucro.
                        </p>
                        <div class="table-wrapper">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Utilizador</th>
                                        <th>Saldo Pré-Pago</th>
                                        <th>Comissão Acumulada</th>
                                        <th>Estado do Robô</th>
                                        <th>Ações Administrativas</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {linhas_financeiro_html if linhas_financeiro_html else '<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">Nenhum utilizador financeiro registado.</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- ABA 4: MAPA MUNDIAL -->
                <div id="mapa" class="tab-content">
                    <div class="panel">
                        <h2><i class="fa-solid fa-globe" style="color: var(--accent-blue);"></i> Mapa Mundial de Conexões Ativas</h2>
                        <div id="map-expanded"></div>
                    </div>
                </div>

                <!-- ABA 5: CONEXÕES -->
                <div id="conexoes" class="tab-content">
                    <div class="panel">
                        <h2><i class="fa-solid fa-network-wired" style="color: var(--accent-blue);"></i> Histórico Completo de Conexões e IPs</h2>
                        <div class="table-wrapper">
                            <table>
                                <thead>
                                    <tr>
                                        <th>País</th>
                                        <th>Localização & IP</th>
                                        <th>Status</th>
                                        <th>Último Contacto</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {ultimas_conexoes_html if ultimas_conexoes_html else '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">Sem conexões registadas.</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

            </div>
        </main>

        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
            function switchTab(tabId, element) {{
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.menu-item').forEach(el => el.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
                element.classList.add('active');

                if(tabId === 'visao-geral' || tabId === 'mapa') {{
                    setTimeout(() => {{ window.dispatchEvent(new Event('resize')); }}, 200);
                }}
            }}

            const map = L.map('map').setView([{centro_lat}, {centro_lon}], 4);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                maxZoom: 18,
                attribution: '&copy; OpenStreetMap'
            }}).addTo(map);

            const mapExp = L.map('map-expanded').setView([{centro_lat}, {centro_lon}], 4);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                maxZoom: 18,
                attribution: '&copy; OpenStreetMap'
            }}).addTo(mapExp);

            {marcadores_js}
            
            setTimeout(() => {{
                mapExp.invalidateSize();
            }}, 300);

            async function adicionarCredito(usuario) {{
                const valorStr = prompt(`Digite o valor de crédito (R$) a adicionar para o utilizador ${{usuario}}:`, "50.0");
                if (!valorStr) return;
                const valor = parseFloat(valorStr);
                if (isNaN(valor) || valor <= 0) {{
                    alert("Valor inválido.");
                    return;
                }}

                try {{
                    const response = await fetch('/api/v1/admin/adicionar-credito', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ usuario: usuario, valor: valor }})
                    }});
                    const res = await response.json();
                    if(response.ok) {{
                        alert(res.mensagem);
                        location.reload();
                    }} else {{
                        alert("Erro: " + (res.detail || "Erro desconhecido"));
                    }}
                }} catch(e) {{
                    alert("Erro de conexão com o servidor.");
                }}
            }}
        </script>
    </body>
    </html>
    """
  return html_content


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 8000))
  uvicorn.run(app, host="0.0.0.0", port=port)
