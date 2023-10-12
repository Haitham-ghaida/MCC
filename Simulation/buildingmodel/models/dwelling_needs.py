from scipy.stats import beta
import pandas as pd
from shape_optim.buildingmodel.utils import get_beta_distribution
from shape_optim import data_path
from pathlib import Path
import numpy as np

#TODO: put constant in one file ?
cp_water = 4186.  # [J/kg.K]
rho_water = 1.  # [kg/l]

daily_dhw_use_by_occupant = {
    'min': 10.,  # in litres at 40°C
    'max': 150.,
    'alpha': 2.5,  # parameters of beta distribution
    'beta': 4.5,
}

conventional_dhw_use_by_occupant = 57.  # in litres

specific_annual_need_by_occupant = {
    'house': {
        'min': 900.,  # in kWh
        'max': 3000.,
        'alpha': 2.5,  # parameters of beta distribution
        'beta': 4.5,
    },
    'apartment': {
        'min': 700.,  # in kWh
        'max': 2600.,
        'alpha': 2,  # parameters of beta distribution
        'beta': 4.5,
    }
}

internal_gain_by_occupant = 50.  # in W

specific_peak_need = {
    'house': [6000, 6000, 6000, 6000, 9000, 9000],
    'apartment': [3000, 3000, 6000, 6000, 6000, 9000]
}

energy_use_path = Path(data_path['energy_use'])

specific_electricity = pd.read_hdf(energy_use_path / 'specific_electricity_sample.hdf')
cooking_energy = pd.read_hdf(energy_use_path / 'cooking_energy_sample.hdf')

building_stat_path = Path(data_path['building_statistics'])
intermittency_factors = pd.read_csv(building_stat_path / 'intermittency_factors.csv')


def calculate_dwelling_level_intermittency(dwellings):
    """
    The actual intermittency factor represents the share of the time that occupants are actually resent in the dwelling.
    The values are taken in a beta distribution with parameters depending on the residential and occupancy types.

    Returns:

    """

    for residential_type in dwellings.residential_type.unique():
        for occupancy_type in dwellings.occupancy_type.unique():
            mask = (dwellings.occupancy_type == occupancy_type) & (dwellings.residential_type == residential_type)
            if occupancy_type == 'vacant dwelling':
                dwellings.loc[mask, 'intermittency_factor'] = 0.
            else:
                int_params = intermittency_factors.loc[(intermittency_factors.occupancy_type == occupancy_type)
                                                       & (intermittency_factors.residential_type == residential_type)]
                int_factors = get_beta_distribution(int_params.iloc[0].to_dict(), mask.sum())
                dwellings.loc[mask, 'intermittency_factor'] = int_factors


def daily_dhw_need(dhw_use, temperature):
    """

    Args:
        dhw_use:
        temperature:

    Returns:

    """
    return (40 - temperature) * cp_water / 3600. * rho_water * dhw_use


def water_temperature(climate):
    """

    Args:
        climate:

    Returns:

    """
    return climate.ground_temperature.min(), climate.ground_temperature.mean()


def conventional_needs(dwellings, mean_water_temperature):
    """
    Conventional dhw need and occupant gains are calculated from the living area of the dwelling
    Args:
        dwellings:

    Returns:

    """

    dwellings['conventional_occupant_gains'] = 0.07 * dwellings['living_area'] * 365  # 70 Wh/m² by day
    dwellings['conventional_occupant_count'] = dwellings['occupant_count']
    dwellings['conventional_dhw_use'] = dwellings['conventional_occupant_count'] * conventional_dhw_use_by_occupant
    dwellings['conventional_dhw_needs'] = daily_dhw_need(dwellings['conventional_dhw_use'],
                                                         mean_water_temperature) * 365. / 1000.


def actual_dhw_needs(dwellings, min_water_temperature, mean_water_temperature):
    """

    The dhw needs are calculated by drawing the daily hot water consumption in a beta distribution and then using
    ground temperature to calculate the equivalent energy needs

    Args:
        dwellings:

    Returns:

    """

    use = get_beta_distribution(daily_dhw_use_by_occupant, dwellings.shape[0])

    dwellings['annual_dhw_use'] = occupant_count_factor(dwellings['occupant_count']) * use
    dwellings['peak_dhw_use'] = occupant_count_factor(dwellings['occupant_count']) * use

    dwellings['annual_dhw_needs'] = daily_dhw_need(dwellings['annual_dhw_use'],
                                                   mean_water_temperature) * 365. / 1000.  # in kWh
    dwellings['peak_dhw_needs'] = daily_dhw_need(dwellings['peak_dhw_use'], min_water_temperature)  # in W over 1 hour

    non_primary_residence = dwellings.occupancy_type != 'primary residence'
    dwellings.loc[non_primary_residence, 'annual_dhw_needs'] *= dwellings.loc[non_primary_residence,
                                                                              'intermittency_factor']



def actual_specific_needs(dwellings):
    """
    Specific needs are obtained by drawing in a sample of specific energy consumption obtained from the dwelling survey
    and conditioned by the number of occupants

    Args:
        dwellings:

    Returns:

    """

    # np.random.seed()

    for occ_count in dwellings.occupant_count.astype(int).unique():
        if occ_count > 6:
            occ_count = 6
        if occ_count > 0:
            dw_mask = (dwellings.occupant_count == occ_count)
            smp_mask = (specific_electricity.occupant_count == occ_count)
            sample = np.random.choice(specific_electricity.loc[smp_mask, 'specific_electricity'], int(dw_mask.sum()))
            dwellings.loc[dw_mask, 'annual_specific_needs'] = sample

    for residential_type, value in specific_peak_need.items():
        for occ_count in dwellings.occupant_count.astype(int).unique():
            if occ_count > 6:
                occ_count = 6
            if occ_count > 0:
                peak_specific_need = value[occ_count - 1]
                dw_mask = (dwellings.residential_type == residential_type) & (dwellings.occupant_count == occ_count)
                dwellings.loc[dw_mask, 'peak_specific_needs'] = peak_specific_need

    non_primary_residence = dwellings.occupancy_type != 'primary residence'
    dwellings.loc[non_primary_residence, 'annual_specific_needs'] *= dwellings.loc[non_primary_residence,
                                                                                   'intermittency_factor']


def actual_cooking_needs(dwellings):
    """
    Specific needs are obtained by drawing in a sample of specific energy consumption obtained from the dwelling survey
    and conditioned by the number of occupants

    Args:
        dwellings:

    Returns:

    """

    # np.random.seed()
    for occ_count in dwellings.occupant_count.astype(int).unique():
        if occ_count > 6:
            occ_count = 6
        if occ_count > 0:
            dw_mask = (dwellings.occupant_count == occ_count)
            smp_mask = (cooking_energy.occupant_count == occ_count)
            sample = np.random.choice(cooking_energy.loc[smp_mask, 'cooking_energy'], int(dw_mask.sum()))
            dwellings.loc[dw_mask, 'annual_cooking_needs'] = sample

    non_primary_residence = dwellings.occupancy_type != 'primary residence'
    dwellings.loc[non_primary_residence, 'annual_cooking_needs'] *= dwellings.loc[non_primary_residence,
                                                                                  'intermittency_factor']


def occupant_gains(dwellings):

    dwellings['occupant_gains'] = dwellings['occupant_count'] * internal_gain_by_occupant * 8760. / 1000. + 0.5 * \
                                  (dwellings['annual_specific_needs'] + dwellings['annual_cooking_needs'])

    dwellings['occupant_gains'] *= dwellings['intermittency_factor']


def occupant_count_factor(occupant_count):
    """
    Specific and dhw use by occupant decreases when the number of occupants in a dwelling increases. This is represented
    by the use of a factor that decreases iwth the number of occupants.
    Args:
        occupant_count:

    Returns:

    """
    return occupant_count ** (1/1.2)


def run_models(dwellings, climate):
    """


    Args:
        dwellings: a Dataframe containing dwellings parameters and results

    Returns:

    """

    calculate_dwelling_level_intermittency(dwellings)
    min_water_temperature, mean_water_temperature = water_temperature(climate)
    conventional_needs(dwellings, mean_water_temperature)
    actual_dhw_needs(dwellings, min_water_temperature, mean_water_temperature)
    actual_specific_needs(dwellings)
    actual_cooking_needs(dwellings)
    occupant_gains(dwellings)
