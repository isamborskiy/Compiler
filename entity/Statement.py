from operator import contains

from entity.CodeGenerator import CodeGenerator
from entity.Expression import BooleanBinaryOperator
from entity.Function import ReadFunction, WriteFunction
from entity.NameMangling import NameMangling
from entity.Scalar import VariableScalar, BoolScalar, Scalar
from entity.StatementsContainer import StatementsContainer
from entity.Type import Type


class WhileStatement(StatementsContainer):
    def __init__(self, condition, statements):
        super(WhileStatement, self).__init__()
        self.__condition = condition
        self.add_all(statements)

    def name_mangling(self, function_name, mangled_name):
        self.__condition.name_mangling(function_name, mangled_name)
        super().name_mangling(function_name, mangled_name)

    def windows_code(self, code_builder, program_state):
        label = "%s_while_%d" % (program_state.function_name, program_state.get_while_number())
        exit_label = "%s_exit" % label
        code_builder.add_label(label)
        if isinstance(self.__condition, BoolScalar):
            code_builder.add_instruction("mov", "eax", self.__condition.value)
        elif isinstance(self.__condition, VariableScalar) \
                and program_state.get_variable(self.__condition.value).type_value == Type.boolean:
            code_builder.add_instruction("mov", "eax", "[%s]" % self.__condition.value)
        elif isinstance(self.__condition, BooleanBinaryOperator):
            self.__condition.windows_code(code_builder, program_state)
        else:
            raise SyntaxError("while condition should be boolean value or boolean expression")
        code_builder.add_instruction("cmp", "eax", "0")
        code_builder.add_instruction("je", exit_label)
        for statement in self:
            statement.windows_code(code_builder, program_state)
        code_builder.add_instruction("jmp", label)
        code_builder.add_label(exit_label)

    def value_type(self, program_state):
        return None

    def __str__(self):
        return "while %s \n" % str(self.__condition) + super().__str__()


class IfStatement(StatementsContainer):
    def __init__(self, condition, statements, else_statement=None):
        super(IfStatement, self).__init__()
        self.__condition = condition
        self.add_all(statements)
        self.__else_statement = else_statement

    def name_mangling(self, function_name, mangled_name):
        self.__condition.name_mangling(function_name, mangled_name)
        super().name_mangling(function_name, mangled_name)

    def windows_code(self, code_builder, program_state):
        label = "%s_if_%d" % (program_state.function_name, program_state.get_if_number())
        exit_label = "%s_exit" % label
        if isinstance(self.__condition, BoolScalar):
            code_builder.add_instruction("mov", "eax", self.__condition.value)
        elif isinstance(self.__condition, VariableScalar) \
                and program_state.get_variable(self.__condition.value).type_value == Type.boolean:
            code_builder.add_instruction("mov", "eax", "[%s]" % self.__condition.value)
        elif isinstance(self.__condition, BooleanBinaryOperator):
            self.__condition.windows_code(code_builder, program_state)
        else:
            raise SyntaxError("while condition should be boolean value or boolean expression")
        code_builder.add_instruction("cmp", "eax", "1")
        code_builder.add_instruction("je", label)
        if self.__else_statement is not None:
            self.__else_statement.windows_code(code_builder, program_state)
        code_builder.add_instruction("jmp", exit_label)
        code_builder.add_label(label)
        for statement in self:
            statement.windows_code(code_builder, program_state)
        code_builder.add_label(exit_label)

    def value_type(self, program_state):
        return None

    def __str__(self):
        else_statement = "" if self.__else_statement is None else str(self.__else_statement)
        return "if %s \n" % str(self.__condition) + super().__str__() + else_statement


class ElseStatement(StatementsContainer):
    def __init__(self, statements):
        super(ElseStatement, self).__init__()
        self.add_all(statements)

    def windows_code(self, code_builder, program_state):
        for statement in self:
            statement.windows_code(code_builder, program_state)

    def value_type(self, program_state):
        return None

    def __str__(self):
        return "else\n" + "\n".join("\t%d  %s" % (i, str(self[i])) for i in range(len(self)))


class ReturnStatement(NameMangling, CodeGenerator):
    def __init__(self, expression):
        self.__expression = expression

    def name_mangling(self, function_name, mangled_name):
        self.__expression.name_mangling(function_name, mangled_name)

    def windows_code(self, code_builder, program_state):
        self.__expression.windows_code(code_builder, program_state)
        code_builder.add_instruction("push", "eax")

    def value_type(self, program_state):
        return None

    def __str__(self):
        return "return %s" % str(self.__expression)


def get_call_function_statement(function_name, args=None):
    if function_name == ReadFunction.FUNCTION_NAME:
        return CallReadFunction(function_name, args)
    elif function_name == WriteFunction.FUNCTION_NAME:
        return CallWriteFunction(function_name, args)
    else:
        return CallFunctionStatement(function_name, args)


class CallFunctionStatement(NameMangling, CodeGenerator):
    def __init__(self, function_name, args=None):
        super(CallFunctionStatement, self).__init__()
        self._function_name = function_name
        args = [] if args is None else args
        self._args = args

    def name_mangling(self, function_name, mangled_name):
        if contains(mangled_name, self._function_name):
            self._function_name = mangled_name[self._function_name]
        for i in range(len(self._args)):
            self._args[i].name_mangling(function_name, mangled_name)

    def windows_code(self, code_builder, program_state):
        for arg in reversed(self._args):
            arg.windows_code(code_builder, program_state)
            code_builder.add_instruction("push", "eax")
        code_builder.add_instruction("call", self._function_name)
        code_builder.add_instruction("sub", "esp", "8")
        code_builder.add_instruction("pop", "eax")
        code_builder.add_instruction("add", "esp", str(4 * (len(self._args) + 1)))

    def value_type(self, program_state):
        if not program_state.contains_function(self._function_name):
            raise ValueError("no function \"%s\" in scope" % self.__unmangling())
        return program_state.get_function(self._function_name).value_type()

    def __unmangling(self):
        try:
            underscore_index = self._function_name.rindex("_")
            return self._function_name[underscore_index + 1:]
        except ValueError:
            return self._function_name

    def __str__(self):
        args = "" if self._args is None else "_".join(str(arg) for arg in self._args)
        return "%s_%s_" % (self._function_name, args)


class CallReadFunction(CallFunctionStatement):
    def __init__(self, function_name, args):
        super(CallReadFunction, self).__init__(function_name, args)

    def value_type(self, program_state):
        return None

    def windows_code(self, code_builder, program_state):
        if len(self._args) != 1:
            raise SyntaxError(
                "actual and formal argument lists of function read is differ in length\nrequired: 1\nfound: %d" % len(
                    self._args))
        if not isinstance(self._args[0], VariableScalar):
            raise SyntaxError("function read cannot be applied to given arguments\nrequired: variable name")
        read_fun = ReadFunction(None, self._function_name, self._args)
        code_builder.add_instruction("call", read_fun.get_label())
        code_builder.add_global_function(read_fun)


class CallWriteFunction(CallFunctionStatement):
    def __init__(self, function_name, args):
        super(CallWriteFunction, self).__init__(function_name, args)

    def windows_code(self, code_builder, program_state):
        if len(self._args) != 1:
            raise SyntaxError(
                "actual and formal argument lists of function write is differ in length\nrequired: 1\nfound: %d" % len(
                    self._args))
        if not isinstance(self._args[0], (Scalar, CallFunctionStatement)):
            raise SyntaxError("function write cannot be applied to given arguments\nrequired: int or boolean")
        write_fun = WriteFunction(None, self._function_name, self._args)
        code_builder.add_instruction("call", write_fun.get_label())
        code_builder.add_global_function(write_fun)

    def value_type(self, program_state):
        return None


class CallPopFunction(CallFunctionStatement):
    FUNCTION_NAME = "__pop"

    def __init__(self, function_name, args=None):
        super(CallPopFunction, self).__init__(function_name, args)

    def name_mangling(self, function_name, mangled_name):
        self._args[0].name_mangling(function_name, mangled_name)

    def windows_code(self, code_builder, program_state):
        self._args[0].windows_code(code_builder, program_state)
        code_builder.add_instruction("pop", "eax")
        code_builder.add_instruction("mov", "[%s]" % self._args[0].name, "eax")

    def value_type(self, program_state):
        return None