"""
Baseline da v1 — gera os numeros reais do prompt ruim para a tabela comparativa
do README (v1 vs v2).

O que faz:
1. Le prompts/bug_to_user_story_v1.yml (o prompt de baixa qualidade que veio do pull)
2. Publica como {USERNAME_LANGSMITH_HUB}/bug_to_user_story_v1
3. Roda o MESMO experimento e as MESMAS metricas de src/evaluate.py contra o
   mesmo dataset, reaproveitando as funcoes de la sem alterar aquele arquivo

Uso:
    python src/baseline_v1.py
"""

import os
import sys
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate

from utils import load_yaml, check_env_vars, print_section_header
from evaluate import (
    create_evaluation_dataset,
    run_experiment,
    display_results,
)

load_dotenv()

PROMPT_FILE = "prompts/bug_to_user_story_v1.yml"
PROMPT_KEY = "bug_to_user_story_v1"
JSONL_PATH = "datasets/bug_to_user_story.jsonl"


def push_v1(client: Client, repo: str, prompt_data: dict) -> bool:
    """Publica a v1 no Hub, para que o experimento possa puxa-la de la."""
    template = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_data["system_prompt"]),
            ("user", prompt_data["user_prompt"]),
        ]
    )

    try:
        url = client.push_prompt(
            repo,
            object=template,
            is_public=True,
            description="Baseline v1 (prompt de baixa qualidade) - usado para comparacao com a v2 otimizada",
            tags=["baseline", "v1", "bug-analysis"],
        )
        print(f"   OK publicado: {url}")
        return True
    except Exception as e:
        print(f"   ERRO no push da v1: {e}")
        return False


def main():
    print_section_header("BASELINE DA V1 (para a tabela comparativa)")

    required = ["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB", "LLM_PROVIDER"]
    if os.getenv("LLM_PROVIDER", "").lower() == "openai":
        required.append("OPENAI_API_KEY")
    else:
        required.append("GOOGLE_API_KEY")

    if not check_env_vars(required):
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB")
    project_name = os.getenv("LANGSMITH_PROJECT")
    dataset_name = f"{project_name}-eval"

    print(f"Provider: {os.getenv('LLM_PROVIDER')}")
    print(f"Modelo Principal: {os.getenv('LLM_MODEL')}")
    print(f"Modelo de Avaliacao: {os.getenv('EVAL_MODEL')}\n")

    data = load_yaml(PROMPT_FILE)
    if not data or PROMPT_KEY not in data:
        print(f"Nao foi possivel ler '{PROMPT_KEY}' de {PROMPT_FILE}")
        print("Rode antes: python src/pull_prompts.py")
        return 1

    prompt_data = data[PROMPT_KEY]
    client = Client()

    # Mesmo dataset usado pela avaliacao da v2 (reutiliza se ja existir)
    create_evaluation_dataset(client, dataset_name, JSONL_PATH)

    repo = f"{username}/{PROMPT_KEY}"
    print(f"\nPublicando baseline no Hub: {repo}")
    if not push_v1(client, repo, prompt_data):
        return 1

    scores, url = run_experiment(client, repo, dataset_name)
    display_results(repo, scores)

    print(f"\nExperimento da v1: {url}")
    print("\nUse estes numeros na tabela 'v1 vs v2' do README.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
