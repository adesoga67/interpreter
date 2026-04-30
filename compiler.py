"""
╔══════════════════════════════════════════════════════════╗
║        Simple Calculator Compiler / Interpreter          ║
║        Lexer → Parser → Evaluator  (Python)              ║
╚══════════════════════════════════════════════════════════╝

Supports: +  -  *  /  ( )  and decimal numbers
"""

import re


# ═══════════════════════════════════════════════════════════
#  TOKENS
# ═══════════════════════════════════════════════════════════

class Token:
    def __init__(self, type_, value):
        self.type  = type_    # NUMBER | PLUS | MINUS | MUL | DIV | LPAREN | RPAREN
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


# ═══════════════════════════════════════════════════════════
#  LEXER
# ═══════════════════════════════════════════════════════════

TOKEN_SPEC = [
    ('NUMBER',  r'\d+(\.\d+)?'),
    ('PLUS',    r'\+'),
    ('MINUS',   r'-'),
    ('MUL',     r'\*'),
    ('DIV',     r'/'),
    ('LPAREN',  r'\('),
    ('RPAREN',  r'\)'),
    ('SKIP',    r'\s+'),
]
MASTER_PATTERN = re.compile(
    '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPEC)
)


def lexer(text: str) -> list[Token]:
    tokens = []
    for m in MASTER_PATTERN.finditer(text):
        kind = m.lastgroup
        val  = m.group()
        if kind == 'SKIP':
            continue
        if kind == 'NUMBER':
            val = float(val) if '.' in val else int(val)
        tokens.append(Token(kind, val))

    # Check for unrecognised characters
    matched_len = sum(len(m.group()) for m in MASTER_PATTERN.finditer(text))
    if matched_len != len(text):
        raise SyntaxError(f"Unrecognised character(s) in: {text!r}")

    return tokens


# ═══════════════════════════════════════════════════════════
#  AST NODES
# ═══════════════════════════════════════════════════════════

class Num:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Num({self.value})"


class BinOp:
    def __init__(self, left, op: str, right):
        self.left  = left
        self.op    = op
        self.right = right

    def __repr__(self):
        return f"BinOp({self.op!r}, {self.left!r}, {self.right!r})"


class UnaryOp:
    def __init__(self, op: str, operand):
        self.op      = op
        self.operand = operand

    def __repr__(self):
        return f"UnaryOp({self.op!r}, {self.operand!r})"


# ═══════════════════════════════════════════════════════════
#  PARSER  (recursive-descent)
#
#  Grammar:
#    expr    → term   (('+' | '-') term)*
#    term    → factor (('*' | '/') factor)*
#    factor  → ('+' | '-') factor
#            | NUMBER
#            | '(' expr ')'
# ═══════════════════════════════════════════════════════════

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos    = 0

    # ── helpers ──────────────────────────────────────────────
    def _peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _consume(self, *expected_types):
        tok = self._peek()
        if tok is None:
            raise SyntaxError("Unexpected end of input")
        if expected_types and tok.type not in expected_types:
            raise SyntaxError(
                f"Expected {' or '.join(expected_types)}, got {tok.type!r} ({tok.value!r})"
            )
        self.pos += 1
        return tok

    # ── grammar rules ────────────────────────────────────────
    def parse(self):
        node = self._expr()
        if self._peek() is not None:
            raise SyntaxError(f"Unexpected token after expression: {self._peek()!r}")
        return node

    def _expr(self):
        node = self._term()
        while self._peek() and self._peek().type in ('PLUS', 'MINUS'):
            op  = self._consume().value      # '+' or '-'
            rhs = self._term()
            node = BinOp(node, op, rhs)
        return node

    def _term(self):
        node = self._factor()
        while self._peek() and self._peek().type in ('MUL', 'DIV'):
            op  = self._consume().value      # '*' or '/'
            rhs = self._factor()
            node = BinOp(node, op, rhs)
        return node

    def _factor(self):
        tok = self._peek()
        if tok is None:
            raise SyntaxError("Unexpected end of input")

        # Unary + / -
        if tok.type in ('PLUS', 'MINUS'):
            op      = self._consume().value
            operand = self._factor()
            return UnaryOp(op, operand)

        # Number literal
        if tok.type == 'NUMBER':
            self._consume('NUMBER')
            return Num(tok.value)

        # Parenthesised sub-expression
        if tok.type == 'LPAREN':
            self._consume('LPAREN')
            node = self._expr()
            self._consume('RPAREN')
            return node

        raise SyntaxError(f"Unexpected token: {tok.type!r} ({tok.value!r})")


# ═══════════════════════════════════════════════════════════
#  EVALUATOR
# ═══════════════════════════════════════════════════════════

def evaluate(node):
    if isinstance(node, Num):
        return node.value

    if isinstance(node, UnaryOp):
        val = evaluate(node.operand)
        return -val if node.op == '-' else val

    if isinstance(node, BinOp):
        left  = evaluate(node.left)
        right = evaluate(node.right)
        if node.op == '+': return left + right
        if node.op == '-': return left - right
        if node.op == '*': return left * right
        if node.op == '/':
            if right == 0:
                raise ZeroDivisionError("Division by zero")
            return left / right

    raise RuntimeError(f"Unknown node type: {type(node)}")


# ═══════════════════════════════════════════════════════════
#  PRETTY-PRINT HELPERS
# ═══════════════════════════════════════════════════════════

def fmt_tokens(tokens: list[Token]) -> str:
    lines = ["  ┌─────────────┬───────────────┐",
             "  │    TYPE     │     VALUE     │",
             "  ├─────────────┼───────────────┤"]
    for tok in tokens:
        lines.append(f"  │ {tok.type:<11} │ {str(tok.value):<13} │")
    lines.append("  └─────────────┴───────────────┘")
    return "\n".join(lines)


def fmt_tree(node, prefix="", is_last=True) -> str:
    connector = "└── " if is_last else "├── "
    child_pfx  = prefix + ("    " if is_last else "│   ")

    if isinstance(node, Num):
        return prefix + connector + f"Num({node.value})"

    if isinstance(node, UnaryOp):
        top  = prefix + connector + f"UnaryOp('{node.op}')"
        body = fmt_tree(node.operand, child_pfx, is_last=True)
        return top + "\n" + body

    if isinstance(node, BinOp):
        top   = prefix + connector + f"BinOp('{node.op}')"
        left  = fmt_tree(node.left,  child_pfx, is_last=False)
        right = fmt_tree(node.right, child_pfx, is_last=True)
        return top + "\n" + left + "\n" + right

    return prefix + connector + "?"


def fmt_result(value) -> str:
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value)


# ═══════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════

DIVIDER = "─" * 52

def run(expression: str):
    print(f"\n{'═' * 52}")
    print(f"  Expression : {expression}")
    print(f"{'═' * 52}")

    # ── 1. Lexer ──────────────────────────────────────────
    print("\n  ① TOKENS\n")
    try:
        tokens = lexer(expression)
    except SyntaxError as e:
        print(f"  [Lexer Error] {e}")
        return
    print(fmt_tokens(tokens))

    # ── 2. Parser ─────────────────────────────────────────
    print(f"\n  ② PARSE TREE\n")
    try:
        ast = Parser(tokens).parse()
    except SyntaxError as e:
        print(f"  [Parser Error] {e}")
        return
    print("  " + fmt_tree(ast).replace("\n", "\n  "))

    # ── 3. Evaluator ──────────────────────────────────────
    print(f"\n  ③ RESULT\n")
    try:
        result = evaluate(ast)
    except ZeroDivisionError as e:
        print(f"  [Eval Error] {e}")
        return
    print(f"  ➤  {expression}  =  {fmt_result(result)}\n")


# ═══════════════════════════════════════════════════════════
#  INTERACTIVE REPL
# ═══════════════════════════════════════════════════════════

DEMO_EXPRESSIONS = [
    "5 + 3 * 2",
    "(4 + 6) / 2",
    "7 - 2 + 4",
]

def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║   Simple Calculator Interpreter  ║")
    print("║   Supports: + - * /  and parentheses ( )             ║")
    print("╚══════════════════════════════════════════════════════╝")
    print("\n  Running demo expressions first...\n")

    for expr in DEMO_EXPRESSIONS:
        run(expr)

    print(f"\n{'═' * 52}")
    print("  INTERACTIVE MODE  —  type an expression and press Enter")
    print("  Type 'exit' or 'quit' to stop.")
    print(f"{'═' * 52}\n")

    while True:
        try:
            expr = input("  >> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if not expr:
            continue
        if expr.lower() in ('exit', 'quit'):
            print("  Goodbye!")
            break

        run(expr)


if __name__ == "__main__":
    main()