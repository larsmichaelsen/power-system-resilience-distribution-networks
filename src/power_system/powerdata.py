from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Bus:
    """
    Bus model used by the load-flow solver.

    Positive complex power represents load consumption.
    Bus type convention: 1 = PQ, 2 = PV, 3 = slack.
    """

    idx: int
    type: int
    v: complex = 1 + 0j
    s: complex = 0 + 0j
    vm_set: Optional[float] = None

    def __post_init__(self):
        self.v = complex(self.v)
        self.s = complex(self.s)


@dataclass
class Branch:
    """
    Fixed series branch model in per unit.

    The parameter b represents the total shunt susceptance.
    """

    idx: int
    from_bus: int
    to_bus: int
    r: float
    x: float
    b: float = 0.0

    Pmax_kW: Optional[float] = None
    I_max_A: Optional[float] = None
    I_max_pu: Optional[float] = None

    z: complex = field(init=False)

    def __post_init__(self):
        self.z = complex(self.r, self.x)


@dataclass
class DG:
    """
    Distributed generation model.

    Active and reactive power are stored in per unit.
    """

    bus: int
    P_pu: float
    Q_pu: float = 0.0

    P_min_pu: Optional[float] = None
    P_max_pu: Optional[float] = None

    def set_power_pu(self, P_pu: float):
        if self.P_min_pu is not None and P_pu < self.P_min_pu:
            raise ValueError("DG below minimum limit")

        if self.P_max_pu is not None and P_pu > self.P_max_pu:
            raise ValueError("DG above maximum limit")

        self.P_pu = P_pu


@dataclass
class RPC:
    """
    Reactive power compensation model.

    Positive Q_pu represents capacitive injection.
    """

    bus: int
    Q_pu: float


@dataclass
class Switch:
    """
    Switchable branch element.

    The impedance z is given in per unit.
    """

    idx: int
    from_bus: int
    to_bus: int
    z: complex
    closed: bool = False

    r: float = field(init=False)
    x: float = field(init=False)
    b: float = field(init=False, default=0.0)

    def __post_init__(self):
        self.z = complex(self.z)
        self.r = self.z.real
        self.x = self.z.imag
        self.b = 0.0


@dataclass
class ES:
    """
    Energy storage model.

    Power, energy, and state of charge are stored in per unit.
    """

    bus: int
    P_pu: float
    Q_pu: float = 0.0

    P_min_pu: Optional[float] = None
    P_max_pu: Optional[float] = None
    E_max_pu: Optional[float] = None
    soc_pu: Optional[float] = None


@dataclass
class PV:
    """
    Photovoltaic generation model.

    The available active power is stored in per unit.
    """

    bus: int
    P_max_pu: float