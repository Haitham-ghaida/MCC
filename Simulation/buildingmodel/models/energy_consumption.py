from buildingmodel.main import *

energy_list     = ['electricity', 'gas', 'oil', 'biomass', 'district_network', 'biogas']
dhw_efficiencies = {'electricity': 0.7, 'gas': 0.6, 'oil': 0.6, 'biomass': 0.6, 'district_network': 0.6, 'biogas': 0.6}

def annual_energy_consumption(buildings):
    """
    Calculates the energy consumption of each building :
     * attribution of thermal need share to main generator and backup
     * calculation of heating consumption using efficiency, thermal need and share for main and backup system
     * calculation of electricity consumption for specific needs by summing the need for each dwelling
     * calculation of dhw consumption and attribution to the corresponding fuel

    Args:
        buildings:

    Returns:

    """
    """
    buildings['annual_specific_needs'] = dwellings.groupby('building_id')['annual_specific_needs'].sum()
    buildings['peak_specific_needs'] = dwellings.groupby('building_id')['peak_specific_needs'].sum()
    buildings['annual_cooking_needs'] = dwellings.groupby('building_id')['annual_cooking_needs'].sum()
    buildings['annual_dhw_needs'] = dwellings.groupby('building_id')['annual_dhw_needs'].sum()
    buildings['peak_dhw_needs'] = dwellings.groupby('building_id')['peak_dhw_needs'].sum()
    """
    buildings.loc[
        buildings.heating_system == 'district_network', 'dhw_energy'] = 'district_network'  # TODO : correct at the diagnosis sample level

    for energy in energy_list:

        buildings[f'annual_{energy}_consumption'] = 0.
        buildings[f'peak_{energy}_consumption'] = 0.
        buildings[f'annual_{energy}_heating'] = 0.
        buildings[f'peak_{energy}_heating'] = 0.
        buildings[f'annual_{energy}_dhw'] = 0.
        buildings[f'peak_{energy}_dhw'] = 0.

        for priority, data_dict in get_heating_system_dict(buildings, energy).items():
            ids = data_dict['ids']
            annual_heating_needs = buildings.loc[ids, 'annual_heating_needs']
            peak_heating_needs = buildings.loc[ids, 'peak_heating_needs']
            efficiency = buildings.loc[ids, f'{priority}_heating_system_efficiency']
            buildings.loc[ids, f'annual_{energy}_heating'] += annual_heating_needs / efficiency * data_dict['share']
            buildings.loc[ids, f'peak_{energy}_heating'] += peak_heating_needs / efficiency * data_dict['share']

            buildings.loc[ids, f'annual_{energy}_consumption'] += buildings.loc[ids, f'annual_{energy}_heating']
            buildings.loc[ids, f'peak_{energy}_consumption'] += buildings.loc[ids, f'peak_{energy}_heating']

        dhw_ids = buildings.loc[(buildings['dhw_energy'] == energy) & (buildings.to_sim)].index
        buildings.loc[dhw_ids, f'annual_{energy}_dhw'] += buildings.loc[dhw_ids, 'annual_dhw_needs'] / dhw_efficiencies[
            energy]
        buildings.loc[dhw_ids, f'peak_{energy}_dhw'] += buildings.loc[dhw_ids, 'peak_dhw_needs'] / dhw_efficiencies[
            energy]
        buildings.loc[dhw_ids, f'annual_{energy}_consumption'] += buildings.loc[dhw_ids, f'annual_{energy}_dhw']
        buildings.loc[dhw_ids, f'peak_{energy}_consumption'] += buildings.loc[dhw_ids, f'peak_{energy}_dhw']

    buildings['annual_electricity_specific'] = 0.
    buildings['peak_electricity_specific'] = 0.
    ids = (buildings.to_sim)
    buildings.loc[ids, 'annual_electricity_consumption'] += buildings.loc[ids, 'annual_specific_needs']
    buildings.loc[ids, 'peak_electricity_consumption'] += buildings.loc[ids, 'peak_specific_needs']
    buildings.loc[ids, 'annual_electricity_specific'] = buildings.loc[ids, 'annual_specific_needs']
    buildings.loc[ids, 'peak_electricity_specific'] = buildings.loc[ids, 'peak_specific_needs']

    cooking_energy = buildings['cooking_energy'][2842]

    buildings.loc[ids, f'annual_{cooking_energy}_consumption'] += buildings['annual_cooking_needs']
    buildings.loc[ids, f'annual_{cooking_energy}_cooking'] = buildings['annual_cooking_needs']

def conventional_energy_consumption(buildings):
    """
    Calculates the conventional energy consumption of each building :
     * attribution of thermal need share to main generator and backup
     * calculation of heating consumption using efficiency, thermal need and share for main and backup system
     * calculation of dhw consumption and attribution to the corresponding fuel

    Args:
        buildings:

    Returns:

    """

    #buildings['conventional_dhw_needs'] = dwellings.groupby('building_id')['conventional_dhw_needs'].sum()

    for energy in energy_list:

        buildings[f'conventional_{energy}_consumption'] = 0.
        buildings[f'conventional_{energy}_heating'] = 0.
        buildings[f'conventional_{energy}_dhw'] = 0.

        for priority, data_dict in get_heating_system_dict(buildings, energy).items():
            ids = data_dict['ids']
            annual_heating_needs = buildings.loc[ids, 'conventional_heating_needs']
            efficiency = buildings.loc[ids, f'{priority}_heating_system_efficiency']
            buildings.loc[ids, f'conventional_{energy}_heating'] += annual_heating_needs / efficiency * data_dict['share']
            buildings.loc[ids, f'conventional_{energy}_consumption'] += buildings.loc[ids, f'conventional_{energy}_heating']

        dhw_ids = buildings.loc[(buildings['dhw_energy'] == energy) & (buildings.to_sim)].index
        buildings.loc[dhw_ids, f'conventional_{energy}_dhw'] += buildings.loc[dhw_ids, 'conventional_dhw_needs'] / \
                                                                dhw_efficiencies[
                                                                    energy]

        buildings.loc[dhw_ids, f'conventional_{energy}_consumption'] += buildings.loc[
            dhw_ids, f'conventional_{energy}_dhw']


def get_heating_system_dict(buildings, energy):
    """

    Args:
        buildings:

    Returns:

    """

    heating_system_dict = {
        'main': {
            'ids': buildings.loc[(buildings['main_heating_energy'] == energy) & (buildings.to_sim)].index,
        },
        'backup': {
            'ids': buildings.loc[(buildings['backup_heating_energy'] == energy) &
                                 (buildings['backup_heating_share'] > 0.) &
                                 (buildings.to_sim)].index,
        }
    }
    heating_system_dict['main']['share'] = 1. - buildings.loc[
        heating_system_dict['main']['ids'], 'backup_heating_share'].values
    heating_system_dict['backup']['share'] = buildings.loc[
        heating_system_dict['backup']['ids'], 'backup_heating_share'].values

    return heating_system_dict


def run_models(buildings):
    """
    runs the energy consumption model

    Args:
        buildings:

    Returns:

    """
    annual_energy_consumption(buildings)
    conventional_energy_consumption(buildings)