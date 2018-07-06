import copy


class Node:
    def __init__(self, idx):
        self.id = idx

    @property
    def size(self):
        return 0

    @property
    def desc(self):
        return "Node", None

    @property
    def max_id(self):
        return self.id

    def traverse(self, fn):
        fn(self)


class Value(Node):
    def __init__(self, idx, val):
        super().__init__(idx)
        self.value = val

    @property
    def size(self):
        return 1

    @property
    def desc(self):
        return "Value", self.value

    def print(self, pre=""):
        print(self.value)


class Object(Node):
    def __init__(self, idx, dct):
        super().__init__(idx)
        self.fields = copy.copy(dct)

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
        if k not in self.fields:
            print(k)
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
    def __init__(self, idx, arr):
        super().__init__(idx)
        self.array = copy.copy(arr)

    @property
    def desc(self):
        return "Array", [0 for _ in range(len(self.array))]

    @property
    def size(self):
        return 1 + sum(e.size for e in self.array)

    @property
    def max_id(self):
        return max(0, self.id, *(e.max_id for e in self.array))

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


def to_tree(graph):
    node_dict = {}
    for node in graph.nodes:
        node_dict[node.id] = node

    def build(idx):
        if idx == 0:
            return Node(0)
        obj = node_dict[idx]
        if obj.HasField("value"):
            return Value(idx, obj.value)
        if obj.HasField("object"):
            ob = Object(idx, {node_dict[n].value: build(v) for n, v in obj.object.links.items()})
            TY = b"\n\x05@type"
            PO = b"\n\x0cast:Position"
            if TY in ob.fields and ob.fields[TY].value == PO:
                return Object(idx, {})  # position invariance
            return ob
        if obj.HasField("array"):
            return Array(idx, [build(e) for e in obj.array.nodes])
        raise Exception("empty node")
    return build(graph.root)
