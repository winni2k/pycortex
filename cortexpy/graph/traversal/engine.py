from enum import Enum

import attr
import collections
import networkx as nx

from .branch import Branch
from cortexpy.graph.serializer import SERIALIZER_GRAPH, EdgeTraversalOrientation


@attr.s(slots=True)
class BranchTraversalSetup(object):
    start_string = attr.ib()
    orientation = attr.ib()
    ignore_first_kmer = attr.ib()
    connecting_node = attr.ib(None)


class EngineTraversalOrientation(Enum):
    original = 0
    reverse = 1
    both = 2


@attr.s(slots=True)
class Engine(object):
    ra_parser = attr.ib()
    traversal_color = attr.ib(0)
    orientation = attr.ib(EngineTraversalOrientation.original)
    graph = attr.ib(attr.Factory(SERIALIZER_GRAPH))
    max_nodes = attr.ib(1000)
    branch_queue = attr.ib(attr.Factory(collections.deque))
    queuer = attr.ib(init=False)
    branch_traverser = attr.ib(init=False)

    def traverse_from(self, start_string):
        self.graph = SERIALIZER_GRAPH()
        self.branch_traverser = Branch(self.ra_parser, self.traversal_color)
        self.queuer = BranchQueuer(self.branch_queue, self.orientation)

        self._process_initial_branch(start_string)
        while 0 < len(self.branch_queue) and len(self.graph) < self.max_nodes:
            self._traverse_a_branch_from_queue()
        return self.graph

    def _process_initial_branch(self, start_string):
        if self.orientation == EngineTraversalOrientation.both:
            self.queuer.add_from(start_string, EdgeTraversalOrientation.original, None)
        else:
            self.queuer.add_from(start_string, EdgeTraversalOrientation[self.orientation.name],
                                 None)
        self._traverse_a_branch_from_queue()
        if self.orientation == EngineTraversalOrientation.both:
            start_kmer = self.ra_parser.get_kmer_for_string(start_string)
            oriented_edge_set = start_kmer.edges[self.traversal_color].oriented(
                EdgeTraversalOrientation.reverse)
            kmer_strings = oriented_edge_set.neighbor_kmer_strings(start_string)
            if len(kmer_strings) == 1:
                self.queuer.add_from(kmer_strings[0], EdgeTraversalOrientation.reverse,
                                     start_string)

    def _traverse_a_branch_from_queue(self):
        setup = self.branch_queue.popleft()
        branch = self.branch_traverser.traverse_from(setup.start_string,
                                                     orientation=setup.orientation,
                                                     parent_graph=self.graph)
        self.graph = nx.union(self.graph, branch.graph)
        self._connect_branch_to_parent_graph(branch, setup)
        self._link_branch_and_queue_neighbor_traversals(branch)

    def _connect_branch_to_parent_graph(self, branch, setup):
        if setup.connecting_node is not None and branch.first_kmer_string is not None:
            self._add_edge_in_orientation(setup.connecting_node, branch.first_kmer_string,
                                          setup.orientation)

    def _link_branch_and_queue_neighbor_traversals(self, traversed_branch):
        orientations_and_kmer_strings = [
            (traversed_branch.orientation, traversed_branch.neighbor_kmer_strings)]
        if self.orientation == EngineTraversalOrientation.both:
            orientations_and_kmer_strings.append(
                (EdgeTraversalOrientation.other(traversed_branch.orientation),
                 traversed_branch.reverse_neighbor_kmer_strings)
            )
        for orientation, kmer_strings in orientations_and_kmer_strings:
            for neighbor_string in kmer_strings:
                if neighbor_string in self.graph:
                    self._add_edge_in_orientation(traversed_branch.last_kmer_string,
                                                  neighbor_string,
                                                  orientation)
                else:
                    self.queuer.add_from_traversed_branch(traversed_branch)

    def _add_edge_in_orientation(self, first, second, orientation):
        if orientation == EdgeTraversalOrientation.reverse:
            first, second = second, first
        self.graph.add_edge(first, second, key=self.traversal_color)


@attr.s(slots=True)
class BranchQueuer(object):
    queue = attr.ib()
    engine_orientation = attr.ib(EngineTraversalOrientation.original)
    _orientations = attr.ib(init=False)

    def __attrs_post_init__(self):
        if self.engine_orientation == EngineTraversalOrientation.both:
            self._orientations = list(EdgeTraversalOrientation)
        else:
            self._orientations = [EdgeTraversalOrientation[self.engine_orientation.name]]

    def add_from(self, start_string, orientation, connecting_node):
        self.queue.append(
            BranchTraversalSetup(start_string,
                                 orientation=orientation,
                                 ignore_first_kmer=False,
                                 connecting_node=connecting_node))

    def add_from_traversed_branch(self, traversed_branch):
        orientation_neighbor_pairs = [
            (traversed_branch.orientation, traversed_branch.neighbor_kmer_strings)]
        if self.engine_orientation == EngineTraversalOrientation.both:
            orientation_neighbor_pairs.append(
                (EdgeTraversalOrientation.other(traversed_branch.orientation),
                 traversed_branch.reverse_neighbor_kmer_strings))
        else:
            assert EdgeTraversalOrientation[
                       self.engine_orientation.name] == traversed_branch.orientation
        for orientation, neighbor_strings in orientation_neighbor_pairs:
            for neighbor_string in neighbor_strings:
                self.add_from(neighbor_string, orientation, traversed_branch.last_kmer_string)
