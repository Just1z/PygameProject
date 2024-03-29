import pygame
from time import time
from typing import Any
from pygame.sprite import Sprite, spritecollideany, spritecollide
from pygame.mask import from_surface
from Main import load_image
from Physics import *
from spriteGroups import all_sprites, platforms, enemies, player_group


class BaseEntity:
    def __init__(self, pos: Point, hor_vel: float, health: int, damage: int):
        self.pos = pos.copy()
        self.hor_vel = hor_vel
        self.hp = health
        self.damage = damage

        self.cur_vel = Vector((0, 0))


class GroundEntity(BaseEntity):
    def __init__(self, pos: Point, hor_vel: float, health: int, damage: int,
                 jump_height: float):
        super().__init__(pos, hor_vel, health, damage)
        self.jumped = False
        self.grounded = False
        self.jump_start = None
        self.fall_start = None

        self.jump_v0y = (jump_height * 2 * g) ** 0.5 // 6
        self.jump_time = self.jump_v0y / g


class Skeleton(GroundEntity, Sprite):
    def __init__(self, pos: Point, player, hor_vel=4.5, health=60, damage=3,
                 jump_height=100):
        GroundEntity.__init__(self, pos, hor_vel, health, damage, jump_height)
        Sprite.__init__(self, all_sprites, enemies)
        self.frames = {'AttackRight': (8, 1, []), 'AttackLeft': (8, 1, []),
                       'DeathRight': (4, 1, []), 'DeathLeft': (4, 1, []),
                       'HitRight': (4, 1, []), 'HitLeft': (4, 1, []),
                       'IdleRight': (4, 1, []), 'IdleLeft': (4, 1, []),
                       'WalkRight': (4, 1, []), 'WalkLeft': (4, 1, [])}
        self.cut_sheet()
        self.direction = True
        self.current_frames = self.frames['IdleLeft'][2]
        self.cur_frame = 0
        self.image = self.current_frames[self.cur_frame]
        self.player = player
        self.rect = self.image.get_rect()
        self.rect.x = self.pos.x
        self.rect.y = self.pos.pg_y
        self.mask = from_surface(self.image)
        self.trigger_radius = 1000
        self.attacking = False

    def changeFrames(self, key):
        if self.frames[key][2] != self.current_frames:
            self.current_frames = self.frames[key][2]
            self.cur_frame = 0

    def updateFrame(self):
        if self.cur_frame == 3 and self.hp <= 0:
            return
        self.cur_frame = (self.cur_frame + 1) % len(self.current_frames)
        if self.cur_frame == 0 and self.attacking:
            self.attacking = False
        self.image = self.current_frames[self.cur_frame]

    def cut_sheet(self):
        for name, (columns, rows, frames) in self.frames.items():
            sheet = load_image(f"Enemies/skeleton/{name}.png")
            self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                    sheet.get_height() // rows)
            for j in range(rows):
                for i in range(columns):
                    frame_location = (self.rect.w * i, self.rect.h * j)
                    frames.append(sheet.subsurface(
                        pygame.Rect(frame_location, self.rect.size)))

    def move(self, direction: Vector):
        self.cur_vel.i = direction.i
        self.cur_vel.j = direction.j

    def attack(self):
        if self.attacking:
            return
        self.attacking = True
        for sprite in spritecollide(self, player_group, False):
            sprite.hp -= self.damage

    def check_grounded(self):
        collides = pygame.sprite.spritecollide(self, platforms, False)
        for collide in collides:
            if self.jumped and not self.grounded:
                if collide.rect.bottom >= self.rect.top >= collide.rect.top:
                    self.rect.top = collide.rect.bottom
                    self.jumped = False
                    self.jump_start = None
                    self.cur_vel.j = 0
            elif not self.jumped and not self.grounded:
                if collide.rect.top <= self.rect.bottom:
                    self.rect.bottom = collide.rect.top
                    self.grounded = True
                    self.fall_start = None
                    self.cur_vel.j = 0

    def check_collision(self):
        collides = pygame.sprite.spritecollide(self, platforms, False)
        for collide in collides:
            if self.cur_vel.i > 0 and self.rect.right < collide.rect.right:
                self.rect.right = collide.rect.left
            if self.cur_vel.i < 0 and self.rect.left > collide.rect.left:
                self.rect.left = collide.rect.right
            else:
                if self.direction and self.rect.right < collide.rect.right:
                    self.rect.right = collide.rect.left
                elif self.rect.left > collide.rect.left:
                    self.rect.left = collide.rect.right
            self.cur_vel.i = 0

    def calc_fall(self):
        if not self.grounded and not self.jumped:
            if self.fall_start is None:
                self.fall_start = time()
            t = time() - self.fall_start
            self.cur_vel.j -= g * t
        if self.grounded:
            self.fall_start = None
            self.cur_vel.j = 0

    def calc_jump(self):
        if self.jumped:
            self.grounded = False
            if self.jump_start is None:
                self.jump_start = time()
                self.cur_vel.j = 0
            t = time() - self.jump_start
            if self.jump_v0y - g * t >= 0:
                self.cur_vel.j = self.jump_v0y - g * t
            else:
                self.jumped = False
                self.jump_start = None
                self.cur_vel.j = 0

    def jump(self):
        if self.grounded and not self.jumped:
            self.jumped = True
            self.grounded = False

    def dir_to_hero(self):
        if distance(self.pos, self.player.pos) > self.trigger_radius:
            return
        direction = Vector((self.pos, self.player.pos))
        i_moving = 0  # это vx
        if direction.i >= 0:
            i_moving = 1  # направление
        elif direction.i < 0:
            i_moving = -1
        if self.grounded:
            self.rect.x += 50 * i_moving
            self.rect.y -= 10
            obstacle = pygame.sprite.spritecollideany(self, platforms)
            self.rect.x -= 50 * i_moving
            self.rect.y += 20
            floor = pygame.sprite.spritecollideany(self, platforms)
            self.rect.y -= 10
            if obstacle or not floor:  # проверка на стену или обрыв впереди
                self.jump()
        self.move(Vector((i_moving, 0)))

    def update(self, *args: Any, **kwargs: Any) -> None:
        if self.hp <= 0:
            self.calc_fall()
            self.check_grounded()
            self.changeFrames('DeathRight' if self.direction else 'DeathLeft')
            return
        self.cur_vel = Vector((0, 0))
        self.dir_to_hero()  # порядок важен!
        self.calc_fall()
        self.calc_jump()
        if not self.attacking:
            self.rect.y -= self.cur_vel.j
        self.check_grounded()
        if not self.attacking:
            self.rect.x += self.cur_vel.i * self.hor_vel
        self.check_collision()
        if spritecollideany(self, player_group) and self.grounded:
            self.attack()
        else:
            self.attacking = False
        if self.attacking:
            self.changeFrames(
                'AttackRight' if self.direction else 'AttackLeft')
        elif self.cur_vel.i > 0:
            self.direction = True
            self.changeFrames('WalkRight')
        elif self.cur_vel.i < 0:
            self.direction = False
            self.changeFrames('WalkLeft')
        elif self.cur_vel.i == 0:
            self.changeFrames('IdleRight' if self.direction else 'IdleLeft')

        self.pos.x = self.rect.x
        self.pos.pg_y = self.rect.y


class Boss(GroundEntity, Sprite):
    def __init__(self, pos: Point, player, hor_vel=5, health=200, damage=4,
                 jump_height=100):
        GroundEntity.__init__(self, pos, hor_vel, health, damage, jump_height)
        Sprite.__init__(self, all_sprites, enemies)
        self.frames = {'AttackRight': (8, 1, []), 'AttackLeft': (8, 1, []),
                       'DeathRight': (10, 1, []), 'DeathLeft': (10, 1, []),
                       'IdleRight': (8, 1, []), 'IdleLeft': (8, 1, []),
                       'RunRight': (8, 1, []), 'RunLeft': (8, 1, [])}
        self.cut_sheet()
        self.direction = True
        self.current_frames = self.frames['IdleLeft'][2]
        self.cur_frame = 0
        self.image = self.current_frames[self.cur_frame]
        self.player = player
        self.rect = self.image.get_rect()
        self.rect.x = self.pos.x
        self.rect.y = self.pos.pg_y
        self.mask = from_surface(self.image)
        self.trigger_radius = 1000
        self.attacking = False

    def changeFrames(self, key):
        if self.frames[key][2] != self.current_frames:
            self.current_frames = self.frames[key][2]
            self.cur_frame = 0

    def updateFrame(self):
        if self.cur_frame == 9 and self.hp <= 0:
            return
        self.cur_frame = (self.cur_frame + 1) % len(self.current_frames)
        if self.cur_frame == 0 and self.attacking:
            self.attacking = False
        self.image = self.current_frames[self.cur_frame]

    def cut_sheet(self):
        for name, (columns, rows, frames) in self.frames.items():
            sheet = load_image(f"Enemies/death/{name}.png")
            self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                    sheet.get_height() // rows)
            for j in range(rows):
                for i in range(columns):
                    frame_location = (self.rect.w * i, self.rect.h * j)
                    frames.append(sheet.subsurface(
                        pygame.Rect(frame_location, self.rect.size)))

    def move(self, direction: Vector):
        self.cur_vel.i = direction.i
        self.cur_vel.j = direction.j

    def attack(self):
        if self.attacking:
            return
        self.attacking = True
        for sprite in spritecollide(self, player_group, False):
            sprite.hp -= self.damage

    def check_grounded(self):
        collides = pygame.sprite.spritecollide(self, platforms, False)
        for collide in collides:
            if self.jumped and not self.grounded:
                if collide.rect.bottom >= self.rect.top >= collide.rect.top:
                    self.rect.top = collide.rect.bottom
                    self.jumped = False
                    self.jump_start = None
                    self.cur_vel.j = 0
            elif not self.jumped and not self.grounded:
                if collide.rect.top <= self.rect.bottom:
                    self.rect.bottom = collide.rect.top
                    self.grounded = True
                    self.fall_start = None
                    self.cur_vel.j = 0

    def check_collision(self):
        collides = pygame.sprite.spritecollide(self, platforms, False)
        for collide in collides:
            if self.cur_vel.i > 0 and self.rect.right < collide.rect.right:
                self.rect.right = collide.rect.left
            if self.cur_vel.i < 0 and self.rect.left > collide.rect.left:
                self.rect.left = collide.rect.right
            else:
                if self.direction and self.rect.right < collide.rect.right:
                    self.rect.right = collide.rect.left
                elif self.rect.left > collide.rect.left:
                    self.rect.left = collide.rect.right
            self.cur_vel.i = 0

    def calc_fall(self):
        if not self.grounded and not self.jumped:
            if self.fall_start is None:
                self.fall_start = time()
            t = time() - self.fall_start
            self.cur_vel.j -= g * t
        if self.grounded:
            self.fall_start = None
            self.cur_vel.j = 0

    def calc_jump(self):
        if self.jumped:
            self.grounded = False
            if self.jump_start is None:
                self.jump_start = time()
                self.cur_vel.j = 0
            t = time() - self.jump_start
            if self.jump_v0y - g * t >= 0:
                self.cur_vel.j = self.jump_v0y - g * t
            else:
                self.jumped = False
                self.jump_start = None
                self.cur_vel.j = 0

    def jump(self):
        if self.grounded and not self.jumped:
            self.jumped = True
            self.grounded = False

    def dir_to_hero(self):
        if distance(self.pos, self.player.pos) > self.trigger_radius:
            return
        direction = Vector((self.pos, self.player.pos))
        i_moving = 0  # это vx
        if direction.i >= 0:
            i_moving = 1  # направление
        elif direction.i < 0:
            i_moving = -1
        if self.grounded:
            self.rect.x += 50 * i_moving
            self.rect.y -= 10
            obstacle = pygame.sprite.spritecollideany(self, platforms)
            self.rect.x -= 50 * i_moving
            self.rect.y += 20
            floor = pygame.sprite.spritecollideany(self, platforms)
            self.rect.y -= 10
            if obstacle or not floor:  # проверка на стену или обрыв впереди
                self.jump()
        self.move(Vector((i_moving, 0)))

    def update(self, *args: Any, **kwargs: Any) -> None:
        if self.hp <= 0:
            self.calc_fall()
            self.check_grounded()
            self.changeFrames('DeathRight' if self.direction else 'DeathLeft')
            return
        self.cur_vel = Vector((0, 0))
        self.dir_to_hero()  # порядок важен!
        self.calc_fall()
        self.calc_jump()
        if not self.attacking:
            self.rect.y -= self.cur_vel.j
        self.check_grounded()
        if not self.attacking:
            self.rect.x += self.cur_vel.i * self.hor_vel
        self.check_collision()
        if spritecollideany(self, player_group) and self.grounded:
            self.attack()
        else:
            self.attacking = False
        if self.attacking:
            self.changeFrames(
                'AttackRight' if self.direction else 'AttackLeft')
        elif self.cur_vel.i > 0:
            self.direction = True
            self.changeFrames('RunRight')
        elif self.cur_vel.i < 0:
            self.direction = False
            self.changeFrames('RunLeft')
        elif self.cur_vel.i == 0:
            self.changeFrames('IdleRight' if self.direction else 'IdleLeft')

        self.pos.x = self.rect.x
        self.pos.pg_y = self.rect.y