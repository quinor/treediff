from trees import Placeholder, Empty, Value, Object, Array
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

    if isinstance(src, Empty):
        best_decision = min(best_decision, (0, "same", None))

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
                res += dst.fields[key].size  # insert subtree
            elif key not in dst.fields:
                res += 1  # remove subtree
            else:
                r, d, p = decision(src.fields[key], dst.fields[key])
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


def add_r(node, path, changes):
    changes.append(("add", path[:-1], (path[-1], node.desc)),)
    if isinstance(node, Object):
        for ind, e in node.fields.items():
            add_r(e, path+[ind], changes)
    if isinstance(node, Array):
        for ind, e in enumerate(node.array):
            add_r(e, path+[ind], changes)


def changelist(src, dst, path, changes):
    """
    writes changelist that can be used on src to perform transition to dst
    """
    cost, action, params = decision(src, dst)

    if action is "same":
        # no changes needed
        pass

    if action is "replace":
        if not isinstance(src, Placeholder):  # placeholders don't need to be removed
            changes.append(("remove", path[:-1], path[-1]),)
        if not isinstance(dst, Placeholder):  # placeholders don't need to be inserted either
            add_r(dst, path, changes)

    if action is "change_value":
        changes.append(("modify", path, dst.value),)

    if action is "match":
        keys = set(src.fields.keys()).union(set(dst.fields.keys()))
        for key in keys:
            newpath = path+[key]
            if key not in src.fields:
                add_r(dst.fields[key], newpath, changes)
            elif key not in dst.fields:
                changes.append(("remove", newpath[:-1], newpath[-1]),)
            else:
                changelist(src.fields[key], dst.fields[key], newpath, changes)

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
            changes.append(("permute", path, perm),)
        for i, e in enumerate(perm):
            changelist(c1[e], c2[i], path+[i], changes)


def distance(src, dst):
    changes = []
    changelist(src, dst, [], changes)
    c, _, __ = decision(src, dst)
    if c != len(changes):
        print("KURWA, KURWA! {} {}".format(c, len(changes)))
    decision_map.clear()
    return changes


def apply(src, changelist):
    src = copy.copy(src)  # now we can modify freely
    path = []
    stack = [src]
    for change in changelist:
        operation, loc_path, params = change
        same_pref = min(
            len(path),
            len(loc_path),
            *(i for i, (a, b) in enumerate(zip(path, loc_path)) if a != b)
        )
        for _ in range(len(path)-same_pref):
            path.pop()
            stack.pop()
        try:
            for el in loc_path[same_pref:]:
                path.append(el)
                stack.append(stack[-1][el])
        except Exception as e:
            print(path)
            print(loc_path)
            print(stack[-1].fields.keys())
            print(operation)
            raise e

        if operation is "add":
            key, (op, v) = params
            if op is "Value":
                n = Value(v)
            if op is "Object":
                n = Object({})
            if op is "Array":
                n = Array([None for _ in range(v)])
            if op is "Empty":
                n = Empty()
            stack[-1][key] = n

        if operation is "remove":
            stack[-1].remove_field(params)

        if operation is "modify":
            stack[-1].value = params

        if operation is "permute":
            l = stack[-1].array[:]
            for _ in range(len(params)-len(l)):
                l.append(None)
            stack[-1].array = [l[pos] for pos in params]

    return src
