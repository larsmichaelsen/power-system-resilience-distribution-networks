import numpy as np


class FBSPowerMatrices:
    """
    Construct BIBC, BCBV, and DLF matrices for Forward--Backward Sweep load flow.

    The radial formulation follows the direct approach of Teng (2003). For weakly
    meshed networks, loop-current variables are introduced and eliminated using
    Kron reduction.
    """

    def __init__(self, topo):
        self.topo = topo
        self.n = topo.n_bus
        self.m = topo.n_branch

        self._meshed_aux = None

        if topo.loops:
            self.BIBC, self.BCBV, self.DLF = self._build_meshed()
        else:
            self.BIBC = self._build_bibc_radial()
            self.BCBV = self._build_bcbv_radial()
            self.DLF = self.BCBV @ self.BIBC

    def _build_bibc_radial(self):
        """
        Build the radial bus-injection to branch-current matrix.

        Each non-slack bus contributes to all branches on its slack-to-bus path.
        """
        B = np.zeros((self.m, self.n), dtype=float)

        for bus in self.topo.bus_order:
            if bus == self.topo.slack:
                continue

            col = self.topo.bus_index[bus]
            path = self.topo.path_to_slack[bus]

            for i in range(len(path) - 1):
                fr, to = path[i], path[i + 1]
                br = self.topo.branch_lookup[(fr, to)]
                B[br, col] = 1.0

        return B

    def _build_bcbv_radial(self):
        """
        Build the radial branch-current to bus-voltage matrix.

        Each row contains the branch impedances on the slack-to-bus path.
        """
        Z = np.zeros((self.n, self.m), dtype=complex)

        for bus in self.topo.bus_order:
            if bus == self.topo.slack:
                continue

            row = self.topo.bus_index[bus]
            path = self.topo.path_to_slack[bus]

            for i in range(len(path) - 1):
                fr, to = path[i], path[i + 1]
                br = self.topo.branch_lookup[(fr, to)]
                Z[row, br] = self.topo.branch_by_index[br].z

        return Z

    def _build_meshed(self):
        """
        Build the reduced DLF matrix for a weakly meshed network.

        The radial matrices are kept as the base formulation. Closed tie branches
        are represented through loop-current variables and eliminated from the
        final voltage relation.
        """
        n_loop = len(self.topo.loops)

        BIBC_r = self._build_bibc_radial()
        BCBV_r = self._build_bcbv_radial()
        A = BCBV_r @ BIBC_r

        L = np.zeros((self.m, n_loop), dtype=float)
        Z_tie = np.zeros((n_loop, n_loop), dtype=complex)

        z_rad = np.array(
            [self.topo.branch_by_index[k].z for k in range(self.m)],
            dtype=complex,
        )

        for loop_idx, loop in enumerate(self.topo.loops):
            tie_id, _ = loop[-1]
            Z_tie[loop_idx, loop_idx] = self.topo.all_branches[tie_id].z

            for br_id, sign in loop:
                if br_id not in self.topo.branch_index:
                    continue

                branch_idx = self.topo.branch_index[br_id]
                L[branch_idx, loop_idx] += sign

        N = (L.T * z_rad) @ L + Z_tie
        M = BCBV_r @ L

        DLF = A - M @ np.linalg.solve(N, M.T)

        self._meshed_aux = (L, N)

        return BIBC_r, BCBV_r, DLF

    def __repr__(self):
        if self.topo.loops:
            return (
                f"FBSPowerMatrices(meshed, "
                f"n_bus={self.n}, loops={len(self.topo.loops)})"
            )

        return f"FBSPowerMatrices(radial, n_bus={self.n})"