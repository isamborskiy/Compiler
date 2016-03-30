from entity.CodeGenerator import CodeGenerator
from entity.NameMangling import NameMangling
from entity.Scalar import BoolScalar, VariableScalar
from entity.Scalar import IntScalar
from entity.Type import Type


def get_expression(sign, left=None, right=None):
    if left is None:
        return UnaryPlus(right) if sign == "+" else UnaryMinus(right)
    else:
        if sign == "+":
            return Plus(left, right)
        if sign == "-":
            return Minus(left, right)
        if sign == "*":
            return Multiply(left, right)
        if sign == "/":
            return Divide(left, right)
        if sign == "%":
            return Modulo(left, right)
        if sign == ">":
            return Greater(left, right)
        if sign == "<":
            return Less(left, right)
        if sign == "==":
            return Equal(left, right)
        if sign == "!=":
            return NotEqual(left, right)
        if sign == ">=":
            return GreaterOrEqual(left, right)
        if sign == "<=":
            return LessOrEqual(left, right)
        if sign == "&&":
            return And(left, right)
        if sign == "||":
            return Or(left, right)


class Operator(NameMangling, CodeGenerator):
    def __init__(self):
        super(Operator, self).__init__()

    def name_mangling(self, function_name, mangled_name):
        raise NotImplementedError

    def windows_code(self, code_builder, program_state):
        raise NotImplementedError

    def value_type(self, program_state):
        raise NotImplementedError


class AssignmentOperator(Operator):
    def __init__(self, name, expression):
        super(AssignmentOperator, self).__init__()
        self.__name = name
        self.__expression = expression

    def name_mangling(self, function_name, mangled_name):
        self.__name.name_mangling(function_name, mangled_name)
        self.__expression.name_mangling(function_name, mangled_name)

    def windows_code(self, code_builder, program_state):
        self.__expression.windows_code(code_builder, program_state)
        code_builder.add_instruction("mov", "[%s]" % self.__name.value, "eax")

    def __str__(self):
        return "%s = %s" % (self.__name, self.__expression)

    def value_type(self, program_state):
        raise NotImplementedError


class UnaryOperator(Operator):
    def __init__(self, value):
        super(UnaryOperator, self).__init__()
        self._value = value

    def name_mangling(self, function_name, mangled_name):
        self._value.name_mangling(function_name, mangled_name)

    def windows_code(self, code_builder, program_state):
        raise NotImplementedError

    def value_type(self, program_state):
        return Type.int

    def __get_sign(self):
        raise NotImplementedError

    def __str__(self):
        return "%s%s" % (self.__get_sign(), self._value)


class UnaryPlus(UnaryOperator):
    def __init__(self, value):
        super(UnaryPlus, self).__init__(value)

    def windows_code(self, code_builder, program_state):
        if isinstance(self._value, (IntScalar, BoolScalar)):
            code_builder.add_instruction("mov", "eax", self._value.value)
        elif isinstance(self._value, VariableScalar):
            code_builder.add_instruction("mov", "eax", "[%s]" % self._value.value)

    def __get_sign(self):
        return "+"


class UnaryMinus(UnaryOperator):
    def __init__(self, value):
        super(UnaryMinus, self).__init__(value)

    def windows_code(self, code_builder, program_state):
        if isinstance(self._value, (IntScalar, BoolScalar)):
            code_builder.add_instruction("mov", "eax", self._value.value)
        elif isinstance(self._value, VariableScalar):
            code_builder.add_instruction("mov", "eax", "[%s]" % self._value.value)
            code_builder.add_instruction("neg", "eax")
        else:
            code_builder.add_instruction("neg", "eax")

    def __get_sign(self):
        return "-"


class BinaryOperator(Operator):
    def __init__(self, left, right):
        super(BinaryOperator, self).__init__()
        self._left = left
        self._right = right

    def name_mangling(self, function_name, mangled_name):
        self._left.name_mangling(function_name, mangled_name)
        self._right.name_mangling(function_name, mangled_name)

    def windows_code(self, code_builder, program_state):
        if isinstance(self._left, (IntScalar, BoolScalar)):
            code_builder.add_instruction("mov", "eax", self._left.value)
        elif isinstance(self._left, VariableScalar):
            code_builder.add_instruction("mov", "eax", "[%s]" % self._left.value)
        else:
            self._left.windows_code(code_builder, program_state)
        code_builder.add_instruction("push", "eax")
        if isinstance(self._right, (IntScalar, BoolScalar)):
            code_builder.add_instruction("mov", "eax", self._right.value)
        elif isinstance(self._right, VariableScalar):
            code_builder.add_instruction("mov", "eax", "[%s]" % self._right.value)
        else:
            self._right.windows_code(code_builder, program_state)
        code_builder.add_instruction("mov", "ebx", "eax")
        code_builder.add_instruction("pop", "eax")
        self.windows_code_operator(code_builder, program_state)

    def windows_code_operator(self, code_builder, program_state):
        raise NotImplementedError

    def value_type(self, program_state):
        return Type.int

    def _get_sign(self):
        raise NotImplementedError

    def __str__(self):
        return "%s %s %s" % (self._left, self._get_sign(), self._right)


class BooleanBinaryOperator(BinaryOperator):
    def __init__(self, left, right):
        super(BooleanBinaryOperator, self).__init__(left, right)

    def windows_code_operator(self, code_builder, program_state):
        label = "%s_bool_op_%d_skip" % (program_state.function_name, program_state.get_if_number())
        code_builder.add_instruction("cmp", "eax", "ebx")
        code_builder.add_instruction("mov", "eax", "1")
        code_builder.add_instruction(self._get_instruction(), label)
        code_builder.add_instruction("xor", "eax", "eax")
        code_builder.add_label(label)

    def _get_instruction(self):
        raise NotImplementedError

    def value_type(self, program_state):
        return Type.boolean

    def _get_sign(self):
        raise NotImplementedError


class Plus(BinaryOperator):
    def __init__(self, left, right):
        super(Plus, self).__init__(left, right)

    def windows_code_operator(self, code_builder, program_state):
        code_builder.add_instruction("add", "eax", "ebx")

    def _get_sign(self):
        return "+"


class Minus(BinaryOperator):
    def __init__(self, left, right):
        super(Minus, self).__init__(left, right)

    def windows_code_operator(self, code_builder, program_state):
        code_builder.add_instruction("sub", "eax", "ebx")

    def _get_sign(self):
        return "-"


class Multiply(BinaryOperator):
    def __init__(self, left, right):
        super(Multiply, self).__init__(left, right)

    def windows_code_operator(self, code_builder, program_state):
        code_builder.add_instruction("cdq")
        code_builder.add_instruction("imul", "ebx")

    def _get_sign(self):
        return "*"


class Divide(BinaryOperator):
    def __init__(self, left, right):
        super(Divide, self).__init__(left, right)

    def windows_code_operator(self, code_builder, program_state):
        code_builder.add_instruction("cdq")
        code_builder.add_instruction("idiv", "ebx")

    def _get_sign(self):
        return "/"


class Modulo(BinaryOperator):
    def __init__(self, left, right):
        super(Modulo, self).__init__(left, right)

    def windows_code_operator(self, code_builder, program_state):
        code_builder.add_instruction("cdq")
        code_builder.add_instruction("idiv", "ebx")
        code_builder.add_instruction("mov", "eax", "edx")

    def _get_sign(self):
        return "%"


class Greater(BooleanBinaryOperator):
    def __init__(self, left, right):
        super(Greater, self).__init__(left, right)

    def _get_instruction(self):
        return "jg"

    def _get_sign(self):
        return ">"


class Less(BooleanBinaryOperator):
    def __init__(self, left, right):
        super(Less, self).__init__(left, right)

    def _get_instruction(self):
        return "jl"

    def _get_sign(self):
        return "<"


class Equal(BooleanBinaryOperator):
    def __init__(self, left, right):
        super(Equal, self).__init__(left, right)

    def _get_instruction(self):
        return "je"

    def _get_sign(self):
        return "=="


class GreaterOrEqual(BooleanBinaryOperator):
    def __init__(self, left, right):
        super(GreaterOrEqual, self).__init__(left, right)

    def _get_instruction(self):
        return "jge"

    def _get_sign(self):
        return ">="


class LessOrEqual(BooleanBinaryOperator):
    def __init__(self, left, right):
        super(LessOrEqual, self).__init__(left, right)

    def _get_instruction(self):
        return "jle"

    def _get_sign(self):
        return "<="


class NotEqual(BooleanBinaryOperator):
    def __init__(self, left, right):
        super(NotEqual, self).__init__(left, right)

    def _get_instruction(self):
        return "jne"

    def _get_sign(self):
        return "!="


class Or(BooleanBinaryOperator):
    def __init__(self, left, right):
        super(Or, self).__init__(left, right)

    def windows_code(self, code_builder, program_state):
        code_builder.add_instruction("and", "eax", "ebx")

    def _get_instruction(self):
        return "or"

    def _get_sign(self):
        return "||"


class And(BooleanBinaryOperator):
    def __init__(self, left, right):
        super(And, self).__init__(left, right)

    def windows_code(self, code_builder, program_state):
        code_builder.add_instruction("or", "eax", "ebx")

    def _get_instruction(self):
        return "and"

    def _get_sign(self):
        return "&&"