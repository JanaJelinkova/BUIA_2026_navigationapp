import math
import heapq

# Coordinates are in percent of floorplan (0..100). For demo treat 1 unit ~= 1 meter.
NODES = {
    # west wing
    'Entrance':   {'id':'Entrance','label':'Hlavní vchod','x':8,'y':50,'type':'entrance'},
    'Lobby':      {'id':'Lobby','label':'Lobby','x':20,'y':50,'type':'corridor'},
    'Stairs':     {'id':'Stairs','label':'Schodiště','x':36,'y':50,'type':'stairs'},

    # classrooms along north corridor
    'C101':       {'id':'C101','label':'Učebna 101','x':46,'y':18,'type':'classroom'},
    'C102':       {'id':'C102','label':'Učebna 102','x':64,'y':18,'type':'classroom'},

    # central corridor / junction
    'CorridorN':  {'id':'CorridorN','label':'Chodba N','x':52,'y':34,'type':'corridor'},
    'Junction':   {'id':'Junction','label':'Křižovatka','x':52,'y':50,'type':'corridor'},

    # east wing
    'Gym':        {'id':'Gym','label':'Tělocvična','x':80,'y':40,'type':'room'},
    'Cafeteria':  {'id':'Cafeteria','label':'Jídelna','x':80,'y':64,'type':'room'},

    # exits
    'ExitA':      {'id':'ExitA','label':'Nouzový východ A','x':98,'y':50,'type':'exit'},
    'ExitB':      {'id':'ExitB','label':'Nouzový východ B','x':52,'y':98,'type':'exit'},
}

EDGES = {
    'Entrance':  ['Lobby'],
    'Lobby':     ['Entrance','Stairs','Junction'],
    'Stairs':    ['Lobby','Junction'],
    'Junction':  ['Lobby','Stairs','CorridorN','Cafeteria','ExitB'],
    'CorridorN': ['Junction','C101','C102'],
    'C101':      ['CorridorN'],
    'C102':      ['CorridorN','Gym'],
    'Gym':       ['C102','Cafeteria','ExitA'],
    'Cafeteria': ['Gym','Junction'],
    'ExitA':     ['Gym'],
    'ExitB':     ['Junction'],
}

def euclid(a, b):
    return math.hypot(a['x'] - b['x'], a['y'] - b['y'])

def nearest_node_to_point(point):
    x, y = point
    p = {'x': x, 'y': y}
    best = None
    best_d = None
    for nid, node in NODES.items():
        d = euclid(p, node)
        if best is None or d < best_d:
            best = nid
            best_d = d
    return best

def dijkstra(start):
    dist = {n: float('inf') for n in NODES}
    prev = {n: None for n in NODES}
    dist[start] = 0.0
    pq = [(0.0, start)]
    while pq:
        d,u = heapq.heappop(pq)
        if d > dist[u]: continue
        for v in EDGES.get(u, []):
            alt = d + euclid(NODES[u], NODES[v])
            if alt < dist[v]:
                dist[v] = alt
                prev[v] = u
                heapq.heappush(pq, (alt, v))
    return dist, prev

def reconstruct_path(prev, target):
    path = []
    u = target
    while u is not None:
        path.append(u)
        u = prev[u]
    path.reverse()
    return path

def make_steps(path_nodes):
    steps = []
    for i in range(len(path_nodes)-1):
        a = NODES[path_nodes[i]]
        b = NODES[path_nodes[i+1]]
        d = euclid(a,b)
        txt = f"{a['label']} → {b['label']} • {d:.1f} m"
        steps.append({'from':a['label'],'to':b['label'],'distance_m':round(d,1),'text':txt})
    return steps

def path_distance(path_nodes, user_point=None):
    total = 0.0
    # if user_point provided, add from user to first node
    if user_point:
        first = NODES[path_nodes[0]]
        total += euclid({'x':user_point[0],'y':user_point[1]}, first)
    for i in range(len(path_nodes)-1):
        total += euclid(NODES[path_nodes[i]], NODES[path_nodes[i+1]])
    return total

def find_route_to_nearest_exit(point):
    # point: (x,y) in percent coords
    user_node = nearest_node_to_point(point)
    dist, prev = dijkstra(user_node)
    exit_nodes = [nid for nid,n in NODES.items() if n.get('type')=='exit']
    if not exit_nodes:
        # fallback: return only user
        return {'path':[{'id':'user','label':'Vy','x':float(point[0]),'y':float(point[1]),'type':'user'}],
                'distance_m':0.0,'eta_s':0,'steps':[]}
    best_exit = min(exit_nodes, key=lambda n: dist.get(n, float('inf')))
    path_nodes = reconstruct_path(prev, best_exit)
    # Prepend user location as virtual node in output
    path = []
    path.append({'id':'user','label':'Vy','x':float(point[0]),'y':float(point[1]),'type':'user'})
    for nid in path_nodes:
        n = NODES[nid]
        path.append({'id':n['id'],'label':n['label'],'x':n['x'],'y':n['y'],'type':n['type']})
    # compute distances treating 1 unit ~ 1 meter
    total_m = path_distance(path_nodes, user_point=point)
    # assume walking speed 1.2 m/s for ETA
    eta_s = int(total_m / 1.2)
    steps = make_steps([user_node] + path_nodes)  # coarse steps from nearest graph node
    return {'path': path, 'distance_m': round(total_m,1), 'eta_s': eta_s, 'steps': steps}