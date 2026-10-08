from fastapi import FastAPI, Request, HTTPException
import json
import os
import logging

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TradingServer")

app = FastAPI()

# Caminho absoluto exato onde o Python busca e gerencia o arquivo de clientes
ARQUIVO_CLIENTES = os.path.abspath("clientes.json")

def carregar_clientes():
    logger.info(f"Procurando arquivo de clientes em: {ARQUIVO_CLIENTES}")
    if not os.path.exists(ARQUIVO_CLIENTES):
        clientes_padrao = {
            "Adm_Master": {
                "senha": "R@oyal0987",
                "licenca": "PROD-XYZ-2026",
                "liberado": True,
                "admin": True
            },
            "Adm_adm": {
                "senha": "09870987",
                "licenca": "PROD-ADM-2026",
                "liberado": True,
                "admin": True
            }
        }
        with open(ARQUIVO_CLIENTES, "w", encoding="utf-8-sig") as f:
            json.dump(clientes_padrao, f, indent=4, ensure_ascii=False)
        logger.info("Arquivo clientes.json criado automaticamente com os administradores.")
        return clientes_padrao
    
    try:
        with open(ARQUIVO_CLIENTES, "r", encoding="utf-8-sig") as f:
            dados = json.load(f)
            logger.info(f"Usuários carregados no sistema: {list(dados.keys())}")
            return dados
    except Exception as e:
        logger.error(f"Erro ao ler o arquivo '{ARQUIVO_CLIENTES}': {str(e)}")
        return {}

@app.post("/api/v1/verificar-licenca")
async def verificar_licenca(request: Request):
    try:
        body_bytes = await request.body()
        clean_bytes = body_bytes.rstrip(b'\x00').strip()
        body = json.loads(clean_bytes.decode('utf-8'))
        
        usuario = body.get("usuario", "")
        senha = body.get("senha", "")
        licenca = body.get("licenca", "")
    except Exception as e:
        logger.error(f"Falha ao decodificar JSON: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Payload JSON inválido: {str(e)}")

    db_clientes = carregar_clientes()

    cliente = db_clientes.get(usuario)
    if not cliente or cliente["senha"] != senha:
        logger.warning(f"Tentativa de acesso negada: Usuário ou senha incorretos para '{usuario}'")
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos.")
    
    if cliente["licenca"] != licenca:
        logger.warning(f"Tentativa de acesso negada: Licença incompatível para '{usuario}'")
        raise HTTPException(status_code=403, detail="Licença incompatível.")
    
    if not cliente["liberado"]:
        logger.warning(f"Tentativa de acesso negada: Acesso não liberado para '{usuario}'")
        raise HTTPException(status_code=403, detail="Acesso não liberado.")
    
    logger.info(f"✅ Licença autorizada com sucesso para: {usuario}")
    return {
        "status": "liberado",
        "admin": cliente["admin"],
        "mensagem": "Acesso autorizado com sucesso."
    }

@app.post("/api/v1/experiencia")
async def verificar_experiencia(request: Request):
    """Nova rota criada para atender às requisições de experiência/teste do robô MQL5."""
    try:
        body_bytes = await request.body()
        clean_bytes = body_bytes.rstrip(b'\x00').strip()
        body = json.loads(clean_bytes.decode('utf-8')) if clean_bytes else {}
        
        logger.info(f"Requisição de experiência recebida: {body}")
    except Exception as e:
        logger.warning(f"Aviso ao processar rota de experiência: {str(e)}")

    # Retorna uma resposta padrão para evitar o erro 404
    return {
        "status": "sucesso",
        "mensagem": "Rota de experiência validada com sucesso."
    }