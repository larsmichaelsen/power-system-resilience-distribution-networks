# Distribution-Network Load Flow and Contingency Analysis

This repository contains a Python-based framework for steady-state load-flow analysis and preliminary N-1 contingency screening in electric power distribution networks. The implementation is based on the Forward-Backward Sweep (FBS) method and supports both radial and weakly meshed network configurations.

The code was developed as part of a master's thesis at the Norwegian University of Science and Technology (NTNU), Department of Electric Energy. It is intended for academic use, with emphasis on transparency, modularity, and reproducibility in load-flow-based resilience studies.

## Features

- Forward-Backward Sweep load-flow solver
- Automatic construction of BIBC, BCBV, and DLF matrices
- Support for radial and weakly meshed distribution networks
- Loop-current correction for weakly meshed operation
- Per-unit conversion with configurable base values
- Slack, PQ, and PV bus representation
- Support for switches, distributed generation, reactive power compensation, and energy storage input files
- Voltage, branch-current, and loss calculation
- Preliminary N-1 branch-contingency screening
- Preserved load ratio (PLR) and disconnected-load indicators
- Export of results to CSV and Excel
- Plotting of voltage profiles and contingency results

## Input Data Format

Each network is defined in a separate folder under `networks/`.

Required files:

- `system.csv` -- base voltage and base power
- `bus.csv` -- bus type, load data, and initial voltage
- `branch.csv` -- fixed line and cable data

Optional files:

- `switch.csv` -- switchable branches
- `dg.csv` -- distributed generation
- `rpc.csv` -- reactive power compensation
- `es.csv` -- energy storage units

All supported input formats are converted internally to a common per-unit representation.

## Usage

Run an interactive load-flow study:

```bash
python scripts/run_pf.py
```


## Method Overview

The FBS formulation uses topology-based matrix construction. The BIBC matrix maps bus current injections to branch currents, while the BCBV matrix maps branch currents to bus-voltage drops. Their product forms the DLF matrix used in the iterative voltage solution. For weakly meshed networks, closed tie branches are represented through loop-current variables and incorporated using a reduced DLF formulation.




## Assumptions and Limitations

- Balanced single-phase equivalent modelling
- Steady-state operation only
- Deterministic branch contingencies
- No chronological repair or time-dependent recovery modelling
- No detailed protection modelling
- No voltage regulator or transformer tap control modelling
- Not intended as an operational distribution-system analysis tool

PLR should be interpreted as a post-contingency load-preservation indicator, not as a complete resilience metric.



## Dependencies

- Python 3.10 or newer
- NumPy
- Pandas
- Matplotlib
- mplcursors
- openpyxl




