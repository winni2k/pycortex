from pycortex.graph.contig_retriever import ContigRetriever
from pycortex.graph.parser.constants import NUM_TO_LETTER
from pycortex.utils import revcomp


def edge_set_as_string(edge_set, is_revcomp=False):
    letters = []

    if is_revcomp:
        num_to_letter = list(reversed(NUM_TO_LETTER))
    else:
        num_to_letter = NUM_TO_LETTER

    for idx, edge in enumerate(edge_set):
        letter = num_to_letter[idx % 4]
        if idx < 4:
            letter = letter.lower()
        if edge:
            letters.append(letter)
        else:
            letters.append('.')

    if is_revcomp:
        incoming, outgoing = letters[:4], letters[4:]
        incoming, outgoing = list(reversed(incoming)), list(reversed(outgoing))
        letters = outgoing + incoming

    return ''.join(letters)


def cortex_kmer_as_cortex_jdk_print_string(kmer, alt_kmer_string=None):
    if kmer is None:
        revcomp_kmer = revcomp(alt_kmer_string)
        if revcomp_kmer > alt_kmer_string:
            revcomp_kmer = alt_kmer_string
        return '{}: {} missing'.format(revcomp_kmer, alt_kmer_string)
    if alt_kmer_string is not None and kmer.kmer != alt_kmer_string:
        is_revcomp = True
    else:
        is_revcomp = False

    edge_set_strings = [edge_set_as_string(edge_set, is_revcomp=is_revcomp) for edge_set in
                        kmer.edges]
    to_print = [str(kmer.kmer)]
    if alt_kmer_string is not None:
        to_print.append(': ' + alt_kmer_string)
    to_print.append(' ' + ' '.join(map(str, kmer.coverage)))
    to_print.append(' ' + ' '.join(edge_set_strings))
    return ''.join(to_print)


def print_contig(args):
    with open(args.graph, 'rb') as fh:
        contig_retriever = ContigRetriever(fh=fh)
        if args.record:
            contig_kmers = contig_retriever.get_kmers_for_contig(args.record)
            if len(contig_kmers) == 1:
                print(cortex_kmer_as_cortex_jdk_print_string(contig_kmers[0][0]))
            else:
                for kmer, kmer_string in contig_kmers:
                    print(cortex_kmer_as_cortex_jdk_print_string(kmer, alt_kmer_string=kmer_string))
        else:
            for kmer in contig_retriever.get_kmers():
                print(cortex_kmer_as_cortex_jdk_print_string(kmer))
