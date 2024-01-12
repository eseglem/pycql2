from typing import Any, Dict, List, Optional

from hypothesis import HealthCheck, given, settings, strategies as st
from hypothesis.extra.lark import LarkStrategy
from lark import Lark, Token
from lark.grammar import Terminal

from pycql2.cql2_pydantic import join_list
from pycql2.cql2_transformer import parser, transformer


class SpacedLarkStrategy(LarkStrategy):
    def __init__(
        self, grammar: Lark, start: str, explicit: Optional[Dict] = None
    ) -> None:
        if explicit is None:
            explicit = {}
        # Let LarkStrategy figure out most of the strategy
        super().__init__(grammar, start, explicit)

        # The logic used to draw symbols requires the actual strategies be in "Terminals"
        # so we can create new Terminal strategies that doesn't clash with the existing ones
        # and use them to create new strategies for the "RULE"s that need them.
        custom_terminals = {
            # Make a new terminal called COORDINATE, that generates a 2d coordinate within
            # normal WGS84 bounds. The grammar is not specific about the coordinate system
            # but this makes it easier to test. It does not cover 3d coordinates but this is
            # a stop gap until a more robust strategy can be created.
            "COORDINATE": (
                st.lists(
                    st.tuples(
                        st.floats(min_value=-180, max_value=180),
                        st.floats(min_value=-90, max_value=90),
                    ),
                    min_size=3,
                )
                .map(lambda x: [*x, x[0]])
                .map(lambda x: join_list([join_list(c, " ") for c in x], ","))
                .map(lambda x: f"({x})")
            ),
            # The grammar just uses DIGIT throughout but we need to make sure that the
            # date and datetime are valid so we need to use the built-in strategies
            # for those and then format them to match the grammar.
            "DATE": st.dates().map(lambda x: x.isoformat()),
            "DATE_TIME": st.datetimes().map(
                lambda x: x.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            ),
        }

        # Then we can set up the custom strategies for "RULE"s that need them by pointing
        # to the new terminals. Note that the `.just()` needs to return an iterable so it
        # can be looped over.
        custom_strategies = {
            # Create a strategy for the linear_ring_coordinates rule because it needs to be closed
            Token("RULE", "linear_ring_coordinates"): st.just((Terminal("COORDINATE"),))
        }

        # Update the strategies
        self.terminal_strategies.update(custom_terminals)
        self.nonterminal_strategies.update(custom_strategies)

    def do_draw(self, data: Any) -> str:
        state: List[Any] = []
        start = data.draw(self.start)
        self.draw_symbol(data, start, state)
        # The default strategy doesn't add spaces between tokens so we need to add them
        # here. Technically they shouldn't be needed, but the grammar is a bit ambiguous
        # and it has problems without them.
        return " ".join(state)


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=SpacedLarkStrategy(parser, "boolean_expression"))
def test_boolean_expression(text: str) -> None:
    tree = parser.parse(text)
    _ = transformer.transform(tree)
