def compute_base_values(V_base_kV, S_base_MVA):
    """Compute voltage, power, and impedance base values."""
    Vb = V_base_kV * 1000.0
    Sb = S_base_MVA * 1e6
    Zb = (Vb * Vb) / Sb

    return Vb, Sb, Zb


def standardize_bus_dataframe(bus_df, Sb):
    """
    Convert supported bus load formats to per-unit active and reactive load.
    """
    bus_df = bus_df.copy()
    bus_cols = set(bus_df.columns)

    if {"P_load_MW", "Q_load_MVAr"}.issubset(bus_cols):
        bus_df["P_pu"] = bus_df["P_load_MW"] * 1e6 / Sb
        bus_df["Q_pu"] = bus_df["Q_load_MVAr"] * 1e6 / Sb

    elif {"P_load_kW", "Q_load_kVar"}.issubset(bus_cols):
        bus_df["P_pu"] = bus_df["P_load_kW"] * 1e3 / Sb
        bus_df["Q_pu"] = bus_df["Q_load_kVar"] * 1e3 / Sb

    elif {"P_load_pu", "Q_load_pu"}.issubset(bus_cols):
        bus_df["P_pu"] = bus_df["P_load_pu"]
        bus_df["Q_pu"] = bus_df["Q_load_pu"]

    elif {"Pd", "Qd"}.issubset(bus_cols):
        bus_df["P_pu"] = bus_df["Pd"] * 1e6 / Sb
        bus_df["Q_pu"] = bus_df["Qd"] * 1e6 / Sb

    else:
        raise ValueError(f"Unsupported bus format: {bus_df.columns.tolist()}")

    if "V_init_pu" not in bus_df.columns:
        bus_df["V_init_pu"] = 1.0

    return bus_df


def standardize_branch_dataframe(br_df, Zb):
    """
    Convert supported branch impedance formats to per-unit parameters.
    """
    br_df = br_df.copy()
    br_cols = set(br_df.columns)

    if {"r_pu", "x_pu"}.issubset(br_cols):
        br_df["r_pu"] = br_df["r_pu"]
        br_df["x_pu"] = br_df["x_pu"]

    elif {"R_ohm", "X_ohm"}.issubset(br_cols):
        br_df["r_pu"] = br_df["R_ohm"] / Zb
        br_df["x_pu"] = br_df["X_ohm"] / Zb

    elif {"br_r", "br_x"}.issubset(br_cols):
        br_df["r_pu"] = br_df["br_r"]
        br_df["x_pu"] = br_df["br_x"]

    else:
        raise ValueError(f"Unsupported branch format: {br_df.columns.tolist()}")

    if "B_sh_pu" not in br_df.columns:
        br_df["B_sh_pu"] = 0.0

    return br_df


def bus_type_to_int(t):
    """Convert bus type labels to the internal integer convention."""
    mapping = {"PQ": 1, "PV": 2, "SLACK": 3}

    if isinstance(t, str):
        key = t.strip().upper()
        if key in mapping:
            return mapping[key]

        raise ValueError(f"Unknown bus type: {t}")

    return int(t)