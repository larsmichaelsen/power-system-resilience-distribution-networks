from pathlib import Path

import pandas as pd

from src.power_system.powerdata import Bus, Branch
from src.power_system.network.model import Network
from src.power_system.network.readers import (
    read_system_data,
    read_bus_data,
    read_branch_data,
)
from src.power_system.network.converters import (
    compute_base_values,
    standardize_bus_dataframe,
    standardize_branch_dataframe,
    bus_type_to_int,
)
from src.power_system.network.devices import (
    load_dgs,
    load_rpcs,
    load_es,
    load_switches,
    apply_dg_injections,
    apply_rpc_injections,
    apply_es_injections,
)


def build_network_from_folder(folder, network_cls=Network):
    """Build a network model from a folder containing the input CSV files."""
    folder = Path(folder)

    Vb_kV, Sb_MVA = read_system_data(folder)

    return build_network_from_csv(
        bus_file=folder / "bus.csv",
        branch_file=folder / "branch.csv",
        V_base_kV=Vb_kV,
        S_base_MVA=Sb_MVA,
        folder=folder,
        network_cls=network_cls,
    )


def build_network_from_csv(
    bus_file,
    branch_file,
    V_base_kV,
    S_base_MVA,
    folder,
    network_cls=Network,
):
    """
    Build a network model from standardized bus and branch input files.

    Input data are converted to per unit before bus, branch, device, topology,
    and matrix objects are constructed.
    """
    Vb, Sb, Zb = compute_base_values(V_base_kV, S_base_MVA)

    bus_df = read_bus_data(bus_file)
    br_df = read_branch_data(branch_file)

    bus_df = standardize_bus_dataframe(bus_df, Sb)
    br_df = standardize_branch_dataframe(br_df, Zb)

    buses = _build_buses(bus_df)
    bus_lookup = {b.idx: b for b in buses}
    branches = _build_branches(br_df, Vb, Sb)

    dgs = load_dgs(folder, Sb)
    rpcs = load_rpcs(folder, Sb)
    es_units = load_es(folder, Sb)

    print(f"Loaded DG units: {len(dgs)}")
    print(f"Loaded RPC units: {len(rpcs)}")
    print(f"Loaded ES units: {len(es_units)}")

    apply_dg_injections(bus_lookup, dgs)
    apply_rpc_injections(bus_lookup, rpcs)
    apply_es_injections(bus_lookup, es_units)

    slack_rows = bus_df[bus_df.Type.str.upper() == "SLACK"]
    if len(slack_rows) != 1:
        raise ValueError("Exactly one slack bus required")

    slack = int(slack_rows.Bus.iloc[0])

    net = network_cls(buses, branches, dgs, rpcs, es_units, slack, Sb)

    net.switches = load_switches(folder, Zb)

    net.base_V = Vb
    net.base_Z = Zb
    net.base_I = Sb / (Vb * (3 ** 0.5))

    net.rebuild_topology_and_matrices()

    return net


def _build_buses(df):
    """Create Bus objects from the standardized bus dataframe."""
    buses = []

    for _, r in df.iterrows():
        buses.append(
            Bus(
                idx=int(r.Bus),
                type=bus_type_to_int(r.Type),
                v=complex(r.V_init_pu),
                s=complex(r.P_pu, r.Q_pu),
            )
        )

    return buses


def _build_branches(df, Vb, Sb):
    """Create Branch objects from the standardized branch dataframe."""
    branches = []

    has_imax = "I_max_A" in df.columns
    has_pmax = "Pmax_kW" in df.columns

    I_base = Sb / (Vb * (3 ** 0.5))

    for _, r in df.iterrows():
        br = Branch(
            idx=int(r.Idx),
            from_bus=int(r.From),
            to_bus=int(r.To),
            r=float(r.r_pu),
            x=float(r.x_pu),
            b=float(r.B_sh_pu),
            Pmax_kW=float(r.Pmax_kW) if has_pmax and pd.notna(r.Pmax_kW) else None,
        )

        if has_imax and pd.notna(r.I_max_A):
            br.I_max_A = float(r.I_max_A)
            br.I_max_pu = br.I_max_A / I_base

        elif has_pmax and pd.notna(r.Pmax_kW):
            P_watt = float(r.Pmax_kW) * 1e3
            I_max = P_watt / (3 ** 0.5 * Vb)
            br.I_max_pu = I_max / I_base

        branches.append(br)

    return branches