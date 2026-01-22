# 3D MRI/CT Volume Viewer

A PyQt5-based desktop application for visualizing 3D medical imaging data (`.nii`, `.nii.gz`, `.npy`). Features an interactive 3D navigation cube, multi-planar reconstruction (Axial, Sagittal, Coronal), fine rotation controls, and video recording capabilities.

## Features

*   **Format Support**: Loads NIfTI (`.nii`, `.nii.gz`) and NumPy (`.npy`) volumes.
*   **Automatic Preprocessing**:
    *   Converts NIfTI files to standard RAS orientation (Right-Anterior-Superior).
    *   Resamples volumes to isotropic 1mm voxel spacing for correct aspect ratios.
*   **Interactive Navigation**:
    *   **3D Cube**: Drag to rotate the cube; clicking faces or rotating past thresholds automatically switches the 2D view.
    *   **Slice Slider**: Scrub through slices in the current view plane.
*   **Multi-Planar View**: Switch instantly between Axial, Sagittal, and Coronal views.
*   **Fine Rotation**: Rotate the in-plane 2D image by precise degrees using a spinbox.
*   **Video Recording**: Record your navigation session and save it as `.mp4` or `.avi`.

## Installation

### Prerequisites

Ensure you have Python 3.8+ installed.

### Install Dependencies

Run the following command to install all required libraries:

pip install numpy PyQt5 matplotlib scipy nibabel opencv-python


Usage
Run the Application:

bash
python mri_viewer.py
Load a Volume:

Click the "Load Volume (.npy / .nii)" button in the top left.

Select a .nii.gz, .nii, or .npy file.

Navigation:

Change View: Click "Axial", "Sagittal", or "Coronal" buttons, or rotate the 3D cube to auto-switch.

Change Slice: Use the horizontal slider or the spinbox to move through the volume.

Rotate Image: Enter a specific angle in the "Fine Rotation Adjustment" box (e.g., 90.0).

Recording:

Click "⏺ Start Recording".

Interact with the viewer (scroll slices, rotate, change views).

Click "⏹ Stop Recording".

Click "💾 Save Video" to export the session.

Troubleshooting
"nibabel library is not installed": Ensure you ran the pip install command above.

Memory Errors: Large CT/MRI scans may require significant RAM. If the app crashes on load, try using a downsampled version of your dataset.

QImage Error (memoryview): This code includes a fix for PyTorch/NumPy memory views. If you modify the array_to_qimage function, ensure you keep the tobytes() or copy() logic.
