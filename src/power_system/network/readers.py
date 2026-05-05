from pathlib import Path

import pandas as pd


def read_system_data(folder):
    """Read system base voltage and power from system.csv."""
    sysfile = Path(folder) / "system.csv"

    if not sysfile.exists():
        raise FileNotFoundError(f"File not found: {sysfile}")

    df = pd.read_csv(sysfile)

    Vb_kV = float(df.loc[0, "V_base_kV"])
    Sb_MVA = float(df.loc[0, "S_base_MVA"])

    return Vb_kV, Sb_MVA


def read_bus_data(bus_file):
    """Read bus input data from CSV."""
    return pd.read_csv(Path(bus_file))


def read_branch_data(branch_file):
    """Read branch input data from CSV."""
    return pd.read_csv(Path(branch_file))


def read_csv_if_exists(file_path):
    """Read a CSV file if it exists, otherwise return None."""
    file_path = Path(file_path)

    if not file_path.exists():
        return None

    return pd.read_csv(file_path)