from src.power_system.topology import NetworkTopology
from src.power_system.fbs_matrices import FBSPowerMatrices


class Network:
    """
    Distribution network model used by the load-flow framework.

    The active topology and FBS matrices can be rebuilt when switch states or
    network configurations change.
    """

    def __init__(self, buses, branches, dgs, rpcs, es_units, slack, base_S):
        self.buses = {b.idx: b for b in buses}
        self.branches = {br.idx: br for br in branches}
        self.switches = {}

        self.dgs = dgs
        self.rpcs = rpcs
        self.es_units = es_units

        self.slack = slack
        self.base_S = base_S

        self.topology = None
        self.matrices = None

        self.load_manager = None

        self.base_V = None
        self.base_Z = None
        self.base_I = None

    @classmethod
    def from_folder(cls, folder):
        """Build a network model from a network input folder."""
        from src.power_system.network.builder import build_network_from_folder

        return build_network_from_folder(folder, network_cls=cls)

    @classmethod
    def from_csv(
        cls,
        bus_file,
        branch_file,
        V_base_kV,
        S_base_MVA,
        folder,
    ):
        """Build a network model from bus, branch, and system base input data."""
        from src.power_system.network.builder import build_network_from_csv

        return build_network_from_csv(
            bus_file=bus_file,
            branch_file=branch_file,
            V_base_kV=V_base_kV,
            S_base_MVA=S_base_MVA,
            folder=folder,
            network_cls=cls,
        )

    def update_loads_for_time(self, t):
        """Update bus loads from the assigned time-series load manager."""
        if self.load_manager is not None:
            self.load_manager.apply_time(self, t)

    def active_branches(self):
        """Return fixed branches and currently closed switch branches."""
        active = dict(self.branches)

        for sw in self.switches.values():
            if sw.closed:
                active[sw.idx] = sw

        return active

    def rebuild_topology_and_matrices(self):
        """Rebuild the active topology and FBS matrices."""
        active = self.active_branches()

        self.topology = NetworkTopology(self.buses, active, self.slack)
        self.matrices = FBSPowerMatrices(self.topology)

    def open_switch(self, switch_id, rebuild=False):
        """Open a switch and optionally rebuild the network matrices."""
        if switch_id not in self.switches:
            raise KeyError(f"Unknown switch id: {switch_id}")

        self.switches[switch_id].closed = False

        if rebuild:
            self.rebuild_topology_and_matrices()

    def close_switch(self, switch_id, rebuild=False):
        """Close a switch and optionally rebuild the network matrices."""
        if switch_id not in self.switches:
            raise KeyError(f"Unknown switch id: {switch_id}")

        self.switches[switch_id].closed = True

        if rebuild:
            self.rebuild_topology_and_matrices()

    def set_switch_state(self, switch_id, closed, rebuild=False):
        """Set switch state and optionally rebuild the network matrices."""
        if switch_id not in self.switches:
            raise KeyError(f"Unknown switch id: {switch_id}")

        self.switches[switch_id].closed = bool(closed)

        if rebuild:
            self.rebuild_topology_and_matrices()

    def __repr__(self):
        return (
            f"Network({len(self.buses)} buses, "
            f"{len(self.branches)} branches, "
            f"{len(self.switches)} switches, "
            f"slack={self.slack})"
        )