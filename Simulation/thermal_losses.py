import datetime
import numpy as np
from Simulation.utils import heating_season, CP_AIR, RHO_AIR
import geopandas as gpd

# Integer variables for boundary types
EXTERIOR_WALL = 0
INTERIOR_WALL = 1
ROOF = 2
FLOOR = 3

def unified_degree_hours(buildings, boundaries, climate, heating_season_start=datetime.datetime(2019, 10, 1),
                         heating_season_end=datetime.datetime(2020, 5, 20)):
    """
    Calculates the unified degree hours for each boundary and building. Unified degree hours are obtained by taking
    the sum of the difference between the heating set point and the exterior temperature for each hour of the heating
    season during which the exterior temperature is below the heating set point. For walls, roofs and buildings,
    the exterior temperature is the air temperature. For floors, it is the ground temperature.

    Args:
        buildings (GeoDataframe): a GeoDataframe containing the building geometries
        boundaries (GeoDataframe): a GeoDataframe containing the boundary geometries
        climate (Dataframe): a Dataframe containing climate data
        heating_season_start (datetime.time): start of the heating season
        heating_season_end (datetime.time): end of the heating season

    Returns:

    """
    # we select the temperatures during the heating season
    heating_season_index = heating_season(climate, heating_season_start, heating_season_end)
    air_temperature = climate.loc[heating_season_index, 'air_temperature']
    ground_temperature = climate.loc[heating_season_index, 'ground_temperature']

    # Calculation is done for unique values of the heating set points and then applied to the corresponding boundaries
    # and buildings
    for mode in ['conventional', 'actual']:
        set_point_variable = f'{mode}_heating_set_point'
        udh_variable = f'{mode}_unified_degree_hours'
        unique_set_points = boundaries[set_point_variable].unique()
        boundaries['unified_degree_hours'] = 0.

        for set_point in unique_set_points:
            # unified degree hours for walls, roofs and buildings
            air_unified_degree_hour = (set_point - air_temperature[air_temperature < set_point]).sum()
            boundaries.loc[(boundaries['type'].isin([0, 2])) & (boundaries[set_point_variable] == set_point),
                           udh_variable] = air_unified_degree_hour
            buildings.loc[buildings[set_point_variable] == set_point, udh_variable] = air_unified_degree_hour

            # unified degree hours for floors
            ground_unified_degree_hour = (set_point - ground_temperature[ground_temperature < set_point]).sum()
            boundaries.loc[(boundaries['type'].isin([3])) & (boundaries[set_point_variable] == set_point),
                           udh_variable] = ground_unified_degree_hour

            # heating season duration in hours
            heating_season_duration = (air_temperature < set_point).sum()
            buildings.loc[buildings[set_point_variable] == set_point, 'heating_season_duration'] = heating_season_duration


def maximal_temperature_difference(buildings, boundaries, climate):
    """
    Calculates the maximal temperature difference between the interior of a building and the exterior air during the
    heating period

    Args:
        boundaries:
        climate:

    Returns:

    """

    boundaries['maximal_temperature_difference'] = 0.
    min_air_temperature = climate['air_temperature'].min()
    min_ground_temperature = climate['ground_temperature'].min()
    boundaries.loc[boundaries['type'] == EXTERIOR_WALL, 'maximal_temperature_difference'] = \
        boundaries.loc[boundaries['type'] == EXTERIOR_WALL, 'actual_heating_set_point'] - min_air_temperature
    boundaries.loc[boundaries['type'] == FLOOR, 'maximal_temperature_difference'] = \
        boundaries.loc[boundaries['type'] == FLOOR, 'actual_heating_set_point'] - min_ground_temperature
    boundaries.loc[boundaries['maximal_temperature_difference'] < 0., 'maximal_temperature_difference'] = 0.

    buildings['maximal_temperature_difference'] = buildings['actual_heating_set_point'] - min_air_temperature
    buildings.loc[buildings['maximal_temperature_difference'] < 0., 'maximal_temperature_difference'] = 0.


def adjacency_factor(boundaries):
    """
    Calculates a factor to apply to a boundary to model the share of losses due to adjacency. Its value is 1.
    for exterior walls, roofs and floors (no loss prevented), 0.2 for interior walls when the other use is residential,
    0.8 for commercial use and 1. for other uses.

    Args:
        boundaries:

    Returns:

    """
    exterior_bnds = boundaries['type'].isin([EXTERIOR_WALL, ROOF, FLOOR])
    interior_bnds = boundaries['type'].isin([INTERIOR_WALL])

    boundaries.loc[exterior_bnds, 'adjacency_factor'] = 1.
    boundaries.loc[interior_bnds, 'adjacency_factor'] = 1.
    #boundaries.loc[interior_bnds & (boundaries['adjacency_usage'] == 'residential'), 'adjacency_factor'] = 0.2
    #boundaries.loc[interior_bnds & (boundaries['adjacency_usage'] == 'commercial'), 'adjacency_factor'] = 0.8


def thermal_bridge_losses(boundaries):
    """
    Calculates the annual losses through thermal bridges. The models consider three types of thermal bridges :
     * between wall and roof
     * between wall and floor
     * between wall and intermediate floor

    For each type, conventional values of thermal bridge linear losses are selected according to the level of insulation
    of the wall, roof and floor

    Args:
        boundaries:

    Returns:

    """
    insulated_wall_ids = boundaries.loc[(boundaries['type'] == EXTERIOR_WALL) & (boundaries.u_value < 0.8)].index
    uninsulated_wall_ids = boundaries.loc[(boundaries['type'] == EXTERIOR_WALL) & (boundaries.u_value >= 0.8)].index
    boundaries.loc[insulated_wall_ids, 'thermal_bridge_loss_factor'] = 0.3 * gpd.GeoSeries(boundaries.loc[insulated_wall_ids, 'geometry']).length * np.abs(np.floor(boundaries.loc[insulated_wall_ids, 'floor_count'] - 1))
    boundaries.loc[uninsulated_wall_ids, 'thermal_bridge_loss_factor'] = 0.9 * gpd.GeoSeries(boundaries.loc[uninsulated_wall_ids, 'geometry']).length * np.abs(np.floor(boundaries.loc[uninsulated_wall_ids, 'floor_count'] - 1))


    insulated_roof_ids = boundaries.loc[(boundaries['type'] == ROOF) & (boundaries.u_value < 1.2)].index
    uninsulated_roof_ids = boundaries.loc[(boundaries['type'] == ROOF) & (boundaries.u_value >= 1.2)].index
    boundaries.loc[insulated_roof_ids, 'thermal_bridge_loss_factor'] = 0.2 * boundaries.loc[insulated_roof_ids, 'geometry'].length
    boundaries.loc[uninsulated_roof_ids, 'thermal_bridge_loss_factor'] = 0.5 * boundaries.loc[uninsulated_roof_ids, 'geometry'].length


    insulated_floor_ids = boundaries.loc[(boundaries['type'] == FLOOR) & (boundaries.u_value < 1.2)].index
    uninsulated_floor_ids = boundaries.loc[(boundaries['type'] == FLOOR) & (boundaries.u_value >= 1.2)].index
    boundaries.loc[insulated_floor_ids, 'thermal_bridge_loss_factor'] = 0.3 * boundaries.loc[insulated_floor_ids, 'geometry'].length
    boundaries.loc[uninsulated_floor_ids, 'thermal_bridge_loss_factor'] = 0.6 * boundaries.loc[uninsulated_floor_ids, 'geometry'].length

    # boundaries['thermal_bridge_loss_factor'] = 0.


def boundary_losses(boundaries):
    """Calculates the annual boundary losses by multiplying the U values of the boundaries with their area and unified
    degree hours. Calculates the peak boundary losses by multiplying the U values of the boundaries with their area
    and maximal temperature difference.

    Args:
        boundaries (GeoDataframe): a GeoDataframe containing the boundary geometries and parameters

    Returns:

    """
    boundaries['loss_factor'] = (boundaries['u_value'] * boundaries['opaque_area'] + boundaries['window_u_value'] *
                                 boundaries['window_area'])
    boundaries['annual_thermal_losses'] = (boundaries['loss_factor'] * boundaries['adjacency_factor'] +
                                           boundaries['thermal_bridge_loss_factor']) * boundaries['actual_unified_degree_hours'] / 1000.
    boundaries['conventional_thermal_losses'] = (boundaries['loss_factor'] * boundaries['adjacency_factor'] +
                                           boundaries['thermal_bridge_loss_factor']) * boundaries['conventional_unified_degree_hours'] / 1000.
    boundaries['peak_thermal_losses'] = (boundaries['loss_factor'] * boundaries['adjacency_factor']
                                         + boundaries['thermal_bridge_loss_factor']) * boundaries['maximal_temperature_difference']


def ventilation_losses(buildings):
    """Calculates the ventilation losses for each building by multiplying the unified degree hours by the air change
    rate, the volume and the heat capacity of the air

    Args:
        buildings:

    Returns:

    """
    #buildings['volume'] = buildings['height'] * buildings.geometry.area
    buildings['annual_ventilation_losses'] = (buildings['actual_unified_degree_hours'] * buildings['volume'] *
                                              buildings['air_change_rate'] * CP_AIR * RHO_AIR) / (3600. * 1000.)
    buildings['conventional_ventilation_losses'] = (buildings['conventional_unified_degree_hours'] * buildings['volume'] *
                                              buildings['air_change_rate'] * CP_AIR * RHO_AIR) / (3600. * 1000.)
    buildings['peak_ventilation_losses'] = (buildings['maximal_temperature_difference'] * buildings['volume'] *
                                            buildings['air_change_rate'] * CP_AIR * RHO_AIR) / 3600.


def run_models(buildings, boundaries, climate):
    """
    run the models to calculate the thermal losses of a building (ventilation and boundaries)

    Args:
        buildings (GeoDataframe): a GeoDataframe containing the building geometries and parameters
        boundaries (GeoDataframe): a GeoDataframe containing the boundary geometries and parameters
        climate (Dataframe): a Dataframe containing climate data
        parameters

    Returns:

    """
    unified_degree_hours(buildings, boundaries, climate)
    maximal_temperature_difference(buildings, boundaries, climate)
    #thermal_bridge_losses(boundaries)
    boundaries['thermal_bridge_loss_factor'] = 0.
    #adjacency_factor(boundaries)
    boundary_losses(boundaries)
    ventilation_losses(buildings)
