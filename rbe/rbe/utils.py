"""Helper utility functions, mostly for interacting with databases.
"""

import time
import sqlite3
from os.path import exists
from rbe import objects
from petrelic.multiplicative.pairing import G1,G2,GT,G1Element,G2Element

def write_pk_to_db(id,pk):
    """Write public key to the key database.

    Parameters
    ----------
    id : int
        identity whose public key we are storing
    pk : element of G1
        public key to store
    """
    keys_db_exists = exists("keys.db")
    con = sqlite3.connect('keys.db')
    cur = con.cursor()

    if not keys_db_exists:
        cur.execute('''CREATE TABLE key_pairs(id INTEGER, pk BLOB)''')

    write_pk_db_time = time.time()
    cur.execute("INSERT INTO key_pairs (id, pk) VALUES(?, ?)",(id,G1Element.to_binary(pk)))
    write_pk_db_time = time.time()-write_pk_db_time

    con.commit()
    con.close()

# def load_sk_from_db(crs,id):
#     """Fetch a user's secret key from the database.
    
#     Parameters
#     ----------
#     crs : CRS
#         common reference string
#     id : int
#         user whose secret key is being requested

#     Returns
#     -------
#     sk : an element of ZR
#         `id`'s secret key
#     """
#     con = sqlite3.connect('keys.db')
#     cur = con.cursor()
    
#     cur.execute("SELECT * FROM key_pairs WHERE id=?", (id,))
#     sk_ser = cur.fetchall()
#     # sk = crs.group.deserialize(sk_ser[0][2])
#     con.commit()
#     con.close()
#     return sk

def insert_or_update(inp):
    """For regular (not efficient update) variant, determine whether to append or update a commitment into pp.

    Returns
    -------
    bool
        `True` for insert, `False` for update
    """
    return len(inp) == 0
