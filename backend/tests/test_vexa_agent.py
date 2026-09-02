"""Tests unitaires de VexaAgent et _http_call_with_retry."""

from unittest.mock import MagicMock, call, patch

import pytest
import requests
from requests.exceptions import ConnectionError, Timeout

from app.exceptions import VexaConnectionError, VexaInvalidMeetingError
from vexa_agent import VexaAgent, _http_call_with_retry


# ── _http_call_with_retry ─────────────────────────────────────────────────────

def test_retry_returns_result_on_first_success():
    fn = MagicMock(return_value='ok')

    result = _http_call_with_retry(fn)

    assert result == 'ok'
    fn.assert_called_once()


def test_retry_succeeds_after_transient_connection_error():
    fn = MagicMock(side_effect=[ConnectionError('réseau'), 'ok'])

    with patch('vexa_agent.time.sleep'):
        result = _http_call_with_retry(fn)

    assert result == 'ok'
    assert fn.call_count == 2


def test_retry_succeeds_after_transient_timeout():
    fn = MagicMock(side_effect=[Timeout('timeout'), Timeout('timeout'), 'ok'])

    with patch('vexa_agent.time.sleep'):
        result = _http_call_with_retry(fn)

    assert result == 'ok'
    assert fn.call_count == 3


def test_retry_raises_after_max_attempts():
    fn = MagicMock(side_effect=ConnectionError('réseau'))

    with patch('vexa_agent.time.sleep'), pytest.raises(ConnectionError):
        _http_call_with_retry(fn)

    assert fn.call_count == 3


def test_retry_does_not_catch_http_error():
    response = MagicMock()
    response.status_code = 500
    fn = MagicMock(side_effect=requests.HTTPError(response=response))

    with pytest.raises(requests.HTTPError):
        _http_call_with_retry(fn)

    fn.assert_called_once()


def test_retry_applies_exponential_backoff():
    fn = MagicMock(side_effect=[ConnectionError(), ConnectionError(), 'ok'])
    sleep_calls = []

    with patch('vexa_agent.time.sleep', side_effect=lambda s: sleep_calls.append(s)):
        _http_call_with_retry(fn)

    assert sleep_calls == [1, 2]


# ── VexaAgent.send_bot ────────────────────────────────────────────────────────

def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    return resp


def test_send_bot_with_meeting_url_posts_correct_payload():
    agent = VexaAgent()
    mock_resp = _mock_response(json_data={'bot_id': '123'})

    with patch('vexa_agent.requests.post', return_value=mock_resp) as mock_post:
        result = agent.send_bot('google_meet', 'abc123', meeting_url='https://meet.google.com/abc')

    payload = mock_post.call_args.kwargs['json']
    assert 'meeting_url' in payload
    assert 'platform' not in payload
    assert result == {'bot_id': '123'}


def test_send_bot_without_url_posts_platform_payload():
    agent = VexaAgent()
    mock_resp = _mock_response(json_data={'bot_id': '456'})

    with patch('vexa_agent.requests.post', return_value=mock_resp) as mock_post:
        agent.send_bot('google_meet', 'abc123')

    payload = mock_post.call_args.kwargs['json']
    assert payload['platform'] == 'google_meet'
    assert payload['native_meeting_id'] == 'abc123'
    assert 'meeting_url' not in payload


def test_send_bot_raises_connection_error_on_network_failure():
    agent = VexaAgent()

    with patch('vexa_agent.requests.post', side_effect=ConnectionError()):
        with pytest.raises(VexaConnectionError):
            agent.send_bot('google_meet', 'abc123')


def test_send_bot_raises_invalid_meeting_on_422():
    agent = VexaAgent()
    mock_resp = _mock_response(status_code=422)

    with patch('vexa_agent.requests.post', return_value=mock_resp):
        with pytest.raises(VexaInvalidMeetingError):
            agent.send_bot('google_meet', 'invalid-url')


def test_send_bot_raises_connection_error_on_non_422_http_error():
    agent = VexaAgent()
    mock_resp = _mock_response(status_code=503)

    with patch('vexa_agent.requests.post', return_value=mock_resp):
        with pytest.raises(VexaConnectionError):
            agent.send_bot('google_meet', 'abc123')


# ── VexaAgent.stop_bot ────────────────────────────────────────────────────────

def test_stop_bot_returns_status_code():
    agent = VexaAgent()
    mock_resp = _mock_response(status_code=200)

    with patch('vexa_agent.requests.delete', return_value=mock_resp):
        result = agent.stop_bot('google_meet', 'abc123')

    assert result == 200


def test_stop_bot_raises_connection_error_on_network_failure():
    agent = VexaAgent()

    with patch('vexa_agent.requests.delete', side_effect=Timeout()):
        with pytest.raises(VexaConnectionError):
            agent.stop_bot('google_meet', 'abc123')


# ── VexaAgent.get_transcript ──────────────────────────────────────────────────

def test_get_transcript_formats_segments_as_lines():
    agent = VexaAgent()
    segments = [
        {'speaker': 'Alice', 'text': 'Bonjour tout le monde'},
        {'speaker': 'Bob', 'text': 'Merci Alice'},
    ]
    mock_resp = _mock_response(json_data={'segments': segments})

    with patch('vexa_agent.requests.get', return_value=mock_resp):
        result = agent.get_transcript('google_meet', 'abc123')

    assert result == 'Alice : Bonjour tout le monde\nBob : Merci Alice'


def test_get_transcript_skips_empty_text_segments():
    agent = VexaAgent()
    segments = [
        {'speaker': 'Alice', 'text': 'Bonjour'},
        {'speaker': 'Bob', 'text': '   '},
        {'speaker': 'Alice', 'text': 'Au revoir'},
    ]
    mock_resp = _mock_response(json_data={'segments': segments})

    with patch('vexa_agent.requests.get', return_value=mock_resp):
        result = agent.get_transcript('google_meet', 'abc123')

    assert 'Bob' not in result
    assert result == 'Alice : Bonjour\nAlice : Au revoir'


def test_get_transcript_returns_empty_string_when_no_segments():
    agent = VexaAgent()
    mock_resp = _mock_response(json_data={'segments': []})

    with patch('vexa_agent.requests.get', return_value=mock_resp):
        result = agent.get_transcript('google_meet', 'abc123')

    assert result == ''


def test_get_transcript_uses_inconnu_when_speaker_missing():
    agent = VexaAgent()
    segments = [{'text': 'Bonjour'}]
    mock_resp = _mock_response(json_data={'segments': segments})

    with patch('vexa_agent.requests.get', return_value=mock_resp):
        result = agent.get_transcript('google_meet', 'abc123')

    assert result == 'Inconnu : Bonjour'


# ── VexaAgent.get_diarized_segments ──────────────────────────────────────────

def test_get_diarized_segments_returns_raw_segments():
    agent = VexaAgent()
    segments = [
        {'speaker': 'Alice', 'text': 'Bonjour', 'start': 0.0, 'end': 2.0},
        {'speaker': 'Bob', 'text': 'Salut', 'start': 2.0, 'end': 4.0},
    ]
    mock_resp = _mock_response(json_data={'segments': segments})

    with patch('vexa_agent.requests.get', return_value=mock_resp):
        result = agent.get_diarized_segments('google_meet', 'abc123')

    assert result == segments


# ── VexaAgent._fetch_segments ─────────────────────────────────────────────────

def test_fetch_segments_raises_connection_error_on_network_failure():
    agent = VexaAgent()

    with patch('vexa_agent.requests.get', side_effect=ConnectionError()):
        with pytest.raises(VexaConnectionError):
            agent._fetch_segments('google_meet', 'abc123')


def test_fetch_segments_raises_connection_error_on_http_error():
    agent = VexaAgent()
    mock_resp = _mock_response(status_code=500)

    with patch('vexa_agent.requests.get', return_value=mock_resp):
        with pytest.raises(VexaConnectionError):
            agent._fetch_segments('google_meet', 'abc123')


def test_fetch_segments_returns_empty_list_when_key_missing():
    agent = VexaAgent()
    mock_resp = _mock_response(json_data={})

    with patch('vexa_agent.requests.get', return_value=mock_resp):
        result = agent._fetch_segments('google_meet', 'abc123')

    assert result == []
