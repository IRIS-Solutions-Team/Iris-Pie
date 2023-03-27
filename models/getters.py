
#[
from __future__ import annotations
# from IPython import embed

import functools as ft_
import json as js_
from typing import (Literal, )

from .. import (quantities as qu_, incidence as in_, )
from ..dataman import (databanks as db_, )
#]

def _decorate_output_format(func):
    """
    """
    #[
    def _wrapper(*args, **kwargs):
        output = func(*args, **kwargs)
        output_format = kwargs.get("output", "Databank")
        return db_.DATABANK_OUTPUT_FORMAT_RESOLUTION[output_format](output)
    return _wrapper
    #]


class GetterMixin:
    """
    Frontend getter methods for Model objects
    """
    #[
    def _get_values_from_primary_variant(
        self,
        /,
        variant_attr: Literal["levels"] | Literal["changes"],
        kind: qu_.QuantityKind,
    ) -> dict[str, Number]:
        qid_to_name = self.create_qid_to_name()
        qids = list(qu_.generate_qids_by_kind(self._quantities, kind))
        x = self._variants[0].retrieve_values(variant_attr, qids)
        return db_.Databank._from_dict({ qid_to_name[q]: float(x[i, 0]) for i, q in enumerate(qids) })

    @_decorate_output_format
    def get_steady_levels(
        self,
        /,
        **kwargs,
    ) -> dict[str, Number]:
        return self._get_values_from_primary_variant(variant_attr="levels", kind=qu_.QuantityKind.LOGLY_VARIABLE, ) | self.get_parameters_stds()

    @_decorate_output_format
    def get_steady_changes(
        self,
        /,
        **kwargs,
    ) -> dict[str, Number]:
        return self._get_values_from_primary_variant(variant_attr="changes", kind=qu_.QuantityKind.LOGLY_VARIABLE, ) | self.get_parameters_stds()

    @_decorate_output_format
    def get_parameters(
        self,
        /,
        **kwargs,
    ) -> dict[str, Number]:
        return self._get_values_from_primary_variant(variant_attr="levels", kind=qu_.QuantityKind.PARAMETER)

    @_decorate_output_format
    def get_stds(
        self,
        /,
        **kwargs,
    ) -> dict[str, Number]:
        return self._get_values_from_primary_variant(variant_attr="levels", kind=qu_.QuantityKind.STD)

    @_decorate_output_format
    def get_parameters_stds(
        self,
        /,
        **kwargs,
    ) -> dict[str, Number]:
        return self._get_values_from_primary_variant(variant_attr="levels", kind=qu_.QuantityKind.PARAMETER_OR_STD)

    @_decorate_output_format
    def get_log_status(
        self,
        /,
        **kwargs,
    ) -> dict[str, bool]:
        return {
            qty.human: qty.logly
            for qty in self._quantities if qty.kind in QuantityKind.LOGLY_VARIABLE
        }

    def get_initials(
        self,
        /,
        kind: Literal["required"] | Literal["discarded"] = "required",
    ) -> in_.Tokens:
        """
        Get required list of initial conditions
        """
        # Get the tokens of state vector with actual incidence in the
        # model, and lag them by one period to get initial conditions
        initial_tokens = [
            in_.Token(t.qid, t.shift-1)
            for t in self._dynamic_descriptor.solution_vectors.get_initials(kind, )
        ]
        return in_.print_tokens(initial_tokens, self.create_qid_to_name(), )

    def _get_steady_databank(
        self,
        start_date: Dater,
        end_date: Dater,
        /,
        deviation: bool = False,
    ) -> db_.Databank:
        """
        """
        num_columns = int(end_date - start_date + 1)
        shift_in_first_column = start_date.get_distance_from_origin()
        #
        array = self.create_some_array(
            deviation=deviation,
            num_columns=num_columns,
            shift_in_first_column=shift_in_first_column,
        )
        #
        time_series_kind = qu_.QuantityKind.LOGLY_VARIABLE | qu_.QuantityKind.SHOCK
        qid_to_kind = self.create_qid_to_kind()
        qid_to_name = {
            qid: (name if qid_to_kind[qid] in time_series_kind else "")
            for qid, name in self.create_qid_to_name().items()
        }
        qid_to_descript = self.create_qid_to_descript()
        #
        return db_.Databank._from_array(
            array, qid_to_name, start_date, 
            array_orientation="horizontal",
            interpret_dates="start_date",
            qid_to_descript=qid_to_descript,
        )
    #]

