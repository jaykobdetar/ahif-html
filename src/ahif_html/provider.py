"""Narrow, explicitly configured inference gateway; never executes model tools."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.error import URLError, HTTPError

from .common import Failure, C, ahif, load_json, validate, sha, schema


@dataclass(frozen=True)
class Reply:
    action: dict
    usage: dict


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Failure('provider_redirect_refused', 'model_unavailable')


def validate_config(config):
    if isinstance(config, dict) and config.get('version') in ('1.1.0', '1.1.1'):
        # An explicit hosted contract; never disguise a cloud endpoint as Ollama.
        validate('model-config-' + config['version'], config)
        from .common import check_path
        ledger = Path(config['openai']['budget_ledger'])
        if not ledger.is_absolute():
            raise Failure('provider_budget_ledger_must_be_absolute')
        check_path(ledger)
        if not config['data_approval']['approved'] or not config['data_approval']['capture_sha256']:
            raise Failure('provider_data_approval_missing')
        if config['budgets']['max_output_tokens_per_call'] > config['budgets']['max_output_tokens_total']:
            raise Failure('provider_output_budget_invalid')
        return config
    validate('model-config', config)
    if config['mode'] == 'live':
        try:
            target = urlsplit(config['endpoint'])
        except ValueError as exc:
            raise Failure('provider_endpoint_invalid') from exc
        if (target.scheme != 'http' or target.hostname not in ('127.0.0.1', 'localhost', '::1')
                or target.username or target.password or target.path not in ('', '/')
                or target.query or target.fragment):
            raise Failure('provider_endpoint_not_loopback')
        if not config['data_approval']['approved'] or not config['model']:
            raise Failure('provider_data_approval_missing')
        if not config['data_approval']['capture_sha256']:
            raise Failure('provider_capture_approval_missing')
        try:
            target.port
        except ValueError as exc:
            raise Failure('provider_endpoint_port_invalid') from exc
        if config['model'].endswith('-cloud') or config['model'].endswith(':cloud'):
            raise Failure('provider_remote_model_refused')
        if config['provider_location'] == 'remote_tunnel' and config['tunnel_declaration'] is None:
            raise Failure('provider_tunnel_declaration_missing')
        if config['provider_location'] == 'workstation' and config['tunnel_declaration'] is not None:
            raise Failure('provider_tunnel_declaration_conflict')
    if config['budgets']['max_output_tokens_per_call'] > config['budgets']['max_output_tokens_total']:
        raise Failure('provider_output_budget_invalid')
    return config


class OllamaProvider:
    mode = 'live'

    def __init__(self, config, transport=None):
        self.config = validate_config(config)
        self.transport = transport or self._http
        target = urlsplit(config['endpoint'])
        host = '127.0.0.1' if target.hostname == 'localhost' else target.hostname
        host = f'[{host}]' if ':' in host else host
        self.endpoint = urlunsplit(('http', host + (f':{target.port}' if target.port else ''), '', '', ''))
        self.local_model = None
        self.gateway_requests = 0

    def _preflight(self, timeout):
        # Metadata-only request. The local server is trusted; no model auto-download,
        # remote model, or cloud routing is accepted by this adapter.
        self.gateway_requests += 1
        raw = self.transport(self.endpoint + '/api/show', C({'model': self.config['model']}), timeout,
                             self.config['budgets']['max_response_bytes'])
        try:
            info = json.loads(raw)
            if (not isinstance(info, dict) or info.get('remote_host') or info.get('remote_model')
                    or info.get('error') or info.get('details', {}).get('format') != 'gguf'
                    or not info.get('model_info')):
                raise ValueError('not an installed local GGUF model')
            self.local_model = {'response_sha256': sha(raw), 'format': 'gguf',
                                'remote_model_routing': False, 'model': self.config['model'],
                                'daemon_location': self.config['provider_location']}
        except (ValueError, TypeError, AttributeError) as exc:
            raise Failure('provider_local_model_not_verified', 'model_unavailable') from exc

    @staticmethod
    def _http(endpoint, payload, timeout, response_limit):
        # Disable environment proxies and redirects. Only this gateway has HTTP.
        opener = build_opener(ProxyHandler({}), NoRedirect())
        req = Request(endpoint, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with opener.open(req, timeout=timeout) as response:
                if response.status != 200:
                    raise Failure('provider_http_error', 'model_unavailable')
                raw = response.read(response_limit + 1)
        except Failure:
            raise
        except HTTPError as exc:
            received = exc.read(8193)
            raw = received[:8192]
            error = Failure('provider_http_error', 'model_unavailable')
            error.http_details = {'status_code': exc.code, 'retained_body_sha256': sha(raw),
                                  'truncated': len(received) > 8192,
                                  'retained_bytes': len(raw), 'body': raw.decode('utf8', errors='replace')}
            raise error from exc
        except (URLError, TimeoutError, OSError) as exc:
            # Never expose response bodies, URLs with query values, or exception secrets.
            raise Failure('provider_transport_error', 'model_unavailable') from exc
        if len(raw) > response_limit:
            raise Failure('provider_response_byte_limit', 'resource_limit')
        return raw

    def call(self, messages, max_output_tokens, timeout):
        self.last_public_response = None
        self.last_public_request = None
        self.last_usage = None
        deadline = time.monotonic() + timeout
        memory = Path('/proc/meminfo')
        if memory.is_file():
            available = next((int(line.split()[1]) for line in memory.read_text().splitlines()
                              if line.startswith('MemAvailable:')), None)
            if available is not None and available < self.config['min_available_memory_mib'] * 1024:
                raise Failure('provider_available_memory_limit', 'resource_limit')
        if self.local_model is None:
            self._preflight(timeout)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise Failure('provider_deadline_limit', 'resource_limit')
        grammar = schema('planner-response-1.1.0')
        proposal = next(v for v in grammar['oneOf'] if v['properties']['action']['enum'] == ['propose'])
        contract = schema('plan')['properties']
        for name in ('contributions', 'rejected', 'unresolved'):
            proposal['properties']['proposal']['properties'][name] = contract[name]
        phase = getattr(self, 'phase', 'planner')
        allowed = ('tool', 'ready_for_review', 'refuse') if phase == 'reviewer_observe' else (
            ('tool', 'review', 'refuse') if phase == 'reviewer_decide' else ('tool', 'propose', 'refuse'))
        grammar['oneOf'] = [v for v in grammar['oneOf'] if v['properties']['action']['enum'][0] in allowed]
        def alias_patterns(value):
            if isinstance(value, dict):
                if value.get('pattern', '').startswith('^sha256:'):
                    value['pattern'] = r'^(n[0-9]+|sha256:[0-9a-f]{64}:[0-9]+)$'
                for child in value.values():
                    alias_patterns(child)
            elif isinstance(value, list):
                for child in value:
                    alias_patterns(child)
        alias_patterns(grammar)
        request = {'model': self.config['model'], 'messages': messages, 'stream': False,
                   'format': grammar if self.config['response_format'] == 'schema' else 'json',
                   'think': False, 'keep_alive': '5m',
                   'options': {'temperature': 0, 'num_predict': max_output_tokens,
                               'num_ctx': self.config['num_ctx']}}
        self.last_public_request = request
        self.gateway_requests += 1
        raw = self.transport(self.endpoint + '/api/chat', C(request), remaining,
                             self.config['budgets']['max_response_bytes'])
        self.last_public_response = {'envelope_sha256': sha(raw), 'envelope_byte_length': len(raw),
                                     'content': None, 'retention': 'content_and_usage_only_no_hidden_thinking'}
        try:
            # Provider operational envelope may have floats; it never enters AHIF.
            envelope = json.loads(raw)
            if not isinstance(envelope, dict):
                raise ValueError('invalid envelope')
            usage = {}
            for output, key in (('input_tokens', 'prompt_eval_count'), ('output_tokens', 'eval_count')):
                count = envelope.get(key)
                usage[output] = count if type(count) is int and 0 <= count <= 9007199254740991 else None
            usage['cache_hits'] = None
            usage['monetary_cost'] = None
            self.last_usage = usage
            message = envelope.get('message')
            content = message.get('content') if isinstance(message, dict) else None
            if isinstance(content, str):
                self.last_public_response['content'] = content
            if envelope.get('error') or envelope.get('remote_host') or envelope.get('remote_model'):
                raise ValueError('provider error')
            if envelope.get('done') is not True:
                raise ValueError('incomplete provider reply')
            if not isinstance(content, str):
                raise ValueError('invalid content')
            if (usage['input_tokens'] is not None and usage['output_tokens'] is not None
                    and usage['input_tokens'] + usage['output_tokens'] > self.config['num_ctx']):
                raise Failure('provider_context_limit', 'resource_limit')
            if envelope.get('done_reason') in ('length', 'max_tokens'):
                raise Failure('provider_output_truncated', 'resource_limit')
            action = ahif.strict_loads(content)
            # Do not retain message.thinking or unknown provider fields.
            return Reply(action, usage)
        except Failure:
            raise
        except (ValueError, KeyError, TypeError, ahif.Invalid) as exc:
            raise Failure('provider_response_invalid', 'unresolved_plan') from exc


class RecordedProvider:
    """Explicit test input, not inference. It has no capture/fixture lookup."""

    def __init__(self, responses, mode='recorded'):
        if mode not in ('recorded', 'mock'):
            raise Failure('recorded_mode_invalid')
        self.mode = mode
        self.responses = iter(responses)

    def call(self, messages, max_output_tokens, timeout):
        try:
            value = next(self.responses)
        except StopIteration as exc:
            raise Failure('recorded_responses_exhausted', 'model_unavailable') from exc
        self.last_public_response = {'content': C(value).decode(), 'retention': 'explicit_test_response'}
        return Reply(value, {'input_tokens': None, 'output_tokens': None,
                             'cache_hits': None, 'monetary_cost': None})


def make_provider(config):
    validate_config(config)
    if config['version'] in ('1.1.0', '1.1.1'):
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(config)
    if config['mode'] == 'live':
        return OllamaProvider(config)
    value = load_json(config['responses_file'], config['budgets']['max_recording_bytes'])
    if not isinstance(value, list):
        raise Failure('recorded_responses_invalid')
    return RecordedProvider(value, config['mode'])
