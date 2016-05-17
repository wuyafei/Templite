# -*- coding: utf-8 -*-
import code_builder
import re


class Templite:

    def __init__(self, text, *contexts):

        self.context = {}
        for context in contexts:
            self.context.update(context)

        code = code_builder.CodeBuilder()
        code.add_line('def render_function(context, do_dots):')
        code.indent()
        # 添加变量定义的section引用，会在后面填充这个section，c_varname = context['varname']
        vars_code = code.add_section()
        code.add_line('result = []')
        # 下面三行都是一些优化小技巧
        code.add_line('append_result = result.append')
        code.add_line('extend_result = result.extend')
        code.add_line('to_str = str')

        self.all_vars = set()  # 整个函数中的变量
        self.loop_vars = set()  # 循环中定义的变量，for var in vars, 这个var就是循环定义的变量
        ops_stack = []  # 用来匹配if endif和for endfor的栈

        buffered = []

        def flush_output():
            """ 让多次append合并成一次extend """
            if len(buffered) == 1:
                code.add_line('append_result(%s)' % buffered[0])
            elif len(buffered) > 1:
                code.add_line('extend_result([%s])' % ', '.join(buffered))
            del buffered[:]

        tokens = re.split(r'(?s)({{.*?}}|{%.*?%}|{#.*?#})', text)
        for token in tokens:
            if token.startswith('{#'):  # 注释标签
                continue
            elif token.startswith('{{'):  # 表达式标签
                expr = self._expr_code(token[2:-2].strip())
                buffered.append('to_str(%s)' % expr)
            elif token.startswith('{%'):
                flush_output()
                words = token[2:-2].strip().split()
                if words[0] == 'if':
                    if len(words) != 2:
                        self._syntax_error(
                            "wrong format of if expression", token)
                    ops_stack.append('if')
                    code.add_line('if (%s):' % self._expr_code(words[1]))
                    code.indent()
                elif words[0] == 'for':
                    if len(words) != 4 or words[2] != 'in':
                        self._syntax_error(
                            'wrong format of for expression', token)
                    ops_stack.append('for')
                    self._variable(words[1], self.loop_vars)
                    code.add_line('for c_%s in %s:' %
                                  (words[1], self._expr_code(words[3])))
                    code.indent()
                elif words[0].startswith('end'):
                    if len(words) != 1:
                        self._syntax_error(
                            'wrong format of end expression', token)
                    end_what = words[0][3:]
                    if not ops_stack:
                        self._syntax_error(
                            'end expression not match any if or for', token)
                    start_what = ops_stack.pop()
                    if start_what != end_what:
                        self._syntax_error('mismatched end tag', end_what)
                    code.dedent()
                else:
                    self._syntax_error('undefined tag', words[0])
            else:
                if token:
                    buffered.append(repr(token))

        if ops_stack:  # 如果处理完所有语句，栈海没有空，那么报错
            self._syntax_error('unmatched action tag', ops_stack[-1])
        flush_output()
        # 把变量添加到section
        for var_name in self.all_vars - self.loop_vars:
            vars_code.add_line('c_%s = context[%r]' % (var_name, var_name))
        code.add_line('return "".join(result)')
        code.dedent()
        self._render_function = code.get_globals()['render_function']

    def _variable(self, var, var_set):
        """ 验证变量名的合法性，并添加到指定的集合，all_vars或者loop_vars """
        if not re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", var):
            self._syntax_error('Not a valid variable name', var)
        var_set.add(var)

    def _expr_code(self, expr):
        """ 将template中的表达式转化为python中的表达式 """
        if '|' in expr:
            pipes = [s.strip() for s in expr.split('|')]  # 管道|两边可以有空格
            code = self._expr_code(pipes[0])  # 递归转化为python表达式
            for func in pipes[1:]:
                self._variable(func, self.all_vars)  # 函数也作为变量加入到all_vars
                code = 'c_%s(%s)' % (func, code)  # 将管道转为python的函数调用
        elif '.' in expr:
            dots = expr.split('.')
            code = self._expr_code(dots[0])
            args = ', '.join(repr(d)
                             for d in dots[1:])  # repr可以确保下面的arg1，arg2上的引号
            # 转成形如 do_dots(name, 'arg1', 'arg2', ...)的函数调用
            code = 'do_dots(%s, %s)' % (code, args)
        else:
            code = 'c_%s' % expr
            self._variable(expr, self.all_vars)
        return code

    def _syntax_error(self, msg, thing):
        raise TempliteSyntaxError('%s: %r' % (msg, thing))

    def render(self, context=None):
        render_context = dict(self.context)
        if context:
            render_context.update(context)
        return self._render_function(render_context, self._do_dots)

    def _do_dots(self, value, *dots):
        for dot in dots:
            try:
                value = getattr(value, dot)
            except AttributeError:
                value = value[dot]
            if callable(value):
                value = value()
            return value


class TempliteSyntaxError(Exception):
    pass


if __name__ == '__main__':
    text = """<h1>Hello {{name|upper}}!</h1>
{% for topic in topics %}
    <p>You are interested in {{topic}}.</p>
{% endfor %}
    """
    templite = Templite(text, {'upper': str.upper})
    html = templite.render({
        'name': "Ned",
        'topics': ['Python', 'Geometry', 'Juggling'],
    })
    print html
