from abc import abstractmethod
import os
import logging
from glob import glob


class ComputationInterface(object):
    """
    Base class for simplifying computation across implementations and frameworks.
    """

    def __init__(self):
        import numpy as np
        self.xp = np
        self.args = None

    def update_args(self, args):
        self.args = args

    @abstractmethod
    def calc_inter_layer_covariance(self, model_wrapper):
        """
        Calculate the covariance matrix for each layer in the network
        :param model_wrapper:
        :return:
        """
        pass

    def load_elements(self, group_name, model_wrapper, experiment=None):
        """
        Load a group of previously computed values.
        :param group_name: directory where the elements are placed
        :param model_wrapper:
        :param experiment: An extra label
        :return:
        """
        path = os.path.join(model_wrapper.model_path, group_name, "*.npy")
        if experiment:
            path = os.path.join(path, experiment)
        path = os.path.join(path, "*.npy")
        group = {}
        for f in glob(path):
            element = self.xp.load(f)

            name = f.split("/")[-1].split(".")[0]
            group[name] = element
        return group

    def store_elements(self, elements, group_name, model_wrapper, experiment=None):
        """
        Store a group of elements in the results_dir
        :param elements: a map of values and their names. The name will result in their filename.
        :param group_name: The name of the group which will be used as a directory name.
        :param model_wrapper:
        :param experiment:
        :return:
        """
        path = os.path.join(model_wrapper.model_path, group_name)
        if experiment:
            path = os.path.join(model_wrapper.model_path, group_name, experiment)
        if not os.path.isdir(path):
            os.makedirs(path)

        for key in elements:
            self.xp.save(os.path.join(path, key), elements[key])

        logging.info("Stored %s of %s for %s in '%s'" % (elements.keys(), group_name, model_wrapper.model_name, path))
        return elements
