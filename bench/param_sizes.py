#!/usr/bin/env python

"""Simulate parameters when all N parties are registered.

Outputs: 
- sizes of elements of G1, G2, GT, and scalar (sk)
- size of aux and pp for both regular and efficient construction
"""

from petrelic.multiplicative.pairing import G1,G2,GT,G1Element,G2Element,GTElement
# from petrelic import bn
import sqlite3
from math import ceil,log2,sqrt
import os

def print_element_sizes():
    print("G1 element size:\t",len(G1Element.to_binary(G1.generator()**G1.order().random())))
    print("G2 element size:\t",len(G2Element.to_binary(G2.generator()**G2.order().random())))
    print("GT element size:\t",len(GTElement.to_binary(GT.generator()**GT.order().random())))
    print("SK size:\t",len(G1.order().random().binary()))

def print_aux_size(N, n, t, eff=False):
    g1_rand = G1Element.to_binary(G1.generator()**G1.order().random())
    # efficient update construction
    if eff:
        filename = "aux_size_eff_{}.db".format(N)
        con = sqlite3.connect(filename)
        cur = con.cursor()
        cur.execute('''CREATE TABLE L (upd BLOB)''')
        cur.execute('''CREATE TABLE L_upd_num (upd INTEGER)''')
        for j in range(N):
            cur.execute('''INSERT INTO L_upd_num (rowid, upd) VALUES (?,?)''',(j,0))
        for i in range(t):
            # decoms for each block, broken into tables by update "chunk" (<= logn due to merge)
            cur.execute('''CREATE TABLE aux_{} (upd BLOB)'''.format(i))
            cur.execute('''CREATE TABLE aux_reg_count_{} (num INTEGER)'''.format(i))
            for j in range(N):
                cur.execute('''INSERT INTO aux_reg_count_{} (rowid, num) VALUES (?,?)'''.format(i),(j,0))
                cur.execute('''INSERT INTO aux_{} (rowid, upd) VALUES (?,?)'''.format(i),(j,g1_rand))
        con.commit()
        con.close()
        print("aux size (efficient):\t",os.path.getsize(filename))
        #os.remove(filename)
    # regular construction
    else:
        filename = "aux_size_not_eff_{}.db".format(N)
        con = sqlite3.connect(filename)
        cur = con.cursor()
        cur.execute('''CREATE TABLE aux (upd BLOB)''')
        for i in range(N*n):
            cur.execute('''INSERT INTO aux (rowid, upd) VALUES (?,?)''',(i,g1_rand))
        con.commit()
        con.close()
        print("aux size (regular):\t",os.path.getsize(filename))
        # os.remove(filename)

def print_pp_size(N, n, t, eff=False):
    g1_rand = G1Element.to_binary(G1.generator()**G1.order().random())
    # efficient update construction
    if eff:
        filename = "pp_size_eff_{}.db".format(N)
        con = sqlite3.connect(filename)
        cur = con.cursor()
        for i in range(t):
            # coms for each block, broken into tables by update "chunk" (<= logn due to merge)
            cur.execute('''CREATE TABLE pp_{} (commitment BLOB)'''.format(i))
            for j in range(n):
                cur.execute("INSERT INTO PP_{}(rowid, commitment) VALUES(?,?)".format(i),(j,g1_rand))
        # n rows with each row corresponding to a block of commitments C^i_1 ... C^i_log n; row i stores the number of parties registered in block i (the sum of the parties in each commitment in that block, i.e. the sum of a block in pp_com_count)
        cur.execute(''' CREATE TABLE pp_block_count (num INTEGER)''')
        # nlogn rows with each row corresponding to a commitment; row i stores number of parties registered under commitment i (pk's contained in that commitment)
        cur.execute(''' CREATE TABLE pp_com_count (num INTEGER)''')
        # initialise all counts to zero
        for i in range(n):
            cur.execute("INSERT INTO pp_block_count(rowid, num) VALUES (?,?)",(i,0))
            for j in range(t):
                cur.execute("INSERT INTO pp_com_count(rowid, num) VALUES (?,?)",(i*n+j,0))
        con.commit()
        con.close()
        print("pp size (efficient):\t",os.path.getsize(filename))
        #os.remove(filename)
    # regular construction
    else:
        filename = "pp_size_not_eff_{}.db".format(N)
        con = sqlite3.connect(filename)
        cur = con.cursor()
        cur.execute('''CREATE TABLE pp (commitment BLOB)''')
        for i in range(n):
            cur.execute('''INSERT INTO pp (rowid, commitment) VALUES (?,?)''',(i,g1_rand))
        con.commit()
        con.close()
        print("pp size (regular):\t",os.path.getsize(filename))
        #os.remove(filename)

if __name__ == "__main__":
    print_element_sizes()

    # 10K ... 10M
    N_arr = [10000, 100000, 1000000, 10000000]
    for N in N_arr:
        n = ceil(sqrt(N))
        t = ceil(log2(n))

        print("\nN = {}".format(N))
        print_aux_size(N, n, t, eff=True)
        print_pp_size(N, n, t, eff=True)
        print_aux_size(N, n, t, eff=False)
        print_pp_size(N, n, t, eff=False)
