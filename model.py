
from typing import (
    Optional as tp_Optional, Iterable as tp_Iterable,
    Self as tp_Self,
)


from numbers import Number
from enum import Flag, auto

from copy import deepcopy as cp_deepcopy


from numpy import (
    ndarray, array, copy, tile, reshape,
    zeros, log, exp, nan_to_num,
)



from .sourcing import (
    Source,
)


from .incidence import (
    Token,
    get_max_shift, get_min_shift,
)


from .equations import (
    EquationKind, Equation,
    finalize_equations_from_humans,
    generate_all_tokens_from_equations
)


from .quantities import (
    QuantityKind, Quantity,
    create_name_to_id, 
    generate_all_quantity_ids, 
    generate_all_quantity_names,
    generate_quantity_ids_by_kind,
)



class EvaluatorKind(Flag):
    STEADY = auto()
    STACKED = auto()
    PERIOD = auto()



class SteadyEvaluator:
    """
    """
    kind = EvaluatorKind.STEADY

    def __init__(self, model: tp_Self) -> None:
        self._equations: list[Equation] = []
        self._quantities: list[Quantity] = []
        self._resolve_incidences(model)
        self._quantity_ids: list[int] = list(generate_all_quantity_ids(model._quantities))
        self._t_zero = -model._get_min_shift()
        self._create_evaluator_function()
        self._create_incidence_matrix()
        num_columns = self._t_zero + 1 + model._get_max_shift()
        self._x: ndarray = model.create_steady_array(num_columns)
        self._z0: ndarray = self._z_from_x()


    @property
    def init(self) -> ndarray:
        return copy(self._z0)

    @property
    def quantities_solved(self) -> list[str]:
        return [ qty.human for qty in self._quantities ]

    @property
    def equations_solved(self) -> list[str]:
        return [ eqn.human for eqn in self._equations ]

    @property
    def num_equations(self) -> int:
        return len(self._equations)

    @property
    def num_quantities(self) -> int:
        return len(self._quantities)

    def eval(self, current: tp_Optional[ndarray]=None):
        x = self._x_from_z(current)
        return self._func(x)

    def _resolve_incidences(self, model: tp_Self) -> None:
        equation_ids = list(generate_equation_ids_by_kind(model._equations, EquationKind.EQUATION))
        quantity_ids = list(generate_quantity_ids_by_kind(model._quantities, QuantityKind.VARIABLE))
        self._equations = [ eqn for eqn in model._equations if eqn.id in equation_ids ]
        self._quantities = [ qty for qty in model._quantities if qty.id in quantity_ids ]

    def _create_evaluator_function(self) -> None:
        xtrings = [ eqn.remove_equation_ref_from_xtring() for eqn in self._equations ]
        func_string = ",".join(xtrings)
        self._func = eval(f"lambda x, t={self._t_zero}: array([{func_string}], dtype=float)")

    def _create_incidence_matrix(self) -> None:
        matrix = zeros((self.num_equations, self.num_quantities), dtype=int)
        for row_index, eqn in enumerate(self._equations):
            column_indices = list(set( tok.quantity_id for tok in eqn.incidence if tok.quantity_id in self._quantity_ids ))
            matrix[row_index, column_indices] = 1
        self.incidence_matrix = matrix

    def _z_from_x(self):
        return self._x[self._quantity_ids, self._t_zero]

    def _x_from_z(self, z: ndarray) -> ndarray:
        x = copy(self._x)
        if z is not None:
            x[self._quantity_ids, :] = reshape(z, (-1,1))
        return x


class Variant:
    """
    """
    def __init__(self, num_names: int=0) -> None:
        self._values: list[tp_Optional[Number]] = [None]*num_names

    def assign(self, name_value: dict[str, Number], names_to_assign: list[str], name_to_id: dict[str, int]) -> None:
        for name in names_to_assign:
            self._values[name_to_id[name]] = name_value[name]

    def _assign_auto_values(self, pos: set[int], auto_value: Number) -> None:
        for p in pos: self._values[p] = auto_value

    @classmethod
    def from_model_source(cls, ms: Source) -> tp_Self:
        self = cls(ms.num_quantities)
        return self



class Model:
    """
    """
    def __init__(self):
        self._quantities: list[Quantity] = []
        self._equations: list[Equation] = []
        self._variants: list[Variant] = []


    def assign(self: tp_Self, variant: int=0, **kwargs) -> tuple[tp_Self, set[str]]:
        """
        """
        names_to_assign = self._get_names_to_assign(kwargs)
        self._variants[variant].assign(kwargs, names_to_assign, create_name_to_id(self._quantities))
        return self, names_to_assign


    def _get_names_to_assign(self: tp_Self, name_value: dict[str, float]) -> set[str]:
        all_names = generate_all_quantity_names(self._quantities)
        names_shocks = [ qty.human for qty in self._quantities if qty.kind in QuantityKind.SHOCK ]
        names_to_assign = set(name_value.keys()).intersection(all_names).difference(names_shocks)
        return names_to_assign


    def change_num_variants(self, new_num: int) -> None:
        """
        """
        if new_num<self.num_variants:
            self._shrink_num_variants(new_num)
        elif new_num>self.num_variants:
            self._expand_num_variants(new_num)


    @property
    def num_variants(self) -> int:
        return len(self._variants)


    def _get_max_shift(self: tp_Self) -> int:
        return get_max_shift(self._collect_all_tokens)


    def _get_min_shift(self: tp_Self) -> int:
        return get_min_shift(self._collect_all_tokens)


    def create_steady_evaluator(self) -> SteadyEvaluator:
        return SteadyEvaluator(self)


    def create_steady_array(self, num_columns: int=1, variant: int=0, missing: tp_Optional[float]=None) -> ndarray:
        steady_vector = array([self._variants[variant]._values], dtype=float).transpose()
        if missing:
            nan_to_num(steady_vector, nan=missing, copy=False)
        steady_array = tile(steady_vector, (1, num_columns))
        return steady_array


    def _assign_auto_values(self: tp_Self) -> None:
        pos_shocks = generate_quantity_ids_by_kind(self._quantities, QuantityKind.SHOCK)
        for v in self._variants:
            v._assign_auto_values(pos_shocks, 0)


    def _shrink_num_variants(self, new_num: int) -> None:
        if new_num<1:
            Exception('Number of variants must be one or more')
        self._variants = self._variants[0:new_num]


    def _expand_num_variants(self, new_num: int) -> None:
        for i in range(self.num_variants, new_num):
            self._variants.append(cp_deepcopy(self._variants[-1]))


    def _collect_all_tokens(self) -> set[Token]:
        return set(generate_all_tokens_from_equations(self._equations))


    @classmethod
    def from_lists( 
        cls,
        transition_variables: list[str], 
        transition_equations: list[str], 
        transition_shocks: tp_Optional[list[str]]=None,
        parameters: tp_Optional[list[str]]=None,
    ) -> tp_Self:

        model_source = Source()
        model_source.add_transition_variables(transition_variables)
        model_source.add_transition_equations(transition_equations)
        model_source.add_transition_shocks(transition_shocks)
        model_source.add_parameters(parameters)
        model_source.seal()

        self = cls()
        self._quantities = cp_deepcopy(model_source.quantities)
        self._equations = cp_deepcopy(model_source.equations)
        self._variants = [ Variant.from_model_source(model_source) ]

        finalize_equations_from_humans(self._equations, create_name_to_id(self._quantities))

        self._assign_auto_values()

        return self
#)


