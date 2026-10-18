"""Configuração imutável: alterações passam pela validação novamente."""

from dataclasses import dataclass
from datetime import date
from math import isfinite
from numbers import Real


@dataclass(frozen=True)
class PPRConfig:
    year: int = 2023
    alpha_g: float = 2.0
    min_population: int = 100_000
    custom_country_codes: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if type(self.year) is not int or not 1960 <= self.year <= date.today().year:
            raise ValueError("O ano deve estar entre 1960 e o ano atual.")
        if (
            isinstance(self.alpha_g, bool)
            or not isinstance(self.alpha_g, Real)
            or not isfinite(self.alpha_g)
            or not 0 <= self.alpha_g <= 2
        ):
            raise ValueError("alpha_g deve ser um número finito entre 0 e 2.")
        if type(self.min_population) is not int or self.min_population < 0:
            raise ValueError("A população mínima deve ser um inteiro não negativo.")
        if self.custom_country_codes is not None:
            if isinstance(self.custom_country_codes, str):
                raise ValueError("Informe uma lista de códigos, não uma string.")
            codes = tuple(dict.fromkeys(str(c).strip().upper() for c in self.custom_country_codes))
            if any(len(c) != 3 or not c.isascii() or not c.isalpha() for c in codes):
                raise ValueError("Use códigos de país com três letras, como BRA e USA.")
            object.__setattr__(self, "custom_country_codes", codes)
