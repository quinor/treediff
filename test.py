#!/usr/bin/env python3

from data import *
from trees import *

base = "/home/quinor/data/sourced/treediff/dataset/67_0"
uast_before, uast_after, src_before, src_after = get_data(base)

before = to_tree(uast_before)
after = to_tree(uast_after)

d, l = distance(before, after)

print(len(d), l)

for c in d:
    print(c)
