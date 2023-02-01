"""Efficient construction of registration-based encryption (RBE), based on 
[GKMR].

Notes
-----
We often make reference to "the paper", by which we mean the paper describing
our efficient RBE construction [GKMR]. We try to use the same 
notation in variable names and comments in the code as we do in the description 
of the construction in the paper, and note any differences when applicable.

References
----------
[GKMR] N. Glaeser, D. Kolonelos, G. Malavolta, A. Rahimi. Efficient 
Registration-Based Encryption. Cryptology ePrint Archive paper [2022/1505](https://eprint.iacr.org/2022/1505).

Examples
--------
Set up CRS, public parameters, and auxiliary information for maximum 100 users:

>>> from algos import setup
>>> crs = setup(100, efficient=False)

Generate keys for user 42:

>>> from algos import gen
>>> pk,sk,xi = gen(crs, 42)

Register user 42:

>>> from algos import reg
>>> reg(crs, 42, pk, xi, efficient=False)

Encrypt a random message to user 42:

>>> from algos import enc
>>> m = crs.group.random(GT)
>>> c = enc(crs, 42, m, efficient=False)

User 42 decrypts the message (gets any updates first):

>>> from algos import upd, dec
>>> upds = upd(crs, 42, efficient=False)
>>> m_prime = dec(crs, 42, sk, upds, c)

The efficient variant of our construction can be run by setting `efficient` to `True` in the above.
"""
