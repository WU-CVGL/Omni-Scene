# Directyle copied from bytedance/MVDream/mvdream/camera_utils.py

import numpy as np
import torch

def create_camera_to_world_matrix(elevation, azimuth, cam_dist=1.0):
    elevation = np.radians(elevation)
    azimuth = np.radians(azimuth)
    # Convert elevation and azimuth angles to Cartesian coordinates on a unit sphere
    x = np.cos(elevation) * np.cos(azimuth) * cam_dist
    y = np.cos(elevation) * np.sin(azimuth) * cam_dist
    z = np.sin(elevation) * cam_dist
    
    # Calculate camera position, target, and up vectors
    camera_pos = np.array([x, y, z])
    target = np.array([0, 0, 0])
    up = np.array([0, 0, 1])
    
    # Construct view matrix
    forward = target - camera_pos
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    new_up = np.cross(right, forward)
    new_up /= np.linalg.norm(new_up)
    cam2world = np.eye(4)
    cam2world[:3, :3] = np.array([right, new_up, -forward]).T
    cam2world[:3, 3] = camera_pos
    return cam2world


def convert_opengl_to_blender(camera_matrix):
    if isinstance(camera_matrix, np.ndarray):
        # Construct transformation matrix to convert from OpenGL space to Blender space
        flip_yz = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
        camera_matrix_blender = np.dot(flip_yz, camera_matrix)
    else:
        # Construct transformation matrix to convert from OpenGL space to Blender space
        flip_yz = torch.tensor([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
        if camera_matrix.ndim == 3:
            flip_yz = flip_yz.unsqueeze(0)
        camera_matrix_blender = torch.matmul(flip_yz.to(camera_matrix), camera_matrix)
    return camera_matrix_blender

def convert_blender_to_opencv(camera_matrix):
    trans = np.diag([1., -1., -1., 1.])
    if isinstance(camera_matrix, np.ndarray):
        camera_matrix_opencv = camera_matrix @ trans
    else:
        trans = torch.from_numpy(trans).to(camera_matrix)
        camera_matrix_opencv = camera_matrix @ trans
    return camera_matrix_opencv


def normalize_camera(camera_matrix):
    ''' normalize the camera location onto a unit-sphere'''
    if isinstance(camera_matrix, np.ndarray):
        camera_matrix = camera_matrix.reshape(-1,4,4)
        translation = camera_matrix[:,:3,3]
        translation = translation / (np.linalg.norm(translation, axis=1, keepdims=True) + 1e-8)
        camera_matrix[:,:3,3] = translation
    else:
        camera_matrix = camera_matrix.reshape(-1,4,4)
        translation = camera_matrix[:,:3,3]
        translation = translation / (torch.norm(translation, dim=1, keepdim=True) + 1e-8)
        camera_matrix[:,:3,3] = translation
    return camera_matrix


def get_camera(num_frames, elevation=15, azimuth_start=0, azimuth_span=360, opencv_coord=False, cam_dist=1.0):
    angle_gap = azimuth_span / num_frames
    cameras = []
    for azimuth in np.arange(azimuth_start, azimuth_span+azimuth_start, angle_gap):
        camera_matrix = create_camera_to_world_matrix(elevation, azimuth, cam_dist)
        if opencv_coord:
            camera_matrix = convert_blender_to_opencv(camera_matrix)
        cameras.append(camera_matrix)
    return torch.tensor(np.stack(cameras, 0)).float()

def rescale_intrisic(camera_intrisic, src_res, tgt_res=(1.0, 1.0)):
    '''rescale camera intrinsic parameter fx, fy, cx, cy to fit in target image resolution'''
    src_h, src_w = src_res
    tgt_h, tgt_w = tgt_res
    fx, fy, cx, cy = camera_intrisic[0, 0], camera_intrisic[1, 1], camera_intrisic[0, 2], camera_intrisic[1, 2]
    scale_h, scale_w = tgt_h / src_h, tgt_w / src_w
    fx_scaled, fy_scaled, cx_scaled, cy_scaled = fx * scale_w, fy * scale_h, cx * scale_w, cy * scale_h
    camera_intrisic_scaled = [[fx_scaled, 0, cx_scaled], [0, fy_scaled, cy_scaled], [0, 0, 1]]
    return camera_intrisic_scaled, fx_scaled, fy_scaled, cx_scaled, cy_scaled