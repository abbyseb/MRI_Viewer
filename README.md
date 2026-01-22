# 🧠 3D MRI / CT Volume Viewer (PyQt5)

A **desktop-based medical imaging viewer** built with **PyQt5** for interactive exploration of 3D MRI and CT volumes.  
The application supports **NIfTI (`.nii`, `.nii.gz`) and NumPy (`.npy`)** formats and provides **multi-planar reconstruction (MPR)** with an intuitive **3D orientation cube**, precise rotation controls, and **session recording**.

This tool is well-suited for:
- Medical imaging research  
- Radiology / radiotherapy visualization  
- Dataset inspection and debugging  
- Educational demonstrations  

---

## ✨ Features

### 📁 Supported Formats
- **NIfTI**: `.nii`, `.nii.gz`
- **NumPy**: `.npy`

---

### 🧭 Automatic Preprocessing (NIfTI)
When loading NIfTI files, the application automatically:

1. **Normalizes orientation to RAS**
   - Ensures consistent anatomical orientation  
   - Uses `nibabel.as_closest_canonical`

2. **Resamples to isotropic spacing**
   - Resampled to **1 × 1 × 1 mm**
   - Prevents geometric distortion
   - Implemented using `nibabel.processing.resample_to_output`

3. **Standardizes internal array layout**
   - Internal format: **(Z, Y, X)**
   - Guarantees correct axial, coronal, and sagittal slicing

---

## 🧩 User Interface Overview

### 🧱 3D Orientation Cube
An interactive cube acting as both:
- A **visual orientation reference**
- A **navigation controller**

**Capabilities**
- Mouse-driven rotation (X and Y axes)
- Slice textures mapped onto cube faces
- Automatic view switching based on dominant face:
  - **Top / Bottom → Axial**
  - **Left / Right → Sagittal**
  - **Front / Back → Coronal**

This enables intuitive spatial navigation without manual plane selection.

---

### 🖼️ Multi-Planar Reconstruction (MPR)

| Plane      | Axis | Slice Direction |
|------------|------|-----------------|
| Axial      | Z    | Inferior → Superior |
| Coronal    | Y    | Posterior → Anterior |
| Sagittal   | X    | Left → Right |

Planes can be switched via:
- Dedicated UI buttons
- Automatic switching through cube rotation

---

### 🎚️ Slice Navigation
- Horizontal slider for rapid navigation
- SpinBox for precise slice selection
- Dynamic slice limits per view plane
- Current position displayed as:  
  `Slice N / Total`

---

### 🔄 Fine Rotation Adjustment
- In-plane rotation using a `QDoubleSpinBox`
- Precision up to **0.1°**
- Rotation applied via `scipy.ndimage.rotate`
- Useful for alignment verification and visual inspection

---

## 🎥 Video Recording

Record your navigation session and export it as a video.

### Recording Workflow
1. Click **⏺ Start Recording**
2. Interact with the viewer:
   - Scroll slices
   - Rotate cube
   - Switch planes
3. Click **⏹ Stop Recording**
4. Click **💾 Save Video**

### Output Formats
- `.mp4`
- `.avi`

### Implementation Details
- Frames captured from the Matplotlib canvas
- Stored as RGB NumPy arrays
- Encoded using **OpenCV (`cv2.VideoWriter`)**
- Default frame rate: **30 FPS**

---
