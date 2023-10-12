# -*- coding: utf-8 -*-

import numpy as np
import pvlib


def sun_position(climate_data, latitude, longitude):
    """Calculate the height and azimuth of the sun for an array of time steps at a given latitude and longitude

    Based on astronomy computations provided by the `ephem package <https://rhodesmill.org/pyephem/>`_
    Uses the ephem.Observer and ephem.Sun classes.

    Args:
        climate_data (Dataframe): a Dataframe with a DateTimeIndex for which the sun position is to be calculated
        latitude (float):
        longitude (float):

    Returns:
        Dataframe : DataFrame containing sun_height and sun_azimuth
    """

    solar_position = pvlib.solarposition.get_solarposition(climate_data.index, latitude, longitude)
    climate_data["sun_height"] = solar_position['elevation']
    climate_data["sun_azimuth"] = solar_position['azimuth']



def sky_temperature(climate_data):
    """Calculate the sky temperature using the air temperature, dew point temperature and sky cover

    Based on `EnergyPlus model <https://bigladdersoftware.com/epx/docs/8-3/engineering-reference/climate-calculations
    .html#energyplus-sky-temperature-calculation/>`_.

    Args:
        climate_data (Dataframe): a Dataframe containing dew point temperature, air temperature and opaque sky cover
        data
        latitude (float):
        longitude (float):

    Returns:
        Dataframe : DataFrame containing sky temperature
    """

    sigma = 5.66797e-8  # Stefan-Boltzmann constant (in W/m2-K4)
    N = climate_data["opaque_sky_cover"] / 10.0
    sky_emissivity = (0.787 + 0.764 * np.log((climate_data["dew_point_temperature"] + 273.15) / 273.15)) * (
        1 + 0.0224 * N - 0.0035 * N ** 2 + 0.00028 * N ** 3
    )
    horizontal_infrared_radiation = sky_emissivity * sigma * (climate_data["air_temperature"] + 273.15) ** 4
    sky_temperature = (horizontal_infrared_radiation / sigma) ** 0.25 - 273.15
    climate_data["sky_temperature"] = sky_temperature



def ground_temperature(climate_data, ground_diffusivity=0.8e-6, depth=0.5):
    """Calculate the ground temperature using the air temperature

    Uses the `Kusuda model <https://bigladdersoftware.com/epx/docs/8-4/engineering-reference/undisturbed-ground
    -temperature-model-kusuda.html/>`_

    Typical values of thermal diffusivity for various types of soils can be found in :
    Andújar Márquez, J. M., Martínez Bohórquez, M. Á., & Gómez Melgar, S. (2016). Ground thermal diffusivity
    calculation by direct soil temperature measurement.
    Application to very low enthalpy geothermal energy systems. Sensors, 16(3), 306.

    Args:
        climate_data (Dataframe): a Dataframe containing air temperature
        ground_diffusivity (float): the thermal diffusivity of the soil in m²/s
        depth (float): the depth at which the ground temperature is to be estimated in meters

    Returns:
        Dataframe : DataFrame containing ground temperature
    """

    # Monthly rolling average of air temperature
    air_temperature_smoothed = climate_data["air_temperature"].rolling(int(24.0 * 30.5)).mean().fillna(method="bfill")
    ground_temperature_delta = (max(air_temperature_smoothed) - min(air_temperature_smoothed)) / 2.0
    ground_average_temperature = np.mean(air_temperature_smoothed)
    time = (np.array(list(range(len(climate_data["air_temperature"])))) + 1.0) / 24.0
    phase_shift = climate_data["air_temperature"].idxmin().dayofyear

    # Kusuda equation 1965
    ground_temperature = ground_average_temperature - ground_temperature_delta * np.exp(
        -depth * np.sqrt(np.pi / (ground_diffusivity * 365.0 * 3600.0))
    ) * np.cos(
        2 * np.pi / 365.0 * (time - phase_shift - depth / 2.0 * np.sqrt(365.0 / (np.pi * ground_diffusivity * 3600.0)))
    )
    climate_data["ground_temperature"] = ground_temperature


def run_models(climate_data, metadata):
    """Runs all climate models

    Args:
        climate_data (DataFrame): a Dataframe containing EPW climate data loaded by
        :func:`buildingmodel.io.climate.load_data`

    Returns:
        Dataframe : DataFrame containing all necessary climate data
    """

    sun_position(climate_data, metadata["latitude"], metadata["longitude"])
    sky_temperature(climate_data)
    ground_temperature(climate_data)
    climate_data['air_temperature'] -= (metadata['building_altitude'][0] - metadata['altitude']) / 100. * 0.6
    climate_data['extra_terrestrial'] = pvlib.irradiance.get_extra_radiation(climate_data.index).values

def run_models_BM(climate_data, metadata):
    """Runs all climate models

    Args:
        climate_data (DataFrame): a Dataframe containing EPW climate data loaded by
        :func:`buildingmodel.io.climate.load_data`

    Returns:
        Dataframe : DataFrame containing all necessary climate data
    """

    sun_position(climate_data, metadata["latitude"], metadata["longitude"])
    sky_temperature(climate_data)
    ground_temperature(climate_data)
    climate_data['air_temperature'] -= (metadata['building_altitude'] - metadata['altitude']) / 100. * 0.6
    climate_data['extra_terrestrial'] = pvlib.irradiance.get_extra_radiation(climate_data.index).values
