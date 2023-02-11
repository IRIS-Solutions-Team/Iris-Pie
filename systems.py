"""
# First-order system and solution

## Unsolved system

$$
A E[x_t] + B E[x_{t-1}] + C + D v_t = 0 \\
F y_t + G x_t + H + J w_t = 0
$$
"""


#[
from __future__ import annotations

import dataclasses
import numpy 
#]


@dataclasses.dataclass
class System:
    """
    Unsolved system matrices
    """
    # Transition equations
    A: numpy.ndarray | None = None
    B: numpy.ndarray | None = None
    C: numpy.ndarray | None = None
    D: numpy.ndarray | None = None
    # Measurement equations
    E: numpy.ndarray | None = None
    B: numpy.ndarray | None = None
    C: numpy.ndarray | None = None
    D: numpy.ndarray | None = None

