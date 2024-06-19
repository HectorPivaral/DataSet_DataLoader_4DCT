Este es el proyecto de graduación para la Licenciatura en Física de la Universidad del Valle de Guatemala, desarrollado por Aaron Pivaral Guerra. El proyecto incluye dos scripts fundamentales para generar un conjunto de datos (DataSet) y un cargador de datos (DataLoader) destinados al entrenamiento de una red neuronal capaz de detectar y rastrear tumores en tomografías computarizadas en 4D (4DCT).

El código hace uso de la librería diffDRR para la generación de imágenes de Radiografías Digitalmente Reconstruidas (DRR) a partir de tomografías computarizadas en 4D, enfocadas en el centro de masa del tumor. Este proceso es crucial para crear datos sintéticos de alta precisión que alimenten el modelo de red neuronal, mejorando así su capacidad para realizar un seguimiento preciso y en tiempo real de la localización tumoral.


@inproceedings{gopalakrishnan2022fast,
  title={Fast auto-differentiable digitally reconstructed radiographs for solving inverse problems in intraoperative imaging},
  author={Gopalakrishnan, Vivek and Golland, Polina},
  booktitle={Workshop on Clinical Image-Based Procedures},
  pages={1--11},
  year={2022},
  organization={Springer}
}
