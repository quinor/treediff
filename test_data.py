from glob import glob
import importlib

from uast_v2_pb2 import Node

def get_data(base):
    uast_before = glob("%s_before_*.pb" % base)[0]
    uast_after = glob("%s_after_*.pb" % base)[0]
    src_before = glob("%s_before_*.src" % base)[0]
    src_after = glob("%s_after_*.src" % base)[0]
    with open(src_before) as fin:
        src_before = fin.read()
    with open(src_after) as fin:
        src_after = fin.read()
    with open(uast_before, "rb") as fin:
        uast_before = Node.FromString(fin.read())
    with open(uast_after, "rb") as fin:
        uast_after = Node.FromString(fin.read())
    return uast_before, uast_after, src_before, src_after
