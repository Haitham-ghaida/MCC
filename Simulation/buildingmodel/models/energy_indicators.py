import pandas as pd
import numpy as np

bin_DPE_values_energy = [-10, 0, 70, 110, 180, 250, 330, 420, np.inf]
bin_DPE_letter_energy = ["X", "A", "B", "C", "D", "E", "F", "G"]

bin_DPE_values_CO2 = [-10, 0, 6, 11, 30, 50, 70, 100, np.inf]
bin_DPE_letter_CO2 = ["X", "A", "B", "C", "D", "E", "F", "G"]

DPE_dict = {'A': [0, 50], 'B': [50, 90], 'C': [90, 150], 'D': [150, 230], 'E': [230, 330], 'F': [330, 450], 'G': [450, 10000], 'X': [-10, 0]}
DPE_color = {'A': 'green', 'B': 'lime', 'C': 'greenyellow', 'D': 'yellow', 'E': 'orange', 'F': 'coral', 'G': 'red', 'X': 'lightgrey'}

def diagnosis_class(buildings):
    """

    Args:
        buildings:
        parameters:

    Returns:

    """

    buildings["diagnosis_class_kWh"] = pd.cut(buildings["conventional_primary_consumption_by_surface"],
                                              bins=bin_DPE_values_energy,
                                              labels=bin_DPE_letter_energy)
    buildings["diagnosis_class_CO2"] = pd.cut(buildings["conventional_CO2_emission_by_surface"],
                                              bins=bin_DPE_values_CO2,
                                              labels=bin_DPE_letter_CO2)

    buildings['diagnosis_class'] = buildings[["diagnosis_class_CO2", "diagnosis_class_kWh"]].max(axis=1)


def conventional_energy_indicators(buildings, parameters):
    """

    Args:
        buildings:
        parameters:

    Returns:

    """
    buildings['conventional_final_consumption'] = 0.
    buildings['conventional_primary_consumption'] = 0.
    buildings['conventional_CO2_emission'] = 0.
    buildings['total_CO2_emission'] = 0.

    for fuel, conversion_factor in parameters.primary_energies.items():
        if fuel == 'electricity':
            buildings['conventional_final_consumption']   += buildings[f'conventional_{fuel}_heating']
            buildings['conventional_primary_consumption'] += conversion_factor * buildings[f'conventional_{fuel}_heating']
        elif fuel == 'electricity_ECS':
            buildings['conventional_final_consumption']   += buildings[f'conventional_electricity_dhw']
            buildings['conventional_primary_consumption'] += conversion_factor * buildings[f'conventional_electricity_dhw']
        else:
            buildings['conventional_final_consumption']   += buildings[f'conventional_{fuel}_heating'] + buildings[f'conventional_{fuel}_dhw']
            buildings['conventional_primary_consumption'] += conversion_factor * (buildings[f'conventional_{fuel}_heating'] + buildings[f'conventional_{fuel}_dhw'])

    for fuel, co2_energy in parameters.co2_energies.items():
        if fuel == 'electricity':
            buildings['conventional_CO2_emission'] += co2_energy * buildings[f'conventional_{fuel}_heating']
            buildings['total_CO2_emission']        += co2_energy * (buildings[f'annual_{fuel}_consumption'] - buildings[f'annual_{fuel}_dhw'])
        elif fuel == 'electricity_ECS':
            buildings['conventional_CO2_emission'] += co2_energy * buildings[f'conventional_electricity_dhw']
            buildings['total_CO2_emission']        += co2_energy * buildings[f'annual_electricity_dhw']
        else:
            buildings['conventional_CO2_emission'] += co2_energy * (buildings[f'conventional_{fuel}_heating'] + buildings[f'conventional_{fuel}_dhw'])
            buildings['total_CO2_emission']        += co2_energy * buildings[f'annual_{fuel}_consumption']

    for col in ['conventional_final_consumption', 'conventional_primary_consumption', 'conventional_CO2_emission', 'total_CO2_emission']:
        buildings[f'{col}_by_surface'] = buildings[col] / buildings['living_area']


def actual_energy_indicators(buildings, parameters):
    """

    Args:
        buildings:
        parameters:

    Returns:

    """
    buildings['total_final_consumption'] = 0.
    buildings['total_primary_consumption'] = 0.
    for fuel, conversion_factor in parameters.primary_energies.items():
        if fuel == 'electricity':
            buildings['total_final_consumption']   += buildings[f'annual_{fuel}_consumption']
            buildings['total_primary_consumption'] += conversion_factor * (buildings[f'annual_{fuel}_consumption'] - buildings[f'annual_electricity_dhw'])
        elif fuel == 'electricity_ECS':
            buildings['total_primary_consumption'] += conversion_factor * buildings[f'annual_electricity_dhw']
        else:
            buildings['total_final_consumption']   += buildings[f'annual_{fuel}_consumption']
            buildings['total_primary_consumption'] += conversion_factor * buildings[f'annual_{fuel}_consumption']

    for col in ['total_final_consumption', 'total_primary_consumption']:
        buildings[f'{col}_by_surface'] = buildings[col] / buildings['living_area']


def run_models(buildings, parameters):
    """

    Args:
        buildings:
        parameters:

    Returns:

    """
    actual_energy_indicators(buildings, parameters)
    conventional_energy_indicators(buildings, parameters)
    diagnosis_class(buildings)