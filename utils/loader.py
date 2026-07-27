# utils/loader.py
# import pygame

# def load_spritesheet(path, num_frames, frame_width, frame_height):
#     sheet = pygame.image.load(path).convert_alpha()
#     frames = []
#     for i in range(num_frames):
#         frame = sheet.subsurface((i * frame_width, 0, frame_width, frame_height))
#         frames.append(frame)
#     return frames

# utils/loader.py

import pygame
from utils.paths import resource_path

def load_spritesheet(path, num_frames, frame_width, frame_height):
    sheet = pygame.image.load(resource_path(path)).convert_alpha()

    frames = []
    for i in range(num_frames):
        frame = sheet.subsurface((i * frame_width, 0, frame_width, frame_height))
        frames.append(frame)

    return frames