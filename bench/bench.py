#!/usr/bin/env python
from rbe import algos
from rbe.objects import *
from rbe import utils
import time
import argparse
from os.path import exists
import numpy as np
import csv
from math import ceil, sqrt

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="run benchmarks for a single block")
    parser.add_argument('-N','--max_parties',
        type=int,
        required=False,
        default=100,
        dest='N',
        help='maximum number of parties to be registered (10^1...10^6)')
    parser.add_argument('-i','--iters',
        type=int,
        required=False,
        default=-1,
        dest='iters',
        help='iterations of benchmarks to do (for a single setup); must be <=sqrt(N). Default is sqrt(N).')
    parser.add_argument('-e','--efficient',
        action='store_true',
        required=False,
        default=False,
        dest='eff',
        help='run efficient update variant')
    parser.add_argument('-f','--full-reg',
        action='store_true',
        required=False,
        default=False,
        dest='full_reg',
        help='run registration (only) for full system capacity (N parties)')
    args = parser.parse_args()
    if args.iters == -1:
        args.iters = ceil(sqrt(args.N))

    ## Setup ###
    setup_time = time.time()
    crs = algos.setup(args.N, efficient=args.eff)
    setup_time = time.time()-setup_time
    if args.iters > crs.n:
        print("selected number of iterations ({}) is greater than max number of parties in block ({})!".format(args.iters, crs.n))
        exit(0)
    print("Setup (s):\t", setup_time)
    print("--------------------------")

    prefix = 'bench{}{}_'.format(args.N, 'e' if args.eff else '')
    f1 = open(prefix+'genreg.csv', 'w')
    f_enc = open(prefix+'enc.csv', 'w')
    f_upd = open(prefix+'upd.csv', 'w')
    f_dec = open(prefix+'dec.csv', 'w')
    writer1 = csv.writer(f1)
    writer_enc = csv.writer(f_enc)
    writer_upd = csv.writer(f_upd)
    writer_dec = csv.writer(f_dec)
    header1 = ['Gen', 'Reg']
    writer1.writerow(header1)
    writer_enc.writerow(['Enc'])
    writer_upd.writerow(['Upd'])
    writer_dec.writerow(['Dec'])
    time_avgs = {
        "Gen": 0,
        "Reg": 0,
        "Enc": 0,
        "Upd": 0,
        "Dec": 0,
    }
    # num_upd = 0

    if args.full_reg:
        ids = np.random.permutation(range(crs.N)).tolist()
        for i in range(crs.N):
            pk,sk,xi = algos.gen(crs,ids[i])
            algos.reg(crs,ids[i],pk,xi,efficient=args.eff)

    else:
        ids = np.random.permutation(range(crs.n)).tolist()

        target_sks = [None]*args.iters
        target_ids = [None]*args.iters
        target_ms = [None]*args.iters
        target_cts = [None]*args.iters
        # iters random, unique, increasing registration times
        # (pick `iters` ids (these will be ids to encrypt to) randomly among the first 1/2 of ids to be registered)
        target_reg_time_stamps = np.random.permutation(range(max(int(crs.n/2),args.iters))).tolist()[:args.iters]
        target_reg_time_stamps = np.sort(target_reg_time_stamps).tolist()

        target_reg_enc_time_diff = np.random.randint(crs.n/4,size=args.iters)
        target_enc_time_stamps = target_reg_time_stamps+target_reg_enc_time_diff
        for i in range(args.iters):
            if target_enc_time_stamps[i] > crs.n-1:
                target_enc_time_stamps[i] = crs.n-1

        target_enc_dec_time_diff = np.random.randint(crs.n/4,size=args.iters)
        target_dec_time_stamps = target_enc_time_stamps+target_enc_dec_time_diff
        for i in range(args.iters):
            if target_dec_time_stamps[i] > crs.n-1:
                target_dec_time_stamps[i] = crs.n-1

        j = 0 # counter for target ids registered
        k = 0 # counter for target ids enc'd to
        l = 0 # counter for target ids dec'd for
        for i in range(crs.n):
            # for csv files
            row1 = []

            gen_time = time.time()
            pk,sk,xi = algos.gen(crs,ids[i])
            gen_time = time.time()-gen_time
            row1 += [gen_time]
            time_avgs["Gen"] += gen_time

            # print("t = {}: Reg id {} with sk {}".format(i, ids[i], sk))
            reg_time = time.time()
            algos.reg(crs,ids[i],pk,xi,efficient=args.eff)
            reg_time = time.time() - reg_time
            row1 += [reg_time]
            time_avgs["Reg"] += reg_time

            # write to csv
            writer1.writerow(row1)

            # if we are registering a target id, save its sk
            if j < args.iters and i == target_reg_time_stamps[j]:
                target_ids[j] = ids[i]
                target_sks[j] = sk
                j = j+1

            # is it time to enc to a target id?
            for k in range(args.iters):
                if i == target_enc_time_stamps[k]:
                    # print("t = {}: Enc to target id {}".format(i, target_ids[k]))
                    target_ms[k] = GT.generator()**GT.order().random()
                    enc_time = time.time()
                    target_cts[k] = algos.enc(crs,target_ids[k],target_ms[k],efficient=args.eff)
                    enc_time = time.time()-enc_time
                    writer_enc.writerow([enc_time])
                    time_avgs["Enc"] += enc_time

            # is it time to dec for a target id?
            for l in range(args.iters):
                if i == target_dec_time_stamps[l]:
                    # print("t = {}: Fetch update for id {}".format(i, target_ids[l]))

                    upd_time = time.time()
                    u = algos.upd(crs, target_ids[l],efficient=args.eff)
                    upd_time = time.time()-upd_time
                    writer_upd.writerow([upd_time])
                    time_avgs["Upd"] += upd_time
                    # print("\t{}".format(u))
                    # num_upd += len(u)

                    # print("t = {}: Dec for target id {}".format(i, target_ids[l]))

                    dec_time = time.time()
                    if args.eff:
                        m_prime = algos.dec(crs,target_ids[l],target_sks[l],u,target_cts[l])
                    else:
                        # easily calculate upd number to use, given enc timestamp
                        m_prime = algos.dec(crs,target_ids[l],target_sks[l],u,target_cts[l],upd_idx=target_enc_time_stamps[l])
                    dec_time = time.time() - dec_time
                    writer_dec.writerow([dec_time])
                    time_avgs["Dec"] += dec_time

                    # ensure correctness
                    assert(target_ms[l] == m_prime)

        time_avgs["Gen"] /= crs.n
        time_avgs["Reg"] /= crs.n
        time_avgs["Enc"] /= args.iters
        time_avgs["Upd"] /= args.iters
        time_avgs["Dec"] /= args.iters

        print("\nAverage Times (s)")
        print("--------------------------")
        for key in time_avgs.keys():
            if key in ["Gen", "Reg"]:
                iters = crs.n
            else:
                iters = args.iters
            print("{}:\t{}\t(avg of {})".format(key,time_avgs[key],iters))

        # print()
        # print("\nAverage Data Transmitted")
        # print("#Upd:\t{}\t(avg of {}; each one is an element of G1)".format(num_upd/args.iters, args.iters))
