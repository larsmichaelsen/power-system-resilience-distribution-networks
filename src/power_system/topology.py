from collections import defaultdict, deque


class NetworkTopology:
    """
    Topology representation used by the Forward--Backward Sweep solver.

    A radial spanning tree is constructed from the slack bus. If the active
    network is disconnected, only the slack-connected component is retained.
    Non-tree branches inside this component are treated as tie branches and
    define fundamental loops.

    Each loop is stored as a list of (branch_id, sign), where sign is +1 when
    the loop direction follows the branch orientation and -1 otherwise.
    """

    def __init__(self, buses, branches, slack):
        self.buses = buses
        self.all_branches = branches
        self.slack = slack

        self.bus_order = sorted(buses.keys())
        self.n_bus = len(self.bus_order)

        self.parent = {}
        self.parent_branch = {}
        self.children = {b: [] for b in self.bus_order}

        self.loops = []
        self.tie_branches = []

        self.graph = self._build_graph()
        visited = self._build_spanning_tree()

        self.slack_component = set(visited)

        self.bus_order = sorted(self.slack_component)
        self.n_bus = len(self.bus_order)

        self.children = {
            b: [c for c in self.children.get(b, []) if c in self.slack_component]
            for b in self.bus_order
        }

        self.branches = {
            br_id: br
            for br_id, br in self.all_branches.items()
            if (br.from_bus in self.slack_component and br.to_bus in self.slack_component)
            and (br_id not in self.tie_branches)
        }

        self.n_branch = len(self.branches)

        self.branch_index = {
            br_id: i
            for i, br_id in enumerate(sorted(self.branches.keys()))
        }

        self.branch_by_index = {
            idx: self.branches[br_id]
            for br_id, idx in self.branch_index.items()
        }

        self.branch_lookup = {}
        for b in self.parent:
            if b in self.slack_component:
                p = self.parent[b]
                if p in self.slack_component:
                    br_id = self.parent_branch[b]
                    if br_id in self.branch_index:
                        self.branch_lookup[(p, b)] = self.branch_index[br_id]

        self.path_to_slack = self._compute_paths()
        self.bus_index = {b: i for i, b in enumerate(self.bus_order)}

    def _build_graph(self):
        """Build an undirected graph from the active branch set."""
        graph = defaultdict(list)

        for br in self.all_branches.values():
            graph[br.from_bus].append((br.to_bus, br.idx))
            graph[br.to_bus].append((br.from_bus, br.idx))

        return graph

    def _build_spanning_tree(self):
        """
        Build a spanning tree from the slack bus.

        The visited set is returned so disconnected buses can be excluded from
        the load-flow topology.
        """
        visited = {self.slack}
        queue = deque([self.slack])

        while queue:
            u = queue.popleft()

            for v, br_id in self.graph[u]:
                if v not in visited:
                    visited.add(v)
                    queue.append(v)

                    self.parent[v] = u
                    self.parent_branch[v] = br_id
                    self.children[u].append(v)

                elif self._is_back_edge(u, v, br_id):
                    self._register_loop(u, v, br_id)

        return visited

    def _is_back_edge(self, u, v, br_id):
        """Return True if the edge is a non-tree branch not already registered."""
        if v == self.parent.get(u):
            return False

        if u == self.parent.get(v):
            return False

        if br_id in self.tie_branches:
            return False

        return True

    def _register_loop(self, u, v, tie_branch):
        """
        Register the fundamental loop created by a tie branch.

        The loop direction is defined as u -> LCA -> v and closed through the
        tie branch.
        """
        path_u = self._path_to_root(u)
        path_v = self._path_to_root(v)

        lca = next(x for x in path_u if x in path_v)

        loop = []

        x = u
        while x != lca:
            br_id = self.parent_branch[x]
            parent = self.parent[x]

            loop.append((br_id, -1))
            x = parent

        stack = []
        x = v
        while x != lca:
            br_id = self.parent_branch[x]
            parent = self.parent[x]

            stack.append((br_id, +1))
            x = parent

        loop.extend(reversed(stack))

        tie = self.all_branches[tie_branch]

        if tie.from_bus == u and tie.to_bus == v:
            s = +1
        elif tie.from_bus == v and tie.to_bus == u:
            s = -1
        else:
            raise ValueError(
                f"Tie branch {tie_branch} endpoints do not match loop nodes {u}-{v}"
            )

        loop.append((tie_branch, s))

        self.tie_branches.append(tie_branch)
        self.loops.append(loop)

    def _path_to_root(self, bus):
        """Return the path from a bus to the slack-rooted tree root."""
        path = []

        while bus in self.parent:
            path.append(bus)
            bus = self.parent[bus]

        path.append(bus)

        return path

    def _compute_paths(self):
        """Compute slack-to-bus paths for all buses in the slack component."""
        paths = {}

        for bus in self.bus_order:
            if bus == self.slack:
                paths[bus] = [self.slack]
                continue

            path = [bus]
            x = bus

            while x != self.slack:
                if x not in self.parent:
                    raise ValueError("Radial basis could not be formed.")

                x = self.parent[x]
                path.append(x)

            path.reverse()
            paths[bus] = path

        return paths

    def __repr__(self):
        if not self.loops:
            return f"Topology(radial, {self.n_bus} buses)"

        return f"Topology(meshed, {self.n_bus} buses, loops={len(self.loops)})"