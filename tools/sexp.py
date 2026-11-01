"""Small, dependency-free reader/writer for KiCad's S-expressions."""
import json
import re

class Sym(str):
    pass

def loads(text):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text)
    stack, root = [], None
    for token in tokens:
        if token == '(':
            node = []
            if stack:
                stack[-1].append(node)
            else:
                root = node
            stack.append(node)
        elif token == ')':
            stack.pop()
        else:
            if token.startswith('"'):
                value = json.loads(token)
            else:
                try:
                    value = float(token) if '.' in token or 'e' in token.lower() else int(token)
                except ValueError:
                    value = Sym(token)
            stack[-1].append(value)
    if stack:
        raise ValueError('unclosed expression')
    return root

def dumps(value):
    if isinstance(value, list):
        return '(' + ' '.join(map(dumps, value)) + ')'
    if isinstance(value, Sym):
        return str(value)
    return json.dumps(value, ensure_ascii=False)

def children(node, key):
    return [v for v in node if isinstance(v, list) and v and v[0] == key]

def child(node, key, default=None):
    return next(iter(children(node, key)), default)
