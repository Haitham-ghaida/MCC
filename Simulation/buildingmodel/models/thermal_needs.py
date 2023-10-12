import numpy as np
import pandas as pd
from pathlib import Path


def calculate_heated_area_share(buildings):
    """
    The heated area share of a building is the share of the total floor surface of the building that is occupied by
    dwellings

    Args:
        buildings:
        dwellings:

    Returns:

    """

    # heated share is one for building with residential_only = True and has_annex = False
    build_mask = (buildings.residential_only) & (buildings.has_annex == False) & (buildings.to_sim)
    buildings.loc[build_mask, 'heated_area_share'] = buildings.loc[build_mask, 'living_area_share']

    # heated share for house with annex
    build_mask = (buildings.residential_type == 'house') & (buildings.residential_only) & (buildings.has_annex) & (
        buildings.to_sim)
    buildings.loc[build_mask, 'heated_area_share'] = np.clip(buildings.loc[build_mask, 'living_area_share'] * 1.2, 0.2,
                                                             1.0)

    # heated share for apartment building with annex
    build_mask = (buildings.residential_type == 'apartment') & (buildings.residential_only) & (buildings.has_annex) & (
        buildings.to_sim)
    buildings.loc[build_mask, 'heated_area_share'] = np.clip(buildings.loc[build_mask, 'living_area_share'] * 1.3, 0.6,
                                                             1.0)

    # heated share for multiple_use
    build_mask = (buildings.residential_only == False) & (buildings.to_sim)
    buildings.loc[build_mask, 'heated_area_share'] = np.clip(buildings.loc[build_mask, 'living_area_share'] * 1.2, 0.,
                                                             1.0)


def calculate_conventional_intermittency(buildings, dwellings):
    """
    The conventional intermittency factor represents the share of heating needs that will be effectively delivered by
    the heating system. It is used to take into account the fact that occupants are not always present in the
    dwelling.
    The values are taken from the 3CL diagnosis method and depend only on the residential building type.

    * house : 0.85
    * apartment : 0.95

    Returns:

    """

    buildings.loc[(buildings.residential_type == 'apartment'), 'conventional_intermittency_factor'] = 0.85
    buildings.loc[(buildings.residential_type == 'house'), 'conventional_intermittency_factor'] = 0.95


def calculate_thermal_needs(buildings, boundaries, parameters):
    """
    Calculates the annual and peak thermal needs by combining the boundary losses, ventilation losses, solar gains,
    occupant internal gains and intermittency factor

    Args:
        buildings (GeoDataframe): a GeoDataframe containing the building geometries and parameters
        boundaries (GeoDataframe): a GeoDataframe containing the boundary geometries and parameters

    Returns:

    """
    buildings['annual_heating_needs'] = 0.
    buildings['conventional_heating_needs'] = 0.
    buildings['peak_heating_needs'] = 0.
    buildings['annual_solar_gains'] = 0.
    buildings['annual_boundary_losses'] = 0.
    gain_share = parameters.maximal_occupant_gain_share
    solar_share = parameters.maximal_solar_gain_share

    for b_index in buildings.loc[buildings.to_sim].building_id:
        current_boundaries = boundaries.loc[boundaries['building_id'] == b_index, :]
        #current_dwellings = dwellings.loc[dwellings['building_id'] == b_index, :]
        heating_season_ration = buildings.loc[b_index, 'heating_season_duration'] / 8760.

        # Actual thermal losses take into account intermittency and actual occupant gains
        buildings.loc[b_index, 'annual_thermal_losses'] = (current_boundaries['annual_thermal_losses'].sum() +
                                                           buildings.loc[b_index, 'annual_ventilation_losses'])
        #buildings.loc[b_index, 'annual_occupant_gains'] = (current_dwellings['occupant_gains'].sum() *heating_season_ration)
        buildings.loc[b_index, 'annual_occupant_gains'] = np.clip(buildings.loc[b_index, 'annual_occupant_gains'],
                                                         0.,
                                                         gain_share * buildings.loc[b_index, 'annual_thermal_losses'])
        buildings.loc[b_index, 'annual_solar_gains'] = current_boundaries['transmitted_solar_gain'].sum()
        buildings.loc[b_index,
                      'annual_solar_gains'] = np.clip(buildings.loc[b_index, 'annual_solar_gains'],
                                                      0.,
                                                      solar_share * buildings.loc[b_index, 'annual_thermal_losses'])

        buildings.loc[b_index, 'annual_heating_needs'] = (buildings.loc[b_index, 'annual_thermal_losses'] -
                                                          buildings.loc[b_index, 'annual_solar_gains'])
        buildings.loc[b_index, 'annual_heating_needs'] *= buildings.loc[b_index, 'heated_area_share']
        buildings.loc[b_index, 'annual_heating_needs'] *= buildings.loc[b_index, 'intermittency_factor']
        buildings.loc[b_index, 'annual_heating_needs'] -= buildings.loc[b_index, 'annual_occupant_gains']
        buildings.loc[b_index, 'annual_heating_needs'] *= buildings.loc[b_index, 'regulation_factor']

        buildings.loc[b_index, 'peak_heating_needs'] = (current_boundaries['peak_thermal_losses'].sum() +
                                                        buildings.loc[b_index, 'peak_ventilation_losses'])

        # Conventional thermal losses do not take into account intermittency and actual occupant gains
        buildings.loc[b_index,
                      'conventional_thermal_losses'] = (current_boundaries['conventional_thermal_losses'].sum() +
                                                        buildings.loc[b_index, 'conventional_ventilation_losses'])
        #buildings.loc[b_index,'conventional_occupant_gains'] = (current_dwellings['conventional_occupant_gains'].sum() *heating_season_ration)
        buildings.loc[b_index,
                      'conventional_occupant_gains'] = np.clip(buildings.loc[b_index, 'conventional_occupant_gains'],
                                                               0.,
                                                               gain_share * buildings.loc[b_index,
                                                                                          'conventional_thermal_losses'])

        buildings.loc[b_index, 'conventional_heating_needs']     = (buildings.loc[b_index, 'conventional_thermal_losses'] - buildings.loc[b_index, 'annual_solar_gains'])
        buildings.loc[b_index, 'conventional_heating_needs']    *= buildings.loc[b_index, 'heated_area_share']
        buildings.loc[b_index, 'conventional_heating_needs']    *= buildings.loc[b_index, 'conventional_intermittency_factor']
        buildings.loc[b_index, 'conventional_heating_needs']    -= buildings.loc[b_index, 'conventional_occupant_gains']
        buildings.loc[b_index, 'conventional_heating_needs']    *= buildings.loc[b_index, 'regulation_factor']

    buildings.loc[(buildings.intermittency_factor == 0.), 'peak_heating_needs'] = 0.

    buildings.loc[buildings['annual_heating_needs'] < 0., 'annual_heating_needs'] = 0.
    #buildings.loc[buildings['conventional_heating_needs'] < 0., 'conventional_heating_needs'] = 0.


def aggregate_intermittency(buildings, dwellings):

    mean_intermittency_factor = dwellings.groupby('building_id')['intermittency_factor'].mean()
    buildings.loc[mean_intermittency_factor.index, 'intermittency_factor'] = mean_intermittency_factor


def calculate_regulation_factor(buildings):
    """
    The actual regulation factor represents the share heating needs that will be effectively needed due to dwelling
    occupants controlling the heating regulation.

    The values are taken in a beta distribution with parameters depending on the residential type and heating system.

    Returns:

    """
    res_types = buildings.loc[buildings.to_sim].residential_type.unique()
    heating_systems = buildings.loc[buildings.to_sim].heating_system.unique()

    for residential_type in res_types:
        for heating_system in heating_systems:
            #print(residential_type,heating_system)
            mask = (buildings.heating_system == heating_system) & (buildings.residential_type == residential_type)
            if heating_system == 'urban heat network':
                heating_system = 'district_network'
            int_params = regulation_factors.loc[(regulation_factors.heating_system == heating_system)
                                                & (regulation_factors.residential_type == residential_type)]
            int_factors = get_beta_distribution(int_params.iloc[0].to_dict(), mask.sum())
            buildings.loc[mask, 'regulation_factor'] = int_factors


def run_models(buildings, boundaries, parameters):
    """

    Args:
        buildings (GeoDataframe): a GeoDataframe containing the building geometries and parameters
        boundaries (GeoDataframe): a GeoDataframe containing the boundary geometries and parameters

    Returns:

    """
    #calculate_conventional_intermittency(buildings, dwellings)
    #aggregate_intermittency(buildings, dwellings)
    #calculate_regulation_factor(buildings)
    #calculate_heated_area_share(buildings)
    calculate_thermal_needs(buildings, boundaries, parameters)
