C_INIT = ""
cimport libc.math as math
import numpy as np

cpdef calculate_shading(double[:, ::1] boundary_centers, double[:, ::1] elevation_model, double[:] boundary_azimuths,
                        double angular_resolution, double bbox_filter, int[:] boundary_type):

    cdef Py_ssize_t k, j, i, shading_id, end, start, boundary_count, elevation_count
    cdef double height, azimuth, distance
    boundary_count = boundary_centers.shape[0]
    elevation_count = elevation_model.shape[0]
    cdef Py_ssize_t shading_count = <Py_ssize_t>(360. / angular_resolution + 1.)
    shading = np.zeros((boundary_count, shading_count), dtype=np.float64)
    cdef double[:, ::1] shading_view = shading

    for k in range(boundary_count):

        if boundary_type[k] == 0: # Exterior Wall
            # We set to 90° all azimuths that are behind the wall studied
            start = <Py_ssize_t>((boundary_azimuths[k] + 90. )/ angular_resolution)
            end = start +  <Py_ssize_t>(180. / angular_resolution) + 1

            if end <= shading_count:
                for i in range(start, end):
                    shading_view[k, i] = 90.
            else:
                for i in range(start, shading_count):
                    shading_view[k, i] = 90.
                for i in range(end - shading_count):
                    shading_view[k, i] = 90.

        if boundary_type[k] == 1 or boundary_type[k] == 3: # Interior wall or Floor
            continue

        for j in range(elevation_count):
            if elevation_model[j, 2] <= boundary_centers[k, 2]:
                continue
            if elevation_model[j, 0] > boundary_centers[k, 0] + bbox_filter or elevation_model[j, 0] < boundary_centers[k, 0] - bbox_filter:
                if elevation_model[j, 1] > boundary_centers[k, 1] + bbox_filter or elevation_model[j, 1] < boundary_centers[k, 1] - bbox_filter:
                    continue

            # We compute the azimuth
            azimuth = (math.atan2((elevation_model[j, 1] - boundary_centers[k, 1]),
                                  (elevation_model[j, 0] - boundary_centers[k, 0]))) * 180. / math.pi
            if azimuth < 0.:
                azimuth += 360.

            shading_id = <Py_ssize_t>(azimuth / angular_resolution)
            if shading_view[k, shading_id] == 90.:
                continue
            # we compute the distance between the two points
            distance = math.sqrt((elevation_model[j, 0] - boundary_centers[k, 0]) ** 2 +
                                 (elevation_model[j, 1] - boundary_centers[k, 1]) ** 2 +
                                 (elevation_model[j, 2] - boundary_centers[k, 2]) ** 2)

            # We compute the height
            height = (math.asin((elevation_model[j, 2] - boundary_centers[k, 2]) / distance)) * 180. / math.pi

            if height > shading_view[k, shading_id]:
                shading_view[k, shading_id] = height

    return shading



cpdef discretize_polygons(double[:, ::1] polygons, int[:] polygon_ends, double resolution):

    cdef Py_ssize_t i
    cdef Py_ssize_t j
    cdef Py_ssize_t k
    cdef int[:] point_counts = np.zeros(polygons.shape[0], dtype=np.int32)
    cdef int total_points = 0
    cdef double[:] vertice_lengths = np.zeros(polygons.shape[0], dtype=np.float64)
    cdef Py_ssize_t start = 0
    cdef Py_ssize_t end = 0
    cdef double[:] current_edge = np.zeros(3, dtype=np.float64)
    cdef double[:] next_edge = np.zeros(3, dtype=np.float64)
    cdef double[:] vertice_direction = np.zeros(2, dtype=np.float64)

    for i in range(polygon_ends.shape[0]):
        start = 0
        if i > 0:
            start = polygon_ends[i-1] + 1
        end = polygon_ends[i]
        for j in range(start, end):
            current_edge = polygons[j, :]
            next_edge = polygons[j + 1, :]
            vertice_lengths[j] = math.sqrt((next_edge[0] - current_edge[0]) ** 2 + (next_edge[1] - current_edge[1]) ** 2)
            if vertice_lengths[j] == 0.:
                point_counts[j] = 0
            else:
                point_counts[j] = <int>(vertice_lengths[j] / resolution) + 1
            total_points += point_counts[j]

    points = np.zeros((total_points, 3), dtype=np.float64)
    cdef double[:, ::1] point_view = points
    cdef Py_ssize_t point_index = 0

    for i in range(polygon_ends.shape[0]):
        start = 0
        if i > 0:
            start = polygon_ends[i-1] + 1
        end = polygon_ends[i]

        for j in range(start, end):
            current_edge = polygons[j, :]
            next_edge = polygons[j + 1, :]
            vertice_direction[0] = (next_edge[0] - current_edge[0]) / vertice_lengths[j]
            vertice_direction[1] = (next_edge[1] - current_edge[1]) / vertice_lengths[j]

            for k in range(point_counts[j]):

                point_view[point_index, 0] = current_edge[0] + vertice_direction[0] * k * resolution
                point_view[point_index, 1] = current_edge[1] + vertice_direction[1] * k * resolution
                point_view[point_index, 2] = current_edge[2]
                point_index += 1

    return points



cpdef visible_beam(double[:, :] shading_mask, double[:] sun_height, double[:] sun_azimuth):
    """This function determines at which time steps the sun beam is obscured given a shading mask array and time series 
    of sun heights and azimuths
    
    Args:
        shading_mask (numpy array):  a N by M numpy array of shadings, where N is the number of boundaries and M the 
        number of azimuths for which the shading has been calculated
        sun_height (numpy array): a time series of sun heights
        sun_azimuth (numpy array): a time series of sun azimuths 

    Returns:
        a N by T array of 0 and 1, where T is the number of time steps of sun position provided
    """
    cdef Py_ssize_t i, j
    cdef Py_ssize_t boundary_count = shading_mask.shape[0]
    cdef Py_ssize_t shading_count = shading_mask.shape[1]
    cdef Py_ssize_t step_count = sun_height.shape[0]
    visible_beam = np.zeros((boundary_count, step_count), dtype=np.float64)
    cdef double[:, ::1] visible_beam_view = visible_beam

    for k in range(boundary_count):

        for i in range(shading_count):

            for j in range(sun_azimuth.shape[0]):

                if i * 360. / shading_count < sun_azimuth[j] < (i + 1) * 360. / shading_count and sun_height[j] > shading_mask[k, i]:

                    visible_beam_view[k, j] = 1

    return visible_beam