import gc
from datetime import datetime
import numpy as np
import pandas as pd
import pvlib
#import buildingmodel.cython_utils.shading as shading_utils
from Simulation.utils import heating_season, add_parameter_from_building

# Integer variables for boundary types
EXTERIOR_WALL = 0
INTERIOR_WALL = 1
ROOF = 2
FLOOR = 3


def mask_influence(boundaries, climate):
    """This function calculates the influence of the solar masks of each boundary on the diffuse and direct normal
    radiation

    For the direct radiation, at each time step and for each boundary, the sun height is compared to the
    height of the solar mask for the current sun azimuth. If it is higher, the original direct radiation value
    is retained. If not, it is set to 0.

    For the diffuse radiation, a sky view factor for each boundary is calculated and then applied to the diffuse
    radiation (Middel, A., Lukasczyk, J., Maciejewski, R., Demuzere, M., & Roth, M. (2018).
    Sky View Factor footprints for urban climate modeling. Urban climate, 25, 120-134.)

    Args:
        boundaries (GeoDataframe): a GeoDataframe containing the boundary geometries
        climate (Dataframe): a Dataframe containing climate data

    Returns:
        a tuple of numpy arrays containing the horizontal diffuse and normal direct radiation for each boundary
        and each time step
    """

    solar_exposed_boundaries = boundaries.loc[boundaries['type'].isin([0, 2]), :]
    mask_columns = [col_name for col_name in solar_exposed_boundaries.columns if col_name.startswith('mask_')]

    masks = solar_exposed_boundaries.loc[solar_exposed_boundaries['type'].isin([0, 2]), mask_columns].values
    #visible_beam = shading_utils.visible_beam(masks.astype(np.float64),
                                              #climate['sun_height'].values.astype(np.float64),
                                              #climate['sun_azimuth'].values.astype(np.float64))
    visible_beam = 0.8
    direct_radiation = climate['direct_normal_radiation'].values * visible_beam

    # sky_view = 1 - 1. / masks.shape[1] * ((np.sin(np.radians(masks)) ** 2).sum(axis=1))
    # diffuse_radiation = climate['diffuse_horizontal_radiation'].values * np.tile(sky_view.reshape((-1, 1)),
    #                                                                              climate.shape[0])

    return direct_radiation


def radiation_on_boundary_model(boundaries, direct_radiation, climate):
    """Calculation of the angle of incidence and diffuse and direct radiation on each boundary

    Returns:

    """
    solar_exposed_boundaries = boundaries.loc[boundaries['type'].isin([EXTERIOR_WALL, ROOF]), :]
    boundary_inclinations = get_boundary_inclination(solar_exposed_boundaries)
    boundary_count = solar_exposed_boundaries.shape[0]

    sun_azimuth = np.tile(climate['sun_azimuth'].values.reshape(-1, 1), boundary_count).transpose()
    zenith = 90. - climate['sun_height'].values
    angle_of_incidence = pvlib.irradiance.aoi(boundary_inclinations.reshape((-1, 1)),
                                              solar_exposed_boundaries['azimuth'].values.reshape((-1, 1)),
                                              zenith,
                                              sun_azimuth)

    poa_direct = np.maximum(direct_radiation * np.cos(np.radians(angle_of_incidence)), 0.)
    # poa_diffuse = sky_diffuse + ground_diffuse

    return poa_direct, angle_of_incidence


def get_boundary_inclination(solar_exposed_boundaries):
    """

    Args:
        solar_exposed_boundaries:

    Returns:

    """

    boundary_inclinations = np.zeros(solar_exposed_boundaries.shape[0])
    boundary_inclinations[solar_exposed_boundaries['type'] == EXTERIOR_WALL] = 90.

    return boundary_inclinations


def transmission_model(boundaries, direct_radiation, angle_of_incidence,
                       heating_period_mask):
    """Calculates the total solar gains absorbed by the boundaries (opaque and windows) and transmitted (windows)
    during the heating season when the air temperature is below the heating set point

    Args:
        boundaries (GeoDataframe): a GeoDataframe containing the boundary geometries
        direct_radiation:
        diffuse_radiation:
        angle_of_incidence:
        heating_period_mask: a pd.DataFrame (time steps x solar boundaries) containing a mask (0 or 1 values) defining
        the steps during the heating season when the air temperature is below the heating set point

    Returns:
        GeoDataframe with columns absorbed_solar_gain and transmitted_solar_gain in kWh
    """

    direct_radiation = direct_radiation * heating_period_mask.values.transpose()

    boundaries['transmitted_solar_gain'] = 0.
    boundaries['window_area'] = boundaries['window_share'] * boundaries['area']
    boundaries['opaque_area'] = boundaries['area'] - boundaries['window_area']

    solar_boundaries = boundaries.loc[boundaries['type'].isin([EXTERIOR_WALL, ROOF]), :]

    window_transmission_factor = solar_boundaries['window_solar_factor'].values.reshape((-1, 1))
    transmission_coefficient = np.clip(((1. - (angle_of_incidence / 90.) ** 5) * window_transmission_factor), 0., 1.)
    direct_transmission = transmission_coefficient * direct_radiation
    boundaries.loc[solar_boundaries.index, 'transmitted_solar_gain'] = solar_boundaries['window_area'] * (direct_transmission).sum(axis=1) / 1000.


def heating_periods(climate, boundaries, heating_season_start=datetime(2019, 10, 1),
                    heating_season_end=datetime(2020, 5, 20)):
    """Calculates the time steps belonging to heating season and for which the air temperature is below the heating set
    point.

    Returns:
        pandas.DataFrame
    """
    heating_season_index = heating_season(climate, heating_season_start, heating_season_end)
    solar_boundaries = boundaries.loc[boundaries['type'].isin([EXTERIOR_WALL, ROOF]), :]
    unique_set_points = solar_boundaries['actual_heating_set_point'].unique()

    heating_period_mask = pd.DataFrame(index=climate.index, columns=solar_boundaries.index, data=0.)

    for set_point in unique_set_points:
        boundary_indices = solar_boundaries.loc[solar_boundaries['actual_heating_set_point'] == set_point, :].index
        heating_period_mask.loc[climate['air_temperature'] < set_point, boundary_indices] = 1.

    heating_period_mask.loc[~heating_period_mask.index.isin(heating_season_index), :] = 0.

    return heating_period_mask


def run_models(buildings, boundaries, climate):
    """

    Args:
        buildings:
        boundaries (GeoDataframe): a GeoDataframe containing the boundary geometries
        climate (Dataframe): a Dataframe containing climate data
        parameters

    Returns:

    """

    direct_radiation = mask_influence(boundaries, climate)
    gc.collect()

    direct_radiation, angle_of_incidence = radiation_on_boundary_model(boundaries, direct_radiation, climate)
    gc.collect()

    heating_period_mask = heating_periods(climate, boundaries)
    gc.collect()
    transmission_model(boundaries, direct_radiation, angle_of_incidence, heating_period_mask)
    gc.collect()
