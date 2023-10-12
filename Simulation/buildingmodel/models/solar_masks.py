import numpy as np
import pandas as pd
import shape_optim.buildingmodel.cython_utils.shading as shading_utils
from shape_optim.buildingmodel.logger import duration_logging


@duration_logging
def elevation_model(buildings, grid_resolution=1.):
    """Create an elevation model from the gis data representing the buildings

    To minimize the computation burden of mask calculation, we include in the grid only the points that fall in the
    building footprints.
    To do so, we iterate over the buildings and create a grid that covers the bounding box of their footprint. Then
    we select only the points that are contained by the building footprint and assign to their z coordinate the
    altitude of the building's roof.

    Args:
        buildings (GeoDataframe): a GeoDataframe containing the building geometries and parameters
        grid_resolution (float): the resolution of the grid on which the elevation model due to buildings will be
        calculated

    Returns: a N x 3 numpy array containing the coordinates of the points

    """

    coordinate_list = []
    polygon_ends = []

    for i, idx in enumerate(buildings.index):
        coordinate_array = np.array(buildings.geometry[idx].exterior.coords)
        non_duplicate_ids = np.append(np.where(np.diff(coordinate_array, axis=0).sum(axis=1) != 0.)[0],
                                      coordinate_array.shape[0] - 1)
        coordinate_array = coordinate_array[non_duplicate_ids, :]
        roof_altitude = buildings.loc[idx, 'height'] + buildings.loc[idx, 'altitude']
        coordinate_array = np.concatenate([coordinate_array, roof_altitude * np.ones((coordinate_array.shape[0], 1))],
                                          axis=1)
        coordinate_list.append(coordinate_array)

        if i == 0:
            polygon_ends.append(coordinate_array.shape[0] - 1)
        else:
            polygon_ends.append(coordinate_array.shape[0] + polygon_ends[i - 1])

    all_coordinates = np.concatenate(coordinate_list).astype(np.float64)
    polygon_ends = np.array(polygon_ends, dtype=np.int32)
    points = np.array(shading_utils.discretize_polygons(all_coordinates, polygon_ends, np.float64(grid_resolution)))
    return points


@duration_logging
def solar_mask(boundaries, elevation_data, angular_resolution=5., bbox_filter=100.):
    """Calculates the solar mask from boundary geometries and elevation data

    For each boundary, the height and azimuth of all the points in the grid are calculated. Then the points are binned
    in the azimuth intervals for which the mask is calculated, with the maximum angular height for each bin giving the
    mask value.

    Args:
        boundaries (GeoDataframe): a GeoDataframe containing the boundary geometries
        elevation_data (numpy array): a N x 3 containing elevation data
        angular_resolution (float): the angular resolution (in degrees) at which the mask will be computed. Defaults to 5.
        bbox_filter (float):

    Returns: a Dataframe containing the angular height of the mask for each boundary (index) and each azimuth interval (columns)

    """

    boundary_centers = np.zeros((boundaries.shape[0], 3))
    boundary_centers[:, 0], boundary_centers[:, 1], boundary_centers[:, 2] = boundaries.loc[:, 'center_x'], \
                                                                             boundaries.loc[:, 'center_y'], \
                                                                             boundaries.loc[:, 'center_z']

    solar_masks = shading_utils.calculate_shading(boundary_centers.astype(np.float64),
                                                  elevation_data.astype(np.float64),
                                                  boundaries.loc[:, 'azimuth'].values.astype(np.float64),
                                                  angular_resolution,
                                                  bbox_filter,
                                                  boundaries.loc[:, 'type'].values.astype(np.int32))
    mask_columns = [f'mask_{i}' for i in range(solar_masks.shape[1])]
    boundaries[mask_columns] = pd.DataFrame(index=boundaries.index,
                                            columns=mask_columns,
                                            data=solar_masks)


def run_models(buildings, boundaries, parameters):
    """

    Args:
        buildings (GeoDataframe):  a GeoDataframe containing the building geometries and parameters
        boundaries (GeoDataframe): a GeoDataframe containing the boundary geometries
        parameters: instance of class Parameters

    Returns:

    """

    elevation_data = elevation_model(buildings, parameters.grid_resolution)
    solar_masks = solar_mask(boundaries, elevation_data, parameters.angular_resolution, parameters.bbox_filter)
    boundaries = pd.concat([boundaries, solar_masks], axis=1)

    return boundaries
