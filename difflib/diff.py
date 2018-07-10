from .graph import Node, Value, Object, Array
from .changelist import Changelist
import numpy as np
import lapjv
import copy


decision_map = {}  # cache


def decision(src, dst):
    """
    returns (cost, decision, params) tuple
    """
    lbl = id(src), id(dst)
    if lbl in decision_map:
        return decision_map[lbl]

    best_decision = min(src.size, 1)+dst.size, "replace", None

    if type(src) != type(dst):
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
                c2 += [Node(0) for _ in range(d)]
            elif d < 0:
                c1 += [Node(0) for _ in range(-d)]
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


def key_id(changelist, key):
    if isinstance(key, int):
        return key
    key_id = changelist.new_id()
    changelist.changes.append(("create", key_id, "Value", key))
    return key_id


def add_r(node, parent_id, idx, changelist):
    if node.id == 0:
        changelist.changes.append(("attach", parent_id, key_id(changelist, idx), 0),)
        return
    newid = changelist.new_id()
    changelist.changes.append(("create", newid, *node.desc),)
    changelist.changes.append(("attach", parent_id, key_id(changelist, idx), newid),)

    if isinstance(node, Object):
        for ind, e in node.fields.items():
            add_r(e, newid, ind, changelist)
    if isinstance(node, Array):
        for ind, e in enumerate(node.array):
            add_r(e, newid, ind, changelist)


def difference(src, dst, parent_id, idx, changelist):
    """
    writes changelist that can be used on src to perform transition to dst
    """
    cost, action, params = decision(src, dst)

    if action is "same":
        # no changes needed
        pass

    if action in ("replace", "change_value"):
        add_r(dst, parent_id, idx, changelist)
        # lack of removal

    if action is "match":
        keys = set(src.fields.keys()).union(set(dst.fields.keys()))
        for key in keys:
            if key not in src.fields:
                add_r(dst[key], src.id, key, changelist)
            elif key not in dst.fields:
                changelist.changes.append(("deattach", src.id, key_id(changelist, key)),)
                # lack of removal
            else:
                difference(src[key], dst[key], src.id, key, changelist)

    if action is "permute":
        perm = params
        c1 = src.array[:]
        c2 = dst.array[:]
        d = len(c1) - len(c2)
        if d > 0:
            c2 += [Node(0) for _ in range(d)]
        elif d < 0:
            c1 += [Node(0) for _ in range(-d)]
        if any(a != b for a, b in enumerate(perm)) or d != 0:
            changelist.changes.append(("create", src.id, "Array", [c1[e].id for e in perm]),)
            changelist.changes.append(("attach", parent_id, key_id(changelist, idx), src.id))
        for i, e in enumerate(perm):
            difference(c1[e], c2[i], src.id, i, changelist)


def distance(src, dst):
    src = src.root
    dst = dst.root
    changes = Changelist(src.max_id)
    difference(src, dst, 0, -1, changes)
    decision_map.clear()
    return changes
