from dataclasses import dataclass
from textual.widgets import Input
from textual import events


class SearchKey(Input):
    # @dataclass
    # class Up(Message):
    #     input: Input
    #     """The `Input` widget that is being submitted."""
    #     value: str
    #     """The value of the `Input` being submitted."""
    #     validation_result: ValidationResult | None = None
    #     """The result of validating the value on submission, formed by combining the results for each validator.
    #     This value will be None if no validation was performed, which will be the case if no validators are supplied
    #     to the corresponding `Input` widget."""
    #
    #     @property
    #     def control(self) -> Input:
    #         """Alias for self.input."""
    #         return self.input
    # class Down()
    async def on_event(self, event: events.Event) -> None:
        if isinstance(event, events.Key):
            # self.post_message()
            self.app.notify(event.key)
        return await super().on_event(event)
