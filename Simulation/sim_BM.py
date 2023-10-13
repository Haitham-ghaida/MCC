import pandas as pd
from Simulation.main import *
import os


path = os.path.dirname(__file__)
data_path = {'data': path + '/data/'}

french_climate_data = data_path['data'] + 'FRA_AR_Grenoble.074850_TMYx.epw'
norway_climate_data = data_path['data'] + 'NOR_OS_Alna.014870_TMYx.2007-2021.epw'
french_climate, french_metadata = load_climate_data(french_climate_data)
norway_climate, norway_metadata = load_climate_data(norway_climate_data)

reno_dict = {'231 Bearing outer wall':None,
             '251 Loadbering deck':None,
             '262 Roof covering':None,
             '234 Windows':None,
             '291 Mass inventory heating':None}

co2_energies = {
                "electricity": 0.079,
                "electricity_ECS": 0.065,
                "gas": 0.227,
                "oil": 0.324,
                "biomass": 0.024,
                'district_network': 0.204,
                "biogas": 0.024
            }

def FMES(climate, metadata, reno_dict, heating_set_point = 18):

    buildings = pd.read_csv(data_path['data'] + 'Building_case_study.csv', sep=';')
    boundaries = pd.read_csv(data_path['data'] + 'Boundaries_case_study.csv', sep=';')
    metadata['building_altitude'] = buildings.altitude.mean()

    buildings['actual_heating_set_point'] = heating_set_point
    boundaries['actual_heating_set_point'] = heating_set_point

    buildings.set_index('building_id', inplace=True, drop=False)

    if reno_dict['291 Mass inventory heating'] is not None:
        buildings['main_heating_system_efficiency'] = reno_dict['291 Mass inventory heating']     # efficiency heating_system
        buildings['cooking_energy'] = 'electricity'
        buildings['dhw_energy'] = 'electricity'
        buildings['main_heating_energy'] = 'electricity'

    if reno_dict['234 Windows'] is not None:
        boundaries.loc[boundaries.window_share != 0., 'window_u_value'] = 1.5      #windows

    if reno_dict['262 Roof covering'] is not None:
        boundaries.loc[boundaries.type == 2, 'u_value'] = 0.2       #roof

    if reno_dict['251 Loadbering deck'] is not None:
        boundaries.loc[boundaries.type == 3, 'u_value'] = 0.2       #floor

    if reno_dict['231 Bearing outer wall'] is not None:
        boundaries.loc[boundaries.type == 0, 'u_value'] = 0.2       #exterior walls

    parameters = Parameters(co2_energies=co2_energies)

    buildings = run_models_quick(buildings, boundaries, climate, metadata, parameters)
    #print(float(buildings['total_CO2_emission'].iloc[0]), float(buildings['total_final_consumption'].iloc[0]), buildings['diagnosis_class'].iloc[0])

    return float(buildings['total_final_consumption'].iloc[0])


Energy_consumption_kWh = FMES(french_climate, french_metadata, reno_dict,16)


