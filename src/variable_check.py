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

    # Remove whitespace and newlines from token to prevent API errors
    fb_token = fb_token.strip()
    
    # Remove FB_TOKEN= prefix if present (common issue in CI/CD environments)
    if fb_token.startswith("FB_TOKEN="):
        fb_token = fb_token[8:]  # Remove "FB_TOKEN=" prefix
    
    # Debug information for troubleshooting
    print(f"Token length: {len(fb_token)}")
    print(f"Token starts with: {repr(fb_token[:20])}")
    print(f"Token ends with: {repr(fb_token[-20:])}")
    print(f"Token contains newlines: {'\\n' in fb_token}")
    print(f"Token contains carriage returns: {'\\r' in fb_token}")

    try:
        response = httpx.get(
            "https://graph.facebook.com/v21.0/me",
            params={"access_token": fb_token},
            timeout=15,
        )
        response.raise_for_status()
        fb_page_name = response.json().get("name")
        
        # Token válido - mostrar sucesso
        create_table_row("FB_TOKEN", format_success(f"Token válido - {fb_page_name}"))

    except httpx.HTTPStatusError as e:
        # Note: intentionally not logging e.request.url here because it
        # embeds the raw access_token in the query string.
        logger.error(
            "FB_TOKEN check failed: HTTP %s - %s",
            e.response.status_code, e.response.text[:500],
        )
        create_table_row("FB_TOKEN", format_error(f"Erro HTTP: {e.response.status_code}"))
    except httpx.RequestError as e:
        logger.error("FB_TOKEN check failed: %s: %s", type(e).__name__, e, exc_info=True)
        create_table_row("FB_TOKEN", format_error("Erro de rede"))




check_fb_token()
write_to_summary("\n</div>")