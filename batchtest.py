#!/usr/bin/env python3

from glob import glob
import data
from difflib import Graph, Changelist, distance
import random
import code


def same(t1, t2):
    new_dist = distance(t1, t2)
    assert len(new_dist.changes) == 0
    new_dist = distance(t2, t1)
    assert len(new_dist.changes) == 0


def main(base):
    print(base)
    uast_before, uast_after, src_before, src_after = data.get_data(base)
    before = Graph(uast_before)
    after = Graph(uast_after)

    before2 = Graph(before.to_pb())
    same(before, before2)
    ch = distance(before, after)
    modified = before2.apply(ch)

    print("distance: {} \tsum: {}".format(len(ch.changes), before.root.size+after.root.size))
    same(after, modified)


pwd = "/home/quinor/data/sourced/treediff/dataset/"
#pwd = "./local_data/"
if __name__ == "__main__":
    names = data.default_dataset()[12:]
#    random.shuffle(names)
    print(len(names))
    for a, b in names:
        main(pwd+"{}_{}".format(a, b))
