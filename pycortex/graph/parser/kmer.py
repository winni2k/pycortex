from struct import unpack
import attr
import numpy as np

import pycortex.edge_set
from pycortex.edge_set import EdgeSet
from pycortex.graph.parser.constants import NUM_TO_LETTER, UINT64_T, UINT32_T
from pycortex.utils import revcomp


@attr.s(slots=True)
class EmptyKmerBuilder(object):
    num_colors = attr.ib(0)
    _seen_kmers = attr.ib(attr.Factory(dict))

    @num_colors.validator
    def not_less_than_zero(self, attribute, value):  # noqa
        if value < 0:
            raise ValueError('value less than zero')

    def build_or_get(self, kmer_string):
        if len(kmer_string) % 2 == 0:
            raise ValueError('kmer_string needs to be odd length')
        if len(kmer_string) < 3:
            raise ValueError('kmer_string needs to length 3 or more')
        kmer_string_to_use = revcomp(kmer_string)
        if kmer_string < kmer_string_to_use:
            kmer_string_to_use = kmer_string

        if kmer_string_to_use in self._seen_kmers:
            return self._seen_kmers[kmer_string_to_use]
        self._seen_kmers[kmer_string_to_use] = EmptyKmer(kmer=kmer_string_to_use,
                                                         coverage=np.zeros(self.num_colors,
                                                                           dtype=np.uint8),
                                                         kmer_size=len(kmer_string_to_use),
                                                         num_colors=self.num_colors)
        return self._seen_kmers[kmer_string_to_use]


def flip_kmer_string_to_match(flip, ref, flip_is_after_reference_kmer=True):
    flip_revcomp = revcomp(flip)
    if flip_is_after_reference_kmer:
        ref_core = ref[1:]
        flip_core = flip[:-1]
        flip_revcomp_core = flip_revcomp[:-1]
    else:
        ref_core = ref[:-1]
        flip_core = flip[1:]
        flip_revcomp_core = flip_revcomp[1:]

    if ref_core == flip_core:
        return flip, False
    elif ref_core == flip_revcomp_core:
        return flip_revcomp, True
    else:
        raise ValueError


def connect_kmers(first, second, color):
    if first == second and first is not second:
        raise ValueError('Kmers are equal, but not the same object')
    connection_is_set = False
    for flip_is_after_reference_kmer in [True, False]:
        for reverse_first_second in [True, False]:
            if reverse_first_second:
                flip_kmer, ref_kmer = second, first
            else:
                flip_kmer, ref_kmer = first, second
            try:
                flipped_string, is_flipped = flip_kmer_string_to_match(
                    flip_kmer.kmer, ref_kmer.kmer,
                    flip_is_after_reference_kmer=flip_is_after_reference_kmer
                )
            except ValueError:
                pass
            else:
                connection_is_set = True
                if flip_is_after_reference_kmer:
                    ref_letter = flipped_string[-1]
                    flip_letter = ref_kmer.kmer[0].lower()
                else:
                    ref_letter = flipped_string[0].lower()
                    flip_letter = ref_kmer.kmer[-1]

                if is_flipped:
                    flip_letter = revcomp(flip_letter).swapcase()
                ref_kmer.edges[color].add_edge(ref_letter)
                flip_kmer.edges[color].add_edge(flip_letter)

    if not connection_is_set:
        raise ValueError(
            'first kmer ({}) cannot be connected to second kmer ({})'.format(first.kmer,
                                                                             second.kmer)
        )


def kmer_eq(self, other):
    if self.kmer != other.kmer:
        return False
    if self.kmer_size != other.kmer_size:
        return False
    if self.num_colors != other.num_colors:
        return False
    if not np.all(self.coverage == other.coverage):
        return False
    if (self.edges is None) != (other.edges is None):
        return False
    if self.edges is not None and not np.all(self.edges == other.edges):
        return False
    return True


@attr.s(slots=True, cmp=False)
class EmptyKmer(object):
    kmer = attr.ib()
    coverage = attr.ib()
    kmer_size = attr.ib()
    num_colors = attr.ib()
    edges = attr.ib(None)

    def __attrs_post_init__(self):
        if self.edges is None:
            self.edges = [pycortex.edge_set.empty() for _ in range(len(self.coverage))]

    def append_color(self, coverage=0, edge_set=None):
        if edge_set is None:
            edge_set = pycortex.edge_set.empty()

        coverage_array = np.resize(self.coverage, len(self.coverage) + 1)
        coverage_array[-1] = coverage
        self.coverage = coverage_array

        self.edges.append(edge_set)
        self.num_colors += 1

    def __eq__(self, other):
        return kmer_eq(self, other)


@attr.s(slots=True, cmp=False)
class Kmer(object):
    _raw_data = attr.ib()
    kmer_size = attr.ib()
    num_colors = attr.ib()
    kmer_container_size_in_uint64ts = attr.ib(1)
    _kmer = attr.ib(None)
    _coverage = attr.ib(None)
    _edges = attr.ib(None)
    _incoming_kmers = attr.ib(None)
    _outgoing_kmers = attr.ib(None)
    _kmer_vals_to_delete = attr.ib(init=False)

    def __attrs_post_init__(self):
        n_vals_left_over = self.kmer_size % 4
        n_vals_to_remove = 4 - n_vals_left_over
        if n_vals_to_remove > 0:
            self._kmer_vals_to_delete = (
                np.arange(0, n_vals_to_remove) + self.kmer_size - n_vals_left_over
            )

    @property
    def kmer(self):
        if self._kmer is None:
            kmer_as_uint64ts = np.frombuffer(
                self._raw_data[:self.kmer_container_size_in_uint64ts * 8],
                dtype='<u8')
            big_endian_kmer = kmer_as_uint64ts.byteswap().newbyteorder()  # change to big endian
            kmer_as_bits = np.unpackbits(
                np.frombuffer(big_endian_kmer.tobytes(), dtype=np.uint8)
            )
            kmer = (
                kmer_as_bits.reshape(-1, 2) * np.array([2, 1])
            ).sum(1)
            self._kmer = ''.join(NUM_TO_LETTER[num] for num in kmer[(len(kmer) - self.kmer_size):])
        return self._kmer

    @property
    def coverage(self):
        if self._coverage is None:
            start = self.kmer_container_size_in_uint64ts * UINT64_T
            coverage_raw = self._raw_data[start:(start + self.num_colors * UINT32_T)]
            fmt_string = ''.join(['I' for _ in range(self.num_colors)])
            self._coverage = np.array(unpack(fmt_string, coverage_raw), dtype=np.uint32)
        return self._coverage

    @coverage.setter
    def coverage(self, val):
        self._coverage = val

    @property
    def edges(self):
        if self._edges is None:
            start = (
                self.kmer_container_size_in_uint64ts * UINT64_T + self.num_colors * UINT32_T
            )
            edge_bytes = list(self._raw_data[start:])
            edge_sets = np.unpackbits(np.array(edge_bytes, dtype=np.uint8)).reshape(-1, 4)
            edge_sets[1::2] = np.fliplr(edge_sets[1::2])
            self._edges = list(map(EdgeSet, edge_sets.reshape(-1, 8)))
        return self._edges

    def append_color(self, coverage=0, edge_set=None):
        if edge_set is None:
            edge_set = pycortex.edge_set.empty()

        coverage_array = np.resize(self.coverage, len(self.coverage) + 1)
        coverage_array[-1] = coverage
        self.coverage = coverage_array

        self.edges.append(edge_set)
        self.num_colors += 1

    def __eq__(self, other):
        return kmer_eq(self, other)


class KmerByStringComparator(object):
    def __init__(self, *, kmer=None, kmer_object=None):
        self.kmer = kmer
        self.kmer_object = kmer_object
        if self.kmer is None:
            self.kmer = self.kmer_object.kmer

    def __eq__(self, other):
        return self.kmer == other.kmer

    def __lt__(self, other):
        return self.kmer < other.kmer

    def __repr__(self):
        return self.kmer
