import sys
import os
import pygame

FPS = 60
pygame.init()
pygame.display.set_caption('Revenge underground')
width, height = 1920, 1080
screen = pygame.display.set_mode((1920, 1020), pygame.RESIZABLE)


def load_image(name, colorkey=None):
    fullname = os.path.join('sprites', name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    if colorkey is not None:
        image = image.convert()
    if colorkey == -1:
        colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


all_sprites = pygame.sprite.Group()
platforms = pygame.sprite.Group()
enemies = pygame.sprite.Group()
clock = pygame.time.Clock()