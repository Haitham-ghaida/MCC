import datetime
from scipy.stats import beta
import numpy as np

CP_AIR = 1004.  # Heat capacity of air in J/kg/K
RHO_AIR = 1.2  # Density of air at 20 °C in kg/m3


def get_building_from_index(buildings, index):

    return [build for build in buildings.values() if build["id"] == index][0]


def heating_season(climate, heating_season_start=datetime.datetime(2019, 10, 1),
                   heating_season_end=datetime.datetime(2020, 5, 20)):
    """
    Create the pandas DateTimeIndex corresponding to the heating season

    Args:
        climate:
        heating_season_start:
        heating_season_end:

    Returns:
        pandas.DateTimeIndex
    """

    climate_year = climate.index[0].year
    heating_season_start = heating_season_start.replace(year=climate_year)
    heating_season_end = heating_season_end.replace(year=climate_year)

    # From January 1st to heating season end
    first_period = climate.index[climate.index.dayofyear < heating_season_end.timetuple().tm_yday]

    # From heating season start to December 31st
    second_period = climate.index[climate.index.dayofyear > heating_season_start.timetuple().tm_yday]

    return first_period.union(second_period)


def add_parameter_from_building(boundaries, buildings, boundary_parameter_name, building_parameter_name, boundary_types=None):
    """

    Args:
        boundaries (GeoDataframe): a GeoDataframe containing the boundary geometries and parameters
        buildings (GeoDataframe): a GeoDataframe containing the building geometries and parameters
        boundary_parameter_name (str): the name of the parameter to retrieve in buildings
        building_parameter_name (str): the name of the parameter to set in boundaries
        boundary_types (list of ints): the list of types of the boundaries on which to apply the parameter. Defaults to
        None in which case it is applied to all types

    Returns:
        boundaries (GeoDataframe): a GeoDataframe containing the boundary geometries and parameters
    """

    if boundary_parameter_name not in boundaries.columns:
        boundaries[boundary_parameter_name] = 0.

    if boundary_types is None:
        boundary_types = range(4)

    for building_index in buildings.index:
        current_boundaries = boundaries.loc[boundaries['building_id'] == buildings.loc[building_index, 'building_id'], :]
        for boundary_type in boundary_types:
            type_boundaries = current_boundaries.loc[current_boundaries['type'] == boundary_type, :]
            boundaries.loc[type_boundaries.index, boundary_parameter_name] = buildings.loc[building_index,
                                                                                           building_parameter_name]


def get_beta_distribution(dist_dict, count):
    """

    Args:
        dist_dict:
        count:

    Returns:

    """
    # np.random.seed()
    beta_distribution = beta.rvs(dist_dict['alpha'],
                                 dist_dict['beta'],
                                 size=count)

    return dist_dict['min'] + beta_distribution * (dist_dict['max'] - dist_dict['min'])
