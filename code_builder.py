# -*- coding: utf-8 -*-


class CodeBuilder:

    def __init__(self, indent=0):
        self.code = []
        self.cur_indent = indent

    INDENT_STEP = 4

    def indent(self):
        self.cur_indent += CodeBuilder.INDENT_STEP

    def dedent(self):
        self.cur_indent -= CodeBuilder.INDENT_STEP

    def add_line(self, line):
        self.code.extend([" " * self.cur_indent, line, "\n"])

    def add_section(self):
        """ 在code列表中添加一个占位用的引用，之后可以将这个引用字符化 """
        section = CodeBuilder(self.cur_indent)
        self.code.append(section)
        return section

    def __str__(self):
        """ 使得CoderBuilder对象可以字符化 """
        return "".join(str(x) for x in self.code)

    def get_globals(self):
        """ 将定义好的render_function返回到global_namespace中 """
        assert self.cur_indent == 0
        python_code = str(self)
        global_namespace = {}
        # 执行完exec后，global_namespace中就存储了指向render_function的引用
        exec(python_code, global_namespace)
        return global_namespace
