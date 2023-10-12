# -*- coding: utf-8 -*-
import datetime

from Simulation.climate import run_models_BM as run_climate_models_BM
from Simulation.solar_gains import run_models as run_solar_gain_models
from Simulation.thermal_losses import run_models as run_thermal_loss_models
from Simulation.thermal_needs import run_models as run_thermal_need_models
from Simulation.energy_consumption import run_models as run_energy_consumption_models
from Simulation.energy_indicators import run_models as run_energy_indicators
from Simulation.buildingmodel.exceptions import ModelListError
from pvlib.iotools import read_epw

EPW_name_dict = {
    "temp_air": "air_temperature",
    "temp_dew": "dew_point_temperature",
    "dni": "direct_normal_radiation",
    "dhi": "diffuse_horizontal_radiation",
    "opaque_sky_cover": "opaque_sky_cover",
}

energy_list     = ['electricity', 'gas', 'oil', 'biomass', 'district_network', 'biogas']

def load_climate_data(file_path):
    """Reads an EPW climate file and returns the relevant climate data

    Args:
        file_path (str): path to EPW climate file

    Returns:
        Dataframe : DataFrame containing air_temperature, dew_point_temperature, wind_speed, wind_direction,
        direct_normal_radiation, diffuse_horizontal_radiation
    """

    data, metadata = read_epw(file_path, coerce_year="2019")
    data = data.loc[:, EPW_name_dict.keys()]
    data = data.rename(EPW_name_dict, axis=1)
    data.astype(float)

    return data, metadata

ALL_MODELS = ['climate', 'solar_masks', 'solar_gains', 'thermal_losses', 'dwelling_needs', 'thermal_needs',
              'energy_consumption', 'energy_indicators']

def run_models_quick(buildings, boundaries, climate, metadata, parameters):

    """buildingmodel main function

    Loads building and weather data and runs the models in model_list in sequential order

    Args:
        dwellings (GeoDataframe): a GeoDataframe containing the dwelling parameters
        boundaries (GeoDataframe): a GeoDataframe containing the boundary geometries and parameters
        buildings (GeoDataframe): a GeoDataframe containing the building geometries and parameters
        climate (GeoDataframe): a GeoDataframe containing the climate data
        metadata (dict): climate metadata
        parameters: instance of class Parameters

    Returns:
        tuple of DataFrame and GeoDataFrame, containing the results of the models
    """

    check_model_list(parameters.models)

    # Climate models
    if 'climate' in parameters.models:
        run_climate_models_BM(climate, metadata)

    # Solar gain models
    if 'solar_gains' in parameters.models:
        run_solar_gain_models(buildings, boundaries, climate)

    # Thermal loss models
    if 'thermal_losses' in parameters.models:
        run_thermal_loss_models(buildings, boundaries, climate)

    """
    # dwelling needs
    if 'dwelling_needs' in parameters.models:
        run_dwelling_need_models(dwellings, climate)
    """

    # Thermal need models
    if 'thermal_needs' in parameters.models:
        run_thermal_need_models(buildings, boundaries, parameters)

    # Energy consumption
    if 'energy_consumption' in parameters.models:
        run_energy_consumption_models(buildings)

    if 'energy_indicators' in parameters.models:
        run_energy_indicators(buildings, parameters)

    return buildings

def check_model_list(model_list):
    """checks a model list for validity

    A model list is valid if it is a slice of the N first elements of :attr:`buildingmodel.main.ALL_MODELS` with N > 0

    Args:
        model_list (list of str): a list of model names in :attr:`buildingmodel.main.ALL_MODELS`

    Returns:
        bool: True if model list is valid
    """

    model_count = len(model_list)

    if model_count > 0 and model_list == ALL_MODELS[:model_count]:
        return True
    else:
        raise ModelListError(model_list, ALL_MODELS)

class Parameters(object):
    """
    A class containing all the parameters necessary for a building simulation
    """

    def __init__(self, simplification_tolerance=2., models=None, grid_resolution=2.0, angular_resolution=10.,
                 bbox_filter=100., albedo=2.0, heating_season_start=datetime.datetime(2019, 10, 1),
                 heating_season_end=datetime.datetime(2020, 5, 20), rename_dict=None, usage_dict=None, category_filters=None,
                 id_col='ID', minimal_surface=15., minimal_height=2.0, vertical_adjacency_tolerance=1.0,
                 minimal_boundary_area=0.5, encoding='utf8', floor_height=None,
                 date_format='%Y-%m-%d', conventional_heating_set_point=19., actual_heating_set_point=20.,
                 maximal_occupant_gain_share=0.3, maximal_solar_gain_share=0.3, temperature_altitude_correction=0.2,
                 max_iteration=5, construction_year_class=None,
                 districts='districts.gpkg', district_level_census='district_level_census.hdf',
                 district_level_diagnosis='district_level_diagnosis_data.hdf',
                 gas_network_route='gas_network_route.gpkg',
                 minimal_diagnosis_share=0.1, gas_network_margin=0.1, primary_energies=None, co2_energies=None, n_cpu=8,
                 climate_folder=None, correct_class_imbalance=True, set_point_list=None):

        if models is None:
            models = ALL_MODELS

        if rename_dict is None:
            rename_dict = {
                'USAGE1': 'main_usage',
                'USAGE2': 'secondary_usage',
                'DATE_APP': 'construction_date',
                'NB_LOGTS': 'dwelling_count',
                'NB_ETAGES': 'floor_count',
                'MAT_MURS': 'wall_material',
                'MAT_TOITS': 'roof_material',
                'HAUTEUR': 'height',
                'Z_MIN_SOL': 'altitude_min',
                'Z_MAX_SOL': 'altitude_max',
            }

        if usage_dict is None:
            usage_dict = {
                'Résidentiel': 'residential',
                'Agricole': 'agriculture',
                'Annexe': 'annex',
                'Commercial et services': 'commercial',
                'Indifférencié': 'unknown',
                'Industriel': 'industrial',
                'Religieux': 'religious'
            }

        if category_filters is None:
            category_filters = {
                'LEGER': ['Non']
            }

        if floor_height is None:
            floor_height = {
                'house': {
                    'min': 2.0,
                    'max': 2.6,
                          },
                'apartment': {
                    'min': 2.6,
                    'max': 3.5,
                          }
            }

        if construction_year_class is None:
            construction_year_class = {
                1: [1000, 1918],
                2: [1919, 1945],
                3: [1946, 1970],
                4: [1971, 1990],
                5: [1991, 2005],
                6: [2006, 2012],
                7: [2013, 2100],
            }

        if primary_energies is None:
            primary_energies = {
                "electricity": 2.0,
                "electricity_ECS": 2.0,
                #"fossil_gas": 1,
                #"liquified_petroleum_gas": 1,
                "gas":1,
                "oil": 1,
                "biomass": 0.6,
                'district_network': 0.6,
                "biogas": 1
            }

        if co2_energies is None:
            co2_energies = {
                "electricity": 0.079,
                "electricity_ECS": 0.065,
                "gas": 0.227,
                "oil": 0.324,
                "biomass": 0.024,
                'district_network': 0.204,
                "biogas": 0.024
            }

        self.simplification_tolerance = simplification_tolerance
        self.models = models
        self.grid_resolution = grid_resolution
        self.angular_resolution = angular_resolution
        self.bbox_filter = bbox_filter
        self.albedo = albedo
        self.heating_season_start = heating_season_start
        self.heating_season_end = heating_season_end
        self.rename_dict = rename_dict
        self.usage_dict = usage_dict
        self.category_filters = category_filters
        self.id_col = id_col
        self.minimal_surface = minimal_surface
        self.minimal_height = minimal_height
        self.floor_height = floor_height
        self.vertical_adjacency_tolerance = vertical_adjacency_tolerance
        self.minimal_boundary_area = minimal_boundary_area
        self.encoding = encoding
        self.date_format = date_format
        self.conventional_heating_set_point = conventional_heating_set_point
        self.actual_heating_set_point = actual_heating_set_point
        self.maximal_occupant_gain_share = maximal_occupant_gain_share
        self.maximal_solar_gain_share = maximal_solar_gain_share
        self.max_iteration = max_iteration
        self.construction_year_class=construction_year_class
        self.districts = districts
        self.gas_network_route = gas_network_route
        self.district_level_census = district_level_census
        self.district_level_diagnosis = district_level_diagnosis
        self.minimal_diagnosis_share = minimal_diagnosis_share
        self.gas_network_margin = gas_network_margin
        self.primary_energies = primary_energies
        self.co2_energies = co2_energies
        self.n_cpu = n_cpu
        self.climate_folder = climate_folder
        self.correct_class_imbalance = correct_class_imbalance
        self.temperature_altitude_correction = temperature_altitude_correction
        self.set_point_list = set_point_list

