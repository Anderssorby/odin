from odin.misc.dataset.base import Cifar10, MNIST, PTBWords, Mini
from odin.misc.dataset.map import MapImageData
import numpy as np

datasets = {
    "cifar10": Cifar10,
    "mnist": MNIST,
    "ptb_words": PTBWords,
    "mini": Mini,
    "satellite_images": MapImageData
}


def load_dataset(name, options=None):
    # type: (str, **dict) -> (np.ndarray, np.ndarray, np.ndarray, np.ndarray)
    dataset = datasets[name](**options)

    return dataset.load()