class Node:
    def __init__(self):
        self.parent = None
        self.label = None

    @property
    def path(self):
        if self.parent is None:
            return []
        return self.parent.path+[self.label]

    @property
    def serialized_path(self):
        return "/".join(str(e) for e in self.path)


class Value(Node):
    def __init__(self, val):
        super().__init__()
        self.value = val
        self.desc = "Value {}".format(self.value)
        self.size = 1

    def print(self, pre=""):
        print(self.value)


class Object(Node):
    def __init__(self, dct):
        super().__init__()
        self.desc = "Object"
        self.fields = dct
        for k, v in self.fields.items():
            v.parent = self
            v.label = k
        self.size = 1 + sum(e.size for e in self.fields.values())

    def add_field(self, k, v):
        self.fields[k] = v
        v.parent = self
        v.label = k

    def remove_field(self, k):
        del self.fields[k]

    def print(self, pre=""):
        print("FIELDS:")
        pre = pre+"  "
        for name, var in self.fields.items():
            print("{}{}: ".format(pre, name), end="")
            var.print(pre)


class Array(Node):
    def __init__(self, arr):
        super().__init__()
        self.desc = "Array"
        self.array = arr
        for k, v in enumerate(self.array):
            v.parent = self
            v.label = k
        self.size = 1 + sum(e.size for e in arr)

    def add_field(self, k, v):
        self.array[k] = v
        v.parent = self
        v.label = k

    def print(self, pre=""):
        print("ELEMENTS:")
        pre = pre+"  "
        for elt in self.array:
            print("{}".format(pre), end="")
            elt.print(pre)


class Empty(Node):
    def __init__(self):
        super().__init__()
        self.desc = "Empty"
        self.size = 1

    def print(self, pre=""):
        print("<EMPTY>")


class Placeholder(Node):
    def __init__(self, parent=None, label=None):
        super().__init__()
        self.desc = "Placeholder"
        self.parent = parent
        self.label = label
        self.size = 0

    def print(self, pre=""):
        print("<EMPTY>")


def to_tree(ast):
    if ast.HasField("value"):
        return Value(ast.value)
    if ast.HasField("object"):
        ob = Object({n: to_tree(v) for n, v in ast.object.fields.items()})
        if "@type" in ob.fields and ob.fields["@type"].value == b'\x12\x0cast:Position':
            return Empty()  # position invariance
        return ob
    if ast.HasField("array"):
        return Array([to_tree(e) for i, e in enumerate(ast.array.array)])
    return Empty()
