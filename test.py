#!/usr/bin/env python3

import data
import trees
import distance

base = "/home/quinor/data/sourced/treediff/dataset/51_0"
uast_before, uast_after, src_before, src_after = data.get_data(base)

before = trees.to_tree(uast_before)
after = trees.to_tree(uast_after)

ch = distance.distance(before, after)

modified = distance.apply(before, ch)
new_dist = distance.distance(before, modified)
assert len(new_dist) == 0

print(len(ch))

for c in ch:
    print(c)
