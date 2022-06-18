import json, os
import torch
import torchvision
import torchvision.transforms as transforms
from torchvision.transforms import ToTensor, ToPILImage
from tqdm import tqdm
import numpy as np
from matplotlib import pyplot as plt

import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models


def make_transform(config):
    size = config['image_size']
    t = transforms.Compose([
         transforms.Resize(size=(size, size)),
         transforms.ToTensor(),
         transforms.Normalize(mean=[0.485, 0.456, 0.406],
                              std=[0.229, 0.224, 0.225]),
     ])

    return t

  
class ZClassifier:
    def __init__(self, model_path):
        with open(os.path.join(model_path, 'zconfig.json')) as f:
            config = json.load(f)
        self._classes = config['classes']
        self._model = torch.load(
            os.path.join(model_path, 'zmodel.pt'), 
            map_location=torch.device('cpu'))
        self._model.eval()
        self._transform = make_transform(config)

    def predict(self, img):
        # Input: PIL image
        # Return: numpy 1D class probs 
        x = self._transform(img)
        with torch.no_grad():
            y = self._model(x.unsqueeze(0))
            y = F.softmax(y, dim=-1)
        return y.squeeze().numpy()
