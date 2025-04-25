# Efficient RBE

Implementation and benchmarking of our paper[^GKMR] describing the first efficient construction of registration-based encryption (RBE).

**THIS IS A PROTOTYPE IMPLEMENTATION, DO NOT USE IN PRODUCTION.**

[^GKMR]: N. Glaeser, D. Kolonelos, G. Malavolta, A. Rahimi. Efficient Registration-Based Encryption. Cryptology ePrint Archive paper [2022/1505](https://eprint.iacr.org/2022/1505).

## Dependencies

We use [petrelic](https://github.com/spring-epfl/petrelic), a Python wrapper around [RELIC](https://github.com/relic-toolkit/relic), to implement the scheme. For installation (Linux only) simply run `pip install petrelic` (full details [here](https://petrelic.readthedocs.io/en/latest/install.html)).

## Setup

Our RBE construction is implemented as a package in the [rbe](rbe/) directory. We use the BLS12-381 elliptic curve with asymmetric pairings. Add the package to your path in order to use it:

```
# in the root directory (efficientRBE)
export PYTHONPATH=$(pwd)/rbe:$PYTHONPATH
```

### Documentation

Generate documentation for `rbe` with [pdoc](https://pdoc.dev/):
```
cd rbe
rm -r docs # may not be necessary
pdoc -o docs -d numpy rbe
```
This creates HTML files with the documentation in the `rbe/docs` directory.

Note that the docstrings are written using the [numpy format](https://numpydoc.readthedocs.io/en/latest/format.html) (general tips [here](https://realpython.com/documenting-python-code/#docstring-formats)).

## Usage

Benchmarks for algorithm runtimes can be taken via `bench/bench.sh` or for individual settings of N and scheme variant (base or efficient) with
```
python3 bench/bench.py [-h] [-N max_parties] [-i iters] [-e]
```

The parameter sizes (of `aux` and `pp`; `crs` size is printed with the benchmarks) for a full system, where all N parties are registered for N = 10k...10M, can be obtained with
```
python3 bench/param_sizes.py
```

The time per operation (group exponentiation, pairing, (de)serialization) and group element bytesizes can be benchmarked with
```
python3 bench-ops/ops-petrelic.py
```
