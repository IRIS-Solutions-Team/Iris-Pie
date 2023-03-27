"""
# Descriptor for first-order systems and solutions

## Unsolved system

$$
A E[x_t] + B E[x_{t-1}] + C + D v_t = 0 \\
F y_t + G x_t + H + J w_t = 0
$$

## State-space solution

$$
x_t = T x{t-1} + K + R v_t \\
y_t = Z x_t + D + H w_t
$$

"""


#[
from __future__ import annotations
# from IPython import embed

import itertools as it_
import dataclasses as dc_
import numpy as np_
from typing import Self, NoReturn
from collections.abc import Iterable

from ..aldi import engines as ad_
from .. import (incidence as in_, equations as eq_, quantities as qu_, )
#]


@dc_.dataclass
class Descriptor:
    """
    """
    #[
    system_vectors: SystemVectors | None = None
    solution_vectors: SolutionVectors | None = None
    system_map: SystemMap | None = None
    system_differn_context: al_.Context | None = None

    def __init__(self, equations, quantities, /,) -> NoReturn:
        self.system_vectors = SystemVectors(equations, quantities)
        self.solution_vectors = SolutionVectors(self.system_vectors)
        self.system_map = SystemMap(self.system_vectors)
        self.system_differn_context = ad_.Context.for_equations(
           ad_.DiffernAtom, 
           self.system_vectors.generate_system_equations_from_equations(equations),
           self.system_vectors.eid_to_wrt_tokens,
        )

    def get_num_backwards(self: Self) -> int:
        return self.system_vectors.get_num_backwards()

    def get_num_forwards(self: Self) -> int:
        return self.system_vectors.get_num_forwards()
    #]


@dc_.dataclass
class SystemVectors:
    """
    Vectors of quantities and equation ids in first-order system matrices
    """
    #[
    transition_eids: Iterable[int] | None = None
    measurement_eids: Iterable[int] | None = None
    eid_to_wrt_tokens: dict[int, in_.Tokens] | None = None
    #
    transition_variables: in_.Tokens | None = None
    initial_conditions: Iterable[bool] | None = None,
    transition_shocks: in_.Tokens | None = None 
    measurement_variables: in_.Tokens | None = None
    measurement_shocks: in_.Tokens | None = None 
    #
    shape_AB_excl_dynid: tuple[int, int] | None = None
    shape_C_excl_dynid: tuple[int, int] | None = None
    shape_D_excl_dynid: tuple[int, int] | None = None
    shape_F: tuple[int, int] | None = None
    shape_G: tuple[int, int] | None = None
    shape_H: tuple[int, int] | None = None

    def __init__(self, equations: eq_.Equations, quantities: qu_.Quantities) -> NoReturn:
        """
        Construct system vectors from a list of equations and a list of quantities
        """
        self.transition_eids = sorted([eqn.id for eqn in equations if eqn.kind in eq_.EquationKind.TRANSITION_EQUATION])
        self.measurement_eids = sorted([eqn.id for eqn in equations if eqn.kind in eq_.EquationKind.MEASUREMENT_EQUATION])
        qid_to_kind = qu_.create_qid_to_kind(quantities)
        all_tokens = set(eq_.generate_all_tokens_from_equations(equations))
        all_wrt_tokens = set(in_.generate_tokens_of_kinds(all_tokens, qid_to_kind, qu_.QuantityKind.SYSTEM_QUANTITY))
        self.eid_to_wrt_tokens = eq_.create_eid_to_wrt_tokens(equations, all_wrt_tokens)
        #
        actual_tokens_transition_variables = set(in_.generate_tokens_of_kinds(all_tokens, qid_to_kind, qu_.QuantityKind.TRANSITION_VARIABLE))
        #
        # Make adjustment for transition variables in measurement
        # equations: each x(t-k) in measurement neecds to be in the current
        # dated (LHS) vector of transition variables; this is done by
        # pretending x(t-k-1) is needed
        adjusted_tokens_transition_variables = _adjust_for_measurement_equations(actual_tokens_transition_variables, equations, qid_to_kind)
        #
        self.transition_variables = in_.sort_tokens(_create_system_transition_vector(adjusted_tokens_transition_variables))
        self.initial_conditions = [ in_.Token(t.qid, t.shift-1) in actual_tokens_transition_variables and t.shift <= 0 for t in self.transition_variables ]
        self.transition_shocks = in_.sort_tokens(in_.generate_tokens_of_kinds(all_tokens, qid_to_kind, qu_.QuantityKind.TRANSITION_SHOCK))
        #
        self.measurement_variables = in_.sort_tokens(in_.generate_tokens_of_kinds(all_tokens, qid_to_kind, qu_.QuantityKind.MEASUREMENT_VARIABLE))
        self.measurement_shocks = in_.sort_tokens(in_.generate_tokens_of_kinds(all_tokens, qid_to_kind, qu_.QuantityKind.MEASUREMENT_SHOCK))
        #
        self.shape_AB_excl_dynid = (len(self.transition_eids), len(self.transition_variables))
        self.shape_C_excl_dynid = (len(self.transition_eids), 1)
        self.shape_D_excl_dynid = (len(self.transition_eids), len(self.transition_shocks))
        #
        self.shape_F = (len(self.measurement_eids), len(self.measurement_variables))
        self.shape_G = (len(self.measurement_eids), len(self.transition_variables))
        self.shape_H = (len(self.measurement_eids), 1)
        self.shape_J = (len(self.measurement_eids), len(self.measurement_shocks))

    def get_num_backwards(self) -> int:
        return _get_num_backwards(self.transition_variables)

    def get_num_forwards(self) -> int:
        return _get_num_forwards(self.transition_variables)

    def generate_system_equations_from_equations(
        self,
        equations: eq_.Equations,
        /
    ) -> eq_.Equations:
        eid_to_equation = { eqn.id:eqn for eqn in equations }
        system_eids = self.transition_eids + self.measurement_eids
        return ( eid_to_equation[eid] for eid in system_eids )
    #]


@dc_.dataclass
class SolutionVectors:
    """
    Vectors of quantities in first-order solution matrices
    """
    #[
    transition_variables: in_.Tokens | None = None
    initial_conditions: Iterable[bool] | None = None,
    transition_shocks: in_.Tokens | None = None 
    measurement_variables: in_.Tokens | None = None
    measurement_shocks: in_.Tokens | None = None 

    def __init__(self, system_vectors: SystemVectors, /, ) -> NoReturn:
        """
        Construct solution vectors and initial conditions indicator
        """
        self.transition_variables, self.initial_conditions = _solution_vector_from_system_vector(system_vectors.transition_variables, system_vectors.initial_conditions)
        self.transition_shocks = system_vectors.transition_shocks
        self.measurement_variables = system_vectors.measurement_variables
        self.measurement_shocks = system_vectors.measurement_shocks

    def get_initials(
        self,
        /, 
        kind: Literal["required"] | Literal["discarded"] = "required",
    ) -> in_.Tokens:
        """
        Get tokens representing required initial conditions
        """
        return list(it_.compress(self.transition_variables, self.initial_conditions))
    #]


def _create_system_transition_vector(tokens_transition_variables: in_.Tokens, /, ) -> in_.Tokens:
    """
    From tokens of transition variables, create vector of transition variables
    along columns of matrix A in unsolved system
    """
    #[
    tokens_transition_variables = set(tokens_transition_variables)
    min_shifts = in_.get_some_shift_by_quantities(tokens_transition_variables, lambda x: min(min(x), -1))
    max_shifts = in_.get_some_shift_by_quantities(tokens_transition_variables, max)
    #
    vector_for_id = lambda qid: [in_.Token(qid, sh) for sh in range(min_shifts[qid]+1, max_shifts[qid]+1)]
    unique_ids = set(t.qid for t in tokens_transition_variables)
    return it_.chain.from_iterable(vector_for_id(i) for i in unique_ids)
    #]


def _solution_vector_from_system_vector(
    system_transition_vector: in_.Tokens, 
    initial_conditions: Iterable[bool],
    /,
) -> in_.Tokens:
    """
    From sorted system vector, get vector of transition variables in solved
    system and the indicator of required initial conditions
    """
    num_forwards = _get_num_forwards(system_transition_vector)
    return system_transition_vector[num_forwards:], initial_conditions[num_forwards:]


def _get_num_forwards(system_transition_vector: in_.Tokens):
    """
    Number of forward-looking tokens in a vector of tokens
    """
    return sum(1 for t in system_transition_vector if t.shift>0)


def _get_num_backwards(system_transition_vector: in_.Tokens):
    """
    Number of backward-looking tokens in a vector of tokens
    """
    return len(system_transition_vector) - _get_num_forwards(system_transition_vector)


@dc_.dataclass
class SystemMap:
    """
    """
    #[
    A: _ArrayMap | None = None
    B: _ArrayMap | None = None
    C: None = None
    D: _ArrayMap | None = None
    dynid_A: np_.ndarray | None = None
    dynid_B: np_.ndarray | None = None
    dynid_C: np_.ndarray | None = None
    dynid_D: np_.ndarray | None = None
    #
    F: _ArrayMap | None = None
    G: _ArrayMap | None = None
    H: None = None
    J: _ArrayMap | None = None

    def __init__(
        self,
        system_vectors: SystemVectors,
    ) -> NoReturn:
        """
        """

        system_eids = system_vectors.transition_eids + system_vectors.measurement_eids
        rhs_offsets = list(it_.accumulate(
            len(system_vectors.eid_to_wrt_tokens[eid]) 
            for eid in system_eids
        ))
        rhs_offsets.pop()
        rhs_offsets.insert(0, 0)
        eid_to_rhs_offset = dict(zip(system_eids, rhs_offsets))
        #
        # Transition equations
        #
        self.A = vstack_array_maps(
            _ArrayMap.for_equation(
                system_vectors.eid_to_wrt_tokens[eid],
                system_vectors.transition_variables,
                eid_to_rhs_offset[eid],
                lhs_row,
            )
            for lhs_row, eid in enumerate(system_vectors.transition_eids)
        )

        lagged_transition_variables = [ t.shifted(-1) for t in system_vectors.transition_variables ]
        lagged_transition_variables = [ 
            t if t not in system_vectors.transition_variables else None 
            for t in lagged_transition_variables 
        ]
        self.B = vstack_array_maps(
            _ArrayMap.for_equation(
                system_vectors.eid_to_wrt_tokens[eid],
                lagged_transition_variables, 
                eid_to_rhs_offset[eid],
                lhs_row,
            )
            for lhs_row, eid in enumerate(system_vectors.transition_eids)
        )
        #
        self.A._remove_nones()
        self.B._remove_nones()
        #
        self.C = _ArrayMap.constant_vector(system_vectors.transition_eids)
        #
        self.D = vstack_array_maps(
            _ArrayMap.for_equation(
                system_vectors.eid_to_wrt_tokens[eid],
                system_vectors.transition_shocks,
                eid_to_rhs_offset[eid],
                lhs_row,
            )
            for lhs_row, eid in enumerate(system_vectors.transition_eids)
        )
        #
        num_dynid_rows = len(system_vectors.transition_variables) - len(system_vectors.transition_eids)
        self.dynid_A, self.dynid_B = _create_dynid_matrices(system_vectors.transition_variables, )
        self.dynid_C = np_.zeros((num_dynid_rows, system_vectors.shape_C_excl_dynid[1]), dtype=float, )
        self.dynid_D = np_.zeros((num_dynid_rows, system_vectors.shape_D_excl_dynid[1]), dtype=float, )
        #
        # Measurement equations
        #
        self.F = vstack_array_maps(
            _ArrayMap.for_equation(
                system_vectors.eid_to_wrt_tokens[eid],
                system_vectors.measurement_variables, 
                eid_to_rhs_offset[eid],
                lhs_row,
            )
            for lhs_row, eid in enumerate(system_vectors.measurement_eids)
        )

        self.G = vstack_array_maps(
            _ArrayMap.for_equation(
                system_vectors.eid_to_wrt_tokens[eid],
                system_vectors.transition_variables, 
                eid_to_rhs_offset[eid],
                lhs_row,
            )
            for lhs_row, eid in enumerate(system_vectors.measurement_eids)
        )

        self.H = _ArrayMap.constant_vector(system_vectors.measurement_eids)

        self.J = vstack_array_maps(
            _ArrayMap.for_equation(
                system_vectors.eid_to_wrt_tokens[eid],
                system_vectors.measurement_shocks, 
                eid_to_rhs_offset[eid],
                lhs_row,
            )
            for lhs_row, eid in enumerate(system_vectors.measurement_eids)
        )
    #]


def _create_dynid_matrices(system_transition_vector: in_.Tokens):
    """
    Create dynamic identity matrix for unsolved system
    """
    #[
    max_shifts = in_.get_some_shift_by_quantities(system_transition_vector, max)
    #
    index_A = ([], [])
    index_B = ([], [])
    row_count = 0
    for i, t in enumerate(system_transition_vector):
        if t.shift==max_shifts[t.qid]:
            continue
        j = system_transition_vector.index(t.shifted(+1))
        index_A[0].append(row_count)
        index_A[1].append(i)
        index_B[0].append(row_count)
        index_B[1].append(j)
        row_count += 1
    #
    num_columns = len(system_transition_vector)
    dynid_A = np_.zeros((row_count, num_columns), dtype=float)
    dynid_B = np_.zeros((row_count, num_columns), dtype=float)
    dynid_A[index_A] = 1
    dynid_B[index_B] = -1
    return dynid_A, dynid_B
    #]


class _ArrayMap:
    """
    """
    #[
    def __init__(self) -> NoReturn:
        self.lhs = ([], [])
        self.rhs = ([], [])

    def __len__(self: Self) -> int:
        return len(self.lhs[0])

    def append(
        self,
        lhs: tuple[int, int], 
        rhs: tuple[int, int],
        /
    ) -> NoReturn:
        """
        """
        self.lhs[0].append(lhs[0])
        self.lhs[1].append(lhs[1])
        self.rhs[0].append(rhs[0])
        self.rhs[1].append(rhs[1])
        # self.lhs = (self.lhs[0]+[lhs[0]], self.lhs[1]+[lhs[1]])
        # self.rhs = (self.rhs[0]+[rhs[0]], self.rhs[1]+[rhs[1]])

    def merge_with(
        self,
        other: Self,
    ) -> NoReturn:
        """
        """
        self.lhs = (self.lhs[0]+other.lhs[0], self.lhs[1]+other.lhs[1])
        self.rhs = (self.rhs[0]+other.rhs[0], self.rhs[1]+other.rhs[1])

    def offset(
        self,
        lhs_row: int, 
        rhs_row_offset: int,
    ) -> NoReturn:
        """
        """
        self.lhs = ([lhs_row if i is not None else None for i in self.lhs[0]], self.lhs[1])
        self.rhs = ([i+rhs_row_offset if i is not None else None for i in self.rhs[0]], self.rhs[1])

    def _remove_nones(self) -> NoReturn:
        """
        """
        if not self.lhs[0]:
            return
        zipped_pruned = [
            i for i in zip(self.lhs[0], self.lhs[1], self.rhs[0], self.rhs[1])
            if i[0] is not None
        ]
        unzipped_pruned = list(zip(*zipped_pruned))
        self.lhs = (list(unzipped_pruned[0]), list(unzipped_pruned[1]))
        self.rhs = (list(unzipped_pruned[2]), list(unzipped_pruned[3]))


    @classmethod
    def for_equation(
        cls,
        tokens_in_equation_on_rhs: in_.Tokens,
        tokens_in_columns_on_lhs: in_.Tokens,
        rhs_offset: int,
        lhs_row: int,
    ) -> Self:
        """
        """
        index = tokens_in_columns_on_lhs.index
        raw_map = (
            (lhs_row, index(t), rhs_row, 0) 
            for rhs_row, t in enumerate(tokens_in_equation_on_rhs, start=rhs_offset)
            if t in tokens_in_columns_on_lhs
        )
        # Collect all lhr_rows, all lhs_columns, all rhs_rows, all rhs_columns
        raw_map = zip(*raw_map)
        map = cls()
        try:
            map.lhs = (list(next(raw_map)), list(next(raw_map)))
            map.rhs = (list(next(raw_map)), list(next(raw_map)))
        except:
            map.lhs = ([], [])
            map.rhs = ([], [])
        # Equivalent to:
        # map = cls()
        # for rhs_row, t in enumerate(tokens_in_equation_on_rhs, start=rhs_offset):
            # if t in tokens_in_columns_on_lhs:
                # lhs_column = tokens_in_columns_on_lhs.index(t)
                # map.append((lhs_row, lhs_column), (rhs_row, 0))
        return map

    @classmethod
    def constant_vector(
        cls,
        eids: Iterable[int],
    ) -> Self:
        """
        """
        num_equations = len(eids)
        self = cls()
        self.lhs = (list(range(num_equations)), [0]*num_equations)
        self.rhs = (list(eids), [0]*num_equations)
        return self
    #]

def vstack_array_maps(maps: Iterable[_ArrayMap]) -> _ArrayMap:
    """
    """
    #[
    stacked_map = _ArrayMap()
    for m in maps:
        stacked_map.merge_with(m)
    return stacked_map
    #]


def _adjust_for_measurement_equations(
    tokens_transition_variables: qu_.Quantities,
    equations: eq_.Equations,
    qid_to_kind: dict[int, qu_.QuantityKind],
    /,
) -> qu_.Quantities:
    tokens_in_measurement_equations = it_.chain.from_iterable(e.incidence for e in equations if e.kind is eq_.EquationKind.MEASUREMENT_EQUATION)
    pretend_needed = [
        in_.Token(t.qid, t.shift-1) for t in tokens_in_measurement_equations
        if qid_to_kind[t.qid] in qu_.QuantityKind.TRANSITION_VARIABLE
    ]
    return set(tokens_transition_variables).union(pretend_needed)

