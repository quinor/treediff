#!/usr/bin/env python3

from glob import glob
import data
import trees
import distance
import changelist


def main(base):
    print(base)
    uast_before, uast_after, src_before, src_after = data.get_data(base)
    before = trees.to_tree(uast_before)
    after = trees.to_tree(uast_after)
    ch = distance.distance(before, after)
    pb = changelist.changelist_to_proto(ch)
    ch = changelist.proto_to_changelist(pb)
    modified = distance.apply(before, ch)
    new_dist = distance.distance(before, modified)
    assert len(new_dist.changes) == 0
    print("distance: {} \tsum: {}".format(len(ch.changes), before.size+after.size))


pwd = "/home/quinor/data/sourced/treediff/dataset/"
#pwd = "./local_data/"
if __name__ == "__main__":
    names = glob(pwd+"*after*.src")
    names = [e.split("/")[-1].split("_")[:2] for e in names]
    print(len(names))
    for a, b in names:
        main(pwd+"{}_{}".format(a, b))
