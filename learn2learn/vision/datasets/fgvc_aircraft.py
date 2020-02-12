#!/usr/bin/env python3

import os
import pickle
import tarfile
import requests
from PIL import Image

from torch.utils.data import Dataset

DATASET_DIR = 'fgvc_aircraft'
DATASET_URL = 'http://www.robots.ox.ac.uk/~vgg/data/fgvc-aircraft/archives/fgvc-aircraft-2013b.tar.gz'
DATA_DIR = os.path.join('fgvc-aircraft-2013b', 'data')
IMAGES_DIR = os.path.join(DATA_DIR, 'images')
LABELS_PATH = os.path.join(DATA_DIR, 'labels.pkl')

# Splits from "Meta-Datasets", Triantafillou et al, 2019
SPLITS = {
    'train': ['A340-300', 'A318', 'Falcon 2000', 'F-16A/B', 'F/A-18', 'C-130',
              'MD-80', 'BAE 146-200', '777-200', '747-400', 'Cessna 172',
              'An-12', 'A330-300', 'A321', 'Fokker 100', 'Fokker 50', 'DHC-1',
              'Fokker 70', 'A340-200', 'DC-6', '747-200', 'Il-76', '747-300',
              'Model B200', 'Saab 340', 'Cessna 560', 'Dornier 328', 'E-195',
              'ERJ 135', '747-100', '737-600', 'C-47', 'DR-400', 'ATR-72',
              'A330-200', '727-200', '737-700', 'PA-28', 'ERJ 145', '737-300',
              '767-300', '737-500', '737-200', 'DHC-6', 'Falcon 900', 'DC-3',
              'Eurofighter Typhoon', 'Challenger 600', 'Hawk T1', 'A380',
              '777-300', 'E-190', 'DHC-8-100', 'Cessna 525', 'Metroliner',
              'EMB-120', 'Tu-134', 'Embraer Legacy 600', 'Gulfstream IV',
              'Tu-154', 'MD-87', 'A300B4', 'A340-600', 'A340-500', 'MD-11',
              '707-320', 'Cessna 208', 'Global Express', 'A319', 'DH-82'
              ],
    'test': ['737-400', '737-800', '757-200', '767-400', 'ATR-42', 'BAE-125',
             'Beechcraft 1900', 'Boeing 717', 'CRJ-200', 'CRJ-700', 'E-170',
             'L-1011', 'MD-90', 'Saab 2000', 'Spitfire'
             ],
    'valid': ['737-900', '757-300', '767-200', 'A310', 'A320', 'BAE 146-300',
              'CRJ-900', 'DC-10', 'DC-8', 'DC-9-30', 'DHC-8-300', 'Gulfstream V',
              'SR-20', 'Tornado', 'Yak-42'
              ],
    'all': ['A340-300', 'A318', 'Falcon 2000', 'F-16A/B', 'F/A-18', 'C-130',
            'MD-80', 'BAE 146-200', '777-200', '747-400', 'Cessna 172',
            'An-12', 'A330-300', 'A321', 'Fokker 100', 'Fokker 50', 'DHC-1',
            'Fokker 70', 'A340-200', 'DC-6', '747-200', 'Il-76', '747-300',
            'Model B200', 'Saab 340', 'Cessna 560', 'Dornier 328', 'E-195',
            'ERJ 135', '747-100', '737-600', 'C-47', 'DR-400', 'ATR-72',
            'A330-200', '727-200', '737-700', 'PA-28', 'ERJ 145', '737-300',
            '767-300', '737-500', '737-200', 'DHC-6', 'Falcon 900', 'DC-3',
            'Eurofighter Typhoon', 'Challenger 600', 'Hawk T1', 'A380',
            '777-300', 'E-190', 'DHC-8-100', 'Cessna 525', 'Metroliner',
            'EMB-120', 'Tu-134', 'Embraer Legacy 600', 'Gulfstream IV',
            'Tu-154', 'MD-87', 'A300B4', 'A340-600', 'A340-500', 'MD-11',
            '707-320', 'Cessna 208', 'Global Express', 'A319', 'DH-82',
            '737-900', '757-300', '767-200', 'A310', 'A320', 'BAE 146-300',
            'CRJ-900', 'DC-10', 'DC-8', 'DC-9-30', 'DHC-8-300', 'Gulfstream V',
            'SR-20', 'Tornado', 'Yak-42',
            '737-400', '737-800', '757-200', '767-400', 'ATR-42', 'BAE-125',
            'Beechcraft 1900', 'Boeing 717', 'CRJ-200', 'CRJ-700', 'E-170',
            'L-1011', 'MD-90', 'Saab 2000', 'Spitfire',
            ],
}


class FGVCAircraft(Dataset):

    def __init__(self, root, mode='all', transform=None, target_transform=None, download=False):
        self.root = os.path.expanduser(root)
        self.transform = transform
        self.target_transform = target_transform
        self._bookkeeping_path = os.path.join(self.root, 'fgvc-aircraft-' + mode + '-bookkeeping.pkl')

        if not self._check_exists() and download:
            self.download(self.root)

        self.load_data(mode)

    def _check_exists(self):
        data_path = os.path.join(self.root, DATASET_DIR)
        images_path = os.path.join(data_path, IMAGES_DIR)
        labels_path = os.path.join(data_path, LABELS_PATH)
        return os.path.exists(data_path) and \
            os.path.exists(images_path) and \
            os.path.exists(labels_path)

    def download(self, root):
        if not os.path.exists(root):
            os.mkdir(root)
        data_path = os.path.join(root, DATASET_DIR)
        if not os.path.exists(data_path):
            os.mkdir(data_path)
        tar_path = os.path.join(data_path, os.path.basename(DATASET_URL))
        if not os.path.exists(tar_path):
            print('Downloading FGVC Aircraft dataset')
            req = requests.get(DATASET_URL)
            with open(tar_path, 'wb') as archive:
                for chunk in req.iter_content(chunk_size=512**2):
                    if chunk:
                        archive.write(chunk)
        with tarfile.open(tar_path) as tar_file:
            tar_file.extractall(data_path)
        family_names = ['images_family_train.txt',
                        'images_family_val.txt',
                        'images_family_test.txt']
        images_labels = []
        for family in family_names:
            with open(os.path.join(data_path, DATA_DIR, family_names[0]), 'r') as family_file:
                for line in family_file.readlines():
                    image, label = line.split(' ', 1)
                    images_labels.append((image.strip(), label.strip()))
        labels_path = os.path.join(data_path, LABELS_PATH)
        with open(labels_path, 'wb') as labels_file:
            pickle.dump(images_labels, labels_file)
        os.remove(tar_path)

    def load_data(self, mode='train'):
        data_path = os.path.join(self.root, DATASET_DIR)
        labels_path = os.path.join(data_path, LABELS_PATH)
        with open(labels_path, 'rb') as labels_file:
            image_labels = pickle.load(labels_file)

        data = []
        split = SPLITS[mode]
        for image, label in image_labels:
            if label in split:
                image = os.path.join(data_path, IMAGES_DIR, image + '.jpg')
                label = split.index(label)
                data.append((image, label))
        self.data = data

    def __getitem__(self, i):
        image, label = self.data[i]
        image = Image.open(image)
        if self.transform:
            image = self.transform(image)
        if self.target_transform:
            label = self.target_transform(label)
        return image, label

    def __len__(self):
        return len(self.data)


if __name__ == '__main__':
    assert len(SPLITS['all']) == len(SPLITS['train']) + len(SPLITS['valid']) + len(SPLITS['test'])
    aircraft = FGVCAircraft('~/data', download=True)
    print(len(aircraft))
