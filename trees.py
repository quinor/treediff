import numpy as np
import lapjv


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


dist_map = {}


def add_r(node, changes):
    changes.append("add {} {}".format(node.serialized_path, node.desc))
    if isinstance(node, Object):
        for e in node.fields.values():
            add_r(e, changes)
    if isinstance(node, Array):
        for e in node.array:
            add_r(e, changes)


def dist(src, dst, final=False):
    changes = []
    lbl = id(src), id(dst)
    if final and lbl not in dist_map:
        dist(src, dst)
    if lbl in dist_map and not final:
        return [], dist_map[lbl]


    if src.__class__ != dst.__class__ or (final and dist_map[lbl] == min(src.size, 1)+dst.size):
        res = min(src.size, 1)+dst.size
        if final:
            if not isinstance(src, Placeholder):
                changes.append("remove {}".format(src.serialized_path))
            add_r(dst, changes)
            src.parent.add_field(src.label, dst)

    elif isinstance(src, Empty):
        res = 0

    elif isinstance(src, Value):
        res = 0 if src.value == dst.value else 1
        if src.value != dst.value and final:
            src.value = dst.value
            changes.append("modify {} to {}".format(src.serialized_path, dst.value))

    elif isinstance(src, Object):
        keys = set(src.fields.keys()).union(set(dst.fields.keys()))
        res = 0
        for key in keys:
            if key not in src.fields:
                res += dst.fields[key].size  # insert subtree
                if final:
                    src.add_field(key, dst.fields[key])
                    add_r(dst.fields[key], changes)
            elif key not in dst.fields:
                res += 1  # remove subtree
                if final:
                    changes.append("remove {}".format(src.fields[key].serialized_path))
                    src.remove_field(key)
            else:
                c, r = dist(src.fields[key], dst.fields[key], final)
                res += r
                if final:
                    changes += c

    elif isinstance(src, Array):
        c1 = src.array[:]
        c2 = dst.array[:]
        if len(c1) == len(c2) and sum(dist(a, b)[1] for a, b in zip(c1, c2)) == 0:
            res = 0
        else:
            d = len(c1) - len(c2)
            if d > 0:
                c2 += [Placeholder(dst, -1) for _ in range(d)]
            elif d < 0:
                c1 += [Placeholder(src, -1) for _ in range(-d)]
            dists = [[dist(f, e)[1] for e in c2] for f in c1]
            dists = np.asarray(dists)
            _, r_ind, _ = lapjv.lapjv(dists)
            res = 0
            res += len(r_ind)-len(dst.array)
            if final:
                for e in r_ind[len(dst.array):]:
                    changes.append("remove {}".format(c1[e].serialized_path))
            if any(i != e for i, e in enumerate(r_ind)):
                res += 1
                if final:
                    changes.append("permute {} to {}".format(
                        src.serialized_path,
                        r_ind[:len(dst.array)],
                    ))
                    src.array = [0]*len(dst.array)
                    for i, e in enumerate(r_ind[:len(dst.array)]):
                        src.add_field(i, c1[e])
            for i, e in enumerate(r_ind[:len(dst.array)]):
                c, r = dist(c1[e], c2[i], final)
                res += r
                if final:
                    changes += c

    else:
        raise Exception("wth?!")

    if not final and min(src.size, 1) + dst.size <= res:
        res = min(src.size, 1) + dst.size

    dist_map[lbl] = res
    return changes, res


def distance(src, dst):
    c, r = dist(src, dst, True)
    dist_map.clear()
    return c, r
