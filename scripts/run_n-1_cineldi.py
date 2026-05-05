from __future__ import annotations

import copy
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.power_system.network import Network
from src.power_system.fbs_solver import solve_fbs


def list_available_networks(base_path: Path) -> list[str]:
    """Return available network folders."""
    return sorted([p.name for p in base_path.iterdir() if p.is_dir()])


def choose_network(base_path: Path) -> str:
    """Let the user select one available network folder."""
    networks = list_available_networks(base_path)

    if not networks:
        raise RuntimeError(f"No network folders found in {base_path}")

    print("\nAvailable networks:")
    for i, name in enumerate(networks):
        print(f"{i}: {name}")

    while True:
        try:
            choice = int(input("Select network index: "))
            return networks[choice]
        except (ValueError, IndexError):
            print("Invalid selection. Try again.")


def get_total_active_load_MW(network: Network) -> float:
    """Return total positive active load in MW."""
    total_p_pu = 0.0

    for bus in network.buses.values():
        if bus.s.real > 0.0:
            total_p_pu += bus.s.real

    return total_p_pu * network.base_S / 1e6


def get_served_active_load_MW(network: Network, served_buses: set[int]) -> float:
    """Return active load served by the slack-connected component."""
    served_p_pu = 0.0

    for bus_id, bus in network.buses.items():
        if bus_id in served_buses and bus.s.real > 0.0:
            served_p_pu += bus.s.real

    return served_p_pu * network.base_S / 1e6


def get_disconnected_load_MW(
    network: Network,
    disconnected_buses: set[int],
) -> float:
    """Return active load disconnected from the slack-connected component."""
    disconnected_p_pu = 0.0

    for bus_id, bus in network.buses.items():
        if bus_id in disconnected_buses and bus.s.real > 0.0:
            disconnected_p_pu += bus.s.real

    return disconnected_p_pu * network.base_S / 1e6


def get_voltage_metrics_served(
    network: Network,
    results,
    v_min_limit: float,
) -> tuple[float, int, list[int]]:
    """Return minimum served-bus voltage and voltage-limit violations."""
    bus_order = list(network.topology.bus_order)
    voltage_map = {bus: vmag for bus, vmag in zip(bus_order, results.Vmag)}

    served_non_slack = [b for b in bus_order if b != network.slack]

    if served_non_slack:
        min_voltage = min(voltage_map[b] for b in served_non_slack)
    else:
        min_voltage = abs(network.buses[network.slack].v)

    undervoltage_buses = [
        b for b in served_non_slack
        if voltage_map[b] < v_min_limit
    ]

    return float(min_voltage), len(undervoltage_buses), sorted(undervoltage_buses)


def classify_contingency(
    plr: float,
    n_voltage_violations_served: int,
    converged: bool,
) -> str:
    """Classify the post-contingency operating state."""
    if not converged:
        return "non_converged"

    has_service_loss = plr < 1.0 - 1e-12
    has_voltage_issue = n_voltage_violations_served > 0

    if not has_service_loss and not has_voltage_issue:
        return "intact"
    if has_service_loss and not has_voltage_issue:
        return "service_loss_only"
    if not has_service_loss and has_voltage_issue:
        return "voltage_issue_only"

    return "service_loss_and_voltage_issue"


def evaluate_post_contingency_feasibility(
    converged: bool,
    plr: float,
    n_voltage_violations_served: int,
) -> tuple[bool, bool, bool]:
    """Evaluate service continuity, voltage feasibility, and case feasibility."""
    service_ok = plr >= 1.0 - 1e-12
    voltage_ok = n_voltage_violations_served == 0
    case_feasible = converged and voltage_ok

    return service_ok, voltage_ok, case_feasible


def evaluate_case(network: Network, v_min_limit: float) -> dict:
    """Evaluate one network state using load, voltage, and PLR indicators."""
    pre_contingency_load_MW = get_total_active_load_MW(network)

    served_buses = set(network.topology.bus_order)
    disconnected_buses = set(network.buses.keys()) - served_buses

    post_contingency_served_load_MW = get_served_active_load_MW(
        network,
        served_buses,
    )
    disconnected_load_MW = get_disconnected_load_MW(
        network,
        disconnected_buses,
    )
    unsupplied_load_MW = max(
        pre_contingency_load_MW - post_contingency_served_load_MW,
        0.0,
    )

    plr = (
        post_contingency_served_load_MW / pre_contingency_load_MW
        if pre_contingency_load_MW > 0.0
        else 1.0
    )

    try:
        results = solve_fbs(
            system=network,
            matrices=network.matrices,
            topo=network.topology,
        )
        converged = True
        error = ""
    except Exception as exc:
        converged = False
        error = str(exc)
        results = None

    if converged:
        min_voltage_pu_served, n_voltage_violations_served, undervoltage_buses_served = (
            get_voltage_metrics_served(
                network=network,
                results=results,
                v_min_limit=v_min_limit,
            )
        )

        if len(results.Ibranch_mag) > 0:
            max_branch_current_A = float((results.Ibranch_mag * network.base_I).max())
        else:
            max_branch_current_A = 0.0

        iterations = int(results.iter_count)
        solve_time_s = float(results.solve_time)
    else:
        min_voltage_pu_served = None
        n_voltage_violations_served = None
        undervoltage_buses_served = []
        max_branch_current_A = None
        iterations = None
        solve_time_s = None

    service_ok, voltage_ok, case_feasible = evaluate_post_contingency_feasibility(
        converged=converged,
        plr=plr,
        n_voltage_violations_served=(
            0 if n_voltage_violations_served is None else n_voltage_violations_served
        ),
    )

    contingency_class = classify_contingency(
        plr=plr,
        n_voltage_violations_served=(
            0 if n_voltage_violations_served is None else n_voltage_violations_served
        ),
        converged=converged,
    )

    return {
        "converged": converged,
        "error": error,
        "pre_contingency_load_MW": float(pre_contingency_load_MW),
        "post_contingency_served_load_MW": float(post_contingency_served_load_MW),
        "unsupplied_load_MW": float(unsupplied_load_MW),
        "disconnected_load_MW": float(disconnected_load_MW),
        "plr": float(plr),
        "service_ok": bool(service_ok),
        "voltage_ok": bool(voltage_ok),
        "case_feasible": bool(case_feasible),
        "contingency_class": contingency_class,
        "min_voltage_pu_served": min_voltage_pu_served,
        "n_voltage_violations_served": n_voltage_violations_served,
        "undervoltage_buses_served": ",".join(map(str, undervoltage_buses_served)),
        "n_disconnected_buses": int(len(disconnected_buses)),
        "disconnected_buses": ",".join(map(str, sorted(disconnected_buses))),
        "iterations": iterations,
        "solve_time_s": solve_time_s,
        "max_branch_current_A": max_branch_current_A,
    }


def evaluate_single_branch_outage(
    base_network: Network,
    branch_id: int,
    v_min_limit: float,
) -> dict:
    """Evaluate one N-1 branch outage."""
    network = copy.deepcopy(base_network)

    if branch_id not in network.branches:
        raise KeyError(f"Unknown branch id: {branch_id}")

    removed_branch = network.branches.pop(branch_id)
    network.rebuild_topology_and_matrices()

    row = evaluate_case(network, v_min_limit=v_min_limit)
    row.update(
        {
            "branch_removed": int(branch_id),
            "from_bus": int(removed_branch.from_bus),
            "to_bus": int(removed_branch.to_bus),
        }
    )

    return row


def run_n_minus_1(
    base_network: Network,
    v_min_limit: float = 0.95,
) -> tuple[dict, pd.DataFrame]:
    """Run the base case and all single-branch outage cases."""
    print("\nRunning base case...")
    base_case = evaluate_case(copy.deepcopy(base_network), v_min_limit=v_min_limit)

    branch_ids = sorted(base_network.branches.keys())
    rows = []

    print(f"Running N-1 for {len(branch_ids)} branches...")

    for i, branch_id in enumerate(branch_ids, start=1):
        row = evaluate_single_branch_outage(
            base_network=base_network,
            branch_id=branch_id,
            v_min_limit=v_min_limit,
        )
        rows.append(row)

        print(
            f"[{i:>3}/{len(branch_ids)}] "
            f"branch {row['branch_removed']} "
            f"({row['from_bus']}->{row['to_bus']}), "
            f"PLR={row['plr']:.4f}, "
            f"class={row['contingency_class']}"
        )

    df = pd.DataFrame(rows).sort_values("branch_removed").reset_index(drop=True)

    return base_case, df


def print_base_case(base_case: dict) -> None:
    """Print the base-case load-flow summary."""
    print("\nBase case summary")
    print(f"Converged:                     {base_case['converged']}")
    print(f"Pre-contingency load [MW]:    {base_case['pre_contingency_load_MW']:.6f}")
    print(f"Served load [MW]:             {base_case['post_contingency_served_load_MW']:.6f}")
    print(f"Unsupplied load [MW]:         {base_case['unsupplied_load_MW']:.6f}")
    print(f"Disconnected load [MW]:       {base_case['disconnected_load_MW']:.6f}")
    print(f"PLR [-]:                      {base_case['plr']:.6f}")
    print(f"Min voltage served [p.u.]:    {base_case['min_voltage_pu_served']:.6f}")
    print(f"Voltage violations served:    {base_case['n_voltage_violations_served']}")
    print(f"Disconnected buses:           {base_case['n_disconnected_buses']}")
    print(f"Iterations:                   {base_case['iterations']}")
    print(f"Solve time [s]:               {base_case['solve_time_s']:.6f}")
    print(f"Max branch current [A]:       {base_case['max_branch_current_A']:.2f}")


def print_overall_summary(results_df: pd.DataFrame, v_min_limit: float) -> None:
    """Print an aggregate summary of the N-1 screening results."""
    print("\nN-1 summary")
    print(f"Number of contingencies:             {len(results_df)}")
    print(f"Converged cases:                     {int(results_df['converged'].sum())}")
    print(f"Cases with service interruption:     {int((results_df['plr'] < 1.0).sum())}")
    print(
        f"Cases with served Vmin < {v_min_limit}:    "
        f"{int((results_df['min_voltage_pu_served'] < v_min_limit).sum())}"
    )
    print(f"Worst PLR:                           {results_df['plr'].min():.6f}")
    print(
        f"Worst served Vmin [p.u.]:            "
        f"{results_df['min_voltage_pu_served'].min():.6f}"
    )
    print("\nContingency class counts:")
    print(results_df["contingency_class"].value_counts())


def save_results(
    network_name: str,
    base_case: dict,
    results_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Save base-case and N-1 screening results to CSV and Excel files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    base_df = pd.DataFrame([base_case])

    results_csv = output_dir / f"n1_results_{network_name}.csv"
    results_xlsx = output_dir / f"n1_results_{network_name}.xlsx"
    base_csv = output_dir / f"base_case_{network_name}.csv"
    base_xlsx = output_dir / f"base_case_{network_name}.xlsx"

    results_df.to_csv(results_csv, index=False)
    results_df.to_excel(results_xlsx, index=False)

    base_df.to_csv(base_csv, index=False)
    base_df.to_excel(base_xlsx, index=False)

    print(f"\nSaved contingency results to: {results_csv.resolve()}")
    print(f"Saved contingency results to: {results_xlsx.resolve()}")
    print(f"Saved base case to:          {base_csv.resolve()}")
    print(f"Saved base case to:          {base_xlsx.resolve()}")


def plot_results(
    results_df: pd.DataFrame,
    network_name: str,
    v_min_limit: float,
    output_dir: Path,
) -> None:
    """Plot PLR and minimum served-bus voltage for the N-1 screening."""
    output_dir.mkdir(parents=True, exist_ok=True)

    x = results_df["branch_removed"]

    fig1, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(x, results_df["plr"], linewidth=1.4)
    ax1.set_xlabel("Removed branch")
    ax1.set_ylabel("PLR [-]")
    ax1.set_title(f"N-1 preserved load ratio – {network_name.upper()}")
    ax1.grid(True, linestyle=":", linewidth=0.6)
    fig1.tight_layout()
    fig1.savefig(output_dir / f"n1_plr_{network_name}.png", dpi=200)

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.plot(x, results_df["min_voltage_pu_served"], linewidth=1.4)
    ax2.axhline(v_min_limit, linestyle="--", linewidth=1.0)
    ax2.set_xlabel("Removed branch")
    ax2.set_ylabel("Minimum voltage of served buses [p.u.]")
    ax2.set_title(f"N-1 minimum served voltage – {network_name.upper()}")
    ax2.grid(True, linestyle=":", linewidth=0.6)
    fig2.tight_layout()
    fig2.savefig(output_dir / f"n1_vmin_{network_name}.png", dpi=200)

    plt.show()


def main():
    base_path = Path(__file__).resolve().parents[1] / "networks"
    output_dir = Path(__file__).resolve().parents[1] / "results" / "n1"

    v_min_limit = 0.95

    net_name = choose_network(base_path)
    folder = base_path / net_name

    network = Network.from_folder(folder)

    print(f"\nNetwork:  {net_name.upper()}")
    print(f"Buses:    {len(network.buses)}")
    print(f"Branches: {len(network.branches)}")
    print(f"Slack:    {network.slack}")

    base_case, results_df = run_n_minus_1(
        base_network=network,
        v_min_limit=v_min_limit,
    )

    print_base_case(base_case)
    print_overall_summary(results_df, v_min_limit=v_min_limit)

    save_results(
        network_name=net_name,
        base_case=base_case,
        results_df=results_df,
        output_dir=output_dir,
    )

    plot_results(
        results_df=results_df,
        network_name=net_name,
        v_min_limit=v_min_limit,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()