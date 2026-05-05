import time

import numpy as np

from src.power_system.results import PowerFlowResults


def solve_fbs(system, matrices, topo, tol=1e-8, max_iter=1000, return_aux: bool = False):
    """
    Solve the load flow using the DLF-based Forward--Backward Sweep method.

    The same iteration structure is used for radial and weakly meshed networks.
    For weakly meshed networks, the reduced DLF matrix is already included in
    the matrix object. Loop currents are recovered after voltage convergence.
    """

    buses = topo.bus_order
    slack = topo.slack
    idx = topo.bus_index
    n = topo.n_bus

    # Shunt susceptance is represented with half of the branch value at each end.
    B_sh = np.zeros(n, dtype=float)
    for br in topo.branches.values():
        if hasattr(br, "b"):
            b_half = br.b * 0.5
            B_sh[idx[br.from_bus]] += b_half
            B_sh[idx[br.to_bus]] += b_half

    V = np.array([system.buses[b].v for b in buses], dtype=complex)
    V_slack = system.buses[slack].v

    start_time = time.time()

    for it in range(1, max_iter + 1):
        S = np.zeros(n, dtype=complex)

        for b in buses:
            if b != slack:
                S[idx[b]] = system.buses[b].s

        Iinj = np.conj(S / np.conj(V))
        Iinj += 1j * B_sh * V
        Iinj[idx[slack]] = 0.0

        dV = matrices.DLF @ Iinj

        V_new = V.copy()
        V_new[idx[slack]] = V_slack

        for b in buses:
            if b != slack:
                V_new[idx[b]] = V_slack - dV[idx[b]]

        if np.max(np.abs(V_new - V)) < tol:
            V = V_new
            break

        V = V_new

    elapsed = time.time() - start_time

    # Final current injections are recomputed from the converged voltage profile.
    S = np.zeros(n, dtype=complex)

    for b in buses:
        if b != slack:
            S[idx[b]] = system.buses[b].s

    Iinj = np.conj(S / np.conj(V))
    Iinj += 1j * B_sh * V
    Iinj[idx[slack]] = 0.0

    I_rad = matrices.BIBC @ Iinj

    B_loop = None
    I_tie_by_id = {}

    if matrices._meshed_aux is not None:
        L, N = matrices._meshed_aux
        M = matrices.BCBV @ L

        B_loop = -np.linalg.solve(N, M.T @ Iinj)
        I_branch = I_rad + L @ B_loop

        for loop_idx, loop in enumerate(topo.loops):
            tie_id, tie_sign = loop[-1]
            I_tie_by_id[int(tie_id)] = complex(tie_sign) * complex(B_loop[loop_idx])
    else:
        I_branch = I_rad

    R_vec = np.array([topo.branch_by_index[k].r for k in range(topo.n_branch)])
    X_vec = np.array([topo.branch_by_index[k].x for k in range(topo.n_branch)])

    results = PowerFlowResults(
        V=V,
        I_branch=I_branch,
        branch_R=R_vec,
        branch_X=X_vec,
        base_S=system.base_S,
        iter_count=it,
        solve_time=elapsed,
    )

    if not return_aux:
        return results

    aux = {
        "bus_order": list(buses),
        "bus_index": dict(idx),
        "Iinj": Iinj,
        "I_rad": I_rad,
        "I_branch": I_branch,
        "B_loop": B_loop,
        "I_tie_by_id": I_tie_by_id,
    }

    return results, aux