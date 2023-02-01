#!/usr/bin/env python3

"""Implementation of the RBE algorithms (Setup, Gen, Reg, Enc, Upd, Dec) and Merge.
"""

from math import ceil,floor, log2,sqrt
from operator import mod

# from more_itertools import last
from rbe.objects import *
from rbe import utils
import sqlite3
from os.path import exists

def setup(N, efficient=False):
    """Generate CRS and initialise auxiliary information and public parameters over the BLS12-381 curve.

    Parameters
    ----------
    N : int 
        maximum number of users
    efficient : bool (optional)
        use efficient update variant

    Returns
    -------
    crs : CRS 
        includes the bilinear group description bg and the h_i's
    
    Notes
    -----
    The pp and aux are not returned but instead initialised as databases.
    """

    # Note: For the efficient variant, consider the public parameter as a matrix of commitments, with log n rows and n columns. For each row, we create a (potential) seperate Aux table.

    crs = CRS(N)

    n = ceil(sqrt(N))
    t = ceil(log2(n))

    # stores number of parties registered in each block
    if exists("aux_count.db") == False:
        con = sqlite3.connect('aux_count.db')
        cur = con.cursor()
        cur.execute('''CREATE TABLE auxCount (totalCount INTEGER)''')
        con.commit()
        con.close()

    # create aux database
    if exists("aux.db") == False:
        con = sqlite3.connect("aux.db")
        cur = con.cursor()

        if efficient:
            cur.execute('''CREATE TABLE L (upd BLOB)''')
            cur.execute('''CREATE TABLE L_upd_num (upd INTEGER)''')
            for j in range(N):
                 cur.execute('''INSERT INTO L_upd_num (rowid, upd) VALUES (?,?)''',(j,0))
            for i in range(t):
                # decoms for each block, broken into tables by update "chunk" (<= logn due to merge)
                cur.execute('''CREATE TABLE aux_{} (upd BLOB)'''.format(i))
                cur.execute('''CREATE TABLE aux_reg_count_{} (num INTEGER)'''.format(i))
                # NOTE the current benchmarks only register one block of parties, so we do it for n
                # for the general case this range would be N
                for j in range(crs.n):
                    cur.execute('''INSERT INTO aux_reg_count_{} (rowid, num) VALUES (?,?)'''.format(i),(j,0))
        else:
            # the regular variant just has one aux table
            cur.execute('''CREATE TABLE aux (upd BLOB)''')

        con.commit()
        con.close()

    # create pp database
    if exists("pp.db") == False:
        con = sqlite3.connect("pp.db")
        cur = con.cursor()

        if efficient:
            for i in range(t):
                # coms for each block, broken into tables by update "chunk" (<= logn due to merge)
                cur.execute('''CREATE TABLE pp_{} (commitment BLOB)'''.format(i))

            # n rows with each row corresponding to a block of commitments C^i_1 ... C^i_log n; row i stores the number of parties registered in block i (the sum of the parties in each commitment in that block, i.e. the sum of a block in pp_com_count)
            cur.execute(''' CREATE TABLE pp_block_count (num INTEGER)''')
            # nlogn rows with each row corresponding to a commitment; row i stores number of parties registered under commitment i (pk's contained in that commitment)
            cur.execute(''' CREATE TABLE pp_com_count (num INTEGER)''')

            # initialise all counts to zero
            for i in range(crs.n):
                cur.execute("INSERT INTO pp_block_count(rowid, num) VALUES (?,?)",(i,0))
            # TODO the current benchmark only registers n parties, so we do it for 1 commitment, for general case the range must be N
            # for i in range((crs.n+1)*(crs.n+1)):
            #    cur.execute("INSERT INTO pp_com_count(rowid, num) VALUES (?,?)",(i,0))
            for i in range(crs.n):
                for j in range(t+1):
                    cur.execute("INSERT INTO pp_com_count(rowid, num) VALUES (?,?)",(i*crs.n+j,0))
        else:
            # the regular variant just has one pp table
            cur.execute('''CREATE TABLE pp (commitment BLOB)''')

        con.commit()
        con.close()

    return crs

def gen(crs, id):
    """Generate keypair and auxiliary information for user `id`

    Parameters
    ----------
    crs : CRS
        common reference string
    id : int
        user identifier

    Returns
    -------
    pk : element of G1
        public key
    sk : element of ZR
        secret key
    helping_values : array of elements of G1
        xi in the paper
    """
    id_index = mod(id,crs.n)
    sk = G1.order().random()
    h_id_index = crs.h_parameters_g1[id_index]
    pk = h_id_index ** sk

    helping_values = [None] * crs.n
   
    for j in range(crs.n):
        i = crs.n-1-j
        if crs.h_parameters_g1[id_index+j+1] == None:
            continue
        helping_values[i] = crs.h_parameters_g1[id_index+j+1]**sk
    return pk,sk,helping_values

def reg(crs, id, pk, helping_values, efficient=False):
    """Register a new user (aux and pp are read from database)

    Parameters
    ----------
    crs : CRS
        common reference string
    id : int
        user identifier (between 0 and `crs.N`-1, inclusive)
    pk : element of G1
        user's public key
    helping_values : array of elements of G1
        helping values (xi)
    efficient : bool (optional)
        use efficient update variant

    Notes
    -----
    Unlike the syntax in the paper, this returns no pp and aux. Instead, 
    we update them directly in their respective databases. 
    """
    utils.write_pk_to_db(id,pk)

    # block index
    k = floor(id/crs.n)
    # switch `id`s to `id_index`?
    id_index = mod(id,crs.n)

    ### Check consistency of the helping values
    h_parameters = crs.h_parameters_g2
    e = pk.pair(h_parameters[crs.n-1])
    for iteration in range(crs.n-1):
        if helping_values[iteration+1] == None:
            continue
        if h_parameters[iteration] == None:
            continue

        if e != helping_values[iteration+1].pair(h_parameters[iteration]):
            print("Helping values are not consistent!")
            exit(-1)

    ### Update the public parameter
    con_pp = sqlite3.connect('pp.db')
    cur_pp = con_pp.cursor()

    if not efficient:
        # fetch commitment
        cur_pp.execute("SELECT * FROM pp WHERE rowid=?", (k,))
        com_ser = cur_pp.fetchall()
        try:
            com = G1Element.from_binary(com_ser[0][0])
        except:
            com = G1.neutral_element()
        new_com = com * pk
        new_com_ser = G1Element.to_binary(new_com)
        if(utils.insert_or_update(com_ser)):
            cur_pp.execute(" INSERT INTO pp(rowid, commitment) VALUES(?,?)",(k,new_com_ser))
        else:
            cur_pp.execute(" UPDATE pp SET commitment = ? WHERE rowid = ?",(new_com_ser,k))
    else:
        ### Find the last full commitment in C^(k)_1, C^(k)_2, ...., then write to the next index

        # get number of parties in block
        cur_pp.execute('''SELECT num FROM pp_block_count WHERE rowid = ?''',(k,))
        num_parties_in_block = cur_pp.fetchall()
        num_parties_bin = bin(num_parties_in_block[0][0])[2:] # chop off '0b'

        # find index after the last nonempty element
        # equivalent to finding last index of 1 in binary representation of num_parties (first index of 1 in little-endian); then pick next index
        # 10100 --flip--> 00101
        # index of 1: 2
        # reverse index numbering: 5-2-1 = 2
        # add 1 to get the next (empty) spot: 3
        # try:
        #     new_com_index = len(num_parties_bin) - num_parties_bin[::-1].index('1')
        # except:
        #     new_com_index = 0

        new_com_index = 0
        for i in range(len(num_parties_bin)):
            if num_parties_bin[i] == "1":
                new_com_index = new_com_index +1 
        # commit to new pk
        # print("INSERT INTO pp_{} (rowid, commitment) VALUES({},{})".format(new_com_index,k,G1Element.to_binary(pk)))
        # print("registering party ----", id, " --- block is --- ", k, " new com index is ",new_com_index)
        cur_pp.execute("INSERT INTO pp_{} (rowid, commitment) VALUES(?,?)".format(new_com_index),(k,G1Element.to_binary(pk)))

        # Update num ids in block (pp_block_count) for block k
        cur_pp.execute("SELECT * FROM pp_block_count WHERE rowid= ?",(k,))
        block_count = cur_pp.fetchall()
        cur_pp.execute("UPDATE pp_block_count SET num = ? WHERE rowid = ?",(block_count[0][0]+1,k))
        # Set count of ids in the new commitment (pp_com_count) to 1
        cur_pp.execute("UPDATE pp_com_count SET num = ? WHERE rowid = ?",(1,k*crs.n+new_com_index))

        num_parties_last_com = 1
        prev_com_index = max(new_com_index-1,0)
        # print("k is --- " , k, " ---- ",k*crs.n+prev_com_index)
        cur_pp.execute("SELECT * FROM pp_com_count WHERE rowid = ?",(k*(crs.n)+prev_com_index,))
        temp = cur_pp.fetchall()
        num_parties_prev_com = temp[0][0]

    con_pp.commit()
    con_pp.close()
    
    ### Update the auxiliary information
    con_aux = sqlite3.connect("aux.db")
    cur_aux = con_aux.cursor()

    if not efficient:
        # find total number of registered party in k-th portion of the aux database
        con_aux_count = sqlite3.connect('aux_count.db')
        cur_aux_count = con_aux_count.cursor()
        cur_aux_count.execute("SELECT * FROM auxCount WHERE rowid=?", (k,))
        total_count = cur_aux_count.fetchall()
        try:
            num_upd = total_count[0][0]
        except:
            num_upd = 0
        con_aux_count.commit()
        con_aux_count.close()

        # for each helping value
        for i in range(crs.n):
            # index of first update for id i in block k
            j = k * (crs.n ** 2) + (i*crs.n)
            if (id == k * crs.n + i):
                # don't update the registering id's aux info
                continue
            
            # fetch latest update
            try:
                cur_aux.execute("SELECT * FROM aux WHERE rowid=?", (j+num_upd-1,))
                last_upd_ser = cur_aux.fetchall()[0][0]
                last_upd = G1Element.from_binary(last_upd_ser)
                new_aux_index = j+num_upd
            except:
                # fetch second-to-last update only if necessary (last update is empty)
                try:
                    cur_aux.execute("SELECT * FROM aux WHERE rowid=?", (j+num_upd-2,))
                    last_upd_ser = cur_aux.fetchall()[0][0]
                    last_upd = G1Element.from_binary(last_upd_ser)
                    new_aux_index = j+num_upd-1
                except:
                    # if it doesn't exist or is empty
                    last_upd = G1.neutral_element()
                    # new_aux_index = j+num_upd
                    new_aux_index = j

            new_aux_value = G1Element.to_binary(last_upd * helping_values[i])
            cur_aux.execute(" INSERT INTO aux(rowid, upd) VALUES(?,?) ",(new_aux_index,new_aux_value))
        
        con_aux.commit()
        con_aux.close()

        ## add the newly registered party into aux_count database
        con_aux_count = sqlite3.connect('aux_count.db')
        cur_aux_count = con_aux_count.cursor()
        cur_aux_count.execute("SELECT * FROM auxCount WHERE rowid=?", (k,))
        total_count = cur_aux_count.fetchall()
        total_count_num = (total_count[0][0] if (len(total_count) !=  0) else 0)+1
        if(utils.insert_or_update(total_count)):
            cur_aux_count.execute(" INSERT INTO auxCount(rowid, totalCount) VALUES(?,?)",(k,total_count_num))
        else:
            cur_aux_count.execute("UPDATE auxCount SET totalCount = ? WHERE rowid = ?",(total_count_num,k))
        con_aux_count.commit()
        con_aux_count.close()
    
    else: # efficient variant
        for i in range(crs.n):
            j = k * crs.n + i
            new_aux_value = helping_values[i] if j != id else G1.neutral_element()
            # TODO this sometimes results in an error (sqlite3.IntegrityError: UNIQUE constraint failed: aux_{}.rowid), even though there should have been a delete done before inserting. So I added this hacky try/except.
            # print(" INSERT INTO aux_{}(rowid, upd) VALUES({},{}) ".format(new_com_index,j,new_aux_value))
            try:
                cur_aux.execute(" INSERT INTO aux_{}(rowid, upd) VALUES(?,?) ".format(new_com_index),(j,G1Element.to_binary(new_aux_value)))
            except:
                cur_aux.execute(" UPDATE aux_{} SET upd=? WHERE rowid=?".format(new_com_index),(G1Element.to_binary(new_aux_value),j))
            cur_aux.execute("UPDATE aux_reg_count_{} SET num = ? WHERE rowid = ?".format(new_com_index),(1,id))

        con_aux.commit()
        con_aux.close()

        ### merge
        # Check if merge is needed i.e. the last two commitments C^(k)_{last} and C^(k)_{last-1} have same number of parties registered in them (can be checked from pp_com_count)
        if new_com_index > 0 and num_parties_prev_com == num_parties_last_com:
            merge(crs,k,new_com_index)

        # # for debugging
        # con_pp = sqlite3.connect('pp.db')
        # cur_pp = con_pp.cursor()
        # con_aux = sqlite3.connect("aux.db")
        # cur_aux = con_aux.cursor()
        # coms = []
        # decoms = []
        # for i in range(ceil(log2(crs.n))):
        #     # fetch the ith commitment in id's block (block k)
        #     cur_pp.execute('''SELECT commitment FROM pp_{} WHERE rowid = ?'''.format(i),(k,))
        #     try:
        #         com = G1Element.from_binary(cur_pp.fetchall()[0][0])
        #     except:
        #         com = G1.neutral_element()
        #     coms += [com]

        #     aux_i = []
        #     for id_index in range(crs.n):
        #         cur_aux.execute("SELECT * FROM aux_{} WHERE rowid = ?".format(i),(k*crs.n+id_index,))
        #         # cur_aux.execute("SELECT * FROM aux_{} WHERE rowid = ?".format(i),(id,))
        #         try:
        #             decom = G1Element.from_binary(cur_aux.fetchall()[0][0])
        #         except:
        #             decom = G1.neutral_element()
        #         aux_i += [decom]
        #     decoms += [aux_i]

        # # print current status of pp
        # print("current pp:")
        # for com in coms:
        #     print("{}".format(com))
        # # print current status of aux (should be the decoms corr to pp)
        # print("current aux:")
        # for aux_i in decoms:
        #     print("{}".format(aux_i))

        # con_pp.commit()
        # con_pp.close()
        # con_aux.commit()
        # con_aux.close()

def enc(crs, id, m, efficient=False):
    """Encrypt a message to a user (an identity).

    Parameters
    ----------
    crs : CRS
        common reference string
    id : int
        user identifier
    m : element of G1
        message to encrypt
    efficient : bool (optional)
        use efficient update variant

    Returns
    -------
    ct : array of Ciphertexts
        encryption of `m` (length 1 for regular version)
    """
    k = floor(id/crs.n) # block index
    id_index = mod(id,crs.n)
    h_parameters_g2 = crs.h_parameters_g2 
    g2 = crs.g2 

    con = sqlite3.connect("pp.db")
    cur = con.cursor()

    # array with all the commitments to encrypt to
    coms = []
    cts = []
    # # for debugging
    # con_aux = sqlite3.connect("aux.db")
    # cur_aux = con_aux.cursor()
    # decoms = []
    if efficient:
        # for each commitment in block k (this is the dimension coms are merged in)
        for i in range(ceil(log2(crs.n))):
            # fetch the ith commitment in id's block (block k)
            cur.execute('''SELECT commitment FROM pp_{} WHERE rowid = ?'''.format(i),(k,))
            try:
                com = G1Element.from_binary(cur.fetchall()[0][0])
            except:
                com = G1.neutral_element()
            coms += [com]

            # # for debugging
            # cur_aux.execute("SELECT * FROM aux_{} WHERE rowid = ?".format(i),(id,))
            # try:
            #     decom = G1Element.from_binary(cur_aux.fetchall()[0][0])
            # except:
            #     decom = G1.neutral_element()
            # decoms += [decom]
    else:
        # make a single-element array with the commitment
        cur.execute('''SELECT commitment FROM pp WHERE rowid = ?''', (k,))
        coms = [G1Element.from_binary(cur.fetchall()[0][0])]

    # encrypt wrt each commitment
    # for com in coms:
    for i in range(len(coms)):
        com = coms[i]
        # print("ciphertext with com {}".format(coms[i]))
        # print("should be dec with decom {}".format(decoms[i]))
        # print("try dec check...")
        # check = coms[i].pair(crs.h_parameters_g2[crs.n-1-id_index]) == \
        #     decoms[i].pair(crs.g2) * (crs.h_parameters_g1[id_index]**sk).pair( 
        #                         crs.h_parameters_g2[crs.n-1-id_index])
        # print(check)

        r = G2.order().random()

        ct0 = com
        ct1 = com.pair(h_parameters_g2[crs.n-1-id_index])**r
        ct2 = g2 **r
        e = crs.h_parameters_g1[id_index].pair(h_parameters_g2[crs.n-1-id_index]) ** r
        ct3 = e*m
        ct = Ciphertext(ct0,ct1,ct2,ct3)

        cts += [ct]

    return cts

# def get_update_num(block_num):
#     """Get number of most recent update.

#     Parameters
#     ----------
#     block_num : int
#         block number containing the `id`
    
#     Returns
#     -------
#     int
#         update number
#     """
#     con = sqlite3.connect('aux_count.db')
#     cur = con.cursor()
#     cur.execute("SELECT totalCount FROM auxCount WHERE auxPart=?",(block_num,))
#     upd_num = cur.fetchall()[0][0]
#     con.commit()
#     con.close()
#     return max(upd_num-2,0)

def upd(crs, id, efficient=False):
    """Get updating information for a user.

    Parameters
    ----------
    crs : CRS
        common reference string
    id : int
        recipient identifier
    efficient : bool (optional)
        use efficient update variant
    
    Returns
    -------
    array of G1 elements
        updating information (list of decommitments)
    """

    k = floor(id/crs.n) # block index
    id_index = mod(id,crs.n)

    if efficient:
        t = ceil(log2(crs.n))
        upds = [G1.neutral_element()]*(2*t)

        con = sqlite3.connect("aux.db")
        cur = con.cursor()

        for i in range(t):
            cur.execute("SELECT * FROM L WHERE rowid=?",(i*crs.N + k*crs.n + id_index,))
            upd_fetched = cur.fetchall()
            upds[i] = G1Element.from_binary(upd_fetched[0][0]) if len(upd_fetched) != 0 else G1.neutral_element()
        for i in range(t):
            cur.execute("SELECT * FROM aux_{} WHERE rowid = ?".format(i),(id,))
            upd_fetched = cur.fetchall()
            upds[t+i] = G1Element.from_binary(upd_fetched[0][0]) if len(upd_fetched) != 0 else G1.neutral_element()
        con.commit()
        con.close()
    else:
        upds = [G1.neutral_element()]

        # fetch number of updates in block
        con_aux_count = sqlite3.connect('aux_count.db')
        cur_aux_count = con_aux_count.cursor()
        cur_aux_count.execute("SELECT * FROM auxCount WHERE rowid=?", (k,))
        try:
            count = cur_aux_count.fetchall()[0][0]
        except:
            count = 0
        con_aux_count.commit()
        con_aux_count.close()

        con = sqlite3.connect("aux.db")
        cur = con.cursor()
        # index of first update for id in the block (k)
        id_updates_index = int(k * (crs.n**2) + crs.n*id_index)

        # fetch all the updates for id (there are at most `count` of them)
        cur.execute("SELECT * FROM aux WHERE rowid BETWEEN ? and ?", (id_updates_index, id_updates_index+(count-1))) # both ends are inclusive
        resp = cur.fetchall()
        upds = [G1.neutral_element()] * len(resp)
        for i in range(len(resp)):
            try:
                upds[i] = G1Element.from_binary(resp[i][0])
            except:
                pass
        upds = [G1.neutral_element()] + upds

        con.commit()
        con.close()

    return upds

def dec(crs, id, sk, upds, cts, upd_idx=-1):
    """Decrypt a ciphertext encrypted to a particular user.

    Parameters
    ----------
    crs : CRS
        common reference string
    id : int
        user identifier
    sk : element of ZR
        secret key
    upds : array of G1 elements
        updating information (decommitments)
    cts : array of Ciphertexts
        ciphertext to decrypt
    upd_idx : int (optional)
        exact update index, if known, to use for decryption

    Returns
    -------
    element of GT
        a message or a special symbol GetUpd (`0`) indicating updating information is required
    """
    m = None
    if upd_idx >= 0:
        upds = [upds[upd_idx]]

    id_index = mod(id,crs.n)
    for ct in cts:
        for u in upds:
            if ct.ct0.pair(crs.h_parameters_g2[crs.n-1-id_index]) == \
                u.pair(crs.g2) * (crs.h_parameters_g1[id_index]**sk).pair( 
                                    crs.h_parameters_g2[crs.n-1-id_index]):

                # print("found successful update at index {}".format(i))
                m = ct.ct3/((u.pair(ct.ct2)**(-1)*(ct.ct1))**(sk.mod_pow(-1,GT.order())))
        
    if m!= None:
        return m

    # if none of them work, ciphertext is not well-formed or update is necessary
    print("Decryption cannot be done, you need to get update first.")
    return 0

# row refers to the row of pp and column refers to the column of pp
# TODO save space by not saving single-element decommitments
def merge(crs,k,last_index):
    """
    Parameters
    ----------
    crs : CRS
        common reference string
    k : int 
        pp/aux block of id, ranges from 0 to `crs.n`-1
    last_index : int
        last non-empty index of the `k`th block of pp (index after newest commitment)
    """
    # base case for the recursive merge
    if last_index == 0:
        return 0
    
    ### First, check if a merge is needed -- i.e. if the last two commitments C^(k)_{last} and C^(k)_{last-1} have same number of parties registered in them
    
    # connect to pp database
    con_pp = sqlite3.connect("pp.db")
    cur_pp = con_pp.cursor()

    # indices of the last two non-empty elements of C^(k)
    cur_pp.execute("SELECT * FROM pp_com_count WHERE rowid = ?", (k*crs.n+last_index,))
    num_parties_last_com = cur_pp.fetchall()[0][0]
    cur_pp.execute("SELECT * FROM pp_com_count WHERE rowid = ?", (k*crs.n+last_index-1,))
    num_parties_prev_com = cur_pp.fetchall()[0][0]

    if num_parties_last_com != num_parties_prev_com:
        # print("merge ended!")
        con_pp.commit()
        con_pp.close()
        return 0

    ### A merge is needed, so fetch from pp the commitments to merge...
    cur_pp.execute("SELECT commitment from pp_{} WHERE rowid = ?".format(last_index),(k,))
    last_com_ser = cur_pp.fetchall()[0][0]
    cur_pp.execute("SELECT commitment from pp_{} WHERE rowid = ?".format(last_index-1),(k,))
    prev_com_ser = cur_pp.fetchall()[0][0]

    # ...and merge them
    merged_com = G1Element.to_binary(G1Element.from_binary(last_com_ser)*G1Element.from_binary(prev_com_ser))
    cur_pp.execute("UPDATE pp_{} SET commitment = ? WHERE rowid = ?".format(last_index-1),(merged_com,k))
    # print("DELETE FROM pp_{} WHERE rowid = {}".format(last_index,k))
    cur_pp.execute("DELETE FROM pp_{} WHERE rowid = ?".format(last_index),(k,))

    # update pp_com_count after merge; notice that pp_block_count will remain unchanged (was updated in reg)
    cur_pp.execute("UPDATE pp_com_count SET num = ? WHERE rowid = ?",(num_parties_last_com+num_parties_prev_com, (k*crs.n+last_index-1)))
    cur_pp.execute("UPDATE pp_com_count SET num = ? WHERE rowid = ?",(0, (k*crs.n+last_index)))
    con_pp.commit()
    con_pp.close()

    ### merge aux info
    con_aux = sqlite3.connect("aux.db")
    cur_aux = con_aux.cursor()
    # fetch elements of last aux at block k
    block_k_idxs = [k*crs.n, k*crs.n + (crs.n-1)]
    cur_aux.execute("SELECT * FROM aux_{} WHERE rowid BETWEEN ? AND ?".format(last_index),(block_k_idxs[0],block_k_idxs[1]))
    last_aux_ser = cur_aux.fetchall()
    last_aux = [None]*crs.n
    for i in range(crs.n):
        val = last_aux_ser[i][0]
        if len(val) == 0:
            last_aux[i] = G1.neutral_element()
        else:
            last_aux[i] = G1Element.from_binary(val)

    # fetch elements of previous aux at block k
    cur_aux.execute("SELECT * FROM aux_{} WHERE rowid BETWEEN ? AND ?".format(last_index-1),(block_k_idxs[0], block_k_idxs[1]))
    prev_aux_ser = cur_aux.fetchall()
    prev_aux = [None]*crs.n
    for i in range(crs.n):
        val = prev_aux_ser[i][0]
        if len(val) == 0:
            prev_aux[i] = G1.neutral_element()
        else:
            prev_aux[i] = G1Element.from_binary(val)

        # print("DELETE FROM aux_{} WHERE rowid = {}".format(last_index, k*crs.n+i))

        # what index would this upd be inserted at in L_i?
        cur_aux.execute("SELECT * FROM L_upd_num WHERE rowid = ?",(k*crs.n+i,))
        L_upd_num_fetched = cur_aux.fetchall()
        L_upd_num = L_upd_num_fetched[0][0] if len(L_upd_num_fetched) != 0 else 0

        # is i in this aux block?
        cur_aux.execute("SELECT * FROM aux_reg_count_{} WHERE rowid = ? ".format(last_index-1),(k*crs.n+i,))
        p_fetched = cur_aux.fetchall()
        p = p_fetched[0][0] if len(p_fetched) != 0 else 0
        # if so, append its upd to L_i
        if(p==1):
            cur_aux.execute("INSERT INTO L(rowid,upd) VALUES(?,?)",(L_upd_num*crs.N + crs.n*k+i ,G1Element.to_binary(prev_aux[i])))
            cur_aux.execute("UPDATE L_upd_num SET upd = ? WHERE rowid = ?",(L_upd_num+1,crs.n*k+i))

        cur_aux.execute("SELECT * FROM aux_reg_count_{} WHERE rowid = ? ".format(last_index),(k*crs.n+i,))
        q_fetched = cur_aux.fetchall()
        q = q_fetched[0][0] if len(q_fetched) != 0 else 0
        porq = p | q

        # merge the prev and last aux info at this index
        # (append elements of last into prev; only for the final element, we multiply: last[2*final] := last[final]*prev[final])
        cur_aux.execute("UPDATE aux_{} SET upd = ? WHERE rowid = ?".format(last_index-1),(G1Element.to_binary(prev_aux[i]*last_aux[i]),k*crs.n+i))

        cur_aux.execute("UPDATE aux_reg_count_{} SET num=? WHERE rowid = ?".format(last_index-1),(porq,k*crs.n+i))
        cur_aux.execute("UPDATE aux_reg_count_{} SET num=? WHERE rowid = ?".format(last_index),(0,k*crs.n+i))
        cur_aux.execute("DELETE FROM aux_{} WHERE rowid = ?".format(last_index), (k*crs.n+i,))

    con_aux.commit()
    con_aux.close()

    return merge(crs,k,last_index-1)
