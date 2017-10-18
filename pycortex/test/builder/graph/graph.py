from io import BytesIO
import attr
from pycortex.test.builder.graph.body import as_edge_set, KmerRecord, Body
from pycortex.test.builder.graph.header import Header
from Bio.Seq import Seq


@attr.s
class Graph(object):
    header = attr.ib(attr.Factory(Header))
    body = attr.ib(attr.Factory(Body))
    kmer_size_is_set = attr.ib(False, init=False)

    def __attrs_post_init__(self):
        self.header.num_colors = 1
        self.body.sort_kmers = True

    def without_sorted_kmers(self):
        self.body.sort_kmers = False
        return self

    def with_kmer_size(self, size):
        self.kmer_size_is_set = True
        self.body.kmer_size = size
        self.header.kmer_size = size
        return self

    def with_kmer(self, kmer_string, colors=0, edges='........'):
        revcomp = str(Seq(kmer_string).reverse_complement())
        if revcomp < kmer_string:
            raise Exception("kmer_string is not lexlow.  Please fix.")
        if isinstance(edges, str):
            edges = [edges]
        if isinstance(colors, int):
            colors = [colors]
        return self.with_kmer_record(
            KmerRecord(kmer_string, colors, tuple([as_edge_set(e) for e in edges])))

    def with_kmer_record(self, record):
        assert len(record.coverage) == self.header.num_colors
        assert len(record.edges) == len(record.coverage)
        self.body.with_kmer_record(record)
        return self

    def with_num_colors(self, n_colors):
        assert n_colors > 0
        self.header.with_num_colors(n_colors)
        return self

    def build(self):
        if not self.kmer_size_is_set:
            self.with_kmer_size(1)
        self.header.with_kmer_container_size(self.body.kmer_container_size)
        return BytesIO(self.header.build().getvalue() + self.body.build().getvalue())
