import uast_v2_1_pb2 as uast
import copy


class Graph:
    # ignores metadata and last_id, assumes all nodes accessible from root

    def __init__(self, pb=None):
        self.node_dict = {}
        self.root = None

        self.node_dict[0] = Node(0)
        if pb is not None:
            self.from_pb(pb)

    def build_node(self, idx):
        if idx == 0:
            return Node(0)
        if isinstance(self.node_dict[idx], Node):
            return self.node_dict[idx]

        obj = self.node_dict[idx]
        if obj.HasField("value"):
            ret = Value(idx, obj.value)
        elif obj.HasField("object"):
            ret = Object(idx, {
                self.build_node(k).value: self.build_node(v)
                for k, v in obj.object.links.items()
            })
            TY = b"\n\x05@type"
            PO = b"\n\x0cast:Position"
            if TY in ret.fields and ret.fields[TY].value == PO:
                ret = Object(idx, {})  # position invariance
        elif obj.HasField("array"):
            ret = Array(idx, [self.build_node(e) for e in obj.array.nodes])
        else:
            raise Exception("empty node")
        self.node_dict[idx] = ret
        return ret

    def from_pb(self, graph_pb):
        for node in graph_pb.nodes:
            self.node_dict[node.id] = node
        self.root = self.build_node(graph_pb.root)

    def to_pb(self):
        max_id = [self.root.max_id]
        l = []

        def key_id(key):
            if isinstance(key, int):
                return key
            max_id[0] += 1
            key_id = max_id[0]
            l.append(uast.Node(id=key_id, value=key))
            return key_id

        def serialize(node):
            if isinstance(node, Value):
                l.append(uast.Node(id=node.id, value=node.value))
            elif isinstance(node, Object):
                l.append(uast.Node(id=node.id, object=uast.Object(links={
                    key_id(k): v.id for k, v in node.fields.items()})))
            elif isinstance(node, Array):
                l.append(uast.Node(id=node.id, array=uast.Array(nodes=[
                    e.id for e in node.array])))
            else:
                assert node.id == 0  # empty node

        self.root.traverse(serialize)

        return uast.Graph(nodes=l, root=self.root.id)

    def apply(self, changelist):
        max_id = changelist.max_id

        for change in changelist.changes:
            operation, loc_target, *params = change
            if loc_target < 0:
                target = max_id - loc_target
            else:
                target = loc_target

            if operation is "create":
                op, v = params
                if op is "Value":
                    n = Value(target, v)
                if op is "Object":
                    n = Object(target, {self.node_dict[k].value: self.node_dict[val] for k, val in v})
                if op is "Array":
                    n = Array(target, [self.node_dict[e] for e in v])
                self.node_dict[loc_target] = self.node_dict[target] = n

            if operation is "attach":
                key, child = params
                if isinstance(self.node_dict[target], Object):
                    key = self.node_dict[key].value
                try:
                    self.node_dict[target][key] = self.node_dict[child]
                except Exception as e:
                    print(target, key, child)
                    raise e

            if operation is "deattach":
                key, = params
                if isinstance(self.node_dict[target], Object):
                    key = self.node_dict[key].value
                self.node_dict[target].remove_field(key)

            if operation is "delete":
                # do nothing cause GC
                pass

        return self


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
        if v.id == 0:
            self.remove_field(k)
        else:
            while k >= len(self.array):
                self.array.append(Node(0))
            self.array[k] = v

    def remove_field(self, k):
        self.array[k] = Node(0)
        while self.array and self.array[-1].id == 0:
            self.array.pop()

    def __getitem__(self, k):
        assert k < len(self.array)
        return self.array[k]
