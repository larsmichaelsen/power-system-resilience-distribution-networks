from dataclasses import dataclass

import numpy as np


@dataclass
class PowerFlowResults:
    """
    Store load-flow results and derived branch-loss quantities.

    The voltage and branch-current arrays are stored in per unit. The system
    power base is given in VA and is used to convert losses to MW and MVAr.
    """

    V: np.ndarray
    I_branch: np.ndarray
    branch_R: np.ndarray
    branch_X: np.ndarray
    base_S: float
    iter_count: int
    solve_time: float

    def __post_init__(self):
        I2 = np.abs(self.I_branch) ** 2

        self.losses_pu = I2 * self.branch_R
        self.total_loss_pu = float(self.losses_pu.sum())

        self.reactive_losses_pu = I2 * self.branch_X
        self.total_reactive_loss_pu = float(self.reactive_losses_pu.sum())

    @property
    def Vmag(self):
        return np.abs(self.V)

    @property
    def Vangle_deg(self):
        return np.degrees(np.angle(self.V))

    @property
    def Ibranch_mag(self):
        return np.abs(self.I_branch)

    @property
    def Ibranch_angle_deg(self):
        return np.degrees(np.angle(self.I_branch))

    @property
    def P_loss_MW(self):
        return self.losses_pu * self.base_S / 1e6

    @property
    def Q_loss_MVAr(self):
        return self.reactive_losses_pu * self.base_S / 1e6

    @property
    def total_loss_MW(self):
        return float(self.total_loss_pu * self.base_S) / 1e6

    @property
    def total_loss_MVAr(self):
        return float(self.total_reactive_loss_pu * self.base_S) / 1e6

    def summary(self):
        print("Power flow summary")
        print(f"Minimum voltage magnitude: {self.Vmag.min():.4f} p.u.")
        print(f"Maximum voltage magnitude: {self.Vmag.max():.4f} p.u.")
        print(f"Total active losses: {self.total_loss_pu:.6f} p.u.")
        print(f"Total reactive losses: {self.total_reactive_loss_pu:.6f} p.u.")