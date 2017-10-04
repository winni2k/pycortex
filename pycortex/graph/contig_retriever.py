import attr

from pycortex.graph import parser as parser


@attr.s(slots=True)
class ContigRetriever(object):
    fh = attr.ib()

    def get_kmers_for_contig(self, contig):
        graph_parser = parser.RandomAccess(self.fh)
        kmer_size = graph_parser.header.kmer_size
        assert len(contig) >= kmer_size
        kmers = []
        for kmer_start in range(len(contig) - kmer_size + 1):
            kmer_string = contig[kmer_start:(kmer_start + kmer_size)]
            try:
                kmer = graph_parser.get_kmer_for_string(kmer_string)
            except parser.RandomAccessError:
                kmer = None
            kmers.append((kmer, kmer_string))
        return kmers

    def get_kmers(self):
        graph_parser = parser.Streaming(self.fh)
        return graph_parser.kmers()
