"""
NIST / CODATA physical constants used by atmospheric_science_lab and friends.

Restored from the compiled cache (__pycache__/nist_constants.cpython-313.pyc)
after a repository cleanup accidentally removed the source file. Values are
canonical CODATA 2018 / NIST SI definitions — all public domain, no
derivation needed.

Atmospheric_science_lab does `from nist_constants import *`, so this module
must continue to expose every name listed below.
"""

from __future__ import annotations

SPEED_OF_LIGHT: float = 299_792_458.0
PLANCK_CONSTANT: float = 6.62607015e-34
REDUCED_PLANCK_CONSTANT: float = 1.054571817e-34
ELEMENTARY_CHARGE: float = 1.602176634e-19
BOLTZMANN_CONSTANT: float = 1.380649e-23
AVOGADRO_CONSTANT: float = 6.02214076e23
VACUUM_PERMEABILITY: float = 1.25663706212e-6
VACUUM_PERMITTIVITY: float = 8.8541878128e-12
GRAVITATIONAL_CONSTANT: float = 6.6743e-11
ELECTRON_MASS: float = 9.1093837015e-31
PROTON_MASS: float = 1.67262192369e-27
NEUTRON_MASS: float = 1.67492749804e-27
ATOMIC_MASS_UNIT: float = 1.6605390666e-27
GAS_CONSTANT: float = 8.314462618
STEFAN_BOLTZMANN_CONSTANT: float = 5.670374419e-8
RYDBERG_CONSTANT: float = 10_973_731.56816
FINE_STRUCTURE_CONSTANT: float = 0.0072973525693
BOHR_RADIUS: float = 5.29177210903e-11
BOHR_MAGNETON: float = 9.2740100783e-24
ELECTRON_VOLT: float = 1.602176634e-19  # 1 eV in joules (== ELEMENTARY_CHARGE)

EARTH_RADIUS: float = 6_371_000.0
EARTH_MASS: float = 5.972e24
SUN_RADIUS: float = 696_000_000.0
SUN_MASS: float = 1.989e30
ASTRONOMICAL_UNIT: float = 149_597_870_700.0
LIGHT_YEAR: float = 9_460_730_472_580_800.0
PARSEC: float = 3.085677581491367e16

R_SPECIFIC_DRY_AIR: float = 287.052874  # J/(kg·K), per WMO
R_SPECIFIC_WATER_VAPOR: float = 461.523  # J/(kg·K)

__all__ = [
    "SPEED_OF_LIGHT",
    "PLANCK_CONSTANT",
    "REDUCED_PLANCK_CONSTANT",
    "ELEMENTARY_CHARGE",
    "BOLTZMANN_CONSTANT",
    "AVOGADRO_CONSTANT",
    "VACUUM_PERMEABILITY",
    "VACUUM_PERMITTIVITY",
    "GRAVITATIONAL_CONSTANT",
    "ELECTRON_MASS",
    "PROTON_MASS",
    "NEUTRON_MASS",
    "ATOMIC_MASS_UNIT",
    "GAS_CONSTANT",
    "STEFAN_BOLTZMANN_CONSTANT",
    "RYDBERG_CONSTANT",
    "FINE_STRUCTURE_CONSTANT",
    "BOHR_RADIUS",
    "BOHR_MAGNETON",
    "ELECTRON_VOLT",
    "EARTH_RADIUS",
    "EARTH_MASS",
    "SUN_RADIUS",
    "SUN_MASS",
    "ASTRONOMICAL_UNIT",
    "LIGHT_YEAR",
    "PARSEC",
    "R_SPECIFIC_DRY_AIR",
    "R_SPECIFIC_WATER_VAPOR",
]
