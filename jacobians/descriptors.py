"""
"""


#[
from __future__ import annotations

from typing import (Self, NoReturn, )
from collections.abc import (Iterable, )
import dataclasses as dc_
import numpy as np_
import scipy as sp_

from ..aldi import (differentiators as ad_, maps as am_, )
from .. import (equations as eq_, quantities as qu_, incidence as in_, )
#]


#••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
# Exposure
#••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••


class Descriptor:
    """
    Describe the Jacobian matrix of a steady-state system
    -----------------------------------------------------
    * _num_rows -- number of rows in the Jacobian matrix
    * _num_columns -- number of columns in the Jacobian matrix
    * _map -- mapping from (row, column) to (equation, quantity)
    * _qid_to_logly -- mapping from quantity ID to whether it is logarithmic
    * _aldi_context -- context for algorithmic differentiator
    * _create_jacobian -- function to create a dense or sparse Jacobian matrix
    * is_sparse -- whether the Jacobian matrix is sparse
    """
    #[
    __slots__ = (
        "_num_rows", "_num_columns", "_map", "_qid_to_logly", "_aldi_context",
        "_create_jacobian", "is_sparse",
    )

    def __init__(self, /, **kwargs, ) -> None:
        """
        """
        self.is_sparse = kwargs.get("sparse_jacobian", False)
        if self.is_sparse:
            self._create_jacobian = self._create_sparse_jacobian
        else:
            self._create_jacobian = self._create_dense_jacobian

    @classmethod
    def for_flat(
        cls, 
        equations: eq_.Equations,
        quantities: qu_.Quantities,
        qid_to_logly: dict[int, bool],
        function_context: dict[str, Callable] | None,
        /,
        **kwargs,
    ) -> NoReturn:
        """
        """
        self = cls(**kwargs, )
        #
        # Extract eids from equations
        eids = [ eqn.id for eqn in equations ]
        #
        # Extract the qids from quantities w.r.t. which the equations are
        # to be differentiated
        all_wrt_qids = [ qty.id for qty in quantities ]
        #
        # Collect the qids w.r.t. which each equation is to be differentiated
        eid_to_wrt_qids = {
            eqn.id: list(_generate_flat_wrt_qids_in_equation(eqn, all_wrt_qids, ))
            for eqn in equations
        }
        #
        # Create the map from eids to rhs offsets; the offset is the number
        # of rows in the Jacobian matrix that precede the equation
        eid_to_rhs_offset = am_.create_eid_to_rhs_offset(eids, eid_to_wrt_qids, )
        #
        self._num_rows = len(eids)
        self._num_columns = len(all_wrt_qids)
        self._qid_to_logly = qid_to_logly
        #
        self._map = am_.ArrayMap.for_equations(
            eids, eid_to_wrt_qids,
            all_wrt_qids, eid_to_rhs_offset,
            #
            rhs_column=0, lhs_column_offset=0,
        )
        #
        num_columns = 1
        self._aldi_context = ad_.Context.for_equations(
            AtomFactory, equations, eid_to_wrt_qids,
            num_columns, function_context,
        )
        #
        return self

    def eval(
        self,
        data_context: np_.ndarray,
        L: np_.ndarray,
        /,
    ) -> np_.ndarray:
        """
        """
        diff_array = self._aldi_context.eval_diff_to_array(data_context, self._qid_to_logly, L, )
        return self._create_jacobian(diff_array, self._map, )

    def _create_dense_jacobian(self, diff_array, map, /, ) -> np_.ndarray:
        """
        Create Jacobian as numpy array
        """
        J = np_.zeros(
            (self._num_rows, self._num_columns, ),
            dtype=float,
        )
        J[map.lhs] = diff_array[map.rhs]
        return J

    def _create_sparse_jacobian(self, diff_array, map, /, ) -> sp_.sparse.coo_matrix:
        """
        Create Jacobian as scipy sparse matrix
        """
        J = sp_.sparse.coo_matrix(
            (diff_array[map.rhs], (map.lhs[0], map.lhs[1], )),
            (self._num_rows, self._num_columns, ),
            dtype=float,
        )
        return J


#••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
# Implementation
#••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••


def _generate_flat_wrt_qids_in_equation(equation, all_wrt_qids):
    """
    Generate subset of the wrt_qids that occur in this equation (no matter what shift)
    """
    return ( 
        qid for qid in all_wrt_qids 
        if in_.is_qid_in_tokens(equation.incidence, qid)
    )


class AtomFactory():
    """
    """
    #[
    @staticmethod
    def create_diff_from_token(
        token: Token,
        wrt_qids: Tokens,
        /,
    ) -> np_.ndarray:
        """
        """
        if token.qid in wrt_qids:
            diff = np_.zeros((len(wrt_qids), 1))
            diff[wrt_qids.index(token.qid)] = 1
        else:
            diff = 0
        return diff

    @staticmethod
    def create_data_index_from_token(
        token: Token,
        columns_to_eval: tuple[int, int],
        /,
    ) -> tuple[int, slice]:
        """
        """
        return (
            token.qid,
            slice(columns_to_eval[0], columns_to_eval[1]+1),
        )

    @staticmethod
    def create_logly_index_from_token(
        token: Token,
        /,
    ) -> int:
        """
        """
        return token.qid
    #]

