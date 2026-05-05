import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path


def load_voltage_data(base_path: Path) -> pd.DataFrame:
    """Load and combine radial and meshed voltage profiles."""
    df_meshed = pd.read_csv(base_path / "Meshed.csv")
    df_radial = pd.read_csv(base_path / "Radial.csv")

    df_radial_plot = pd.DataFrame({
        "Bus": df_radial["Bus"],
        "Voltage_pu": df_radial["Voltage_pu_radial"],
        "Case": "Radial",
    })

    df_meshed_plot = pd.DataFrame({
        "Bus": df_meshed["Bus"],
        "Voltage_pu": df_meshed["Voltage_pu_meshed"],
        "Case": "Meshed",
    })

    return pd.concat([df_radial_plot, df_meshed_plot], ignore_index=True)


def plot_voltage(df_plot: pd.DataFrame) -> None:
    """Plot voltage profile comparison for radial and meshed operation."""
    sns.set_theme(style="whitegrid", context="paper")

    fig, ax = plt.subplots(figsize=(6.2, 4.8))

    sns.lineplot(
        data=df_plot,
        x="Bus",
        y="Voltage_pu",
        hue="Case",
        style="Case",
        linewidth=1.5,
        ax=ax,
    )

    ax.set_xlabel("Bus number")
    ax.set_ylabel("Voltage (p.u.)")
    ax.set_xlim(df_plot["Bus"].min(), df_plot["Bus"].max())
    ax.set_ylim(0.95, 1.005)
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.7)
    ax.legend(frameon=False, title=None)

    fig.tight_layout()
    plt.show()


def main() -> None:
    base_path = Path(".")
    df_plot = load_voltage_data(base_path)
    plot_voltage(df_plot)


if __name__ == "__main__":
    main()