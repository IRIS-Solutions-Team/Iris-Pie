"""
Resolve substitutions in model equations
"""


#[
from __future__ import annotations

import re as re_
import operator as op_
#]


def resolve_substitutions(
    parsed: dict[str, tuple],
    where_substitute: list[str],
    /,
) -> dict[str, tuple]:
    where_substitute = set(where_substitute).intersection(parsed.keys())
    definitions = _define_substitutions(parsed["substitutions"], )
    subs_pattern = re_.compile(r"\$(" + "|".join(lhs for lhs in definitions.keys()) + r")\$")
    replace = lambda match: definitions[match.group(1)]
    make_substitutions = lambda source: re_.sub(subs_pattern, replace, source)
    for wh in where_substitute:
        parsed[wh] = [
            (label, (make_substitutions(dynamic), make_substitutions(steady)))
            for label, (dynamic, steady) in parsed[wh]
        ]
    return parsed


def _define_substitutions(substitutions: list, /, ) -> dict[str, str]:
    return dict(_separate_lhs_rhs(s[1][0]) for s in substitutions)


_SUBS_NAME = re_.compile("\w+")


def _separate_lhs_rhs(subs_string: str, /, ) -> tuple[str, str]:
    subs_string = subs_string.replace(":=", "=", )
    lhs, rhs = subs_string.split("=", maxsplit=1, )
    return lhs, rhs


