# Tests unitaires sur l'extraction JSON du LLM (LLMService.generate_structured_summary).
#
# Le client Anthropic est entierement mocke : aucun appel reseau reel, donc
# aucune dependance a une cle API valide ni a des credits sur le compte.

from unittest.mock import MagicMock, patch

from app.schemas.llm_summary import ActionItem, StructuredSummary
from app.services.llm_service import LLMService

SAMPLE_TRANSCRIPTION = "Alice : On a fini l'authentification. Bob : Reste le résumé IA."


# ── JSON valide ───────────────────────────────────────────────────────────

@patch('app.services.llm_service.anthropic.Anthropic')
def test_generate_structured_summary_parses_valid_json(mock_anthropic_cls):
    # Arrange : le client mocke renvoie une reponse structuree deja validee
    # par le SDK (c'est le contrat de client.messages.parse avec
    # output_format) - LLMService n'a qu'a la relayer.
    mock_client = MagicMock()
    fake_response = MagicMock()
    fake_response.parsed_output = StructuredSummary(
        themes=['Authentification', 'Résumé IA'],
        decisions=['Merger la PR une fois les tests verts'],
        actions=[ActionItem(description='Écrire le résumé IA', responsable='Bob', echeance=None)],
    )
    mock_client.messages.parse.return_value = fake_response
    mock_anthropic_cls.return_value = mock_client

    service = LLMService()

    # Act
    result = service.generate_structured_summary(SAMPLE_TRANSCRIPTION)

    # Assert : le JSON structuré est correctement parsé et retourné tel quel
    assert result is not None
    assert result.themes == ['Authentification', 'Résumé IA']
    assert result.decisions == ['Merger la PR une fois les tests verts']
    assert len(result.actions) == 1
    assert result.actions[0].description == 'Écrire le résumé IA'
    assert result.actions[0].responsable == 'Bob'

    # et la transcription d'origine a bien été envoyée dans le prompt
    _, kwargs = mock_client.messages.parse.call_args
    sent_content = kwargs['messages'][0]['content']
    assert SAMPLE_TRANSCRIPTION in sent_content
    assert kwargs['output_format'] is StructuredSummary


# ── Échec de l'appel API ──────────────────────────────────────────────────
# Remplace l'ancien cas "JSON mal formé + retry" : depuis la migration vers
# Anthropic, les structured outputs garantissent un JSON conforme au schéma
# côté serveur, donc le seul cas d'échec possible aujourd'hui est un échec
# de l'appel API lui-même (timeout, quota, erreur réseau...).

@patch('app.services.llm_service.anthropic.Anthropic')
def test_generate_structured_summary_returns_none_on_api_failure(mock_anthropic_cls):
    # Arrange : le client mocke lève une exception, comme le ferait le SDK
    # Anthropic en cas de timeout, de quota dépassé ou d'erreur serveur.
    mock_client = MagicMock()
    mock_client.messages.parse.side_effect = Exception('boom: API unavailable')
    mock_anthropic_cls.return_value = mock_client

    service = LLMService()

    # Act : ne doit PAS lever d'exception
    result = service.generate_structured_summary(SAMPLE_TRANSCRIPTION)

    # Assert : l'erreur est absorbée, l'application ne plante pas
    assert result is None


# ── Transcription vide ────────────────────────────────────────────────────

@patch('app.services.llm_service.anthropic.Anthropic')
def test_generate_structured_summary_with_empty_transcription_skips_api_call(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client

    service = LLMService()
    result = service.generate_structured_summary('   ')

    assert result is None
    mock_client.messages.parse.assert_not_called()
