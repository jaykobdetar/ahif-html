"""Finite structural candidate accounting; neither an event classifier nor completeness proof."""
from __future__ import annotations

import time

from .common import C, Failure, bound
from .index import attrs

VERSION = '1.1.0'
STRUCTURAL_TAGS = frozenset(('article', 'li', 'blockquote', 'section', 'tr', 'dd'))
NATIVE_ATTRIBUTES = frozenset(('data-post-id', 'data-comment-id', 'data-review-id'))
HINT_CLASSES = frozenset(('post', 'comment', 'reply', 'review', 'contribution'))
HEADER_TAGS = frozenset(('header', 'time', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'cite'))


class Candidates:
    def __init__(self, index, maximum=5000):
        self.index = index
        self.nodes = {node['ref']: node for node in index['nodes']}
        self.ends = {}
        stack = []
        for node in index['nodes']:
            while stack and stack[-1]['depth'] >= node['depth']:
                self.ends[stack.pop()['ref']] = node['order']
            stack.append(node)
        for node in stack:
            self.ends[node['ref']] = len(index['nodes'])
        self.items = []
        self.total = self.unsupported = 0
        for node in index['nodes']:
            if node['kind'] != 'element':
                continue
            a = attrs(node)
            signals = []
            if node['tag'] in STRUCTURAL_TAGS:
                signals.append('structural_tag')
            if NATIVE_ATTRIBUTES.intersection(a):
                signals.append('native_id_attribute')
            if HINT_CLASSES.intersection(a.get('class', '').lower().split()):
                signals.append('semantic_class_hint')
            if a.get('role') in ('article', 'listitem', 'comment'):
                signals.append('semantic_role_hint')
            if not signals:
                continue
            if node['flags']:
                self.unsupported += 1
                continue
            self.total += 1
            if len(self.items) < maximum:
                self.items.append({'node': node['ref'], 'ordinal': len(self.items),
                    'tag': node['tag'], 'parent': node['parent'], 'signals': signals,
                    'subtree_nodes': self.ends[node['ref']] - node['order']})
        self.refs = {item['node'] for item in self.items}
        self.truncated = self.total > maximum
        self.manifest = {'version': VERSION, 'index_id': index['index_id'],
            'capture_sha256': index['capture']['sha256'], 'candidate_limit': maximum,
            'total_supported_candidates': self.total, 'unsupported_candidates': self.unsupported,
            'inventory_truncated': self.truncated, 'candidates': self.items,
            'not_completeness_proof': True,
            'rules': {'structural_tags': sorted(STRUCTURAL_TAGS),
                      'native_attributes': sorted(NATIVE_ATTRIBUTES),
                      'class_hints': sorted(HINT_CLASSES),
                      'meaning': 'Candidates require interpretation; tags and hints do not establish posting events.'}}
        self.manifest['inventory_id'] = bound('candidate-inventory-1.1.0', self.manifest)

    def contains(self, root, ref):
        a, b = self.nodes.get(root), self.nodes.get(ref)
        return bool(a and b and a['order'] <= b['order'] < self.ends[root])

    def context(self, ref):
        """Stable small header/ancestor context repeated on every subtree page."""
        node = self.nodes[ref]
        refs = [ref]
        parent = node['parent']
        for _ in range(2):
            if parent is None:
                break
            refs.append(parent)
            parent = self.nodes[parent]['parent']
        for other in self.index['nodes'][node['order']:self.ends[ref]]:
            if other['flags']:
                continue
            a = attrs(other)
            if other['tag'] in HEADER_TAGS or a.get('rel') == 'author' or a.get('itemprop') == 'author':
                refs.append(other['ref'])
                refs.extend(other['children'][:2])
                if len(refs) >= 12:
                    break
        return list(dict.fromkeys(refs))[:12]

    def accounting(self, plan):
        outcomes = {}
        for contribution in plan['contributions']:
            outcomes.setdefault(contribution['container'], []).append(('include', None))
        for field, decision in (('rejected', 'reject'), ('unresolved', 'unresolved')):
            for item in plan[field]:
                outcomes.setdefault(item['node'], []).append((decision, item['reason']))
        decisions, missing, conflicting = [], [], []
        for item in self.items:
            ref = item['node']
            selected = outcomes.get(ref, [])
            if not selected:
                missing.append(ref)
            elif len(selected) != 1:
                conflicting.append(ref)
            else:
                decisions.append({'node': ref, 'decision': selected[0][0], 'reason': selected[0][1]})
        return {'version': VERSION, 'inventory_id': self.manifest['inventory_id'],
                'decisions': decisions, 'missing': missing, 'conflicting': conflicting,
                'additional_selected': [item['container'] for item in plan['contributions']
                                        if item['container'] not in self.refs],
                'inventory_truncated': self.truncated, 'not_completeness_proof': True,
                'accounted': not (missing or conflicting or self.truncated)}

    def require_accounted(self, plan):
        report = self.accounting(plan)
        if not report['accounted']:
            error = Failure('candidate_accounting_incomplete', 'unresolved_plan')
            # Bounded diagnostics; full deterministic report is saved outside model views.
            error.feedback = {'missing': report['missing'][:20],
                              'conflicting': report['conflicting'][:20],
                              'remaining_missing': len(report['missing']),
                              'inventory_truncated': self.truncated,
                              'instruction': 'Assign every candidate exactly once using contributions.container, rejected.node or unresolved.node.'}
            raise error
        return report


class CandidateInspector:
    """Use the existing Inspector's safe serialization and cumulative budgets."""
    def __init__(self, candidates, inspector):
        self.candidates, self.inspector = candidates, inspector

    def call(self, name, arguments):
        ins, candidates = self.inspector, self.candidates
        before = set(ins.exposed), set(ins.inspected)
        started = time.monotonic()
        ins.calls += 1
        if ins.calls > ins.limits['tool_calls'] or ins.tool_elapsed > ins.limits['wall_seconds']:
            raise Failure('inspection_budget_exhausted', 'resource_limit')
        try:
            allowed = {'start', 'limit'} if name == 'candidate_inventory' else {
                'candidate_ref', 'start', 'limit', 'max_characters'}
            if not isinstance(arguments, dict) or set(arguments) - allowed:
                raise Failure('tool_arguments_invalid')
            def integer(key, default, maximum, minimum=0):
                value = arguments.get(key, default)
                if type(value) is not int or not minimum <= value <= maximum:
                    raise Failure('tool_arguments_invalid')
                return value
            if name == 'candidate_inventory':
                start = integer('start', 0, len(candidates.items))
                limit = integer('limit', 10, 30, 1)
                chosen = candidates.items[start:start + limit]
                result = {'inventory_id': candidates.manifest['inventory_id'],
                          'candidates': chosen, 'total_candidates': candidates.total,
                          'inventory_truncated': candidates.truncated,
                          'next_start': start + len(chosen) if start + len(chosen) < len(candidates.items) else None,
                          'not_completeness_proof': True}
                ins.exposed.update(item['node'] for item in chosen)
            else:
                ref = arguments.get('candidate_ref')
                if ref not in candidates.nodes:
                    raise Failure('unknown_node_reference')
                node = candidates.nodes[ref]
                if node['kind'] != 'element' or node['flags']:
                    raise Failure('unsupported_candidate_reference')
                count = candidates.ends[ref] - node['order']
                start = integer('start', 0, count)
                limit = integer('limit', 12, 30, 1)
                max_chars = integer('max_characters', 300, 1000, 1)
                chosen = candidates.index['nodes'][node['order'] + start:min(node['order'] + start + limit, candidates.ends[ref])]
                result = {'candidate_ref': ref, 'start': start, 'subtree_nodes': count,
                          'nodes': [ins._node(n, max_chars) for n in chosen],
                          'context': [ins._node(candidates.nodes[r], min(200, max_chars)) for r in candidates.context(ref)],
                          'next_start': start + len(chosen) if start + len(chosen) < count else None,
                          'context_is_bounded_preview': True, 'not_completeness_proof': True}
                ins.inspected.update(n['ref'] for n in chosen)
            size = len(C(result).decode('utf8'))
            if size > ins.limits['tool_characters']:
                ins.exposed, ins.inspected = before
                result = {'truncated': True, 'reason': 'tool_result_character_limit',
                          'suggestion': 'Reduce limit and max_characters; retry the same start.'}
                size = len(C(result).decode('utf8'))
            ins.characters += size
            if ins.characters > ins.limits['inspected_characters']:
                raise Failure('inspection_character_limit', 'resource_limit')
            return result
        except Exception:
            ins.exposed, ins.inspected = before
            raise
        finally:
            ins.tool_elapsed += time.monotonic() - started
