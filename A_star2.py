import networkx as nx
import heapq
import matplotlib.pyplot as plt

# Define world

G = nx.Graph()
G.add_edge('Oradea', 'Zerind', weight=71)
G.add_edge('Oradea', 'Sibiu', weight=151)
G.add_edge('Zerind', 'Arad', weight=75)
G.add_edge('Sibiu', 'Arad', weight=140)
G.add_edge('Arad', 'Timisoara', weight=118)
G.add_edge('Lugoj', 'Timisoara', weight=111)
G.add_edge('Lugoj', 'Mehadia', weight=70)
G.add_edge('Drobeta', 'Mehadia', weight=75)
G.add_edge('Drobeta', 'Craiova', weight=120)
G.add_edge('Craiova', 'Pitesti', weight=138)
G.add_edge('Craiova', 'RV', weight=146)
G.add_edge('Pitesti', 'RV', weight=97)
G.add_edge('RV', 'Sibiu', weight=80)
G.add_edge('Sibiu', 'Fagaras', weight=99)
G.add_edge('Fagaras', 'Bucharest', weight=211)
G.add_edge('Pitesti', 'Bucharest', weight=101)
G.add_edge('Giurgiu', 'Bucharest', weight=90)
G.add_edge('Urziceni', 'Bucharest', weight=85)

attr = {
    'Arad':{'h': 366},
    'Bucharest':{'h': 0},
    'Craiova':{'h': 160},
    'Drobeta':{'h': 242},
    'Fagaras':{'h': 176},
    'Giurgiu':{'h': 77},
    'Lugoj':{'h': 244},
    'Mehadia':{'h': 241},
    'Oradea':{'h': 380},
    'Pitesti':{'h': 100},
    'RV':{'h': 193},
    'Sibiu':{'h': 253},
    'Zerind':{'h': 374},
    'Urziceni':{'h': 80},
    'Timisoara': {'h':329}
}

nx.set_node_attributes(G, attr)

#subax1 = plt.subplot(121)
nx.draw(G, with_labels=True, font_weight='bold')
#subax2 = plt.subplot(122)
#nx.draw_shell(G, with_labels=True, font_weight='bold')
plt.show()

START = 'Lugoj '
GOAL = 'Bucharest'

#--- Methods----

def heruistic (node) :
    return G.nodes[node]['h']

def g_dist (current, next):
    return G[current][next]['weight']

def f_score (current, next):
    return heruistic(next) + g_dist(current=current, next=next)

def a_star (start, goal) :
    
    path = []

    explored = set()
    
    frontier = []
    heapq.heappush(frontier, (heruistic(node=start), start))

    while frontier:
        current = heapq.heappop(frontier)[1]

        if current==goal:
            path.append(goal)
            return path

        if current in explored:
            continue

        path.append(current)
        explored.add(current)

        for neighbor in G.neighbors(current):
            heapq.heappush(frontier, (f_score(current, next=neighbor), neighbor))

    return path
        
#print(a_star(START, GOAL))