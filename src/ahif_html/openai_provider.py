"""Explicit Luna Responses gateway and a shared, append-only spending ledger.

Pricing/source contract checked 2026-09-16:
https://developers.openai.com/api/docs/models/gpt-5.6-luna
https://developers.openai.com/api/reference/python/resources/responses/methods/create

The ledger bounds this adapter's requests, not unrelated account spending. Known
usage is reconciled to a conservative price upper bound; unknown outcomes keep
their full reservation. It is not a billing statement or a tokenizer estimate.
"""
from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import fcntl
import json
import os
from pathlib import Path
import re
import stat
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import uuid4

from .common import C, Failure, ahif, check_path, schema, sha
from .provider import Reply, validate_config

ENDPOINT = 'https://api.openai.com/v1/responses'
MODEL = 'gpt-5.6-luna'
MODEL_CONTEXT = 1_050_000
MODEL_OUTPUT = 128_000
NANODOLLARS = 1_000_000_000
MAX_CAP = 3 * NANODOLLARS
MAX_LEDGER_BYTES = 4 * 1024 * 1024
MAX_REQUEST_BYTES = 8 * 1024 * 1024
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
PRICING = {'version': 'luna-standard-2026-09-16', 'model': MODEL,
           'input_nanodollars_per_token': 200, 'cached_input_nanodollars_per_token': 20,
           'output_nanodollars_per_token': 1200, 'cache_write_input_nanodollars_per_token': 250,
           'long_context_above_input_tokens': 272000,
           'long_cache_write_input_nanodollars_per_token': 500,
           'long_output_nanodollars_per_token': 1800,
           'maximum_context_tokens': MODEL_CONTEXT, 'maximum_output_tokens': MODEL_OUTPUT,
           'settlement': 'upper_bound_all_input_at_cache_write_rate; output_includes_reasoning'}


def _usd(value):
    return format(Decimal(value) / NANODOLLARS, '.9f')


def _cap(value):
    try:
        if not isinstance(value, str):
            raise ValueError()
        amount = Decimal(value) * NANODOLLARS
        if not amount.is_finite() or amount != amount.to_integral_value() or not 0 < amount <= MAX_CAP:
            raise ValueError()
        return int(amount)
    except (InvalidOperation, ValueError):
        raise Failure('openai_ledger_cap_invalid') from None


def reservation_nanodollars(max_output_tokens):
    if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= MODEL_OUTPUT:
        raise Failure('provider_output_budget_invalid')
    # Reserve the full documented model context, even when num_ctx is smaller.
    # The API has no request input-token cap corresponding to Ollama's num_ctx.
    return MODEL_CONTEXT * 500 + max_output_tokens * 1800


def _ledger_path(path):
    if not Path(path).is_absolute():
        raise Failure('openai_ledger_path_not_absolute')
    return check_path(path)


@contextmanager
def _locked(path, *, create=False):
    path = _ledger_path(path)
    flags = os.O_RDWR | os.O_APPEND | os.O_CLOEXEC | os.O_NOFOLLOW
    if create:
        flags |= os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        raise Failure('openai_ledger_already_exists') from None
    except OSError:
        raise Failure('openai_ledger_unavailable') from None
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        info = os.fstat(fd)
        current = path.stat(follow_symlinks=False)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino)):
            raise Failure('openai_ledger_unsafe_file')
        with os.fdopen(fd, 'r+b', closefd=False) as stream:
            yield stream
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _append(stream, event):
    data = C(event) + b'\n'
    stream.seek(0, os.SEEK_END)
    if stream.tell() + len(data) > MAX_LEDGER_BYTES:
        raise Failure('openai_ledger_byte_limit', 'resource_limit')
    stream.write(data)
    stream.flush()
    os.fsync(stream.fileno())


def _read(stream):
    stream.seek(0)
    raw = stream.read(MAX_LEDGER_BYTES + 1)
    try:
        if len(raw) > MAX_LEDGER_BYTES or not raw.endswith(b'\n'):
            raise ValueError()
        events = [ahif.strict_loads(line) for line in raw.splitlines()]
        header = events[0]
        if (set(header) != {'operation', 'ledger_version', 'model', 'cap_nanodollars', 'pricing'}
                or header['operation'] != 'initialize' or header['ledger_version'] != '1.0.0'
                or header['model'] != MODEL or header['pricing'] != PRICING
                or type(header['cap_nanodollars']) is not int or not 0 < header['cap_nanodollars'] <= MAX_CAP):
            raise ValueError()
        requests = {}
        for event in events[1:]:
            identifier = event.get('reservation_id')
            if not isinstance(identifier, str) or not re.fullmatch(r'[0-9a-f]{32}', identifier):
                raise ValueError()
            if event.get('operation') == 'reserve':
                if (set(event) != {'operation', 'reservation_id', 'request_sha256', 'max_output_tokens', 'amount_nanodollars'}
                        or identifier in requests or not re.fullmatch(r'[0-9a-f]{64}', event['request_sha256'])
                        or event['amount_nanodollars'] != reservation_nanodollars(event['max_output_tokens'])):
                    raise ValueError()
                requests[identifier] = {'reservation': event, 'settlement': None}
                if _totals(header, requests)['charged_upper_bound_nanodollars'] > header['cap_nanodollars']:
                    raise ValueError()
            elif event.get('operation') == 'reconcile':
                if (set(event) != {'operation', 'reservation_id', 'amount_nanodollars', 'response_id', 'response_model', 'response_status', 'usage'}
                        or identifier not in requests or requests[identifier]['settlement'] is not None
                        or type(event['amount_nanodollars']) is not int
                        or not 0 <= event['amount_nanodollars'] <= requests[identifier]['reservation']['amount_nanodollars']
                        or event['response_model'] != MODEL
                        or event['response_status'] not in ('completed', 'failed', 'cancelled', 'incomplete')
                        or not isinstance(event['response_id'], str)
                        or not re.fullmatch(r'resp_[A-Za-z0-9_-]{1,240}', event['response_id'])):
                    raise ValueError()
                usage = event['usage']
                parsed = _usage({'usage': usage}, requests[identifier]['reservation']['max_output_tokens'])
                if event['amount_nanodollars'] != _usage_price(parsed):
                    raise ValueError()
                requests[identifier]['settlement'] = event
            else:
                raise ValueError()
        return header, requests
    except (ahif.Invalid, ValueError, KeyError, TypeError, AttributeError, IndexError):
        raise Failure('openai_ledger_invalid') from None


def _totals(header, requests):
    committed = sum(r['settlement']['amount_nanodollars'] for r in requests.values() if r['settlement'] is not None)
    outstanding = sum(r['reservation']['amount_nanodollars'] for r in requests.values() if r['settlement'] is None)
    available = header['cap_nanodollars'] - committed - outstanding
    return {'ledger_version': '1.0.0', 'model': MODEL, 'cap_nanodollars': header['cap_nanodollars'],
            'committed_nanodollars': committed, 'outstanding_nanodollars': outstanding,
            'charged_upper_bound_nanodollars': committed + outstanding, 'available_nanodollars': available,
            'cap_usd': _usd(header['cap_nanodollars']), 'committed_upper_bound_usd': _usd(committed),
            'outstanding_usd': _usd(outstanding), 'available_usd': _usd(available),
            'reservations': len(requests), 'settled_requests': sum(r['settlement'] is not None for r in requests.values()),
            'pending_requests': sum(r['settlement'] is None for r in requests.values())}


def initialize_ledger(path, cap_usd='3.00'):
    """Create once. Never reset or refund a pre-existing trial/readiness ledger."""
    path = _ledger_path(path)
    cap = _cap(cap_usd)
    header = {'operation': 'initialize', 'ledger_version': '1.0.0', 'model': MODEL,
              'cap_nanodollars': cap, 'pricing': PRICING}
    with _locked(path, create=True) as stream:
        _append(stream, header)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return _totals(header, {})


def ledger_snapshot(path):
    with _locked(path) as stream:
        return _totals(*_read(stream))


def _reserve(path, payload, maximum):
    amount = reservation_nanodollars(maximum)
    with _locked(path) as stream:
        header, requests = _read(stream)
        if amount > _totals(header, requests)['available_nanodollars']:
            raise Failure('provider_dollar_budget_exhausted', 'resource_limit')
        identifier = uuid4().hex
        _append(stream, {'operation': 'reserve', 'reservation_id': identifier,
                         'request_sha256': sha(payload), 'max_output_tokens': maximum, 'amount_nanodollars': amount})
    return identifier


def _reconcile(path, identifier, envelope, usage):
    with _locked(path) as stream:
        _, requests = _read(stream)
        request = requests.get(identifier)
        cost = _usage_price(usage)
        if request is None or request['settlement'] is not None or cost > request['reservation']['amount_nanodollars']:
            raise Failure('openai_ledger_reconciliation_invalid')
        _append(stream, {'operation': 'reconcile', 'reservation_id': identifier, 'amount_nanodollars': cost,
                         'response_id': envelope['id'], 'response_model': MODEL, 'response_status': envelope['status'],
                         'usage': {'input_tokens': usage['input_tokens'], 'output_tokens': usage['output_tokens'],
                                   'input_tokens_details': {k: usage[k] for k in ('cached_tokens', 'cache_write_tokens') if usage[k] is not None},
                                   'output_tokens_details': {'reasoning_tokens': usage['reasoning_tokens']} if usage['reasoning_tokens'] is not None else {}}})
    return cost


def _usage(envelope, maximum):
    value = envelope.get('usage')
    if not isinstance(value, dict):
        raise ValueError('missing_usage')
    result = {}
    for field, ceiling in (('input_tokens', MODEL_CONTEXT), ('output_tokens', maximum)):
        count = value.get(field)
        if type(count) is not int or not 0 <= count <= ceiling:
            raise ValueError('invalid_usage')
        result[field] = count
    if 'total_tokens' in value and (type(value['total_tokens']) is not int or value['total_tokens'] != sum(result.values())):
        raise ValueError('invalid_usage_total')
    for group, fields, ceiling in [('input_tokens_details', ('cached_tokens', 'cache_write_tokens'), result['input_tokens']),
                                   ('output_tokens_details', ('reasoning_tokens',), result['output_tokens'])]:
        details = value.get(group, {})
        if not isinstance(details, dict):
            raise ValueError('invalid_usage_details')
        for field in fields:
            count = details.get(field)
            if count is not None and (type(count) is not int or not 0 <= count <= ceiling):
                raise ValueError('invalid_usage_details')
            result[field] = count
    if sum(result[k] or 0 for k in ('cached_tokens', 'cache_write_tokens')) > result['input_tokens']:
        raise ValueError('invalid_cache_usage')
    # Cached token count does not establish a count of cache-hit requests.
    return {**result, 'cache_hits': None, 'monetary_cost': None}


def _usage_price(usage):
    long = usage['input_tokens'] > 272000
    return usage['input_tokens'] * (500 if long else 250) + usage['output_tokens'] * (1800 if long else 1200)


def _envelope(raw):
    def unique(pairs):
        value = {}
        for key, child in pairs:
            if key in value:
                raise ValueError('duplicate_response_key')
            value[key] = child
        return value
    def constant(_):
        raise ValueError('nonfinite_response_number')
    # Operational envelope floats may exist, but duplicate/nonfinite JSON is
    # never trusted to reduce a durable reservation.
    return json.loads(raw, object_pairs_hook=unique, parse_constant=constant)


def action_grammar(phase='planner'):
    """Same expanded per-phase action grammar as Ollama, plus root object type."""
    grammar = schema('planner-response-1.1.0')
    proposal = next(v for v in grammar['oneOf'] if v['properties']['action']['enum'] == ['propose'])
    contract = schema('plan')['properties']
    for name in ('contributions', 'rejected', 'unresolved'):
        proposal['properties']['proposal']['properties'][name] = contract[name]
    allowed = ('tool', 'ready_for_review', 'refuse') if phase == 'reviewer_observe' else (
        ('tool', 'review', 'refuse') if phase == 'reviewer_decide' else ('tool', 'propose', 'refuse'))
    grammar['oneOf'] = [v for v in grammar['oneOf'] if v['properties']['action']['enum'][0] in allowed]
    def aliases(value):
        if isinstance(value, dict):
            if value.get('pattern', '').startswith('^sha256:'):
                value['pattern'] = r'^(n[0-9]+|sha256:[0-9a-f]{64}:[0-9]+)$'
            for child in value.values():
                aliases(child)
        elif isinstance(value, list):
            for child in value:
                aliases(child)
    aliases(grammar)
    grammar['type'] = 'object'
    return grammar


def wire_schema(phase='planner'):
    """Explicit transport envelope; the nested host action grammar is unchanged.

    Responses rejects top-level oneOf even with strict:false. Requests retain this
    wrapper in both decoder policies. Config 1.1.1 explicitly permits a direct
    action response too; neither policy changes the host action language.
    """
    return {'type': 'object', 'properties': {'result': action_grammar(phase)},
            'required': ['result'], 'additionalProperties': False}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Failure('provider_redirect_refused', 'model_unavailable')


class OpenAIProvider:
    mode = 'live'

    def __init__(self, config, transport=None):
        self.config = validate_config(config)
        if (config.get('version') not in ('1.1.0', '1.1.1') or config.get('provider_location') != 'hosted'
                or config.get('endpoint') != ENDPOINT or config.get('model') != MODEL
                or config.get('openai', {}).get('reasoning_effort') != 'medium'
                or config['openai'].get('api_key_env') != 'OPENAI_API_KEY'):
            raise Failure('openai_configuration_unsupported')
        self.wire_mode = 'result_only' if config['version'] == '1.1.0' else config['openai'].get('wire_mode')
        if self.wire_mode not in ('result_only', 'result_or_action'):
            raise Failure('openai_configuration_unsupported')
        if config['version'] == '1.1.1' and self.wire_mode != 'result_or_action':
            raise Failure('openai_configuration_unsupported')
        self.ledger = _ledger_path(config['openai']['budget_ledger'])
        ledger_snapshot(self.ledger)
        self.transport = transport or self._http
        self.gateway_requests = 0
        self.last_public_request = self.last_public_response = self.last_usage = None

    def _http(self, endpoint, payload, timeout, response_limit):
        if endpoint != ENDPOINT:
            raise Failure('provider_endpoint_invalid')
        key = os.environ.get('OPENAI_API_KEY')
        if not key or any(c.isspace() for c in key):
            raise Failure('provider_api_key_missing', 'model_unavailable')
        opener = build_opener(ProxyHandler({}), _NoRedirect())
        request = Request(endpoint, data=payload, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key}, method='POST')
        try:
            with opener.open(request, timeout=timeout) as response:
                if response.status != 200:
                    raise Failure('provider_http_error', 'model_unavailable')
                raw = response.read(response_limit + 1)
        except Failure:
            raise
        except HTTPError as exc:
            error = Failure('provider_http_error', 'model_unavailable')
            error.http_details = {'status_code': exc.code, 'body_retained': False}
            # Retain only bounded machine error identifiers, never free-form
            # messages, headers, request echoes, credentials, or response bodies.
            try:
                diagnostic_raw = exc.read(min(response_limit, 8192) + 1)
                if len(diagnostic_raw) <= min(response_limit, 8192):
                    diagnostic = _envelope(diagnostic_raw)
                    fields = diagnostic.get('error', {}) if isinstance(diagnostic, dict) else {}
                    if isinstance(fields, dict):
                        identifiers = {k: v for k in ('code', 'type', 'param')
                                       if isinstance(v := fields.get(k), str)
                                       and re.fullmatch(r'[A-Za-z0-9_.\[\]-]{1,160}', v) and key not in v}
                        if identifiers:
                            error.http_details['error_identifiers'] = identifiers
            except (OSError, ValueError, TypeError):
                pass
            raise error from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise Failure('provider_transport_error', 'model_unavailable') from None
        if len(raw) > response_limit:
            raise Failure('provider_response_byte_limit', 'resource_limit')
        return raw

    def call(self, messages, max_output_tokens, timeout):
        self.last_public_request = self.last_public_response = self.last_usage = None
        reservation_nanodollars(max_output_tokens)
        if max_output_tokens > self.config['budgets']['max_output_tokens_per_call']:
            raise Failure('provider_output_budget_invalid')
        if timeout <= 0:
            raise Failure('provider_deadline_limit', 'resource_limit')
        if not os.environ.get('OPENAI_API_KEY') or any(c.isspace() for c in os.environ['OPENAI_API_KEY']):
            raise Failure('provider_api_key_missing', 'model_unavailable')
        if not isinstance(messages, list) or any(not isinstance(m, dict) or set(m) != {'role', 'content'}
                or m['role'] not in ('system', 'developer', 'user', 'assistant') or not isinstance(m['content'], str) for m in messages):
            raise Failure('provider_messages_invalid')
        request = {'model': MODEL, 'input': messages, 'max_output_tokens': max_output_tokens,
                   'reasoning': {'effort': 'medium'}, 'text': {'format': {'type': 'json_schema', 'name': 'ahif_action',
                   'strict': False, 'schema': wire_schema(getattr(self, 'phase', 'planner'))}},
                   'store': False, 'service_tier': 'default', 'truncation': 'disabled'}
        payload = C(request)
        if len(payload) > min(MAX_REQUEST_BYTES, self.config['budgets']['max_input_token_charge']):
            raise Failure('provider_request_byte_limit', 'resource_limit')
        self.last_public_request = request
        identifier = _reserve(self.ledger, payload, max_output_tokens)
        self.gateway_requests += 1
        limit = min(MAX_RESPONSE_BYTES, self.config['budgets']['max_response_bytes'])
        try:
            raw = self.transport(ENDPOINT, payload, timeout, limit)
        except Failure:
            raise
        except (OSError, TimeoutError, ValueError):
            raise Failure('provider_transport_error', 'model_unavailable') from None
        if not isinstance(raw, bytes) or len(raw) > limit:
            raise Failure('provider_response_byte_limit', 'resource_limit')
        self.last_public_response = {'envelope_sha256': sha(raw), 'envelope_byte_length': len(raw),
                                     'response_id': None, 'model': None, 'status': None, 'content': None, 'usage': None,
                                     'retention': 'content_usage_and_identity_only_no_hidden_reasoning'}
        if self.wire_mode == 'result_or_action':
            self.last_public_response.update(decoder_version='1.0.1', wire_shape=None)
        reconciled = False
        try:
            envelope = _envelope(raw)
            if not isinstance(envelope, dict):
                raise ValueError('invalid_envelope')
            observed_model = envelope.get('model')
            if isinstance(observed_model, str) and re.fullmatch(r'[A-Za-z0-9._:-]{1,200}', observed_model):
                self.last_public_response['model'] = observed_model
            identifier_value, status = envelope.get('id'), envelope.get('status')
            if not isinstance(identifier_value, str) or not re.fullmatch(r'resp_[A-Za-z0-9_-]{1,240}', identifier_value):
                raise ValueError('invalid_response_id')
            if status not in ('completed', 'failed', 'in_progress', 'cancelled', 'queued', 'incomplete'):
                raise ValueError('invalid_response_status')
            self.last_public_response.update(response_id=identifier_value, status=status)
            if envelope.get('model') != MODEL:
                raise Failure('provider_model_mismatch', 'model_unavailable')
            if envelope.get('service_tier', 'default') != 'default':
                raise Failure('provider_service_tier_mismatch', 'model_unavailable')
            if status in ('queued', 'in_progress'):
                # Interim usage is not a final charge. The server may still be
                # working; keep the full reservation and stop the trial.
                raise Failure('provider_response_nonterminal', 'model_unavailable')
            usage = _usage(envelope, max_output_tokens)
            self.last_usage = usage
            self.last_public_response['usage'] = usage
            cost = _reconcile(self.ledger, identifier, envelope, usage)
            reconciled = True
            usage['cost_upper_bound_nanodollars'] = cost
            usage['cost_upper_bound_usd'] = _usd(cost)
            usage['cost_basis'] = PRICING['settlement']
            output = envelope.get('output')
            if not isinstance(output, list):
                raise ValueError('invalid_output')
            texts = []
            refused = False
            for item in output:
                if not isinstance(item, dict):
                    raise ValueError('invalid_output_item')
                if item.get('type') == 'reasoning':
                    continue
                if item.get('type') != 'message' or item.get('role') != 'assistant' or not isinstance(item.get('content'), list):
                    raise ValueError('unsupported_output_item')
                for content in item['content']:
                    if not isinstance(content, dict):
                        raise ValueError('invalid_output_content')
                    if content.get('type') == 'refusal':
                        refused = True
                    elif content.get('type') == 'output_text' and isinstance(content.get('text'), str):
                        texts.append(content['text'])
                    else:
                        raise ValueError('unsupported_output_content')
            content = ''.join(texts)
            self.last_public_response['content'] = content
            if usage['input_tokens'] + usage['output_tokens'] > self.config['num_ctx']:
                raise Failure('provider_context_limit', 'resource_limit')
            if status == 'incomplete':
                raise Failure('provider_output_incomplete', 'unresolved_plan')
            if status != 'completed' or envelope.get('error'):
                raise Failure('provider_response_not_completed', 'model_unavailable')
            if refused:
                raise Failure('provider_refused', 'model_refused')
            if not texts:
                raise ValueError('missing_output_text')
            wire = ahif.strict_loads(content)
            if isinstance(wire, dict) and set(wire) == {'result'} and isinstance(wire['result'], dict):
                action, shape = wire['result'], 'result_envelope'
            elif (self.wire_mode == 'result_or_action' and isinstance(wire, dict)
                  and 'action' in wire and 'result' not in wire):
                action, shape = wire, 'direct_action'
            else:
                raise ValueError('invalid_wire_envelope')
            if self.wire_mode == 'result_or_action':
                self.last_public_response['wire_shape'] = shape
            return Reply(action, usage)
        except Failure:
            raise
        except (ValueError, TypeError, KeyError, ahif.Invalid):
            if not reconciled:
                raise Failure('provider_budget_usage_unknown', 'model_unavailable') from None
            raise Failure('provider_response_invalid', 'unresolved_plan') from None
