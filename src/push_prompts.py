"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Le os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PUBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descricao, tecnicas utilizadas)
"""

import os
import sys
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_FILE = "prompts/bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"
EXPECTED_INPUT_VARS = {"bug_report"}


def build_chat_prompt(prompt_data: dict) -> ChatPromptTemplate:
    """Monta o ChatPromptTemplate a partir dos campos do YAML."""
    return ChatPromptTemplate.from_messages(
        [
            ("system", prompt_data["system_prompt"]),
            ("user", prompt_data["user_prompt"]),
        ]
    )


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura basica de um prompt (versao simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    if not isinstance(prompt_data, dict):
        return False, ["Prompt invalido: esperado um dicionario"]

    for field in ("description", "system_prompt", "user_prompt", "version"):
        if not str(prompt_data.get(field, "")).strip():
            errors.append(f"Campo obrigatorio ausente ou vazio: {field}")

    system_prompt = str(prompt_data.get("system_prompt", ""))
    user_prompt = str(prompt_data.get("user_prompt", ""))

    if "TODO" in system_prompt or "TODO" in user_prompt:
        errors.append("Prompt ainda contem marcadores TODO")

    techniques = prompt_data.get("techniques_applied", []) or []
    if len(techniques) < 2:
        errors.append(
            f"Minimo de 2 tecnicas em techniques_applied, encontradas: {len(techniques)}"
        )

    # A variavel do dataset e {bug_report} e deve estar APENAS no user prompt.
    if "{bug_report}" not in user_prompt:
        errors.append("user_prompt nao contem a variavel {bug_report}")

    if "{bug_report}" in system_prompt:
        errors.append(
            "system_prompt contem {bug_report} (defeito herdado da v1) - mantenha a variavel so no user_prompt"
        )

    # O template precisa compilar e expor exatamente a variavel esperada.
    if not errors:
        try:
            template = build_chat_prompt(prompt_data)
            found = set(template.input_variables)
            if found != EXPECTED_INPUT_VARS:
                errors.append(
                    f"input_variables inesperadas: {sorted(found)} (esperado: {sorted(EXPECTED_INPUT_VARS)}). "
                    "Chaves literais nos exemplos precisam ser escapadas como chave dupla."
                )
        except Exception as e:
            errors.append(f"Falha ao compilar o ChatPromptTemplate: {e}")

    return (len(errors) == 0, errors)


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PUBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrario
    """
    techniques = prompt_data.get("techniques_applied", []) or []
    tags = list(prompt_data.get("tags", []) or [])

    description = (
        f"{prompt_data.get('description', '')} | Tecnicas aplicadas: {', '.join(techniques)}"
    ).strip()

    try:
        template = build_chat_prompt(prompt_data)
        client = Client()

        url = client.push_prompt(
            prompt_name,
            object=template,
            is_public=True,
            description=description[:400],
            tags=tags,
        )

        print("   OK push concluido")
        print(f"   URL: {url}")
        return True

    except Exception as e:
        print(f"   ERRO no push: {e}")
        print("\nVerifique:")
        print("  - LANGSMITH_API_KEY valida no .env")
        print("  - USERNAME_LANGSMITH_HUB corresponde ao seu handle publico do Hub")
        return False


def main():
    """Funcao principal"""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB")

    data = load_yaml(PROMPT_FILE)
    if not data:
        return 1

    prompt_data = data.get(PROMPT_KEY)
    if not prompt_data:
        print(f"Chave '{PROMPT_KEY}' nao encontrada em {PROMPT_FILE}")
        return 1

    print(f"Validando {PROMPT_FILE}...")
    is_valid, errors = validate_prompt(prompt_data)

    if not is_valid:
        print("\nPrompt invalido:")
        for error in errors:
            print(f"   - {error}")
        return 1

    techniques = prompt_data.get("techniques_applied", [])
    print(f"   OK valido | tecnicas aplicadas: {len(techniques)}")
    for technique in techniques:
        print(f"      - {technique}")

    repo = f"{username}/{PROMPT_KEY}"
    print(f"\nEnviando para o Hub (publico): {repo}")

    if not push_prompt_to_langsmith(repo, prompt_data):
        return 1

    print("\nProximo passo: python src/evaluate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
