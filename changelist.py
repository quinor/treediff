import uast_v2_1_pb2 as uast


class Changelist:
    def __init__(self, max_id):
        self.counter = 0
        self.max_id = max_id
        self.changes = []

    def new_id(self):
        self.counter -= 1
        return self.counter


def changelist_to_proto(changelist):
    max_id = changelist.max_id
    convert = lambda x: x if x >= 0 else max_id-x

    l = []
    for change in changelist.changes:
        operation, target, *params = change
        target = convert(target)

        if operation is "create":
            op, v = params
            p = {}
            if op is "Value":
                p["value"] = v
            if op is "Object":
                p["object"] = uast.Object(links={})  # TODO: keys from v
            if op is "Array":
                p["array"] = uast.Array(nodes=v)
            l.append(uast.Change(
                create=uast.Node(id=target, **p)

            ))

        if operation is "delete":
            l.append(uast.Change(
                delete=target
            ))

        if operation is "attach":
            key, child = params
            child = convert(child)
            key = convert(key)
            l.append(uast.Change(
                attach=uast.Attach(parent=target, key=key, child=child)
            ))

        if operation is "deattach":
            key, = params
            key = convert(key)
            l.append(uast.Change(
                deattach=uast.Deattach(parent=target, key=key)
            ))
    return uast.Changelist(changes=l, last_id=max_id)


def proto_to_changelist(pb):
    # WIP
    ch = Changelist(pb.last_id)
    convert = lambda x: x if x <= ch.max_id else ch.max_id-x

    for change in pb.changes:

        if change.HasField("create"):
            if change.create.HasField("value"):
                name, param = "Value", change.create.value
            elif change.create.HasField("object"):
                name, param = "Object", {
                    convert(k): convert(v)
                    for k, v in change.create.object.links
                }
            elif change.create.HasField("array"):
                name, param = "Array", {
                    convert(v)
                    for v in change.create.array.nodes
                }
            else:
                assert False
            ch.changes.append((
                "create",
                convert(change.create.id),
                name,
                param
            ),)

        if change.HasField("delete"):
            ch.changes.append(("delete", convert(change.delete)),)

        if change.HasField("attach"):
            ch.changes.append((
                "attach",
                convert(change.attach.parent),
                convert(change.attach.key),
                convert(change.attach.child),
            ),)

        if change.HasField("deattach"):
            ch.changes.append((
                "deattach",
                convert(change.deattach.parent),
                convert(change.deattach.key),
            ),)

    return ch
