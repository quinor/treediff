class Node:
    _counter = 0

    def __init__(self):
        self.id = self._counter
        Node._counter += 1

    @property
    def max_id(self):
        return self.id

    def traverse(self, fn):
        fn(self)


class Value(Node):
    def __init__(self, val):
        super().__init__()
        self.value = val
        self.desc = "Value", self.value
        self.size = 1

    def print(self, pre=""):
        print(self.value)


class Object(Node):
    def __init__(self, dct):
        super().__init__()
        self.fields = dct
        if isinstance(dct, list):
            raise Exception("wth?!")

    @property
    def desc(self):
        return "Object", {}

    @property
    def size(self):
        return 1 + sum(e.size for e in self.fields.values())

    @property
    def max_id(self):
        return max(self.id, 0, *(e.max_id for e in self.fields.values()))

    def traverse(self, fn):
        fn(self)
        for e in self.fields.values():
            e.traverse(fn)

    def __setitem__(self, k, v):
        self.fields[k] = v

    def remove_field(self, k):
        assert k in self.fields
        del self.fields[k]

    def __getitem__(self, k):
        return self.fields[k]

    def print(self, pre=""):
        print("FIELDS:")
        pre = pre+"  "
        for name, var in self.fields.items():
            print("{}{}: ".format(pre, name), end="")
            var.print(pre)


class Array(Node):
    def __init__(self, arr):
        super().__init__()
        self.array = arr

    @property
    def desc(self):
        return "Array", [None for _ in range(len(self.array))]

    @property
    def size(self):
        return 1 + sum(e.size for e in self.array)

    @property
    def max_id(self):
        try:
            return max(0, self.id, *(e.max_id for e in self.array))
        except Exception:
            print(self.array)

    def traverse(self, fn):
        fn(self)
        for e in self.array:
            e.traverse(fn)

    def __setitem__(self, k, v):
        while len(self.array) <= k:
            self.array.append(None)
        self.array[k] = v

    def remove_field(self, k):
        self.array[k] = None
        while self.array and self.array[-1] is None:
            self.array.pop()

    def __getitem__(self, k):
        assert k < len(self.array)
        return self.array[k]

    def print(self, pre=""):
        print("ELEMENTS:")
        pre = pre+"  "
        for elt in self.array:
            print("{}".format(pre), end="")
            elt.print(pre)


class Placeholder(Node):
    def __init__(self):
        super().__init__()
        self.desc = "Placeholder", None
        self.size = 0

    def print(self, pre=""):
        print("<EMPTY>")


def to_tree(ast):
    if ast.HasField("value"):
        return Value(ast.value)
    if ast.HasField("object"):
        ob = Object({n: to_tree(v) for n, v in ast.object.fields.items()})
        if "@type" in ob.fields and ob.fields["@type"].value == b'\x12\x0cast:Position':
            return Object({})  # position invariance
        return ob
    if ast.HasField("array"):
        return Array([to_tree(e) for i, e in enumerate(ast.array.array)])
    return Object({})  # that is an empty node!
