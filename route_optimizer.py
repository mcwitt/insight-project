import networkx as nx

class RoutingGraph:

    def __init__(self):
        self.G = nx.Graph() 


    def add_way(self, waypoints):

        wp_next = iter(waypoints)
        next(wp_next)

        for wp1, wp2 in zip(waypoints, wp_next):

            u, v = wp1.node_id, wp2.node_id
            dist = wp2.cdist - wp1.cdist
            score = wp2.cscore - wp1.cscore

            if ((u, v) not in self.G.edge or
                dist < self.G.get_edge_data[u, v]['weight']):

                data = {'i': wp1.idx, 
                        'j': wp2.idx, 
                        'way_id': wp1.way_id, 
                        'dist': dist,
                        'score': score}

                self.G.add_edge(u, v, data)


    def get_optimal_path(self, u, v, alpha=0):

        for edge in self.G.edges_iter():
            edge_data = self.G.get_edge_data(*edge)
            dist = edge_data['dist']
            score = edge_data['score']
            weight = dist*(1 + alpha*score)
            self.G.add_edge(*edge, weight=weight)

        self.G = self.G.to_undirected()
        nodes = nx.shortest_path(self.G, u, v, weight='weight')
        edges = [self.G.get_edge_data(u_, v_) for u_, v_ in zip(nodes, nodes[1:])]

        return nodes, edges

