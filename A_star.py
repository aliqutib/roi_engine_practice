import heapq

# ─────────────────────────────────────────────
# THE GRID  (0 = free, 1 = wall)
# ─────────────────────────────────────────────
grid = [
    [0, 0, 0, 1, 0],
    [0, 1, 0, 1, 0],
    [0, 1, 0, 0, 0],
    [0, 0, 0, 1, 0],
    [0, 1, 0, 0, 0],
]

START = (0, 0)
GOAL  = (4, 0)

# ─────────────────────────────────────────────
# HEURISTIC  — Manhattan distance to goal
# This is our "h" score: a guess of remaining cost.
# ─────────────────────────────────────────────
def heuristic(node, goal):
    return abs(node[0] - goal[0]) + abs(node[1] - goal[1])

# ─────────────────────────────────────────────
# A* SEARCH
# ─────────────────────────────────────────────
def astar(grid, start, goal):
    rows, cols = len(grid), len(grid[0])

    # open_list is a min-heap sorted by f = g + h
    # Each entry: (f, g, node)
    open_list = []
    heapq.heappush(open_list, (0, 0, start))

    # came_from lets us reconstruct the path at the end
    came_from = {}

    # g_score is dict: keeping g score of every node
    # g_score[node] = cheapest known cost from start to node
    g_score = {start: 0}

    # explored = nodes we've already fully explored
    explored = set()

    while open_list:

        # ── PICK BEST NODE (lowest f) ──────────
        f, g, current = heapq.heappop(open_list)

        # Skip if we already found a better path here
        if current in explored:
            continue
        explored.add(current)

        # ── GOAL CHECK ────────────────────────
        if current == goal:
            return reconstruct_path(came_from, current)

        # ── EXPAND NEIGHBORS ──────────────────
        row, col = current
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:  # up, down, left, right
            neighbor = (row + dr, col + dc)

            # Skip out-of-bounds or walls
            if not (0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols):
                continue
            if grid[neighbor[0]][neighbor[1]] == 1:
                continue
            if neighbor in explored:
                continue

            # ── COMPUTE SCORES ────────────────
            new_g = g + 1                            # each step costs 1
            new_h = heuristic(neighbor, goal)
            new_f = new_g + new_h

            # Only add to open list if this path is better
            if new_g < g_score.get(neighbor, float('inf')):
                g_score[neighbor] = new_g
                came_from[neighbor] = current
                heapq.heappush(open_list, (new_f, new_g, neighbor))

    return None  # No path found


# ─────────────────────────────────────────────
# PATH RECONSTRUCTION
# Walk backwards from goal → start using came_from
# ─────────────────────────────────────────────
def reconstruct_path(came_from, current):
    path = []
    while current in came_from:
        path.append(current)
        current = came_from[current]
    path.append(current)  # add start
    path.reverse()
    return path


# ─────────────────────────────────────────────
# RUN IT
# ─────────────────────────────────────────────
path = astar(grid, START, GOAL)

if path:
    print("Path found:", path)
    # Visualize on the grid
    for r in range(len(grid)):
        row_str = ""
        for c in range(len(grid[0])):
            if (r, c) == START:
                row_str += "S "
            elif (r, c) == GOAL:
                row_str += "G "
            elif (r, c) in path:
                row_str += "* "
            elif grid[r][c] == 1:
                row_str += "█ "
            else:
                row_str += ". "
        print(row_str)
else:
    print("No path found.")