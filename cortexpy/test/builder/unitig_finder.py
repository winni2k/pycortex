import attr

from cortexpy.graph import Interactor
from cortexpy.graph.serializer.unitig import UnitigFinder
from cortexpy.test.builder.graph import colored_de_bruijn


@attr.s(slots=True)
class UnitigFinderBuilder(object):
    builder = attr.ib(attr.Factory(colored_de_bruijn.ColoredDeBruijnGraphBuilder))
    test_coverage = attr.ib(True)
    seed_kmers = attr.ib(None)

    def __attrs_post_init__(self):
        self.builder.with_colors(0)

    @property
    def graph(self):
        return self.builder

    def without_test_coverage(self):
        self.test_coverage = False
        return self

    def with_colors(self, *colors):
        self.builder.with_colors(*colors)
        return self

    def with_seeds(self, *seeds):
        self.seed_kmers = set(seeds)

    def build(self):
        graph = self.builder.build()
        if self.seed_kmers is None:
            self.seed_kmers = [next(iter(graph))]
        graph = Interactor(
            graph,
            colors=self.builder.colors
        ).make_graph_nodes_consistent(self.seed_kmers).graph
        return UnitigFinder(graph, colors=list(self.builder.colors),
                            test_coverage=self.test_coverage)
