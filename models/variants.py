"""
"""

#[
from __future__ import annotations

import numpy
from numbers import Number

from ..quantities import get_max_qid
#]


class Variant:
    """
    Container for parameter variant specific attributes of a model
    """
    _missing = numpy.nan
    __slots__ = ["levels", "changes"]
    #[
    def __init__(self, quantities:Quantities, /, ) -> NoReturn:
        self._initilize_values(quantities)

    def _initilize_values(self, quantities:Quantities, /, ) -> NoReturn:
        max_qid = get_max_qid(quantities, )
        size_array = max_qid + 1
        self.levels = numpy.full((size_array,), self._missing, dtype=float, )
        self.changes = numpy.full((size_array,), self._missing, dtype=float, )

    def update_values_from_dict(self, update: dict, /, ) -> NoReturn:
        self.levels = update_levels_from_dict(self.levels, update, )
        self.changes = update_changes_from_dict(self.changes, update, )

    def update_levels_from_array(self, levels: numpy.ndarray, qids: Iterable[int], /, ) -> NoReturn:
        self.levels = update_from_array(self.levels, levels, qids, )

    def update_changes_from_array(self, changes: numpy.ndarray, qids: Iterable[int], /, ) -> NoReturn:
        self.changes = update_from_array(self.changes, changes, qids, )

    def create_steady_array(
        self, qid_to_logly,
        /,
        num_columns: int = 1,
    ) -> numpy.ndarray:
        """
        """
        return create_steady_array(self.levels, self.changes, qid_to_logly, num_columns, )
    #]


def create_steady_array(
    levels: numpy.ndarray,
    changes: numpy.ndarray,
    qid_to_logly: dict[int, bool],
    /,
    num_columns: int = 1,
) -> numpy.ndarray:
    """
    Create a steady array from levels and changes with a certain number of columns
    """
    levels = levels.reshape(-1, 1)
    changes = changes.reshape(-1, 1)
    steady_array = numpy.tile(levels, (1, num_columns))
    return steady_array


def update_from_array(
    values: numpy.ndarray,
    updated_values: numpy.ndarray,
    qids: list[int],
    /,
) -> numpy.ndarray:
    """
    Update variant levels or changes from an array and a list of qids
    """
    if updated_values is not None:
        values[qids] = updated_values.flat
    return values


def update_levels_from_dict(
    levels: numpy.ndarray,
    update: dict[int, Number|tuple],
    /,
) -> numpy.ndarray:
    """
    Update variant levels from a dictionary
    """
    for qid, new_value in update.items():
        new_value = new_value if isinstance(new_value, Number) else new_value[0]
        levels[qid] = new_value if new_value is not ... else levels[qid]
    return levels


def update_changes_from_dict(
    changes: numpy.ndarray,
    update: dict[int, Number|tuple],
    /,
) -> numpy.ndarray:
    """
    Update variant changes from a dictionary
    """
    for qid, new_value in update.items():
        new_value = ... if isinstance(new_value, Number) else new_value[1]
        changes[qid] = new_value if new_value is not ... else changes[qid]
    return changes


