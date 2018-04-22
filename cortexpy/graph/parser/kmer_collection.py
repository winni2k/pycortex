from itertools import chain

import attr
import numpy as np

from cortexpy.graph.parser.kmer import KmerData


@attr.s(slots=True, cmp=False, frozen=True)
class KmerDataCollection(object):
    _kmers_data = attr.ib()
    num_colors = attr.ib(init=False)
    _coverage = attr.ib(None)
    _edges = attr.ib(None)
    raw_kmer = attr.ib(None)

    def __attrs_post_init__(self):
        assert len(self._kmers_data) > 0
        first = self._kmers_data[0]
        assert all((first.kmer == k.kmer for k in self._kmers_data))
        assert all((first.kmer_size == k.kmer_size for k in self._kmers_data))

        object.__setattr__(self, "num_colors", sum((k.num_colors for k in self._kmers_data)))

    @property
    def kmer(self):
        return self._kmers_data[0].kmer

    @property
    def kmer_size(self):
        return self._kmers_data[0].kmer_size

    @property
    def coverage(self):
        if self._coverage is None:
            object.__setattr__(self, "_coverage",
                               np.concatenate([k.coverage for k in self._kmers_data]))
        return self._coverage

    @property
    def edges(self):
        if self._edges is None:
            object.__setattr__(self, "_edges",
                               list(chain.from_iterable(k.edges for k in self._kmers_data)))
        return self._edges

    def get_raw_kmer(self):
        for kmer in self._kmers_data:
            try:
                return kmer.get_raw_kmer()
            except AttributeError:
                pass
        raise ValueError('At least one kmer should have a raw kmer')
