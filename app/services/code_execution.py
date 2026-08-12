"""Gamified Code Lab content plus deliberately constrained local runners.

Python is interpreted through a small AST evaluator, SQL is run against an
in-memory lesson database, and native C/C++/Java compilation is disabled unless
the local owner explicitly opts in. Never enable native compilation on a public
deployment without an isolated container runner.
"""
from __future__ import annotations

import ast
import re
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import CodeChallengeProgress, LearningDNA, User
from app.services.catalog import CODE_LABS, code_labs
from app.settings import settings


def _challenge(challenge_id, language, level, title, prompt, concept, starter, checks, xp=35):
    return {'id': challenge_id, 'language': language, 'level': level, 'title': title, 'prompt': prompt, 'concept': concept, 'starter': starter, 'checks': checks, 'xp': xp}


CODE_CHALLENGES = [
    _challenge('py-hello', 'Python', 1, 'Hello, coder!', 'Print the words Hello, Learner.', 'print()', 'print("Hello, Learner")', ['hello, learner']),
    _challenge('py-math', 'Python', 2, 'XP calculator', 'Store 12 and 8 in variables. Print their total.', 'Variables and addition', 'daily_xp = 12\nbonus_xp = 8\nprint(daily_xp + bonus_xp)', ['20']),
    _challenge('py-condition', 'Python', 3, 'Focus check', 'Print Ready when focus is 30 or more.', 'if statements', 'focus = 42\nif focus >= 30:\n    print("Ready")', ['ready']),
    _challenge('py-loop', 'Python', 4, 'Counting loop', 'Use range to add 1 through 5. Print the total.', 'for loops', 'total = 0\nfor number in range(1, 6):\n    total += number\nprint(total)', ['15'], 45),
    _challenge('py-function', 'Python', 5, 'Make a function', 'Create greet(name), return a greeting, then print it for Iqra.', 'Functions and return', 'def greet(name):\n    return "Hello, " + name\n\nprint(greet("Iqra"))', ['hello, iqra'], 50),
    _challenge('c-hello', 'C', 1, 'C launch', 'Print Welcome to C.', 'printf()', '#include <stdio.h>\n\nint main(void) {\n  printf("Welcome to C\\n");\n  return 0;\n}', ['welcome to c']),
    _challenge('c-math', 'C', 2, 'C total', 'Add 14 and 6, then print the result.', 'int variables', '#include <stdio.h>\n\nint main(void) {\n  int first = 14, second = 6;\n  printf("%d\\n", first + second);\n  return 0;\n}', ['20']),
    _challenge('c-condition', 'C', 3, 'C condition', 'Print Ready when score is at least 50.', 'if statements', '#include <stdio.h>\n\nint main(void) {\n  int score = 72;\n  if (score >= 50) printf("Ready\\n");\n  return 0;\n}', ['ready']),
    _challenge('c-loop', 'C', 4, 'C loop total', 'Use a for loop to add 1 through 5 and print the total.', 'for loops', '#include <stdio.h>\n\nint main(void) {\n  int total = 0;\n  for (int i = 1; i <= 5; i++) total += i;\n  printf("%d\\n", total);\n  return 0;\n}', ['15'], 45),
    _challenge('c-function', 'C', 5, 'C function', 'Use a function square to print the square of 6.', 'Functions', '#include <stdio.h>\n\nint square(int value) { return value * value; }\nint main(void) {\n  printf("%d\\n", square(6));\n  return 0;\n}', ['36'], 50),
    _challenge('cpp-hello', 'C++', 1, 'C++ launch', 'Print Welcome to C++.', 'cout', '#include <iostream>\nusing namespace std;\n\nint main() {\n  cout << "Welcome to C++" << endl;\n  return 0;\n}', ['welcome to c++']),
    _challenge('cpp-math', 'C++', 2, 'C++ total', 'Add 14 and 6, then print the result.', 'int variables', '#include <iostream>\nusing namespace std;\n\nint main() {\n  int first = 14, second = 6;\n  cout << first + second << endl;\n  return 0;\n}', ['20']),
    _challenge('cpp-condition', 'C++', 3, 'C++ condition', 'Print Ready when score is at least 50.', 'if statements', '#include <iostream>\nusing namespace std;\n\nint main() {\n  int score = 72;\n  if (score >= 50) cout << "Ready" << endl;\n  return 0;\n}', ['ready']),
    _challenge('cpp-loop', 'C++', 4, 'C++ loop total', 'Use a for loop to add 1 through 5 and print the total.', 'for loops', '#include <iostream>\nusing namespace std;\n\nint main() {\n  int total = 0;\n  for (int i = 1; i <= 5; i++) total += i;\n  cout << total << endl;\n  return 0;\n}', ['15'], 45),
    _challenge('cpp-function', 'C++', 5, 'C++ function', 'Use a function square to print the square of 6.', 'Functions', '#include <iostream>\nusing namespace std;\n\nint square(int value) { return value * value; }\nint main() {\n  cout << square(6) << endl;\n  return 0;\n}', ['36'], 50),
    _challenge('sql-select', 'MySQL', 1, 'Meet the learners', 'Select name and score from students.', 'SELECT', 'SELECT name, score\nFROM students;', ['aanya', 'ravi', 'mina']),
    _challenge('sql-filter', 'MySQL', 2, 'High-score filter', 'Show students with a score of at least 80.', 'WHERE', 'SELECT name, score\nFROM students\nWHERE score >= 80;', ['aanya', 'ravi']),
    _challenge('sql-count', 'MySQL', 3, 'Count the class', 'Count all rows in students.', 'COUNT', 'SELECT COUNT(*) AS total\nFROM students;', ['3']),
    _challenge('sql-order', 'MySQL', 4, 'Leaderboard', 'Sort students by score from highest to lowest.', 'ORDER BY', 'SELECT name, score\nFROM students\nORDER BY score DESC;', ['aanya | 92', 'ravi | 84', 'mina | 73'], 45),
    _challenge('sql-group', 'MySQL', 5, 'Course groups', 'Count learners in every course.', 'GROUP BY', 'SELECT course, COUNT(*) AS learners\nFROM enrollments\nGROUP BY course\nORDER BY course;', ['algorithms', 'python', '2'], 50),
    _challenge('java-hello', 'Java', 1, 'Java launch', 'Print Welcome to Java.', 'System.out.println', 'public class Main {\n  public static void main(String[] args) {\n    System.out.println("Welcome to Java");\n  }\n}', ['welcome to java']),
    _challenge('java-math', 'Java', 2, 'Java total', 'Add 14 and 6, then print the result.', 'int variables', 'public class Main {\n  public static void main(String[] args) {\n    int first = 14, second = 6;\n    System.out.println(first + second);\n  }\n}', ['20']),
    _challenge('java-condition', 'Java', 3, 'Java condition', 'Print Ready when score is at least 50.', 'if statements', 'public class Main {\n  public static void main(String[] args) {\n    int score = 72;\n    if (score >= 50) System.out.println("Ready");\n  }\n}', ['ready']),
    _challenge('java-loop', 'Java', 4, 'Java loop total', 'Use a for loop to add 1 through 5 and print the total.', 'for loops', 'public class Main {\n  public static void main(String[] args) {\n    int total = 0;\n    for (int i = 1; i <= 5; i++) total += i;\n    System.out.println(total);\n  }\n}', ['15'], 45),
    _challenge('java-function', 'Java', 5, 'Java method', 'Create square and print the square of 6.', 'Methods', 'public class Main {\n  static int square(int value) { return value * value; }\n  public static void main(String[] args) {\n    System.out.println(square(6));\n  }\n}', ['36'], 50),
]


class SafePythonError(Exception):
    pass


class SafePythonRunner:
    def __init__(self):
        self.output: list[str] = []
        self.functions: dict[str, ast.FunctionDef] = {}
        self.steps = 0
        self.call_depth = 0

    def tick(self):
        self.steps += 1
        if self.steps > 8_000:
            raise SafePythonError('Your program used too many steps. Keep loops below 500 iterations.')

    def evaluate(self, node, env):
        self.tick()
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str, bool, type(None))):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            raise SafePythonError(f'Unknown name: {node.id}')
        if isinstance(node, ast.List): return [self.evaluate(item, env) for item in node.elts]
        if isinstance(node, ast.Tuple): return tuple(self.evaluate(item, env) for item in node.elts)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd, ast.Not)):
            value = self.evaluate(node.operand, env)
            return -value if isinstance(node.op, ast.USub) else value if isinstance(node.op, ast.UAdd) else not value
        if isinstance(node, ast.BinOp):
            left, right = self.evaluate(node.left, env), self.evaluate(node.right, env)
            operations = {ast.Add: lambda: left + right, ast.Sub: lambda: left - right, ast.Mult: lambda: left * right, ast.Div: lambda: left / right, ast.FloorDiv: lambda: left // right, ast.Mod: lambda: left % right, ast.Pow: lambda: left ** right}
            operation = operations.get(type(node.op))
            if operation:
                value = operation()
                if isinstance(value, (int, float)) and abs(value) > 1_000_000_000:
                    raise SafePythonError('That number is too large for the learning runner.')
                return value
        if isinstance(node, ast.Compare):
            left = self.evaluate(node.left, env)
            checks = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b, ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b, ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b}
            for operation, comparator in zip(node.ops, node.comparators):
                right = self.evaluate(comparator, env); check = checks.get(type(operation))
                if not check or not check(left, right): return False
                left = right
            return True
        if isinstance(node, ast.BoolOp):
            values = [self.evaluate(value, env) for value in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.Subscript):
            return self.evaluate(node.value, env)[self.evaluate(node.slice, env)]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id; args = [self.evaluate(arg, env) for arg in node.args]
            if name == 'print':
                if len(self.output) >= 100: raise SafePythonError('Output limit reached.')
                self.output.append(' '.join(str(arg) for arg in args)); return None
            if name == 'range':
                values = list(range(*args))
                if len(values) > 500: raise SafePythonError('Keep range loops below 500 iterations.')
                return values
            if name in {'len', 'sum', 'min', 'max', 'str', 'int'}:
                return {'len': len, 'sum': sum, 'min': min, 'max': max, 'str': str, 'int': int}[name](*args)
            return self.call_function(name, args, env)
        raise SafePythonError('This Python feature is not available in the safe learning runner yet.')

    def execute_block(self, statements, env):
        for statement in statements:
            result = self.execute(statement, env)
            if isinstance(result, tuple) and result[0] == 'return': return result

    def execute(self, node, env):
        self.tick()
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            env[node.targets[0].id] = self.evaluate(node.value, env); return
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            value, right = env.get(node.target.id), self.evaluate(node.value, env)
            if isinstance(node.op, ast.Add): env[node.target.id] = value + right
            elif isinstance(node.op, ast.Sub): env[node.target.id] = value - right
            elif isinstance(node.op, ast.Mult): env[node.target.id] = value * right
            else: raise SafePythonError('Use +=, -=, or *= in this learning runner.')
            return
        if isinstance(node, ast.Expr): self.evaluate(node.value, env); return
        if isinstance(node, ast.If): return self.execute_block(node.body if self.evaluate(node.test, env) else node.orelse, env)
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            values = self.evaluate(node.iter, env)
            if not isinstance(values, (list, tuple, range)) or len(values) > 500: raise SafePythonError('Use a small range or list in a for loop.')
            for value in values:
                env[node.target.id] = value
                result = self.execute_block(node.body, env)
                if result: return result
            return
        if isinstance(node, ast.FunctionDef):
            if len(node.args.args) > 4: raise SafePythonError('Keep functions to four parameters or fewer.')
            self.functions[node.name] = node; return
        if isinstance(node, ast.Return): return ('return', self.evaluate(node.value, env) if node.value else None)
        raise SafePythonError('Use variables, print, if, for, and simple functions in this learning runner.')

    def call_function(self, name, args, env):
        function = self.functions.get(name)
        if not function: raise SafePythonError(f'Only simple built-in or defined functions are allowed: {name}')
        if len(args) != len(function.args.args): raise SafePythonError(f'{name} expects {len(function.args.args)} argument(s).')
        if self.call_depth >= 8: raise SafePythonError('Function nesting is too deep.')
        self.call_depth += 1
        local = dict(env)
        for arg, value in zip(function.args.args, args): local[arg.arg] = value
        result = self.execute_block(function.body, local)
        self.call_depth -= 1
        return result[1] if result else None

    def run(self, code: str):
        try:
            tree = ast.parse(code, mode='exec')
            environment = {}
            self.execute_block(tree.body, environment)
            return '\n'.join(self.output) or '(Program finished with no output.)'
        except (SyntaxError, SafePythonError, ValueError, TypeError, ZeroDivisionError) as error:
            raise SafePythonError(str(error)) from error


def _sql_runner(code: str):
    query = code.strip().rstrip(';')
    lower = query.casefold()
    if not lower.startswith('select') or ';' in query or any(token in lower for token in ('attach', 'pragma', 'insert', 'update', 'delete', 'drop', 'alter')):
        return {'ok': False, 'output': 'Use one read-only SELECT query in the MySQL lesson dataset.', 'runner': 'Secure SQL lesson engine'}
    connection = sqlite3.connect(':memory:')
    try:
        connection.executescript('''
            CREATE TABLE students (name TEXT, score INTEGER, level TEXT);
            INSERT INTO students VALUES ('Aanya', 92, 'Gold'), ('Ravi', 84, 'Silver'), ('Mina', 73, 'Bronze');
            CREATE TABLE enrollments (name TEXT, course TEXT);
            INSERT INTO enrollments VALUES ('Aanya', 'Python'), ('Ravi', 'Python'), ('Mina', 'Algorithms');
        ''')
        cursor = connection.execute(query)
        rows = cursor.fetchmany(25); headers = [item[0] for item in cursor.description]
        body = '\n'.join(' | '.join(str(value) for value in row) for row in rows) or '(No rows returned.)'
        return {'ok': True, 'output': ' | '.join(headers) + '\n' + body, 'runner': 'Secure SQL lesson engine'}
    except sqlite3.Error as error:
        return {'ok': False, 'output': f'SQL feedback: {error}', 'runner': 'Secure SQL lesson engine'}
    finally:
        connection.close()


_BANNED_NATIVE = ('system(', 'popen', 'fork', 'exec', 'createprocess', 'shell', 'socket', 'winsock', 'fstream', 'ifstream', 'ofstream', 'freopen', 'remove(', 'rename(', 'unlink', 'open(', 'read(', 'write(', 'filesystem', 'windows.h', 'thread', 'mutex', 'asm', '__', '#pragma', 'malloc', 'free(', 'new ', 'delete ')
_ALLOWED_HEADERS = {'stdio.h', 'iostream', 'string', 'vector', 'cmath'}


def _native_source_allowed(language: str, code: str):
    source = code.casefold()
    if len(code) > 6_000 or 'main' not in source:
        return 'Include a short program with a main function.'
    if any(token in source for token in _BANNED_NATIVE):
        return 'This local compiler allows only beginner console programs: variables, if statements, for loops, functions, and output.'
    headers = re.findall(r'#\s*include\s*<([^>]+)>', source)
    if any(header not in _ALLOWED_HEADERS for header in headers) or re.search(r'#(?!\s*include)', source):
        return 'Only standard beginner headers are allowed in the local compiler.'
    if language == 'Java' and ('class main' not in source or 'java.io' in source):
        return 'Use public class Main and console output only.'
    return None


def _decode_native_string(value: str):
    return bytes(value, 'utf-8').decode('unicode_escape')


def _extract_main_body(code: str):
    match = re.search(r'\bmain\s*\([^)]*\)\s*\{', code)
    if not match:
        raise ValueError('Add a main function so Code Lab knows where your program starts.')
    depth = 1
    start = match.end()
    index = start
    while index < len(code):
        if code[index] == '{':
            depth += 1
        elif code[index] == '}':
            depth -= 1
            if depth == 0:
                return code[start:index]
        index += 1
    raise ValueError('Check your braces. Code Lab could not find the end of main.')


def _native_functions(code: str):
    functions = {}
    pattern = r'(?:static\s+)?int\s+([A-Za-z_]\w*)\s*\(\s*int\s+([A-Za-z_]\w*)\s*\)\s*\{\s*return\s+([^;]+);?\s*\}'
    for name, parameter, expression in re.findall(pattern, code, re.S):
        if name != 'main':
            functions[name] = (parameter, expression)
    return functions


def _eval_native_expr(expression: str, env: dict[str, int], functions: dict[str, tuple[str, str]]):
    expression = expression.strip()
    expression = re.sub(r'\([A-Za-z_][\w\s:*&<>]*\)', '', expression)

    def call_function(match):
        name, raw_arg = match.group(1), match.group(2)
        if name not in functions:
            return match.group(0)
        parameter, body = functions[name]
        local = dict(env)
        local[parameter] = int(_eval_native_expr(raw_arg, env, functions))
        return str(_eval_native_expr(body, local, functions))

    expression = re.sub(r'\b([A-Za-z_]\w*)\s*\(([^()]+)\)', call_function, expression)
    expression = expression.replace('&&', ' and ').replace('||', ' or ')
    expression = re.sub(r'!(?!=)', ' not ', expression)
    expression = re.sub(r'\b([A-Za-z_]\w*)\b', lambda item: str(env.get(item.group(1), item.group(1))), expression)
    if not re.fullmatch(r'[\d\s+\-*/%().<>=!&|andornot]+', expression):
        raise ValueError('Use beginner arithmetic, comparisons, variables, and one-argument int functions.')
    return eval(expression, {'__builtins__': {}}, {})


def _remember_native_ints(source: str, env: dict[str, int], functions: dict[str, tuple[str, str]]):
    for declaration in re.finditer(r'\bint\s+([^;{}()]+);', source):
        for part in declaration.group(1).split(','):
            if '=' not in part:
                continue
            name, expression = part.split('=', 1)
            name = name.strip()
            if re.fullmatch(r'[A-Za-z_]\w*', name):
                env[name] = int(_eval_native_expr(expression, env, functions))


def _apply_native_assignments(source: str, env: dict[str, int], functions: dict[str, tuple[str, str]]):
    source = re.sub(r'\bint\s+[^;]+;', '', source)
    for name, expression in re.findall(r'\b([A-Za-z_]\w*)\s*=\s*([^;]+);', source):
        if name not in {'if', 'for', 'return'}:
            env[name] = int(_eval_native_expr(expression, env, functions))
    for name, expression in re.findall(r'\b([A-Za-z_]\w*)\s*\+=\s*([^;]+);', source):
        env[name] = env.get(name, 0) + int(_eval_native_expr(expression, env, functions))


def _native_prints(language: str, source: str, env: dict[str, int], functions: dict[str, tuple[str, str]]):
    output: list[str] = []
    if language == 'C':
        pattern = r'printf\s*\(\s*"((?:\\.|[^"])*)"\s*(.*?)\)\s*;'
        for template, rest in re.findall(pattern, source, re.S):
            text = _decode_native_string(template)
            argument = rest.strip()[1:].strip() if rest.strip().startswith(',') else ''
            if '%d' in text and argument:
                text = text.replace('%d', str(_eval_native_expr(argument, env, functions)), 1)
            output.extend(line for line in text.splitlines() if line)
    elif language == 'C++':
        for expression in re.findall(r'cout\s*<<\s*(.*?)\s*;', source, re.S):
            pieces = []
            for part in re.split(r'\s*<<\s*', expression):
                part = part.strip()
                if not part or part in {'endl', 'std::endl'}:
                    continue
                string_match = re.fullmatch(r'"((?:\\.|[^"])*)"', part)
                pieces.append(_decode_native_string(string_match.group(1)) if string_match else str(_eval_native_expr(part, env, functions)))
            if pieces:
                output.append(''.join(pieces))
    else:
        pattern = r'System\.out\.print(?:ln)?\s*\(\s*(.*?)\s*\)\s*;'
        for expression in re.findall(pattern, source, re.S):
            string_match = re.fullmatch(r'"((?:\\.|[^"])*)"', expression.strip())
            output.append(_decode_native_string(string_match.group(1)) if string_match else str(_eval_native_expr(expression, env, functions)))
    return output


def _native_lesson_runner(language: str, code: str, reason: str):
    runner = f'Beginner {language} lesson runner'
    try:
        functions = _native_functions(code)
        body = _extract_main_body(code)
        env: dict[str, int] = {}
        _remember_native_ints(body, env, functions)
        output: list[str] = []

        loop_pattern = r'for\s*\(\s*int\s+([A-Za-z_]\w*)\s*=\s*(-?\d+)\s*;\s*\1\s*(<=|<)\s*(-?\d+)\s*;\s*(?:\1\+\+|\+\+\1)\s*\)\s*(?:\{(?P<braced>.*?)\}|(?P<single>[^;]+;))'
        for match in re.finditer(loop_pattern, body, re.S):
            variable, start, operator, stop = match.group(1), int(match.group(2)), match.group(3), int(match.group(4))
            block = match.group('braced') or match.group('single') or ''
            limit = stop + 1 if operator == '<=' else stop
            if limit - start > 500:
                raise ValueError('Keep beginner loops below 500 turns.')
            for value in range(start, limit):
                env[variable] = value
                _apply_native_assignments(block, env, functions)
                output.extend(_native_prints(language, block, env, functions))
        body_without_loops = re.sub(loop_pattern, '', body, flags=re.S)

        if_pattern = r'if\s*\((.*?)\)\s*(?:\{(?P<braced>.*?)\}|(?P<single>[^;]+;))'
        for match in re.finditer(if_pattern, body_without_loops, re.S):
            block = match.group('braced') or match.group('single') or ''
            if bool(_eval_native_expr(match.group(1), env, functions)):
                _apply_native_assignments(block, env, functions)
                output.extend(_native_prints(language, block, env, functions))
        body_without_control = re.sub(if_pattern, '', body_without_loops, flags=re.S)
        _apply_native_assignments(body_without_control, env, functions)
        output.extend(_native_prints(language, body_without_control, env, functions))
        return {'ok': True, 'output': '\n'.join(output) or '(Program finished with no output.)', 'runner': f'{runner} ({reason})'}
    except (ValueError, ArithmeticError, TypeError, SyntaxError) as error:
        help_text = 'Install MinGW/JDK and set LOCAL_COMPILER_ENABLED=true for advanced native programs.'
        return {'ok': False, 'output': f'{error}\n\n{help_text}', 'runner': runner}


def _native_runner(language: str, code: str):
    safety_error = _native_source_allowed(language, code)
    if safety_error:
        return {'ok': False, 'output': safety_error, 'runner': 'Protected local compiler'}
    compiler = {'C': shutil.which('gcc'), 'C++': shutil.which('g++'), 'Java': shutil.which('javac')}.get(language)
    if not settings.local_compiler_enabled:
        return _native_lesson_runner(language, code, 'protected fallback')
    if not compiler:
        return _native_lesson_runner(language, code, 'compiler not installed')
    with tempfile.TemporaryDirectory(prefix='learndna_code_') as folder:
        work = Path(folder)
        try:
            if language == 'Java':
                source = work / 'Main.java'; source.write_text(code, encoding='utf-8')
                compiled = subprocess.run([compiler, str(source)], cwd=work, capture_output=True, text=True, timeout=8, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if compiled.returncode: return {'ok': False, 'output': (compiled.stderr or compiled.stdout)[-2000:], 'runner': 'Protected local compiler'}
                command = ['java', '-cp', str(work), 'Main']
            else:
                suffix, compiler_flags = ('.c', ['-std=c11']) if language == 'C' else ('.cpp', ['-std=c++17'])
                source, executable = work / f'Main{suffix}', work / 'program.exe'
                source.write_text(code, encoding='utf-8')
                compiled = subprocess.run([compiler, *compiler_flags, '-O0', str(source), '-o', str(executable)], cwd=work, capture_output=True, text=True, timeout=8, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if compiled.returncode: return {'ok': False, 'output': (compiled.stderr or compiled.stdout)[-2000:], 'runner': 'Protected local compiler'}
                command = [str(executable)]
            executed = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=2, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            output = (executed.stdout + executed.stderr).strip()
            return {'ok': executed.returncode == 0, 'output': output or '(Program finished with no output.)', 'runner': 'Protected local compiler'}
        except subprocess.TimeoutExpired:
            return {'ok': False, 'output': 'Program stopped after 2 seconds. Check your loop condition.', 'runner': 'Protected local compiler'}
        except OSError as error:
            return _native_lesson_runner(language, code, f'compiler could not start: {error}')


def _run_language(language: str, code: str):
    if language == 'Python':
        try: return {'ok': True, 'output': SafePythonRunner().run(code), 'runner': 'Secure Python learning engine'}
        except SafePythonError as error: return {'ok': False, 'output': f'Python feedback: {error}', 'runner': 'Secure Python learning engine'}
    if language == 'MySQL': return _sql_runner(code)
    if language in {'C', 'C++', 'Java'}: return _native_runner(language, code)
    return {'ok': False, 'output': 'Choose Python, C, C++, MySQL, or Java.', 'runner': 'Code Lab'}


def _challenge_hints(challenge):
    """Hints are intentionally conceptual: Code Quest never pre-fills a solution."""
    language = challenge['language']
    level = challenge['level']
    language_starts = {
        'Python': 'Start with one short line. Python uses indentation only after a colon.',
        'C': 'A C program begins with #include <stdio.h> and a main function.',
        'C++': 'A C++ program needs iostream, then a main function to begin.',
        'MySQL': 'Begin with SELECT and name the information you want to inspect.',
        'Java': 'Java runs from a Main class and a main method.',
    }
    level_hints = {
        1: 'Focus on the requested text first. Use the language’s standard output command.',
        2: 'Make two named values, then use the addition operator inside your output statement.',
        3: 'Write the condition first. The message should only run when that condition is true.',
        4: 'Create a total starting at zero. Repeat a small update for every number in the range.',
        5: 'Give the reusable action a name, return or produce its result, then call it once.',
    }
    final_nudges = {
        'Python': 'Check spelling and indentation, then run your smallest version.',
        'C': 'Check semicolons and braces, then run your smallest version.',
        'C++': 'Check semicolons, braces, and the output operator, then run it.',
        'MySQL': 'Check the table and column names, then end the query with a semicolon.',
        'Java': 'Check braces, semicolons, and the exact class name Main, then run it.',
    }
    return [language_starts[language], level_hints[level], final_nudges[language]]


def _challenge_summary(challenge, progress):
    # The finished starter source and answer checks stay on the server.  Students
    # receive the goal and progressively revealable hints instead.
    summary = {key: value for key, value in challenge.items() if key not in {'checks', 'starter'}}
    summary['hints'] = _challenge_hints(challenge)
    summary['completed'] = bool(progress and progress.completed)
    summary['attempts'] = progress.attempts if progress else 0
    return summary


def _stats(db: Session, user: User):
    records = db.query(CodeChallengeProgress).filter_by(user_id=user.id, completed=True).all()
    completed = len(records); earned = sum(next((item['xp'] for item in CODE_CHALLENGES if item['id'] == record.challenge_id), 0) for record in records)
    return {'completed': completed, 'total': len(CODE_CHALLENGES), 'xp': earned, 'level': max(1, completed // 4 + 1), 'next_level': min(len(CODE_CHALLENGES), (completed // 4 + 1) * 4)}


def coding_dashboard(db: Session, user: User):
    progress = {item.challenge_id: item for item in db.query(CodeChallengeProgress).filter_by(user_id=user.id).all()}
    engine = {
        'Python': 'Secure Python engine: variables, conditions, loops, lists, and simple functions.',
        'MySQL': 'Secure SQL dataset: SELECT, WHERE, JOIN-style lesson tables, ORDER BY, and GROUP BY.',
        'C': 'Beginner C lesson runner; real compiler is used when enabled locally.',
        'C++': 'Beginner C++ lesson runner; real compiler is used when enabled locally.',
        'Java': 'Beginner Java lesson runner; real compiler is used when enabled locally.',
    }
    return {'labs': code_labs(user.coding_language), 'challenges': [_challenge_summary(item, progress.get(item['id'])) for item in CODE_CHALLENGES], 'stats': _stats(db, user), 'engine': engine}


def run_code(db: Session, user: User, language: str, code: str, challenge_id: str | None = None):
    challenge = next((item for item in CODE_CHALLENGES if item['id'] == challenge_id), None) if challenge_id else None
    if challenge and challenge['language'] != language:
        return {'ok': False, 'output': 'Choose the language assigned to this challenge.', 'runner': 'Code Lab'}
    result = _run_language(language, code)
    if not challenge:
        return result
    checks = [str(check).casefold() for check in challenge['checks']]
    passed = bool(result['ok']) and all(check in result['output'].casefold() for check in checks)
    progress = db.query(CodeChallengeProgress).filter_by(user_id=user.id, challenge_id=challenge['id']).first()
    if not progress:
        progress = CodeChallengeProgress(user_id=user.id, challenge_id=challenge['id'], attempts=0, completed=False); db.add(progress)
    progress.attempts = (progress.attempts or 0) + 1
    reward = 0
    if passed and not progress.completed:
        progress.completed = True; progress.completed_at = datetime.utcnow(); reward = challenge['xp']
        dna = db.get(LearningDNA, user.id)
        if dna: dna.xp += reward; dna.problem_solving = min(100, dna.problem_solving + 2); dna.confidence = min(100, dna.confidence + 1)
    db.commit()
    result['challenge'] = {'id': challenge['id'], 'passed': passed, 'newly_completed': reward > 0, 'xp_earned': reward, 'message': 'Challenge complete! Your XP is saved.' if passed else 'Almost there. Compare your output with the goal, edit the code, and run it again.'}
    result['stats'] = _stats(db, user)
    return result
