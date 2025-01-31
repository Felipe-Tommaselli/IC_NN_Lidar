#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACTIVE PROJECT!

This class was used a lot for the data augmentation algorithms on real data. However, with the artificial dataset, there
is no need to use this technique. Without the artificial dataset, this data augmentation with rotation adds a lot 
of consistency to the dataset. However, the pattern created was a bit off compared to the real one. 
With this, there is no need to use this algorithm in the current artificial implementation, but on real data, it is a good 
way out of overfitting.

@author: Felipe-Tommaselli
"""

import os
import sys
import torch
import numpy as np
import random
import matplotlib.pyplot as plt
from datetime import datetime 

import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torchvision.transforms import functional as F
from torch.utils.data import Dataset, DataLoader, random_split, ConcatDataset, Subset
from torchsummary import summary
from torchvision import transforms
from torchvision import datasets
import torchvision.models as models
from PIL import Image
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score
from efficientnet_pytorch import EfficientNet


class RotatedDataset(Subset):
    ''' this class works like a wrapper for the original dataset, rotating the images'''

    def __init__(self, dataset, angles, rot_type):
        super().__init__(dataset, np.arange(len(dataset)))
        self.angles = angles
        self.rot_type = rot_type
        
    def __getitem__(self, idx):
        data = super().__getitem__(idx) # get the original data

        image = data['image']
        label = data['labels']
        angle = random.choice(self.angles) 
        
        key = len(label)
        if key == 3:
            # we suppose m1 = m2, so we can use the same deprocess
            m1, b1, b2 = label
            m2 = m1
            label = [m1, m2, b1, b2]
        elif key == 4:
            m1, m2, b1, b2 = label
            label = [m1, m2, b1, b2]

        # select the rotation point from the middle or the axis
        if self.rot_type == 'middle': 
            rot_point_np = np.array([112, 112])
            rot_point = (112, 112)
        elif self.rot_type == 'axis':
            rot_point_np = np.array([112, 224])
            rot_point = (112, 224)

        # this only works with PIL, some temporarlly conversion is needed
        pil_image = Image.fromarray(image)

        # Rotate the image around the rotation point with "1D white" background
        rotated_pil_image = transforms.functional.rotate(pil_image, int(angle), fill=255, center=rot_point)

        # convert back to numpy
        rotated_image = np.array(rotated_pil_image)
        
        label =  PreProcess.deprocess(rotated_image, label)
        m1, m2, b1, b2 = label
        x1 = np.arange(0, rotated_image.shape[0])
        x2 = np.arange(0, rotated_image.shape[0])

        y1 = m1*x1 + b1
        y2 = m2*x2 + b2

        # ROTATION MATRIX (for the labels)
        rotation_matrix = np.array([[np.cos(np.radians(angle)), np.sin(np.radians(angle)), rot_point_np[0]*(1-np.cos(np.radians(angle)))-rot_point_np[1]*np.sin(np.radians(angle))], 
                                    [-np.sin(np.radians(angle)), np.cos(np.radians(angle)), rot_point_np[1]*(1-np.cos(np.radians(angle)))+rot_point_np[0]*np.sin(np.radians(angle))], 
                                    [0, 0, 1]])

        # add one dim to the points for matrix multiplication
        points1 = np.stack((x1, y1, np.ones_like(x1)))
        points2 = np.stack((x2, y2, np.ones_like(x2)))

        # apply transformation
        transformed_points1 = rotation_matrix @ points1
        transformed_points2 = rotation_matrix @ points2

        # get the new points
        x1_rotated = transformed_points1[0]
        y1_rotated = transformed_points1[1]
        x2_rotated = transformed_points2[0]
        y2_rotated = transformed_points2[1]

        # get the new line parameters
        m1r, b1r = np.polyfit(x1_rotated, y1_rotated, 1)
        m2r, b2r = np.polyfit(x2_rotated, y2_rotated, 1)

        if key == 3: 
            rotated_label = [m1r, b1r, b2r]
        elif key == 4:
            rotated_label = [m1r, m2r, b1r, b2r]

        # fig, ax = plt.subplots(1, 2, figsize=(10, 5))
        # ax[0].plot(x1, y1, color='green')
        # ax[0].plot(x2, y2, color='green')
        # ax[0].imshow(image)
        # plt.title(f'nn_cnn: {idx}, angle: {angle}, rot_type: {self.rot_type}')
        # ax[1].plot(x1_rotated, y1_rotated, color='red')
        # ax[1].plot(x2_rotated, y2_rotated, color='red')
        # ax[1].imshow(rotated_image)
        # plt.show()

        # normalize
        rotated_label = NnDataLoader.process_label(rotated_label)

        return {"image": rotated_image, "labels": rotated_label, "angle": angle} 


def transformData(dataset):
    ''' This function garantees that the Data Augmentation occurs!
    I opted for 2 different transformations (both rotations):
        1. Rotation on the middle of the image (112, 112)
        2. Rotation on the axis of the points (112, 224)
        ----------------
        |              |
        |              |
        |     (1)      |
        |              |
        |              |
        ------(2)-------
    
    I select random images from the original dataset, create two new datasets with 
    the rotated images and then concatenate them. With that I can get more images 
    for training and also garantee that the Data Augmentation occurs.
    '''
    
    # both datasets have the same size and dont replace the original images
    num_rotated = int(len(dataset) * 0.2)
    rotated_indices = np.random.choice(len(dataset), num_rotated, replace=False)
    
    # this line create one subset with the indices above for the RotatedDataset class that mount the dataset
    # the lambda function bellow basically remove the 0 angle (no rotation) from the list of angles
    # both the dataset (middle or axis) have the same size but not the same images
    rotated_dataset1 = RotatedDataset(Subset(dataset, rotated_indices), 
                                    angles = np.array(list(filter(lambda x: x != 0, np.arange(-20, 20, 2)))), 
                                    rot_type = 'middle')
    rotated_dataset2 = RotatedDataset(Subset(dataset, rotated_indices), 
                                    angles = np.array(list(filter(lambda x: x != 0, np.arange(-20, 20, 2)))), 
                                    rot_type = 'axis')
    concat_dataset = ConcatDataset([dataset, rotated_dataset1, rotated_dataset2])
    return concat_dataset

