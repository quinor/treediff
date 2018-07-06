#!/usr/bin/env python3

import data
import trees
import distance
import changelist

base = "/home/quinor/data/sourced/treediff/dataset/150_0"
uast_before, uast_after, src_before, src_after = data.get_data(base)

before = trees.to_tree(uast_before)
after = trees.to_tree(uast_after)

ch = distance.distance(before, after)

pb = changelist.changelist_to_proto(ch)
ch = changelist.proto_to_changelist(pb)

modified = distance.apply(before, ch)
new_dist = distance.distance(before, modified)
assert len(new_dist.changes) == 0

print(len(ch.changes))

for c in ch.changes:
    print(c)

print(pb)
