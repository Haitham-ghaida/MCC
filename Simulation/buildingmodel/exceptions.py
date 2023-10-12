# -*- coding: utf-8 -*-


class ModelListError(Exception):
    def __init__(self, model_list, all_models):
        msg = f"Model list {model_list} is incompatible with model order {all_models}"
        Exception.__init__(self, msg)


class BuildingGeometryError(Exception):
    def __init__(self, shape):
        msg = f"Buildings contain an incompatible geometry {shape}. Must be either a Polygon " \
              f"or MultiPolygon "
        Exception.__init__(self, msg)