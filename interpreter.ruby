# ╔══════════════════════════════════════════════════════════╗
# ║       Simple Calculator Compiler / Interpreter           ║
# ║       Lexer → Parser → Evaluator  (Ruby)                 ║
# ╚══════════════════════════════════════════════════════════╝
#
# Supports: + - * / and parentheses ( )


# ═══════════════════════════════════════════════════════════
#  TOKEN
# ═══════════════════════════════════════════════════════════

Token = Struct.new(:type, :value) do
  def to_s
    "Token(#{type}, #{value.inspect})"
  end
end


# ═══════════════════════════════════════════════════════════
#  LEXER
# ═══════════════════════════════════════════════════════════

class Lexer
  TOKEN_SPEC = [
    [:NUMBER,  /\d+(\.\d+)?/],
    [:PLUS,    /\+/],
    [:MINUS,   /\-/],
    [:MUL,     /\*/],
    [:DIV,     /\//],
    [:LPAREN,  /\(/],
    [:RPAREN,  /\)/],
    [:SKIP,    /\s+/],
  ]

  def initialize(text)
    @text = text
  end

  def tokenize
    tokens = []
    pos = 0

    while pos < @text.length
      matched = false

      TOKEN_SPEC.each do |type, pattern|
        m = @text[pos..].match(/\A#{pattern}/)
        next unless m

        unless type == :SKIP
          val = m[0]
          val = val.include?('.') ? val.to_f : val.to_i if type == :NUMBER
          tokens << Token.new(type, val)
        end

        pos += m[0].length
        matched = true
        break
      end

      raise SyntaxError, "Unexpected character: '#{@text[pos]}'" unless matched
    end

    tokens
  end
end


# ═══════════════════════════════════════════════════════════
#  AST NODES
# ═══════════════════════════════════════════════════════════

Num      = Struct.new(:value)
BinOp    = Struct.new(:left, :op, :right)
UnaryOp  = Struct.new(:op, :operand)


# ═══════════════════════════════════════════════════════════
#  PARSER  (recursive-descent)
#
#  Grammar:
#    expr   → term   (('+' | '-') term)*
#    term   → factor (('*' | '/') factor)*
#    factor → ('+' | '-') factor | NUMBER | '(' expr ')'
# ═══════════════════════════════════════════════════════════

class Parser
  def initialize(tokens)
    @tokens = tokens
    @pos    = 0
  end

  def parse
    node = expr
    raise SyntaxError, "Unexpected token: #{peek}" if peek
    node
  end

  private

  def peek
    @tokens[@pos]
  end

  def consume(*types)
    tok = peek
    raise SyntaxError, "Unexpected end of input" if tok.nil?
    if types.any? && !types.include?(tok.type)
      raise SyntaxError, "Expected #{types.join(' or ')}, got #{tok.type} (#{tok.value.inspect})"
    end
    @pos += 1
    tok
  end

  def expr
    node = term
    while peek && %i[PLUS MINUS].include?(peek.type)
      op    = consume.value
      right = term
      node  = BinOp.new(node, op, right)
    end
    node
  end

  def term
    node = factor
    while peek && %i[MUL DIV].include?(peek.type)
      op    = consume.value
      right = factor
      node  = BinOp.new(node, op, right)
    end
    node
  end

  def factor
    tok = peek
    raise SyntaxError, "Unexpected end of input" if tok.nil?

    if %i[PLUS MINUS].include?(tok.type)
      op      = consume.value
      operand = factor
      return UnaryOp.new(op, operand)
    end

    if tok.type == :NUMBER
      consume(:NUMBER)
      return Num.new(tok.value)
    end

    if tok.type == :LPAREN
      consume(:LPAREN)
      node = expr
      consume(:RPAREN)
      return node
    end

    raise SyntaxError, "Unexpected token: #{tok.type} (#{tok.value.inspect})"
  end
end


# ═══════════════════════════════════════════════════════════
#  EVALUATOR
# ═══════════════════════════════════════════════════════════

class Evaluator
  def evaluate(node)
    case node
    when Num
      node.value

    when UnaryOp
      val = evaluate(node.operand)
      node.op == '-' ? -val : val

    when BinOp
      left  = evaluate(node.left)
      right = evaluate(node.right)
      case node.op
      when '+' then left + right
      when '-' then left - right
      when '*' then left * right
      when '/'
        raise ZeroDivisionError, "Division by zero" if right == 0
        left.to_f / right
      end

    else
      raise RuntimeError, "Unknown node: #{node.class}"
    end
  end
end


# ═══════════════════════════════════════════════════════════
#  PRETTY-PRINT HELPERS
# ═══════════════════════════════════════════════════════════

def fmt_tokens(tokens)
  lines = []
  lines << "  \u250C\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u252C\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510"
  lines << "  \u2502    TYPE     \u2502     VALUE     \u2502"
  lines << "  \u251C\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u253C\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524"
  tokens.each do |tok|
    lines << "  \u2502 #{tok.type.to_s.ljust(11)} \u2502 #{tok.value.to_s.ljust(13)} \u2502"
  end
  lines << "  \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2534\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518"
  lines.join("\n")
end

def fmt_tree(node, prefix = "", is_last = true)
  connector = is_last ? "\u2514\u2500\u2500 " : "\u251C\u2500\u2500 "
  child_pfx  = prefix + (is_last ? "    " : "\u2502   ")

  case node
  when Num
    prefix + connector + "Num(#{node.value})"
  when UnaryOp
    top  = prefix + connector + "UnaryOp('#{node.op}')"
    body = fmt_tree(node.operand, child_pfx, true)
    "#{top}\n#{body}"
  when BinOp
    top   = prefix + connector + "BinOp('#{node.op}')"
    left  = fmt_tree(node.left,  child_pfx, false)
    right = fmt_tree(node.right, child_pfx, true)
    "#{top}\n#{left}\n#{right}"
  else
    prefix + connector + "?"
  end
end

def fmt_result(value)
  value.is_a?(Float) && value == value.to_i ? value.to_i.to_s : value.to_s
end


# ═══════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════

def run(expression)
  puts "\n#{"═" * 52}"
  puts "  Expression : #{expression}"
  puts "═" * 52

  # 1. Lexer
  puts "\n  \u2460 TOKENS\n\n"
  begin
    tokens = Lexer.new(expression).tokenize
  rescue SyntaxError => e
    puts "  [Lexer Error] #{e.message}"
    return
  end
  puts fmt_tokens(tokens)

  # 2. Parser
  puts "\n  \u2461 PARSE TREE\n\n"
  begin
    ast = Parser.new(tokens).parse
  rescue SyntaxError => e
    puts "  [Parser Error] #{e.message}"
    return
  end
  puts "  " + fmt_tree(ast).gsub("\n", "\n  ")

  # 3. Evaluator
  puts "\n  \u2462 RESULT\n\n"
  begin
    result = Evaluator.new.evaluate(ast)
  rescue ZeroDivisionError => e
    puts "  [Eval Error] #{e.message}"
    return
  end
  puts "  \u27A4  #{expression}  =  #{fmt_result(result)}\n"
end


# ═══════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════

DEMO = [
  "5 + 3 * 2",
  "(4 + 6) / 2",
  "7 - 2 + 4",
]

puts "\u2554#{"═" * 54}\u2557"
puts "\u2551   Simple Calculator Compiler / Interpreter (Ruby)    \u2551"
puts "\u2551   Supports: + - * /  and parentheses ( )             \u2551"
puts "\u255A#{"═" * 54}\u255D"
puts "\n  Running demo expressions...\n"

DEMO.each { |expr| run(expr) }

puts "\n#{"═" * 52}"
puts "  INTERACTIVE MODE  \u2014  type an expression, Enter to run"
puts "  Type 'exit' or 'quit' to stop."
puts "#{"═" * 52}\n"

loop do
  print "\n  >> "
  input = gets&.chomp&.strip
  break if input.nil? || %w[exit quit].include?(input.downcase)
  next if input.empty?
  run(input)
end

puts "  Goodbye!"