from pathlib import Path

import pandas as pd

from src.power_system.powerdata import DG, RPC, Switch, ES


def load_dgs(folder, Sb):
    """Load distributed generation units from dg.csv if available."""
    dg_file = Path(folder) / "dg.csv"
    if not dg_file.exists():
        return []

    dg_df = pd.read_csv(dg_file)
    cols = set(dg_df.columns)

    dgs = []

    if {"Bus", "P_min_kW", "P_max_kW"}.issubset(cols):

        for _, r in dg_df.iterrows():
            bus = int(r.Bus)

            P_min_kW = float(r.P_min_kW)
            P_max_kW = float(r.P_max_kW)

            if P_min_kW > P_max_kW:
                raise ValueError(
                    f"DG at bus {bus}: P_min_kW cannot be greater than P_max_kW"
                )

            P_init_kW = 0.5 * (P_min_kW + P_max_kW)

            P_min_pu = P_min_kW * 1e3 / Sb
            P_max_pu = P_max_kW * 1e3 / Sb
            P_pu = P_init_kW * 1e3 / Sb

            dgs.append(
                DG(
                    bus=bus,
                    P_pu=P_pu,
                    Q_pu=0.0,
                    P_min_pu=P_min_pu,
                    P_max_pu=P_max_pu,
                )
            )

        return dgs

    elif {"Bus", "P_MW", "Q_MVAr"}.issubset(cols):

        for _, r in dg_df.iterrows():
            bus = int(r.Bus)

            P_pu = float(r.P_MW) * 1e6 / Sb
            Q_pu = float(r.Q_MVAr) * 1e6 / Sb

            dgs.append(
                DG(
                    bus=bus,
                    P_pu=P_pu,
                    Q_pu=Q_pu,
                    P_min_pu=P_pu,
                    P_max_pu=P_pu,
                )
            )

        return dgs

    else:
        raise ValueError(
            f"Unsupported dg.csv format: {dg_df.columns.tolist()}"
        )


def load_rpcs(folder, Sb):
    """Load reactive power compensation units from rpc.csv if available."""
    rpc_file = Path(folder) / "rpc.csv"
    if not rpc_file.exists():
        return []

    rpc_df = pd.read_csv(rpc_file)
    rpc_df["Q_pu"] = rpc_df["Q_sh_MVAr"] * 1e6 / Sb

    rpcs = []
    for _, r in rpc_df.iterrows():
        rpcs.append(RPC(int(r.Bus), r.Q_pu))

    return rpcs


def load_es(folder, Sb):
    """Load energy storage units from es.csv if available."""
    es_file = Path(folder) / "es.csv"
    if not es_file.exists():
        return []

    es_df = pd.read_csv(es_file)

    required = {"Bus", "P_min_kW", "P_max_kW", "E_max_kWh", "SOC_init_frac"}
    if not required.issubset(set(es_df.columns)):
        raise ValueError(
            f"es.csv must contain columns {required}, "
            f"but found {es_df.columns.tolist()}"
        )

    es_units = []

    for _, r in es_df.iterrows():
        P_min_pu = r.P_min_kW * 1e3 / Sb
        P_max_pu = r.P_max_kW * 1e3 / Sb

        P_init_pu = 0.0

        E_max_pu = r.E_max_kWh * 1e3 / Sb
        soc_pu = r.SOC_init_frac * E_max_pu

        es_units.append(
            ES(
                bus=int(r.Bus),
                P_pu=P_init_pu,
                Q_pu=0.0,
                P_min_pu=P_min_pu,
                P_max_pu=P_max_pu,
                E_max_pu=E_max_pu,
                soc_pu=soc_pu,
            )
        )

    return es_units


def load_switches(folder, Zb):
    """Load switchable branches from switch.csv if available."""
    sw_file = Path(folder) / "switch.csv"
    if not sw_file.exists():
        return {}

    df = pd.read_csv(sw_file)
    cols = set(df.columns)

    switches = {}
    for _, r in df.iterrows():
        if {"R_ohm", "X_ohm"}.issubset(cols):
            z = complex(r.R_ohm / Zb, r.X_ohm / Zb)
        elif {"r_pu", "x_pu"}.issubset(cols):
            z = complex(r.r_pu, r.x_pu)
        else:
            raise ValueError(f"Unsupported switch format: {df.columns.tolist()}")

        sw = Switch(
            idx=int(r.Idx),
            from_bus=int(r.From),
            to_bus=int(r.To),
            z=z,
            closed=bool(r.Closed),
        )
        switches[sw.idx] = sw

    return switches


def apply_dg_injections(bus_lookup, dgs):
    """Apply DG injections to the bus complex-power demand."""
    for dg in dgs:
        bus_lookup[dg.bus].s -= complex(dg.P_pu, dg.Q_pu)


def apply_rpc_injections(bus_lookup, rpcs):
    """Apply reactive power compensation to the bus complex-power demand."""
    for rpc in rpcs:
        bus_lookup[rpc.bus].s -= 1j * rpc.Q_pu


def apply_es_injections(bus_lookup, es_units):
    """Apply energy storage injections to the bus complex-power demand."""
    for es in es_units:
        bus_lookup[es.bus].s -= complex(es.P_pu, es.Q_pu)