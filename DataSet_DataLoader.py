# -*- coding: utf-8 -*-
"""
@author: aaron
"""

from ct4d_image_generator import CT4D_DataLoader
import os
import torch
from torch.utils.data import Dataset
from torch.utils.data import DataLoader

class MiDataset(Dataset):
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.pacientes = [dir_name for dir_name in os.listdir(self.base_dir) if os.path.isdir(os.path.join(self.base_dir, dir_name))]
        self.porcentajes_respiracion = ['10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%']
        self.total_images = len(self.pacientes) * len(self.porcentajes_respiracion)

    def __len__(self):
        return self.total_images * 3

    def __getitem__(self, idx):
        # Ajustar idx para manejar tres imágenes (marcos) por cada conjunto de datos
        marco_idx = idx % 3
        idx = idx // 3
        paciente, porcentaje = self.determinar_indices(idx)
        path_file = f"{self.base_dir}/{paciente}/{porcentaje}"
        generador = CT4D_DataLoader(path_file, name_contour = "GTV Lesion A:GTV Lesion A")
        imagenes = generador.DRR_Generator(Height = 512, Width = 512, Poisson_Noise_scale = 300, Gaussian_kernel_size = 14, Gaussian_sigma = 6)
        marcos = ['axial', 'coronal', 'sagital']

        imagen = imagenes[marco_idx]
        marco = marcos[marco_idx]
        posicion_centro_masa = generador.COM
        label = (*posicion_centro_masa, porcentaje, marco)

        return imagen, label

    def determinar_indices(self, idx):
        total_porcentajes = len(self.porcentajes_respiracion)
        porcentaje_idx = idx % total_porcentajes
        paciente_idx = idx // total_porcentajes
        porcentaje = self.porcentajes_respiracion[porcentaje_idx]
        paciente = self.pacientes[paciente_idx]
        return paciente, porcentaje

base_dir = '/File Path/'
mi_dataset = MiDataset(base_dir)
dataloader = DataLoader(mi_dataset, batch_size=64, shuffle=True)