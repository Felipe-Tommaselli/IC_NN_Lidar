#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script describe a convolutional network, that will be used to infer the angle and the distance in
the image generated by the lidar data. Note that the label of the images were generated manually with help
of the UI generated by the script lidar_tag.py.  

At the end, plot the result of the cost function with the matplotlib library by number of epochs.

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

torch.cuda.empty_cache()

from dataloader import *
sys.path.append('../')
from pre_process import *


def getData(csv_path, train_path, batch_size, num_workers=0):
    ''' get images from the folder (assets/images) and return a DataLoader object '''
    
    dataset = NnDataLoader(csv_path, train_path)

    print(f'dataset size (no augmentation): {len(dataset)}')
    #! artificial não se beneficia muito disso
    # dataset = transformData(dataset)
    #print(f'dataset size (w/ augmentation): {len(dataset)}')

    train_size, val_size = int(0.7*len(dataset)), np.ceil(0.3*len(dataset)).astype('int')
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
    
    train_data = DataLoader(train_dataset, batch_size=batch_size, shuffle=True,num_workers=num_workers)
    val_data  = DataLoader(val_dataset, batch_size=batch_size, shuffle=True,num_workers=num_workers)

    print(f'train size: {train_size}, val size: {val_size}')
    _ = input('----------------- Press Enter to continue -----------------')
    return train_data, val_data


def cross_validate(model, criterion, optimizer, scheduler, data, num_epochs, num_splits=5):
    #TODO: IMPLEMENT THIS
    kf = KFold(n_splits=num_splits, shuffle=True, random_state=42)

    avg_train_losses = []
    avg_val_losses = []

    for fold, (train_idx, val_idx) in enumerate(kf.split(data)):
        print(f"Fold {fold+1}:")

        train_data = data[train_idx]
        val_data = data[val_idx]

        train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True, num_workers=num_workers)
        val_loader = DataLoader(val_data, batch_size=batch_size, shuffle=False, num_workers=num_workers)

        model = YourModel()  # Initialize your model here
        optimizer = optim.SGD(model.parameters(), lr=lr)

        results = train_model(model, criterion, optimizer, scheduler, train_loader, val_loader, num_epochs)

        avg_train_losses.append(results['train_losses'])
        avg_val_losses.append(results['val_losses'])

    return avg_train_losses, avg_val_losses


def train_model(model, criterion, optimizer, scheduler, train_loader, val_loader, num_epochs):

    train_losses = []
    val_losses = []
    predictions_list = []
    labels_list = []

    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0

        for i, data in enumerate(train_loader):
            images, labels = data['image'], data['labels']
            # convert to float32 and send it to the device
            # image dimension: (batch, channels, height, width)
            images = images.type(torch.float32).to(device)
            images = images.unsqueeze(1)
            # convert labels to float32 and send it to the device
            labels = [label.type(torch.float32).to(device) for label in labels]
            # convert labels to tensor
            labels = torch.stack(labels)
            # convert to format: tensor([[value1, value2, value3, value4], [value1, value2, value3, value4], ...])
            # this is: labels for each image, "batch" times -> shape: (batch, 4)
            labels = labels.permute(1, 0)    
            outputs = model(images)
            loss = criterion(outputs, labels) 
            # Loss_with_L2 = Loss_without_L2 + λ * ||w||^2
            # Calculate L2 regularization loss
            # l2_regularization_loss = 0
            # for param in model.parameters():
            #     l2_regularization_loss += torch.norm(param, 2)
            # loss += weight_decay * l2_regularization_loss  # Add L2 regularization loss to the total loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            #scheduler.step()
            running_loss += loss.item()
        else:
        # valing the model
            with torch.no_grad():
                # Set the model to evaluation mode
                model.eval()
                total = 0
                val_loss = 0
                for i, data in enumerate(val_loader):
                    images, labels = data['image'], data['labels']
                    # image dimension: (batch, channels, height, width)
                    images = images.type(torch.float32).to(device)
                    images = images.unsqueeze(1)
                    labels = [label.type(torch.float32).to(device) for label in labels]
                    labels = torch.stack(labels)
                    labels = labels.permute(1, 0)
                    labels_list.append(labels)
                    total += len(labels)
                    outputs = model.forward(images)
                    # get the predictions to calculate the accuracy
                    _, preds = torch.max(outputs, 1)
                    val_loss += criterion(outputs, labels).item()
                val_losses.append(val_loss/len(val_loader))
            pass
        train_losses.append(running_loss/len(train_loader))
        print(f'[{epoch+1}/{num_epochs}] .. Train Loss: {train_losses[-1]:.5f} .. val Loss: {val_losses[-1]:.5f}')


    results = {
        'train_losses': train_losses,
        'val_losses': val_losses,
    }
    
    return results

def plotResults(results, epochs, lr):
    # losses
    # print both losses side by side with subplots (1 row, 2 columns)
    # ax1 for train losses and ax2 for val losses

    fig, ax = plt.subplots()

    # Plotting training and validation losses
    ax.plot(results['train_losses'], label='Training Loss', marker='o')
    ax.plot(results['val_losses'], label='Validation Loss', marker='o')

    # Adding labels and title
    ax.set_xlabel('Epochs')
    ax.set_ylabel('Loss')
    ax.set_title('Learning Loss Plot (MSE Loss)\nFinal Training Loss: {:.4f}'.format(results['train_losses'][-1]))

    # Adding legend
    ax.legend()

    # Adjusting layout for better visualization
    plt.tight_layout()

    # Save the plot in the current folder
    day_time = datetime.now().strftime("%d-%m-%Y_%H-%M-%S") 
    fig.savefig(f'losses_lr={lr}_{day_time}.png')
    


if __name__ == '__main__':
    ############ START ############
    # Set the device to GPU if available
    global device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    #device = torch.device('cpu')
    print('Using {} device'.format(device))

    ############ PARAMETERS ############    
    epochs = 10
    lr = float(5*1e-4) # TODO: test different learning rates
    step_size = 2 # TODO: test different step sizes
    gamma = 0
    batch_size = 140 # 160 AWS
    weight_decay = 1e-2 # L2 regularization

    ############ DATA ############
    csv_path = "../data/artificial_data/tags/Artificial_Label_Data6.csv"
    # train_path = os.getcwd() + SLASH + 'artificial_data' + SLASH + 'train4' + SLASH
    train_path = os.path.join(os.getcwd(), '..', 'data', 'artificial_data', 'train6')
    train_data, val_data = getData(batch_size=batch_size, csv_path=csv_path, train_path=train_path)

    ############ MODEL ############
    model = models.mobilenet_v2()

    ########### MOBILE NET ########### 
    model.features[0][0] = nn.Conv2d(1, 32, kernel_size=3, stride=2, padding=1, bias=False)

    # MobileNetV2 uses a different attribute for the classifier
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Sequential(
    nn.Linear(num_ftrs, 512),
    nn.BatchNorm1d(512),
    nn.ReLU(inplace=True),
    nn.Linear(512, 3)
    )

    # Moving the model to the device (GPU/CPU)
    model = model.to(device)
    ############ NETWORK ############
    criterion = nn.MSELoss()
    #optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    # optimizer = torch.optim.SGD(model.parameters(), lr=lr, weight_decay=weight_decay, momentum=0.0)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=step_size, gamma=gamma)

    ############ DEBBUG ############
    #summary(model, (1, 224, 224))
    #print(model)

    ############ TRAINING ############
    results = train_model(model=model, criterion=criterion, optimizer=optimizer, scheduler=scheduler, train_loader=train_data, val_loader=val_data, num_epochs=epochs)

    ############ RESULTS ############
    plotResults(results, epochs, lr)

    ############ SAVE MODEL ############
    # get day for the name of the file
    day_time = datetime.now().strftime("%d-%m-%Y_%H-%M-%S") 
    path = os.getcwd() + '/models/' + 'model' + '_' + str(lr).split('.')[1] + '_' + str(day_time) + '.pth'
    torch.save(model.state_dict(), path)
    print(f'Saved PyTorch Model State to:\n{path}')

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script describe a convolutional network, that will be used to infer the angle and the distance in
the image generated by the lidar data. Note that the label of the images were generated manually with help
of the UI generated by the script lidar_tag.py.  

At the end, plot the result of the cost function with the matplotlib library by number of epochs.

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

torch.cuda.empty_cache()

from dataloader import *
sys.path.append('../')
from pre_process import *


def getData(csv_path, train_path, batch_size, num_workers=0):
    ''' get images from the folder (assets/images) and return a DataLoader object '''
    
    dataset = NnDataLoader(csv_path, train_path)

    print(f'dataset size (no augmentation): {len(dataset)}')
    #! artificial não se beneficia muito disso
    # dataset = transformData(dataset)
    #print(f'dataset size (w/ augmentation): {len(dataset)}')

    train_size, val_size = int(0.7*len(dataset)), np.ceil(0.3*len(dataset)).astype('int')
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
    
    train_data = DataLoader(train_dataset, batch_size=batch_size, shuffle=True,num_workers=num_workers)
    val_data  = DataLoader(val_dataset, batch_size=batch_size, shuffle=True,num_workers=num_workers)

    print(f'train size: {train_size}, val size: {val_size}')
    _ = input('----------------- Press Enter to continue -----------------')
    return train_data, val_data


def cross_validate(model, criterion, optimizer, scheduler, data, num_epochs, num_splits=5):
    #TODO: IMPLEMENT THIS
    kf = KFold(n_splits=num_splits, shuffle=True, random_state=42)

    avg_train_losses = []
    avg_val_losses = []

    for fold, (train_idx, val_idx) in enumerate(kf.split(data)):
        print(f"Fold {fold+1}:")

        train_data = data[train_idx]
        val_data = data[val_idx]

        train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True, num_workers=num_workers)
        val_loader = DataLoader(val_data, batch_size=batch_size, shuffle=False, num_workers=num_workers)

        model = YourModel()  # Initialize your model here
        optimizer = optim.SGD(model.parameters(), lr=lr)

        results = train_model(model, criterion, optimizer, scheduler, train_loader, val_loader, num_epochs)

        avg_train_losses.append(results['train_losses'])
        avg_val_losses.append(results['val_losses'])

    return avg_train_losses, avg_val_losses


def train_model(model, criterion, optimizer, scheduler, train_loader, val_loader, num_epochs):

    train_losses = []
    val_losses = []

    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0

        for i, data in enumerate(train_loader):
            images, labels = data['image'], data['labels']
            # convert to float32 and send it to the device
            # image dimension: (batch, channels, height, width)
            images = images.type(torch.float32).to(device)
            images = images.unsqueeze(1)
            # convert labels to float32 and send it to the device
            labels = [label.type(torch.float32).to(device) for label in labels]
            # convert labels to tensor
            labels = torch.stack(labels)
            # convert to format: tensor([[value1, value2, value3, value4], [value1, value2, value3, value4], ...])
            # this is: labels for each image, "batch" times -> shape: (batch, 4)
            labels = labels.permute(1, 0)    
            outputs = model(images)
            loss = criterion(outputs, labels) 
            # Loss_with_L2 = Loss_without_L2 + λ * ||w||^2
            # Calculate L2 regularization loss
            # l2_regularization_loss = 0
            # for param in model.parameters():
            #     l2_regularization_loss += torch.norm(param, 2)
            # loss += weight_decay * l2_regularization_loss  # Add L2 regularization loss to the total loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            #scheduler.step()
            running_loss += loss.item()
        else:
        # valing the model
            with torch.no_grad():
                # Set the model to evaluation mode
                model.eval()
                val_loss = 0.0
                for i, data in enumerate(val_loader):
                    images, labels = data['image'], data['labels']
                    # image dimension: (batch, channels, height, width)
                    images = images.type(torch.float32).to(device)
                    images = images.unsqueeze(1)
                    labels = [label.type(torch.float32).to(device) for label in labels]
                    labels = torch.stack(labels)
                    labels = labels.permute(1, 0)
                    
                    outputs = model.forward(images)
                    val_loss += criterion(outputs, labels).item()
                val_losses.append(val_loss/len(val_loader))
            pass
        train_losses.append(running_loss/len(train_loader))
        print(f'[{epoch+1}/{num_epochs}] .. Train Loss: {train_losses[-1]:.5f} .. val Loss: {val_losses[-1]:.5f}')


    results = {
        'train_losses': train_losses,
        'val_losses': val_losses,
    }
    
    return results

def plotResults(results, epochs, lr):
    # losses
    # print both losses side by side with subplots (1 row, 2 columns)
    # ax1 for train losses and ax2 for val losses

    fig, ax = plt.subplots()

    # Plotting training and validation losses
    ax.plot(results['train_losses'], label='Training Loss', marker='o')
    ax.plot(results['val_losses'], label='Validation Loss', marker='o')

    # Adding labels and title
    ax.set_xlabel('Epochs')
    ax.set_ylabel('Loss')
    ax.set_title('Learning Loss Plot (MSE Loss)\nFinal Training Loss: {:.4f}'.format(results['train_losses'][-1]))

    # Adding legend
    ax.legend()

    # Adjusting layout for better visualization
    plt.tight_layout()

    # Save the plot in the current folder
    day_time = datetime.now().strftime("%d-%m-%Y_%H-%M-%S") 
    fig.savefig(f'losses_lr={lr}_{day_time}.png')
    


if __name__ == '__main__':
    ############ START ############
    # Set the device to GPU if available
    global device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    #device = torch.device('cpu')
    print('Using {} device'.format(device))

    ############ PARAMETERS ############    
    epochs = 10
    lr = float(5*1e-4) # TODO: test different learning rates
    step_size = 2 # TODO: test different step sizes
    gamma = 0
    batch_size = 160 # 160 AWS
    weight_decay = 1e-8 # L2 regularization

    ############ DATA ############
    csv_path = "../data/artificial_data/tags/Artificial_Label_Data6.csv"
    # train_path = os.getcwd() + SLASH + 'artificial_data' + SLASH + 'train4' + SLASH
    train_path = os.path.join(os.getcwd(), '..', 'data', 'artificial_data', 'train6')
    train_data, val_data = getData(batch_size=batch_size, csv_path=csv_path, train_path=train_path)

    ############ MODEL ############
    model = models.mobilenet_v2()

    ########### MOBILE NET ########### 
    model.features[0][0] = nn.Conv2d(1, 32, kernel_size=3, stride=2, padding=1, bias=False)

    # MobileNetV2 uses a different attribute for the classifier
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Sequential(
    nn.Linear(num_ftrs, 512),
    nn.BatchNorm1d(512),
    nn.ReLU(inplace=True),
    nn.Linear(512, 3)
    )

    # Moving the model to the device (GPU/CPU)
    model = model.to(device)
    ############ NETWORK ############
    criterion = nn.MSELoss()
    #optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    # optimizer = torch.optim.SGD(model.parameters(), lr=lr, weight_decay=weight_decay, momentum=0.0)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=step_size, gamma=gamma)

    ############ DEBBUG ############
    #summary(model, (1, 224, 224))
    #print(model)

    ############ TRAINING ############
    results = train_model(model=model, criterion=criterion, optimizer=optimizer, scheduler=scheduler, train_loader=train_data, val_loader=val_data, num_epochs=epochs)

    ############ RESULTS ############
    plotResults(results, epochs, lr)

    ############ SAVE MODEL ############
    # get day for the name of the file
    day_time = datetime.now().strftime("%d-%m-%Y_%H-%M-%S") 
    path = os.getcwd() + '/models/' + 'model' + '_' + str(lr).split('.')[1] + '_' + str(day_time) + '.pth'
    torch.save(model.state_dict(), path)
    print(f'Saved PyTorch Model State to:\n{path}')

