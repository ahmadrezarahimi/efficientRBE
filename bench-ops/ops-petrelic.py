#!/usr/bin/env python
import time
from numpy.random import randint
import numpy as np
from petrelic.multiplicative.pairing import G1,G2,GT, G1Element,G2Element,GTElement

if __name__ == "__main__":
    # random groups elements
    a_scalar = G1.order().random()
    b_scalar = G2.order().random()
    a = G1.generator() ** a_scalar
    b = G2.generator() ** b_scalar

    # more random scalars
    scalar1 = G1.order().random()
    scalar2 = G2.order().random()
    scalart = GT.order().random()

    exp_g1_time = 0.0
    exp_g2_time = 0.0
    pairing_time = 0.0
    exp_gt_time = 0.0
    g1_serialize_time = 0.0
    g1_deserialize_time = 0.0
    g2_serialize_time = 0.0
    g2_deserialize_time = 0.0
    gt_serialize_time = 0.0
    gt_deserialize_time = 0.0

    iters = 100
    print("averaging over {} iterations".format(iters), end="", flush=True)
    for i in range(iters):
        # exponentiations
        start = time.time()
        a_exp = a ** scalar1
        exp_g1_time += time.time()-start

        start = time.time()
        b_exp = b ** scalar2
        exp_g2_time += time.time()-start

        # pairing
        start = time.time()
        c = a.pair(b)
        pairing_time += time.time()-start

        # GT exp
        start = time.time()
        c_exp = c ** scalart
        exp_gt_time += time.time()-start

        # --- serialization ---
        # G1
        start = time.time()
        a_bytes = G1Element.to_binary(a)
        g1_serialize_time += time.time()-start

        start = time.time()
        G1Element.from_binary(a_bytes)
        g1_deserialize_time += time.time()-start

        # G2
        start = time.time()
        b_bytes = G2Element.to_binary(b)
        g2_serialize_time += time.time()-start

        start = time.time()
        G2Element.from_binary(b_bytes)
        g2_deserialize_time += time.time()-start

        # GT
        start = time.time()
        c_bytes = GTElement.to_binary(c)
        gt_serialize_time += time.time()-start

        start = time.time()
        GTElement.from_binary(c_bytes)
        gt_deserialize_time += time.time()-start

        print(i if i>0 and i%10==0 else ".", end="", flush=True)

    print("\n")
    print("exp in G1\t{}".format(exp_g1_time / iters))
    print("exp in G2\t{}".format(exp_g2_time / iters))
    print("exp in GT\t{}".format(exp_gt_time / iters))
    print()
    print("pairing\t\t{}".format(pairing_time / iters))
    print()
    print("serialize in G1\t\t{}".format(g1_serialize_time / iters))
    print("deserialize in G1\t{}".format(g1_deserialize_time / iters))
    print("serialize in G2\t\t{}".format(g2_serialize_time / iters))
    print("deserialize in G2\t{}".format(g2_deserialize_time / iters))
    print("serialize in GT\t\t{}".format(gt_serialize_time / iters))
    print("deserialize in GT\t{}".format(gt_deserialize_time / iters))

    # sizes
    print()
    print("G1 bytes:\t{}".format(len(a_bytes)))
    print("G2 bytes:\t{}".format(len(b_bytes)))
    print("GT bytes:\t{}".format(len(c_bytes)))
