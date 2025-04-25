#!/usr/bin/env python3

"""Objects to represent RBE ciphertexts and CRS.
"""

from math import ceil,sqrt,log2
from petrelic.multiplicative.pairing import G1,G2,GT,G1Element,G2Element
from petrelic.bn import Bn
from rbe import utils
import sqlite3

class Ciphertext:
    """RBE ciphertext

    Parameters
    ----------
    ct0 : element of G1
        first element of the ciphertext tuple
    ct2 : element of G2
        third element of the ciphertext tuple
    ct1, ct3 : elements of GT
        second and fourth elements of the ciphertext tuple
    """
    def __init__(self,ct0,ct1,ct2,ct3):
        """Construct ciphertext object from tuple of elements."""
        self.ct0 = ct0
        self.ct1 = ct1
        self.ct2 = ct2
        self.ct3 = ct3

    def get_size(self):
        """Calculate the size (in bytes) of the ciphertext."""
        ct_size = 0
        ct_size = ct_size + len(self.group.serialize(self.ct0))
        ct_size = ct_size + len(self.group.serialize(self.ct1))
        ct_size = ct_size + len(self.group.serialize(self.ct2))
        ct_size = ct_size + len(self.group.serialize(self.ct3))
        return ct_size

class CRS:
    """Common Reference String over the BLS12-381 curve (asymmetric pairing).

    Dependencies
    ------------
    * petrelic
    * math.ceil
    * math.sqrt

    Attributes
    ----------
    g1 : element of G1
        generator of G1
    g2 : element of G2
        generator of G2
    N : int
        maximum number of users
    n : int
        block size, `sqrt(N)`
    log_n : int
        `log2(n)`
    B: int
        number of blocks (`N/n`)
    h_parameters_g1 : array of elements of G1
        `h[i] = g1**{z**i}`, where i ranges from 1 to 2`n`, inclusive
    h_parameters_g2 : array of elements of G2
        `h[i] = g2**{z**i}` where i ranges from 1 to 2`n`, inclusive
    """


    def __init__(self,N=None,g1=None,g2=None,z=None):
        """
        Generate a CRS over BLS12-381 using the given parameters.
        
        If all parameters are set to `None`, try to read a CRS from file "crs". If `g1`, `g2`, or `z` are given as None, choose them at random.

        Parameters
        ----------
        N : int, optional
            maximum number of users
        g1 : element of G1, optional
            generator of G1
        g2 : element of G2, optional
            generator of G2
        z : element of ZR, optional
            CRS trapdoor in ZR (if `None`, `z` is chosen at random)

        See Also
        --------
        CRS : for descriptions of the other parameters
        """

        if N is None:
            try:
                print("loading from file")
                self.load_from_file()
            except Exception as e:
                print("Error loading CRS from file: ",e)
        else:
            self.N = N
            self.n = ceil(sqrt(N))
            self.log_n = ceil(log2(self.n))
            self.B = ceil(N/self.n)
            self.g1 = G1.generator() if g1 is None else g1
            self.g2 = G2.generator() if g2 is None else g2

            # initialise h_i
            z = G1.order().random() if z is None else z
            h_values_crs1 = [None] * (2*self.n)
            h_values_crs2 = [None] * (2*self.n)
            for i in range(2*self.n):
                if i == (self.n): # h_n := \empty
                    continue
                h_values_crs1[i] = self.g1 ** (z.mod_pow(i+1,G1.order()))
                h_values_crs2[i] = self.g2 ** (z.mod_pow(i+1,G2.order()))
            self.h_parameters_g1 = h_values_crs1
            self.h_parameters_g2 = h_values_crs2
            self.save_to_file()
    
    def save_to_file(self):
        """Save CRS to database.
        """

        keys_db_exists = utils.exists("crs.db")
        con = sqlite3.connect('crs.db')
        cur = con.cursor()
        if not keys_db_exists:
            cur.execute('''CREATE TABLE crs(pk BLOB)''')
        cur.execute("INSERT INTO crs(rowid, pk) VALUES(?,?)",(0,self.N))
        cur.execute("INSERT INTO crs(rowid, pk) VALUES(?,?)",(1,self.g1.to_binary()))
        cur.execute("INSERT INTO crs(rowid, pk) VALUES(?,?)",(2,self.g2.to_binary()))
        for i in range(2*self.n):
            if (i == self.n):
                cur.execute("INSERT INTO crs(rowid, pk) VALUES(?,?)",(2*i+3,"empty"))
                continue
            cur.execute("INSERT INTO crs(rowid, pk) VALUES(?,?)",(2*i+3,self.h_parameters_g1[i].to_binary()))
            cur.execute("INSERT INTO crs(rowid, pk) VALUES(?,?)",(2*i+4,self.h_parameters_g2[i].to_binary()))

        con.commit()
        con.close()

    def load_from_file(self):
        """Load CRS from database.
        """

        con = sqlite3.connect("crs.db")
        cur = con.cursor()

        cur.execute("SELECT * FROM crs WHERE rowid=?", (0,))
        self.N = cur.fetchall()[0][0]
        self.n = int(ceil(sqrt(self.N)))
        self.log_n = int(ceil(log2(self.n)))
        self.B = ceil(self.N/self.n)
        cur.execute("SELECT * FROM crs WHERE rowid=?", (1,))
        self.g1 = G1Element.from_binary(cur.fetchall()[0][0])
        cur.execute("SELECT * FROM crs WHERE rowid=?", (2,))
        self.g2 = G2Element.from_binary(cur.fetchall()[0][0])
        h1 = [None]*(2*self.n)
        h2 = [None]*(2*self.n)
        for i in range(2*self.n):
            if i == self.n:
                h1[i] = None
                h2[i] = None
                continue
            cur.execute("SELECT * FROM crs WHERE rowid=?", (2*i+3,))
            h1[i] = G1Element.from_binary(cur.fetchall()[0][0])
            cur.execute("SELECT * FROM crs WHERE rowid=?", (2*i+4,))
            h2[i] = G2Element.from_binary(cur.fetchall()[0][0])
        self.h_parameters_g1 = h1
        self.h_parameters_g2 = h2
        con.commit()
        con.close()