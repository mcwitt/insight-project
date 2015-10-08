import networkx as nx
from collections import defaultdict


def _add_way(G, waypoints):

    wp_next = iter(waypoints)
    next(wp_next)

    for wp1, wp2 in zip(waypoints, wp_next):

        u, v = wp1.node_id, wp2.node_id
        dist = wp2.cdist - wp1.cdist
        score = wp2.cscore - wp1.cscore

        # TODO: eventually will select path of lowest weight
        if ((u, v) not in G.edge or dist < G.get_edge_data[u, v]['dist']):

            data = {'i': wp1.idx,
                    'j': wp2.idx,
                    'way_id': wp1.way_id,
                    'dist': dist,
                    'score': score}

            G.add_edge(u, v, data)


class RoutingGraph:

    def __init__(self, waypoints, alpha=1):

        G = nx.Graph() 
        ways = defaultdict(list)

        for wp in waypoints:
            ways[wp.way_id].append(wp)

        for way_id, wps in ways.items():
            _add_way(G, wps)

        self.G = G.to_undirected()
        self.alpha = alpha

    @property
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, value):
        """
        Update the relative weight of distance and scenery score used to
        determine the edge weights. Weights are determined from
        W = dist * (1 + alpha * score),
        where 0 < score < 1 (lower is better).
        """

        self._alpha = value

        for edge in self.G.edges_iter():
            edge_data = self.G.get_edge_data(*edge)
            dist = edge_data['dist']
            score = edge_data['score']
            weight = dist * score**value
            self.G.add_edge(*edge, weight=weight)



    def get_optimal_path(self, u, v):
        """
        Find the optimal path (i.e. path of least total weight) between the
        nodes with IDs u, v.
        """

        self.G = self.G.to_undirected()
        nodes = nx.shortest_path(self.G, u, v, weight='weight')
        edges = [self.G.get_edge_data(u_, v_) for u_, v_ in zip(nodes, nodes[1:])]

        return nodes, edges

