import networkx as nx
from collections import defaultdict


def _add_way(G, way_id, waypoints, alpha=0):
    """
    Add way, specified by list of waypoints, to the routing graph G.
    The parameter `alpha` controls the relative weighting of distance
    and score through the formula weight = distance * score^alpha.
    """

    wp_next = iter(waypoints)
    next(wp_next)

    for wp1, wp2 in zip(waypoints, wp_next):

        u1, u2 = wp1.node_id, wp2.node_id
        dist = wp2.cdist - wp1.cdist
        score = wp2.cscore - wp1.cscore
        weight = dist * score**alpha

        if not G.has_edge(u1, u2) or weight < G.get_edge_data(u1, u2)['weight']:

            edge_data = dict(way_id=way_id,
                             idx1=wp1.idx,
                             idx2=wp2.idx,
                             dist=dist,
                             score=score,
                             weight=weight)

            G.add_edge(u1, u2, edge_data)


class RoutingGraph:

    def __init__(self, waypoints, alpha=0):

        self._alpha = alpha
        self.G = nx.Graph()
        ways = defaultdict(list)

        for wp in waypoints:
            ways[wp.way_id].append(wp)

        for way_id, wps in ways.items():
            _add_way(self.G, way_id, wps, alpha)


    @property
    def alpha(self):
        return self._alpha

    def get_optimal_path(self, u1, u2):
        """
        Find the optimal path (i.e. path of least total weight) between the
        nodes identified by u1, u2.
        """

        nodes = nx.shortest_path(self.G, u1, u2, weight='weight')
        edges = [self.G.get_edge_data(u1_, u2_) for u1_, u2_ in zip(nodes, nodes[1:])]

        return nodes, edges

