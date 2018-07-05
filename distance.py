from trees import Placeholder, Value, Object, Array
import numpy as np
import lapjv
import copy


decision_map = {}


def decision(src, dst):
    """
    returns (cost, decision, params) tuple
    """
    lbl = id(src), id(dst)
    if lbl in decision_map:
        return decision_map[lbl]

    best_decision = min(src.size, 1)+dst.size, "replace", None

    if src.__class__ != dst.__class__:
        decision_map[lbl] = best_decision
        return best_decision

    if isinstance(src, Value):
        best_decision = min(
            best_decision,
            (0, "same", None) if src.value == dst.value else (1, "change_value", None)
        )

    if isinstance(src, Object):
        keys = set(src.fields.keys()).union(set(dst.fields.keys()))
        res = 0
        for key in keys:
            if key not in src.fields:
                res += dst[key].size  # insert subtree
            elif key not in dst.fields:
                res += 1  # remove subtree
            else:
                r, d, p = decision(src[key], dst[key])
                res += r
        best_decision = min(
            best_decision,
            (res, "same" if res == 0 else "match", None)
        )

    elif isinstance(src, Array):
        c1 = src.array[:]
        c2 = dst.array[:]
        r_ind = None
        if len(c1) == len(c2) and sum(decision(a, b)[0] for a, b in zip(c1, c2)) == 0:
            res = 0
        else:
            d = len(c1) - len(c2)
            if d > 0:
                c2 += [Placeholder() for _ in range(d)]
            elif d < 0:
                c1 += [Placeholder() for _ in range(-d)]
            dists = [[decision(f, e)[0] for e in c2] for f in c1]
            dists = np.asarray(dists)
            _, r_ind, _ = lapjv.lapjv(dists)
            res = 0
            if any(i != e for i, e in enumerate(r_ind)) or d != 0:
                res += 1
            for i, e in enumerate(r_ind):
                r, d, p = decision(c1[e], c2[i])
                res += r

        best_decision = min(
            best_decision,
            (res, "same" if res == 0 else "permute", r_ind)
        )

    decision_map[lbl] = best_decision

    return best_decision


def add_r(node, parent_id, idx, counter, changes):
    if isinstance(node, Placeholder):
        return
    newid = counter[0]
    counter[0] -= 1
    changes.append(("create", newid, *node.desc),)
    changes.append(("attach", parent_id, idx, newid),)

    if isinstance(node, Object):
        for ind, e in node.fields.items():
            add_r(e, newid, ind, counter, changes)
    if isinstance(node, Array):
        for ind, e in enumerate(node.array):
            add_r(e, newid, ind, counter, changes)


def changelist(src, dst, parent_id, idx, counter, changes):
    """
    writes changelist that can be used on src to perform transition to dst
    """
    cost, action, params = decision(src, dst)

    if action is "same":
        # no changes needed
        pass

    if action in ("replace", "change_value"):
        add_r(dst, parent_id, idx, counter, changes)
        # lack of removal

    if action is "match":
        keys = set(src.fields.keys()).union(set(dst.fields.keys()))
        for key in keys:
            if key not in src.fields:
                add_r(dst[key], src.id, key, counter, changes)
            elif key not in dst.fields:
                changes.append(("deattach", src.id, key),)
                # lack of removal
            else:
                changelist(src[key], dst[key], src.id, key, counter, changes)

    if action is "permute":
        perm = params
        c1 = src.array[:]
        c2 = dst.array[:]
        d = len(c1) - len(c2)
        if d > 0:
            c2 += [Placeholder() for _ in range(d)]
        elif d < 0:
            c1 += [Placeholder() for _ in range(-d)]
        if any(a != b for a, b in enumerate(perm)) or d != 0:
            changes.append(("create", src.id, "Array", [c1[e] for e in perm]),)
            changes.append(("attach", parent_id, idx, src.id))
        for i, e in enumerate(perm):
            changelist(c1[e], c2[i], src.id, i, counter, changes)


def distance(src, dst):
    changes = []
    changelist(src, dst, 0, -1, [-1], changes)
    decision_map.clear()
    return changes


def apply(src, changes):
    src = copy.copy(src)  # now we can modify freely
    nodes = {}
    src.traverse(lambda node: nodes.__setitem__(node.id, node))

    for change in changes:
        operation, target, *params = change

        if operation is "create":
            op, v = params
            if op is "Value":
                n = Value(v)
            if op is "Object":
                n = Object(v)
            if op is "Array":
                n = Array(v)
            nodes[n.id] = nodes[target] = n

        if operation is "attach":
            key, child = params
            nodes[target][key] = nodes[child]

        if operation is "deattach":
            key, = params
            nodes[target].remove_field(key)

        if operation is "remove":
            # do nothing cause GC
            pass

    return src
