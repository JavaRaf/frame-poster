import os

import httpx

from src.logger import get_logger

logger = get_logger(__name__)


SUMMARY_FILE = os.getenv("GITHUB_STEP_SUMMARY")


def write_to_summary(content: str) -> None:
    if SUMMARY_FILE:
        with open(SUMMARY_FILE, "a") as f:
            f.write(content + "\n")


# Cabeçalho do relatório
write_to_summary('<h1 align="center">Verificação de Variáveis</h1>')
write_to_summary('<p align="center">Status das variáveis e tokens do sistema</p>')
write_to_summary('<div align="center">')
write_to_summary("\n| Variável | Status |")
write_to_summary("|----------|---------|")


def format_success(text: str) -> str:
    return f"$\\fbox{{\\color{{#126329}}\\textsf{{✅  {text}}}}}$"  # LaTeX MathJax


def format_error(text: str) -> str:
    return f"$\\fbox{{\\color{{#82061E}}\\textsf{{❌  {text}}}}}$"  # LaTeX MathJax


def format_warning(text: str) -> str:
    return f"$\\fbox{{\\color{{#FFA500}}\\textsf{{⚠️  {text}}}}}$"  # LaTeX MathJax


def create_table_row(key: str, status: str) -> None:
    write_to_summary(f"| `{key}` | {status} |")


# Verificação do token do Facebook
def check_fb_token() -> None:
    fb_token = os.getenv("FB_TOKEN")
    if not fb_token:
        create_table_row("FB_TOKEN", format_error("Token não encontrado"))
        return

    try:
        response = httpx.get(
            "https://graph.facebook.com/me",
            params={"access_token": fb_token},
            timeout=15,
        )
        response.raise_for_status()
        fb_page_name = response.json().get("name")
        
        # Token válido - mostrar sucesso
        create_table_row("FB_TOKEN", format_success(f"Token válido - {fb_page_name}"))

    except httpx.HTTPStatusError as e:
        logger.error(f"Erro HTTP: {e}", exc_info=True)
        create_table_row("FB_TOKEN", format_error(f"Erro HTTP: {e.response.status_code}"))
    except Exception as e:
        logger.error(f"Erro inesperado: {e}", exc_info=True)
        create_table_row("FB_TOKEN", format_error("Erro inesperado"))




check_fb_token()
write_to_summary("\n</div>")