from pathlib import Path

import matplotlib.pyplot as plt
import mplcursors
import pandas as pd

from src.power_system.network import Network
from src.power_system.fbs_solver import solve_fbs


def list_available_networks(base_path):
    """Return available network folders."""
    return sorted([p.name for p in base_path.iterdir() if p.is_dir()])


def choose_network(base_path):
    """Let the user select one available network folder."""
    networks = list_available_networks(base_path)

    if not networks:
        raise RuntimeError("No network folders found.")

    print("\nAvailable networks:")
    for i, name in enumerate(networks):
        print(f"{i}: {name}")

    while True:
        try:
            choice = int(input("Select network index: "))
            return networks[choice]
        except (ValueError, IndexError):
            print("Invalid selection. Try again.")


def main():
    base_path = Path("../networks")

    net_name = choose_network(base_path)
    folder = base_path / net_name

    network = Network.from_folder(folder)

    print(f"\nNetwork:  {net_name.upper()}")
    print(f"Buses:    {len(network.buses)}")
    print(f"Branches: {len(network.branches)}")
    print(f"Slack:    {network.slack}")

    results = solve_fbs(
        system=network,
        matrices=network.matrices,
        topo=network.topology,
    )

    print("\nPower flow results")
    print(f"Iterations:     {results.iter_count}")
    print(f"Solve time:     {results.solve_time:.6f} s")
    print(f"Min voltage:    {results.Vmag.min():.6f} p.u.")
    print(f"Max voltage:    {results.Vmag.max():.6f} p.u.")

    I_amp = results.Ibranch_mag * network.base_I
    print(f"Max branch current: {I_amp.max():.2f} A")

    buses = sorted(network.buses.keys())
    V = results.Vmag

    fig, ax = plt.subplots(figsize=(8, 5))
    line, = ax.plot(buses, V, linewidth=1.4)

    ax.set_xlabel("Bus index")
    ax.set_ylabel("Voltage magnitude [p.u.]")
    ax.set_title(f"Voltage profile – {net_name.upper()}")
    ax.grid(True, linestyle=":", linewidth=0.6)
    fig.tight_layout()

    cursor = mplcursors.cursor(line, hover=True)

    @cursor.connect("add")
    def on_add(sel):
        x, y = sel.target
        sel.annotation.set_text(
            f"Bus: {int(round(x))}\nVoltage: {y:.6f} p.u."
        )

    plt.show()

    voltage_df = pd.DataFrame(
        {
            "Bus": buses,
            "Voltage_pu": V,
            "Voltage_kV": V * network.base_V / 1000.0,
        }
    )

    output_path = Path(f"voltage_results_{net_name}.xlsx")
    voltage_df.to_excel(output_path, index=False)

    print(f"Results written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()