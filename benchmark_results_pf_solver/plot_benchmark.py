import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np


def load_csv(path: Path):
    """Load CSV file with columns: Bus, Voltage_pu."""
    df = pd.read_csv(path)
    df = df.sort_values("Bus")
    return df["Bus"].values, df["Voltage_pu"].values


def plot_voltage(buses1, v1, buses2, v2, title, label1, label2):
    """Plot two voltage profiles with identical styling."""
    plt.figure(figsize=(8, 5))

    plt.plot(buses1, v1, linewidth=1.4, label=label1)
    plt.plot(buses2, v2, linewidth=1.4, label=label2)

    plt.title(title)
    plt.xlabel("Bus")
    plt.ylabel("Voltage [p.u.]")
    plt.grid(True, linestyle=":", linewidth=0.6)
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_difference(buses, diff, title, label):
    """Plot absolute difference between two voltage profiles."""
    plt.figure(figsize=(8, 5))

    plt.plot(buses, diff, linewidth=1.4, label=label)

    plt.title(title)
    plt.xlabel("Bus")
    plt.ylabel("Voltage Difference [p.u.]")
    plt.grid(True, linestyle=":", linewidth=0.6)
    plt.legend()
    plt.tight_layout()
    plt.show()


def main():
    base = Path(__file__).parent


    # IEEE 33
    buses_fbs_33, v_fbs_33 = load_csv(base / "IEEE33" / "FBS.csv")
    buses_ref_33, v_ref_33 = load_csv(base / "IEEE33" / "PyDSAL.csv")

    plot_voltage(
        buses_fbs_33, v_fbs_33,
        buses_ref_33, v_ref_33,
        title="Voltage Magnitude Profile (IEEE 33-Bus)",
        label1="FBS",
        label2="PyDSAL"
    )

    diff_33 = np.abs(v_fbs_33 - v_ref_33)
    plot_difference(
        buses_fbs_33, diff_33,
        title="Voltage Difference |FBS − PyDSAL| (IEEE 33-Bus)",
        label="|FBS − PyDSAL|"
    )


    # IEEE 69
    buses_fbs_69, v_fbs_69 = load_csv(base / "IEEE69" / "FBS.csv")
    buses_ref_69, v_ref_69 = load_csv(base / "IEEE69" / "PyDSAL.csv")

    plot_voltage(
        buses_fbs_69, v_fbs_69,
        buses_ref_69, v_ref_69,
        title="Voltage Magnitude Profile (IEEE 69-Bus)",
        label1="FBS",
        label2="PyDSAL"
    )

    diff_69 = np.abs(v_fbs_69 - v_ref_69)
    plot_difference(
        buses_fbs_69, diff_69,
        title="Voltage Difference |FBS − PyDSAL| (IEEE 69-Bus)",
        label="|FBS − PyDSAL|"
    )


    # CINELDI (Bus 1–124)
    buses_fbs_c, v_fbs_c = load_csv(base / "CINELDI" / "FBS.csv")
    buses_ref_c, v_ref_c = load_csv(base / "CINELDI" / "CINELDI.csv")

    plot_voltage(
        buses_fbs_c, v_fbs_c,
        buses_ref_c, v_ref_c,
        title="Voltage Magnitude Profile (CINELDI MV, Bus 1–124)",
        label1="FBS",
        label2="Pandapower (CINELDI)"
    )

    diff_c = np.abs(v_fbs_c - v_ref_c)
    plot_difference(
        buses_fbs_c, diff_c,
        title="Voltage Difference |FBS − Pandapower| (CINELDI)",
        label="|FBS − Pandapower|"
    )


if __name__ == "__main__":
    main()
