# -*- coding: utf-8 -*-
"""ct4d_image_generator.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1nF839SJMf9XA5l3t5FA1x2n3t_7EJ71-
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path
import pydicom
import os
from diffdrr.drr import DRR
from diffdrr.visualization import plot_drr
from diffdrr.data import read_dicom
import torch.nn.functional as F

class CT4D_DataLoader:
    def __init__(self, path_dicom_files, name_contour = "tumor"):
        self.Name_Contour = name_contour
        self.ds_struct_set = pydicom.dcmread(next((os.path.join(path_dicom_files, archivo) for archivo in os.listdir(path_dicom_files)
                                                  if archivo.endswith('.dcm') and archivo.startswith('struct_set')), None))
        self.CT_files = [os.path.join(path_dicom_files, archivo) for archivo in os.listdir(path_dicom_files)
                        if archivo.endswith('.dcm') and archivo.startswith('CT')]
        self.ROINumberSequence =self.find_the_ROI_Number_Sequence()
        self.COM = self.find_center_of_mass()

    def find_the_ROI_Number_Sequence(self):
        try:
            # Useful Variables for the function
            contour_dict = {}
            ROINumber = 0
            ROINumberSequence = 0

            # Get the list of contour sequences
            contour_sequences = self.ds_struct_set.ROIContourSequence

            # Get the list of structured set ROI sequences
            contour_Dato = self.ds_struct_set.StructureSetROISequence

            '''Loop through the structured set ROI sequences
            to find the the contour ROI Number'''
            for i, contour_Dato in enumerate(contour_Dato):
                contour_name = contour_Dato.ROIName
                contour_number = contour_Dato.ROINumber
                contour_dict[contour_name] = contour_number
                for key in contour_dict:
                    if self.Name_Contour == key:
                        ROINumber = contour_dict[key]

            for i, contour_sequence in enumerate(contour_sequences):
                contour_number = contour_sequence.ReferencedROINumber
                if contour_number == ROINumber:
                    ROINumberSequence = i
        except:
            print('There is not contour name like:'+ str(self.Name_Contour))
            ROINumberSequence = False
        return ROINumberSequence

    def find_center_of_mass(self):
        try:
            # Useful variables
            Binary_Mask = []

            ds_aux = pydicom.dcmread(self.CT_files[0])
            dcmfiles = list(self.CT_files)
            locations = torch.tensor([float(pydicom.dcmread(p).SliceLocation) for p in dcmfiles])
            Zmm_position_max = torch.max(locations)

            # Get Contour Data
            contour_data = self.ds_struct_set.ROIContourSequence[self.ROINumberSequence].ContourSequence

            x_max, x_min, y_max, y_min = [], [], [], []
            for Contour in contour_data:
                Contour_i = Contour.ContourData
                x_coords, y_coords = torch.tensor(Contour_i[0::3]), torch.tensor(Contour_i[1::3])
                x_max.append(torch.max(x_coords))
                x_min.append(torch.min(x_coords))
                y_max.append(torch.max(y_coords))
                y_min.append(torch.min(y_coords))

            X_max, X_min = torch.max(torch.tensor(x_max)), torch.min(torch.tensor(x_min))
            Y_max, Y_min = torch.max(torch.tensor(y_max)), torch.min(torch.tensor(y_min))

            # Create a grid of coordinates of the bounding box of the polygon
            x_coords_grid, y_coords_grid = torch.meshgrid(torch.arange(X_min, X_max), torch.arange(Y_min, Y_max))
            for contour in contour_data:
                contour_i = contour.ContourData
                x_coords = torch.tensor(contour_i[0::3])
                y_coords = torch.tensor(contour_i[1::3])

                # Create a closed polygon from the contour data
                polygon_vertices = torch.stack((x_coords, y_coords), dim=1)
                polygon_path = Path(polygon_vertices.numpy())  # Path creation remains with Matplotlib, requires numpy array

                # Check which points are inside the polygon
                points = torch.stack((x_coords_grid.flatten(), y_coords_grid.flatten()), dim=1)
                mask = polygon_path.contains_points(points.numpy())  # Interaction with Path object requires numpy array

                # Reshape the mask to the grid shape and create binary mask
                mask = torch.tensor(mask, dtype=torch.int32).reshape(x_coords_grid.shape)
                binary_mask = torch.zeros_like(mask)
                binary_mask[mask == 1] = 1
                Binary_Mask.append(binary_mask)

            Binary_Mask = torch.stack(Binary_Mask)
            Z_coordinate = []
            for contour in contour_data:
                Contour_j = contour.ContourData
                Z_coordinate.append(Contour_j[2])

            Z_coordinate = torch.tensor(Z_coordinate)

            # 3D meshgrid
            x_coords_grid, y_coords_grid, z_coords_grid = torch.meshgrid(torch.arange(X_min, X_max), torch.arange(Y_min, Y_max), Z_coordinate)

            # Transpose the grid to match the binary mask shape
            x_coords_grid = x_coords_grid.permute(2, 0, 1)
            y_coords_grid = y_coords_grid.permute(2, 0, 1)
            z_coords_grid = z_coords_grid.permute(2, 0, 1)

            # Calculate total mass
            mass = torch.sum(Binary_Mask)

            # Calculate weighted coordinates
            weighted_x = torch.sum(x_coords_grid * Binary_Mask)
            weighted_y = torch.sum(y_coords_grid * Binary_Mask)
            weighted_z = torch.sum(z_coords_grid * Binary_Mask)

            # Calculate center of mass
            center_of_mass = torch.tensor([weighted_x, weighted_y, weighted_z], dtype=torch.float64) / mass
            COM_x_px = (center_of_mass[0] - ds_aux.ImagePositionPatient[0]) / (self.Volume_calculation_PixelSpacing()[1][0])
            COM_y_py = (center_of_mass[1] - ds_aux.ImagePositionPatient[1]) / (self.Volume_calculation_PixelSpacing()[1][1])
            COM_z_pz = (Zmm_position_max - center_of_mass[2]) / (self.Volume_calculation_PixelSpacing()[1][2])
            center_of_mass = torch.tensor([COM_x_px, COM_y_py, COM_z_pz], dtype=torch.float64)

        except:
            print('There is not contour name like:' + str(self.Name_Contour))
            center_of_mass = False
        return center_of_mass


    def DRR_Generator(self, Height, Width, Poisson_Noise_scale, Gaussian_kernel_size, Gaussian_sigma):
      Image_list = []
      Volume, Spacing = self.Volume_calculation_PixelSpacing()
      device = "cuda" if torch.cuda.is_available() else "cpu"
      drr = DRR(
          Volume,      # The CT volume as a numpy array
          Spacing,     # Voxel dimensions of the CT
          sdr=800.0,   # Source-to-detector radius (half of the source-to-detector distance)
          height= Height,  # Height of the DRR (if width is not seperately provided, the generated image is square)
          width = Width,
          delx=Spacing[0],    # Pixel spacing (in mm)
      ).to(device)
      '''
      With the six vectors yaw, pitch, roll, Bx, By, and Bz, the first index[0] is in the Axial axis,
      the second index[1] is in the Coronal axis, and the third index [2] is in the Sagittal axis
      '''
      bx = self.COM[0]
      by = self.COM[1]
      bz = self.COM[2]
      yaw = [torch.pi, torch.pi, -torch.pi/2]
      pitch = [torch.pi/2, 0, 0]
      roll = [torch.pi / 2,torch.pi / 2, torch.pi/2]
      Bx = [bx, bx, bx]
      By = [511 - by, by, 511 - by]
      Bz = [bz, 104 - bz, 104 - bz]

      for i in range(3):
        # Set the camera pose with rotations (yaw, pitch, roll) and translations (x, y, z)
        rotations = torch.tensor([[yaw[i], pitch[i], roll[i]]], device=device)
        translations = torch.tensor([[By[i]*Spacing[0], Bx[i]*Spacing[1], Bz[i]*Spacing[2]]], device=device)

        # Make the DRR
        img = drr(rotations, translations)
        img = img / torch.max(img)
        Padding_Image = self.mirror_padding(img, Gaussian_kernel_size)
        Gaussian_noise = self.convolve_with_gaussian(Padding_Image, Gaussian_kernel_size, Gaussian_sigma)
        Poisson_noise = self.add_poisson_noise(Gaussian_noise, Poisson_Noise_scale)
        diffdrr = Poisson_noise.squeeze()
        Image_list.append(diffdrr)

        #plt.imshow(diffdrr, cmap="gray")
        #plt.show()
      return Image_list

    def Volume_calculation_PixelSpacing(self):
      # Get the volumen data from CT and the pixel spacing
      correct_zero = True
      dcmfiles = self.CT_files
      dcmfiles = list(dcmfiles)
      locations = [float(pydicom.dcmread(p).SliceLocation) for p in dcmfiles]
      pairs = zip(dcmfiles, locations)
      # Zip the two lists together, then sort by the location
      sorted_pairs = sorted(zip(dcmfiles, locations), key=lambda x: x[1], reverse=True)
      # Unzip the sorted pairs
      sorted_dcmfiles, sorted_locations = zip(*sorted_pairs)

      ds =pydicom.dcmread(sorted_dcmfiles[0])
      nx, ny = ds.pixel_array.shape
      nz = len(sorted_dcmfiles)
      del_x, del_y = ds.PixelSpacing
      del_x, del_y = float(del_x), float(del_y)
      volume = np.zeros((nx, ny, nz)).astype(np.float32)
      del_zs = []
      for idx, dcm in enumerate(sorted_dcmfiles):
          ds = pydicom.dcmread(dcm)
          volume[:, :, idx] = ds.pixel_array
          del_zs.append(ds.ImagePositionPatient[2])
          del ds
          #print(pydicom.dcmread(dcm).SliceLocation)
          #print(idx)
      if correct_zero:
          volume[volume == volume.min()] = 0
      del_zs = np.diff(del_zs)
      del_z = float(np.abs(np.unique(del_zs)[0]))
      spacing = [del_x, del_y, del_z]
      return volume, spacing

    def mirror_padding(self, image, kernel_size):
      # Calculate padding for each dimension
      padding_size = kernel_size // 2
      padding = (padding_size, padding_size, padding_size, padding_size)
      # Perform mirror padding
      padded_image = F.pad(image, padding, mode='reflect')
      return padded_image


    def add_poisson_noise(self, image, scale):
      noise = torch.poisson(image*scale)/scale
      return noise

    def gaussian_kernel(self,size: int, sigma: float):
        """Generate a Gaussian kernel."""
        if sigma < 0.02:
          sigma = 0.017
        x = torch.linspace(-5, 5, size)
        x_grid, y_grid = torch.meshgrid(x, x)
        d = torch.sqrt(x_grid**2 + y_grid**2)
        g = torch.exp(-(d**2)/(2*sigma**2))
        return g / g.sum()

    def convolve_with_gaussian(self,image, kernel_size, sigma):
        """Convolve an image with a Gaussian kernel."""
        kernel = self.gaussian_kernel(kernel_size, sigma)
        kernel = kernel.unsqueeze(0).unsqueeze(0).to('cuda')  # Make it 4D: [batch, channels, height, width]
        padding = 0
        return F.conv2d(image, kernel, padding=padding)