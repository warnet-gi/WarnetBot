class CantNoneError(Exception):
    def __init__(self, var: str) -> None:
        super().__init__(f"{var} cannot be None")
