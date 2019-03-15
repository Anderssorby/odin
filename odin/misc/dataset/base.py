#!/usr/bin/env python
# -*- coding: utf-8 -*-
import glob
import logging
import sys
from subprocess import check_call

from scipy import linalg
from six.moves import cPickle as pickle
from skimage.io import imsave

from odin import data_dir
from odin.utils.generate import *
from odin.utils.transformer import Transformer


def unpickle(file):
    fp = open(file, 'rb')
    if sys.version_info.major == 2:
        data = pickle.load(fp)
    elif sys.version_info.major == 3:
        data = pickle.load(fp, encoding='latin-1')
    fp.close()

    return data


def preprocessing(data):
    mean = np.mean(data, axis=0)
    mdata = data - mean
    sigma = np.dot(mdata.T, mdata) / mdata.shape[0]
    U, S, V = linalg.svd(sigma)
    components = np.dot(np.dot(U, np.diag(1 / np.sqrt(S))), U.T)
    whiten = np.dot(mdata, components.T)

    return components, mean, whiten


def download_and_unwrap_tarball(source, name, force=False):
    """

    :param source: URL of interest
    :param name:
    :param force: Ignore the existence check
    :return: path to the extracted dir
    """
    target_dir = os.path.join(data_dir, name)
    if os.path.isdir(target_dir) and not force:
        return target_dir
    tar_file = os.path.join(data_dir, name+".tar.gz")
    logging.info("Downloading from %s to %s" % (source, target_dir))
    check_call(["mkdir", "-p", target_dir])
    check_call(["wget", "-N", source, "-O", tar_file])
    check_call(["tar", "-zxvf", tar_file, "-C", data_dir])
    check_call(["rm", tar_file])
    return target_dir


class Dataset:
    """
    Superclass of data sets
    """
    name: str
    dataset: (np.ndarray, np.ndarray, np.ndarray, np.ndarray)
    source: str

    def __init__(self,
                 whitening=False,
                 prompt=True, **kwargs):
        self.path = os.path.join(data_dir, self.name)
        self.whitening = whitening
        self.prompt = prompt
        self.args = kwargs

    def _extract_train(self):
        # type: () -> (list, list)
        pass

    def _extract_test(self):
        # type: () -> (list, list)
        pass

    def _download(self):
        download_and_unwrap_tarball(self.source)

    def _prepare_and_save(self):
        logging.info("Preparing dataset.")

        if not os.path.exists(self.path):
            os.makedirs(self.path)

        # prepare training dataset
        data, labels = self._extract_train()

        np.save(os.path.join(self.path, 'train_data'),
                np.asarray(data, dtype=np.float32))
        np.save(os.path.join(self.path, 'train_labels'),
                np.asarray(labels, dtype=np.int32))

        data, labels = self._extract_test()

        np.save(os.path.join(self.path, 'test_data'), data)
        np.save(os.path.join(self.path, 'test_labels'), labels)

    def __len__(self):
        return 4

    def __getitem__(self, item):
        return self.dataset[item]

    def load(self):
        if not os.path.isdir(self.path):
            try:
                if self.prompt:
                    answer = input("Do you want to download %s? [Y/n]" % self.name).lower()
                    if answer == "n":
                        exit(0)

                self._download()

                self._prepare_and_save()
            except Exception:
                print("Cleaning up broken dir ".join(self.path))
                # check_call(["rm", "-rf", self.path])

        train_data = np.load(os.path.join(self.path, 'train_data.npy'))
        train_labels = np.load(os.path.join(self.path, 'train_labels.npy'))
        test_data = np.load(os.path.join(self.path, 'test_data.npy'))
        test_labels = np.load(os.path.join(self.path, 'test_labels.npy'))

        return train_data, train_labels, test_data, test_labels


class Cifar10(Dataset):
    source = "http://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz"
    name = "cifar10"

    def _extract_train(self):

        trans = Transformer()
        data = np.zeros((50000, 3 * 32 * 32), dtype=np.float)
        labels = []
        for i, data_fn in enumerate(
                sorted(glob.glob('cifar-10-batches-py/data_batch*'))):
            batch = unpickle(data_fn)
            data[i * 10000:(i + 1) * 10000] = batch['data']
            labels.extend(batch['labels'])

        if self.whitening:
            components, mean, data = preprocessing(data)
            np.save(os.path.join(self.path, "components"), components)
            np.save(os.path.join(self.path, "mean"), mean)

        data = data.reshape((50000, 3, 32, 32)).transpose((0, 2, 3, 1))
        labels = np.asarray(labels, dtype=np.int32)
        training_data = []
        training_labels = []
        for d, l in zip(data, labels):
            imgs = trans(d)
            for img in imgs:
                training_data.append(img)
                training_labels.append(l)

        # saving training dataset
        for i in range(50000):
            d = data[i]
            d -= d.min()
            d /= d.max()
            d = (d * 255).astype(np.uint8)
            imsave(os.path.join(self.path, 'train_{}.png'.format(i)), d)

        return training_data, training_labels

    def _extract_test(self):
        test = unpickle('cifar-10-batches-py/test_batch')
        data = np.asarray(test['data'], dtype=np.float)
        data = data.reshape((10000, 3, 32, 32)).transpose((0, 2, 3, 1))
        labels = np.asarray(test['labels'], dtype=np.int32)

        for i in range(10000):
            d = data[i]
            d -= d.min()
            d /= d.max()
            d = (d * 255).astype(np.uint8)
            imsave(os.path.join(self.path, 'test_{}.png'.format(i)), d)

        return data, labels

    def load(self):
        from keras.datasets import cifar10
        return cifar10.load_data()


class MNIST(Dataset):
    name = "mnist"
    image_dim = 28 * 28
    image_shape = (28, 28, 1)

    dataset: (np.ndarray, np.ndarray, np.ndarray, np.ndarray)

    def __init__(self):
        super(MNIST, self).__init__()

        from keras.utils.data_utils import get_file
        path = 'mnist.npz'
        path = get_file(path,
                        origin='https://s3.amazonaws.com/img-datasets/mnist.npz',
                        file_hash='8a61469f7ea1b51cbae51d4f78837e45')
        f = np.load(path)
        self.train = self.x_train, self.y_train = f['x_train'], f['y_train']
        self.test = self.x_test, self.y_test = f['x_test'], f['y_test']
        self.dataset = self.x_train, self.y_train, self.x_test, self.y_test
        f.close()

        # make sure that each type of digits have exactly 10 samples
        sup_images = []
        sup_labels = []
        rnd_state = np.random.get_state()
        np.random.seed(0)
        for cat in range(10):
            ids = np.where(self.train[1] == cat)[0]
            np.random.shuffle(ids)
            sup_images.extend(self.train[0][ids[:10]])
            sup_labels.extend(self.train[1][ids[:10]])
        np.random.set_state(rnd_state)
        self.supervised_train = (
            np.asarray(sup_images),
            np.asarray(sup_labels),
        )

        self.validation = self.test

    def _extract_test(self):
        unpickle("train-images-idx3-ubyte.gz")

    def _extract_train(self):
        pass

    def _download(self):
        sources = [
            "http://yann.lecun.com/exdb/mnist/train-images-idx3-ubyte.gz",
            "http://yann.lecun.com/exdb/mnist/train-labels-idx1-ubyte.gz",
            "http://yann.lecun.com/exdb/mnist/t10k-images-idx3-ubyte.gz",
            "http://yann.lecun.com/exdb/mnist/t10k-labels-idx1-ubyte.gz"
        ]
        for i, source in enumerate(sources):
            print("Downloading %d of 4" % (i + 1))
            download_and_unwrap_tarball(source)

    def __len__(self):
        return 4

    def __getitem__(self, item):
        return self.dataset[item]

    def load(self, is_chainer=False):

        if is_chainer:
            import chainer
            train, test = chainer.datasets.get_mnist()
            return train, test
        else:
            return self.train, self.test


class PTBWords(Dataset):
    name = "ptb_words"

    def load(self):
        import chainer
        train, val, test = chainer.datasets.get_ptb_words()
        return train, val, test


class Mini(Dataset):
    name = "mini"

    def load(self):
        file = os.path.join(data_dir, "mini.npy")
        if not os.path.isfile(file):
            train, test = generate_dataset()

            if not os.path.isdir(data_dir):
                os.mkdir(data_dir)

            np.save(file, (train, test))
        else:
            train, test = np.load(file)

        return train, test

