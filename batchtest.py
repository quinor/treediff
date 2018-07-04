#!/usr/bin/env python3

from glob import glob
import data
import trees
import distance


def main(base):
    print(base)
    uast_before, uast_after, src_before, src_after = data.get_data(base)
    before = trees.to_tree(uast_before)
    after = trees.to_tree(uast_after)
    changelist = distance.distance(before, after)
    modified = distance.apply(before, changelist)
    new_dist = distance.distance(before, modified)
    assert len(new_dist) == 0
    print("distance: {} \tsum: {}".format(len(changelist), before.size+after.size))


pwd = "/home/quinor/data/sourced/treediff/dataset/"
#pwd = "./local_data/"
if __name__ == "__main__":
    names = glob(pwd+"*after*.src")
    names = [e.split("/")[-1].split("_")[:2] for e in names]
    print(len(names))
    for a, b in names:
        main(pwd+"{}_{}".format(a, b))
