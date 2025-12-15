class _ReturnSignal(Exception):
    """Internal control flow for return."""

    def __init__(self, value: object) -> None:
        super().__init__("return")
        self.value = value
