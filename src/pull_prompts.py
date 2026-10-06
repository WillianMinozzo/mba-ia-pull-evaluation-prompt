"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

SOURCE_PROMPT = "leonanluppi/bug_to_user_story_v1"
OUTPUT_PATH = "prompts/bug_to_user_story_v1.yml"
PROMPT_KEY = "bug_to_user_story_v1"


def extract_templates(prompt_obj) -> dict:
    """
    Extrai system_prompt / user_prompt de um ChatPromptTemplate do LangChain.

    Percorre prompt_obj.messages e separa por tipo de mensagem, usando a
    serializacao nativa (.prompt.template de cada mensagem).
    """
    system_parts: list = []
    user_parts: list = []

    messages = getattr(prompt_obj, "messages", None)

    if not messages:
        # PromptTemplate simples, sem lista de mensagens
        return {"system_prompt": getattr(prompt_obj, "template", ""), "user_prompt": ""}

    for message in messages:
        inner = getattr(message, "prompt", None)
        template = getattr(inner, "template", None)

        if template is None:
            template = getattr(message, "content", "")

        role = type(message).__name__.lower()

        if "system" in role:
            system_parts.append(template)
        else:
            user_parts.append(template)

    return {
        "system_prompt": "\n".join(system_parts).strip(),
        "user_prompt": "\n".join(user_parts).strip(),
    }


def pull_prompts_from_langsmith() -> bool:
    """
    Faz pull do prompt de baixa qualidade do LangSmith Hub e salva em YAML.

    Returns:
        True se sucesso, False caso contrario
    """
    print(f"Puxando prompt do LangSmith Hub: {SOURCE_PROMPT}")

    try:
        client = Client()
        # dangerously_pull_public_prompt=True e obrigatorio quando o identificador
        # tem dono explicito ("owner/nome"): o objeto vem serializado de terceiros.
        prompt_obj = client.pull_prompt(
            SOURCE_PROMPT,
            dangerously_pull_public_prompt=True,
        )
    except Exception as e:
        print(f"\nErro ao fazer pull de '{SOURCE_PROMPT}': {e}\n")
        print("Verifique:")
        print("  - LANGSMITH_API_KEY esta configurada no .env")
        print("  - LANGSMITH_ENDPOINT aponta para https://api.smith.langchain.com")
        print("  - O prompt existe e esta publico no Hub")
        return False

    print("   OK prompt carregado")

    templates = extract_templates(prompt_obj)

    if not templates["system_prompt"] and not templates["user_prompt"]:
        print("   ERRO: nao foi possivel extrair nenhum template do prompt")
        return False

    input_variables = list(getattr(prompt_obj, "input_variables", []) or [])

    data = {
        PROMPT_KEY: {
            "description": "Prompt para converter relatos de bugs em User Stories",
            "system_prompt": templates["system_prompt"],
            "user_prompt": templates["user_prompt"],
            "version": "v1",
            "source": SOURCE_PROMPT,
            "input_variables": input_variables,
            "tags": ["bug-analysis", "user-story", "product-management"],
        }
    }

    if not save_yaml(data, OUTPUT_PATH):
        return False

    print(f"   OK salvo em {OUTPUT_PATH}")
    print(f"   Variaveis de entrada: {input_variables}")
    print(f"   system_prompt: {len(templates['system_prompt'])} chars")
    print(f"   user_prompt:   {len(templates['user_prompt'])} chars")

    return True


def main():
    """Funcao principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    Path("prompts").mkdir(parents=True, exist_ok=True)

    if not pull_prompts_from_langsmith():
        return 1

    print("\nProximo passo: refatorar em prompts/bug_to_user_story_v2.yml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
