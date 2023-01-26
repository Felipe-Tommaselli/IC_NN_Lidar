#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script describe a convolutional network, that will be used to infer the angle and the distance in
the image generated by the lidar data. Note that the label of the images were generated manually with help
of the UI generated by the script lidar_tag.py.  

create a neural network with convolutional layers in Python with the Pytorch framework, the scripts must follow the following instructions:
1. It receives images through a function called "def getData", which obtains through the DataLoader images in a folder on the computer and stores them in a dataframe by the Pandas library. The images are already separated into test and training sets and must be stored in the "test_data" and "train_data" variables. The images are 640 x 480 in size.
2. It must contain a function called "def getLabels", which will get lines from a file with extension ".csv", in which each line is a label of each image obtained by the "getData" function. Images and labels are defined by an already identified id. The Labels are already separated into test and training sets and must be stored in the "test_labels" and "train_labels" variables, corresponding to each image;
3. the classes forming the neural network by itself "class NetworkCNN" , it is composed of 3 convolutional layers, a pooling layer and a dropout layer, with 2 final layers of Fully Connected type (all with forward step);
4. the training function defined by "def fit(model, criterion, optimizer, train_loader, test_loader, num_epochs)" which must iterate through the images of "train_data" and "train_label" applying a step forward, a loss function (by criterion ), a step optimizer and a backward loss, in addition to updating the loss. In addition, the function must assemble a test model, iterating through the test dataset looking for the labels' predictions with a calculated accuracy. The initial image is sized 640 x 480, it must be scaled down;
5. The fit function call must be in the format: model = NetworkCNN(), with the criterion to be defined (cost/loss function), learning rate of 0.001 and Adam optimizer. Finally, the model must be trained and then tested. Number of epochs of 20.

At the end, plot the result of the cost function with the matplotlib library by number of epochs.

@author: andres
@author: Felipe-Tommaselli
"""

import os
import pandas as pd
import torch
import numpy as np
import matplotlib.pyplot as plt
from statistics import mean
#from torchvision.io import read_image
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, random_split
from torchsummary import summary

torch.cuda.empty_cache()

from dataloader import *

class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride = 1, downsample = None):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Sequential(
                        nn.Conv2d(in_channels, out_channels, kernel_size = 3, stride = stride, padding = 1),
                        nn.BatchNorm2d(out_channels),
                        nn.ReLU())
        self.conv2 = nn.Sequential(
                        nn.Conv2d(out_channels, out_channels, kernel_size = 3, stride = 1, padding = 1),
                        nn.BatchNorm2d(out_channels))
        self.downsample = downsample
        self.relu = nn.ReLU()
        self.out_channels = out_channels
        
    def forward(self, x):
        residual = x
        out = self.conv1(x)
        out = self.conv2(out)
        if self.downsample:
            residual = self.downsample(x)
        out += residual
        out = self.relu(out)
        return out

class NetworkCNN(nn.Module):
    
    def __init__(self, block, num_classes = 4):
        super(NetworkCNN, self).__init__()
        
        # input image: 507x507
        layers = [2, 2, 2, 2]

        # input image: 507x507
        self.inplanes = 64
        self.conv1 = nn.Sequential(
                        nn.Conv2d(1, 64, kernel_size = 3, stride = 2, padding = 1),
                        nn.BatchNorm2d(64),
                        nn.ReLU())
        self.maxpool = nn.MaxPool2d(kernel_size = 3, stride = 1, padding = 1)
        self.layer0 = self._make_layer(block, 64, layers[0], stride = 1)
        self.layer1 = self._make_layer(block, 128, layers[1], stride = 2)
        self.layer2 = self._make_layer(block, 256, layers[2], stride = 2)
        self.layer3 = self._make_layer(block, 512, layers[3], stride = 2)
        self.avgpool = nn.AvgPool2d(7, stride=1)
        self.fc = nn.Linear(512 * 26 * 26, num_classes)
        
    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes:
            
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes, kernel_size=1, stride=stride),
                nn.BatchNorm2d(planes),
            )
        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)
    
    
    def forward(self, x):
        x = self.conv1(x)
        x = self.maxpool(x)
        x = self.layer0(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        return x

def getData(csv_path, batch_size=5, num_workers=0):
    ''' get images from the folder (assets/images) and return a DataLoader object '''
    train_data = DataLoader(LidarDatasetCNN(csv_path, train=True), batch_size=batch_size, shuffle=True,num_workers=num_workers)
    test_data = DataLoader(LidarDatasetCNN(csv_path, train=False), batch_size=batch_size, shuffle=True,num_workers=num_workers)

    # get one image shape from the train_data
    for i, data in enumerate(train_data):
        print(f'images shape: {data["image"].shape}')
        break
    print('-'*65)
    return train_data, test_data

def fit(model, criterion, optimizer, train_loader, test_loader, num_epochs):

    train_losses = []
    test_losses = [0]

    accuracy_list = [0]
    predictions_list = []
    labels_list = []

    for epoch in range(num_epochs):
        running_loss = 0

        for i, data in enumerate(train_loader):
            images, labels = data['image'], data['labels']
            
            # convert to float32 and send it to the device

            # image dimension: batch x 1 x 650 x 650 (batch, channels, height, width)
            images = images.type(torch.float32).to(device)
            images = images.unsqueeze(1)

            labels = [label.type(torch.float32).to(device) for label in labels]
            # convert labels to tensor
            labels = torch.stack(labels)
            # convert to format: tensor([[value1, value2, value3, value4], [value1, value2, value3, value4], ...])
            # this is: labels for each image, "batch" times -> shape: (batch, 4)
            labels = labels.permute(1, 0)

            outputs = model(images)
            loss = criterion(outputs, labels) 
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            running_loss += loss.item()

        else:
        # Testing the model
            # with torch.no_grad():
            #     # Set the model to evaluation mode
            #     model.eval()

            #     total = 0
            #     test_loss = 0
            #     correct = 0

            #     for i, data in enumerate(test_loader):
            #         images, labels = data['image'], data['labels']
            #         # image dimension: batch x 1 x 650 x 650 (batch, channels, height, width)
            #         images = images.type(torch.float32).to(device)
            #         images = images.unsqueeze(1)

            #         labels = [label.type(torch.float32).to(device) for label in labels]
            #         labels = torch.stack(labels)
            #         labels = labels.permute(1, 0)

            #         labels_list.append(labels)
            #         total += len(labels)
        
            #         outputs = model.forward(images) # propagação para frente

            #         predictions = torch.max(outputs, 1)[1].to(device)
            #         predictions_list.append(predictions)
            #         print('predictions:', predictions)
            #         print('labels:', labels)
            #         correct += (predictions == labels).sum()

            #         test_loss += criterion(outputs, labels).item()
            #     test_losses.append(test_loss/len(test_loader))

            #     accuracy = correct * 100 / total
            #     accuracy_list.append(accuracy.item())


            # # Set the model to training mode
            # model.train()
            pass
        train_losses.append(running_loss/len(train_loader))
        test_losses.append(running_loss/len(train_loader))

        print(f'[{epoch+1}/{num_epochs}] .. Train Loss: {train_losses[-1]:.5f} .. Test Loss: {test_losses[-1]:.5f} .. Test Accuracy: {accuracy_list[-1]:.3f}%')

            
    results = {
        'train_losses': train_losses,
        'test_losses': test_losses,
        'accuracy_list': accuracy_list
    }
    
    return results

def plotResults(results, epochs):
    # losses
    plt.plot(results['train_losses'], label='Training loss')
    plt.legend(frameon=False)
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("Loss")
    plt.show()

    # accuracy
    plt.plot(results['accuracy_list'], label='Accuracy')
    plt.legend(frameon=False)
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.title("Accuracy")
    plt.show()


if __name__ == '__main__':
    # Set the device to GPU if available
    global device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print('Using {} device'.format(device))

    # Get the data
    train_data, test_data = getData(csv_path="~/Documents/IC_NN_Lidar/assets/tags/Label_Data.csv")

    # Create the model on GPU if available
    model = NetworkCNN(ResidualBlock).to(device)
    # summary(model, (1, 650, 650))

    # loss function for regression
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    global epochs
    epochs = 20
    global batch_size
    batch_size = 4

    # Train the model
    #! without test data yet 
    results = fit(model=model, criterion=criterion, optimizer=optimizer, train_loader=train_data, test_loader=train_data, num_epochs=epochs)

    plotResults(results, epochs)

    # Save the model
    torch.save(model.state_dict(), 'model.pth')
    print('Saved PyTorch Model State to model.pth')

    #* not there yet

    # # Load the model
    # model = NetworkCNN()
    # model.load_state_dict(torch.load('model.pth'))

    # # Test the model
    # with torch.no_grad():
    #     # Set the model to evaluation mode
    #     model.eval()

    #     total = 0
    #     correct = 0

    #     for images, labels in test_data:
    #         images, labels = images.to(device), labels.to(device)
    #         outputs = model.forward(images)
    #         predictions = torch.max(outputs, 1)[1].to(device)
    #         correct += (predictions == labels).sum()
    #         total += len(labels)

    #     print(f'Accuracy of the network on the 10000 test images: {correct * 100 / total}%')

    # # Test the model with a single image
    # with torch.no_grad():
    #     # Set the model to evaluation mode
    #     model.eval()

    #     image = test_data[0][0].to(device)
    #     label = test_data[0][1].to(device)

    #     output = model.forward(image)
    #     prediction = torch.max(output, 0)[1].to(device)

    #     print(f'Prediction of the network on the first image: {prediction}')
    #     print(f'Label of the first image: {label}')

    # # plot results of the test
    # plt.imshow(image.cpu().numpy().squeeze(), cmap='gray_r')
    # plt.show()