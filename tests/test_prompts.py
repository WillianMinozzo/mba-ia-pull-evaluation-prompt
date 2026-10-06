"""
Testes automatizados para validacao de prompts.
"""
import re
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = str(Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml")
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt():
    data = load_prompts(PROMPT_FILE)
    assert data is not None, f"YAML vazio ou invalido: {PROMPT_FILE}"
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' ausente em {PROMPT_FILE}"
    return data[PROMPT_KEY]


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt):
        """Verifica se o campo 'system_prompt' existe e nao esta vazio."""
        assert "system_prompt" in prompt, "Campo 'system_prompt' ausente"
        system_prompt = prompt["system_prompt"]
        assert isinstance(system_prompt, str), "'system_prompt' deve ser string"
        assert system_prompt.strip(), "'system_prompt' esta vazio"
        assert len(system_prompt.strip()) > 200, "'system_prompt' curto demais para um prompt otimizado"

    def test_prompt_has_role_definition(self, prompt):
        """Verifica se o prompt define uma persona (ex: "Voce e um Product Manager")."""
        system_prompt = prompt["system_prompt"]
        assert re.search(
            r"voc[eê]\s+[eé]\s+(um|uma)\s+\w+", system_prompt, re.IGNORECASE
        ), "system_prompt nao define uma persona ('Voce e um/uma ...')"

    def test_prompt_mentions_format(self, prompt):
        """Verifica se o prompt exige formato Markdown ou User Story padrao."""
        text = prompt["system_prompt"] + prompt.get("user_prompt", "")
        lowered = text.lower()

        has_user_story_template = all(
            token in lowered for token in ("como um", "eu quero", "para que")
        )
        has_acceptance_criteria = "critérios de aceitação" in lowered or "criterios de aceitacao" in lowered
        has_markdown = "markdown" in lowered

        assert has_user_story_template, "Prompt nao exige o template 'Como um... eu quero... para que...'"
        assert has_acceptance_criteria or has_markdown, "Prompt nao exige Criterios de Aceitacao nem Markdown"

    def test_prompt_has_few_shot_examples(self, prompt):
        """Verifica se o prompt contem exemplos de entrada/saida (tecnica Few-shot)."""
        system_prompt = prompt["system_prompt"]
        lowered = system_prompt.lower()

        example_markers = len(re.findall(r"exemplo\s*\d", lowered))
        assert example_markers >= 2, f"Few-shot exige >= 2 exemplos, encontrados: {example_markers}"

        assert lowered.count("entrada") >= 2, "Exemplos nao possuem bloco de ENTRADA"
        assert lowered.count("saída") >= 2 or lowered.count("saida") >= 2, "Exemplos nao possuem bloco de SAIDA"

    def test_prompt_no_todos(self, prompt):
        """Garante que voce nao esqueceu nenhum `[TODO]` no texto."""
        for field in ("description", "system_prompt", "user_prompt"):
            value = str(prompt.get(field, ""))
            assert "[TODO]" not in value, f"'{field}' ainda contem [TODO]"
            # Mesmo criterio do validate_prompt_structure() em src/utils.py:
            # substring case-sensitive, para nao colidir com a palavra "todos" em portugues.
            assert "TODO" not in value, f"'{field}' ainda contem TODO"

    def test_minimum_techniques(self, prompt):
        """Verifica (atraves dos metadados do yaml) se pelo menos 2 tecnicas foram listadas."""
        techniques = prompt.get("techniques_applied", [])
        assert isinstance(techniques, list), "'techniques_applied' deve ser uma lista"
        assert len(techniques) >= 2, f"Minimo de 2 tecnicas, encontradas: {len(techniques)}"

        is_valid, errors = validate_prompt_structure(prompt)
        assert is_valid, f"validate_prompt_structure falhou: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
