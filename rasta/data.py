import os
import torch
import numpy as np
from torch.utils.data import DataLoader, SubsetRandomSampler
from torchvision import transforms, datasets

def get_classes(file_path):
    return os.listdir(file_path)

class WikiArtDataLoader:
    def __init__(self, file_path, batch_size, data_split, random_seed, num_workers=4, pin_memory=False):
        """
        Args:
            file_path: path to wikiart data (folders of classes)
            batch_size: batch size
            data_split (tuple): tuple of ratio of sizes (train, valid) or (train, valid, test) with sum of 1
            random_seed: seed, can be for reproducibility
            num_workers: number of subprocesses
            pin_memory: True if using CUDA & GPU
        """
        def is_valid_split(data_split):
            if len(data_split) == 2:
                for ratio in data_split:
                    if ratio < 0 or ratio > 1:
                        return False
                return data_split[0]+data_split[1] <= 1
            if len(data_split) == 3:
                for ratio in data_split:
                    if ratio < 0 or ratio > 1:
                        return False
                return data_split[0] + data_split[1] + data_split[2] == 1
            return False

        if is_valid_split(data_split):
            train_size = data_split[0]
            valid_size = data_split[1]
        else:
            print("value error")
            raise ValueError("data_split is not correctly formatted")

        normalize = transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))

        transform_train = transforms.Compose([
            # transforms.RandomCrop((224,224)),
            transforms.Resize((224,224)),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            # normalize,
        ])
        transform_valid = transforms.Compose([
            # transforms.RandomCrop((224,224)),
            transforms.Resize((224,224)),
            transforms.ToTensor(),
            # normalize,
        ])
        transform_test = transforms.Compose([
            # transforms.RandomCrop((224,224)),
            transforms.Resize((224,224)),
            transforms.ToTensor(),
            # normalize,
        ])

        train_dataset = datasets.ImageFolder(file_path, transform=transform_train)
        valid_dataset = datasets.ImageFolder(file_path, transform=transform_valid)
        test_dataset = datasets.ImageFolder(file_path, transform=transform_test)

        # shuffles and splits indices into the train, validation, and test data sets
        num_imgs = len(train_dataset)
        indices = range(num_imgs)
        split1 = int(np.floor(train_size * num_imgs))
        split2 = int(split1 + np.floor(valid_size * num_imgs))
        indices_train, indices_valid, indices_test = indices[:split1], indices[split1:split2], indices[split2:]
        sampler_train = SubsetRandomSampler(indices_train)
        sampler_valid = SubsetRandomSampler(indices_valid)
        sampler_test = SubsetRandomSampler(indices_test)

        # creates the data loaders
        self.train_loader = DataLoader(
            train_dataset, batch_size=batch_size, sampler=sampler_train, 
            num_workers=num_workers, pin_memory=pin_memory,
        )
        self.valid_loader = DataLoader(
            valid_dataset, batch_size=batch_size, sampler=sampler_valid, 
            num_workers=num_workers, pin_memory=pin_memory,
        )
        self.test_loader = DataLoader(
            test_dataset, batch_size=batch_size, sampler=sampler_test, 
            num_workers=num_workers, pin_memory=pin_memory,
        )

        self.train_dataset = train_dataset
        self.valid_dataset = valid_dataset
        self.test_dataset = test_dataset

    def __getitem__(self, item):
        if item == 'train':
            return self.train_loader
        elif item == 'valid' or item == 'val' or item == 'validation':
            return self.valid_loader
        elif item == 'test':
            return self.test_loader
        else:
            raise KeyError('not a valid data loader')

if __name__ == "__main__":
    DATA_FOLDER = "/data/wikiart"

    wikiart_loader = WikiArtDataLoader('data/wikiart', 9, (0.8, 0.1, 0.1), random_seed=42, num_workers=4, pin_memory=False)
    
    # check dims of image and prints example
    imgs, classes = next(iter(wikiart_loader.train_loader))
    print(imgs.size())
    print(imgs)
    print(classes)
