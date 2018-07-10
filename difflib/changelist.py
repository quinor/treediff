import uast_v2_1_pb2 as uast


class Changelist:
    def __init__(self, max_id=None, pb=None):
        self.counter = 0
        self.max_id = max_id
        self.changes = []
        if pb is not None:
            self.from_pb(pb)

    def new_id(self):
        self.counter -= 1
        return self.counter

    def to_pb(self):
        max_id = self.max_id
        convert = lambda x: x if x >= 0 else max_id-x

        l = []
        for change in self.changes:
            operation, target, *params = change
            target = convert(target)

            if operation is "create":
                op, v = params
                p = {}
                if op is "Value":
                    p["value"] = v
                if op is "Object":
                    p["object"] = uast.Object(links={
                        convert(k): convert(val)
                        for k, val in v
                    })
                if op is "Array":
                    p["array"] = uast.Array(nodes=[convert(e) for e in v])
                l.append(uast.Change(
                    create=uast.Node(id=target, **p)
                ))

            if operation is "delete":
                l.append(uast.Change(
                    delete=target
                ))

            if operation is "attach":
                key, child = params
                l.append(uast.Change(
                    attach=uast.Attach(parent=target, key=convert(key), child=convert(child))
                ))

            if operation is "deattach":
                key, = params
                l.append(uast.Change(
                    deattach=uast.Deattach(parent=target, key=convert(key))
                ))
        return uast.Changelist(changes=l, last_id=max_id)


    def from_pb(self, changelist_pb):
        self.max_id=changelist_pb.last_id
        convert = lambda x: x if x <= self.max_id else self.max_id-x

        for change in changelist_pb.changes:

            if change.HasField("create"):
                if change.create.HasField("value"):
                    name, param = "Value", change.create.value
                elif change.create.HasField("object"):
                    name, param = "Object", {
                        convert(k): convert(v)
                        for k, v in change.create.object.links
                    }
                elif change.create.HasField("array"):
                    name, param = "Array", [
                        convert(v)
                        for v in change.create.array.nodes
                    ]
                else:
                    assert False
                self.changes.append((
                    "create",
                    convert(change.create.id),
                    name,
                    param
                ),)

            if change.HasField("delete"):
                self.changes.append(("delete", convert(change.delete)),)

            if change.HasField("attach"):
                self.changes.append((
                    "attach",
                    convert(change.attach.parent),
                    convert(change.attach.key),
                    convert(change.attach.child),
                ),)

            if change.HasField("deattach"):
                self.changes.append((
                    "deattach",
                    convert(change.deattach.parent),
                    convert(change.deattach.key),
                ),)
