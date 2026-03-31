import math
import random
import sys
import pygame

pygame.init()

WIDTH, HEIGHT = 960, 720
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space_Defense")
CLOCK = pygame.time.Clock()

WHITE = (245, 245, 245)
BLACK = (10, 10, 20)
GRAY = (120, 120, 140)
LIGHT_GRAY = (180, 180, 200)
RED = (255, 60, 60)
DARK_RED = (180, 30, 30)
GREEN = (80, 220, 120)
BLUE = (80, 170, 255)
YELLOW = (255, 220, 80)
ORANGE = (255, 150, 40)
PURPLE = (170, 90, 255)
CYAN = (80, 240, 240)
MAGENTA = (255, 90, 200)

STATE_START = "start"
STATE_FARMING = "farming"
STATE_BOSS_WARNING = "boss_warning"
STATE_BOSS = "boss"
STATE_SHOP = "shop"
STATE_GAME_OVER = "game_over"
STATE_CLEAR = "clear"

FARMING_DURATION = 10.0
BASE_PLAYER_MAX_HP = 10
BASE_PLAYER_DAMAGE = 15
REROLL_COST = 10


def load_font(size, bold=False):
    font_candidates = [
        "malgungothic",
        "malgun gothic",
        "nanumgothic",
        "applegothic",
        "arial",
    ]
    for name in font_candidates:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except:
            pass
    return pygame.font.SysFont(None, size, bold=bold)


FONT_20 = load_font(20)
FONT_22 = load_font(22)
FONT_28 = load_font(28)
FONT_36 = load_font(36, bold=True)
FONT_52 = load_font(52, bold=True)
FONT_72 = load_font(72, bold=True)


def clamp(v, a, b):
    return max(a, min(b, v))


def circle_collision(x1, y1, r1, x2, y2, r2):
    dx = x1 - x2
    dy = y1 - y2
    return dx * dx + dy * dy <= (r1 + r2) * (r1 + r2)


def rect_circle_collision(rect, cx, cy, cr):
    closest_x = clamp(cx, rect.left, rect.right)
    closest_y = clamp(cy, rect.top, rect.bottom)
    dx = cx - closest_x
    dy = cy - closest_y
    return dx * dx + dy * dy <= cr * cr


def line_circle_collision(x1, y1, x2, y2, cx, cy, cr, line_width):
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return circle_collision(x1, y1, line_width * 0.5, cx, cy, cr)
    t = ((cx - x1) * dx + (cy - y1) * dy) / (dx * dx + dy * dy)
    t = clamp(t, 0.0, 1.0)
    px = x1 + t * dx
    py = y1 + t * dy
    return circle_collision(px, py, line_width * 0.5, cx, cy, cr)


def draw_text(surface, text, font, color, x, y, center=False):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)
    return rect


class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.speed = random.uniform(20, 100)
        self.size = random.randint(1, 3)

    def update(self, dt):
        self.y += self.speed * dt
        if self.y > HEIGHT:
            self.y = -5
            self.x = random.randint(0, WIDTH)

    def draw(self, surface):
        pygame.draw.circle(surface, (180, 180, 220), (int(self.x), int(self.y)), self.size)


class HitParticle:
    def __init__(self, x, y, color, count=8, size_min=2, size_max=5, speed_min=80, speed_max=220, life=0.25):
        self.particles = []
        self.alive = True
        for _ in range(count):
            ang = random.uniform(0, math.pi * 2)
            speed = random.uniform(speed_min, speed_max)
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed
            radius = random.randint(size_min, size_max)
            life_scale = random.uniform(life * 0.7, life * 1.3)
            self.particles.append([x, y, vx, vy, radius, color, life_scale, life_scale])

    def update(self, dt):
        alive_count = 0
        for p in self.particles:
            if p[6] <= 0:
                continue
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= 0.94
            p[3] *= 0.94
            p[6] -= dt
            alive_count += 1
        self.alive = alive_count > 0

    def draw(self, surface):
        for x, y, vx, vy, radius, color, life_left, life_max in self.particles:
            if life_left <= 0:
                continue
            scale = max(0.1, life_left / life_max)
            r = max(1, int(radius * scale))
            alpha = int(255 * scale)
            temp = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(temp, (color[0], color[1], color[2], alpha), (r * 2, r * 2), r)
            surface.blit(temp, (x - r * 2, y - r * 2))


class PlayerBullet:
    def __init__(self, x, y, vx, vy, damage, speed, pierce):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.speed = speed
        self.radius = 6
        self.pierce_left = pierce
        self.alive = True

    def update(self, dt):
        self.x += self.vx * self.speed * dt
        self.y += self.vy * self.speed * dt
        if self.y < -30 or self.x < -30 or self.x > WIDTH + 30:
            self.alive = False

    def draw(self, surface):
        pygame.draw.circle(surface, CYAN, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius - 2)


class EnemyBullet:
    def __init__(self, x, y, vx, vy, speed, damage, radius=8, color=ORANGE):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.speed = speed
        self.damage = damage
        self.radius = radius
        self.color = color
        self.alive = True

    def update(self, dt):
        self.x += self.vx * self.speed * dt
        self.y += self.vy * self.speed * dt
        if self.x < -50 or self.x > WIDTH + 50 or self.y < -50 or self.y > HEIGHT + 50:
            self.alive = False

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)


class GoldDrop:
    def __init__(self, x, y, value):
        self.x = x
        self.y = y
        self.value = value
        self.radius = 10 if value < 10 else 14
        self.vy = random.uniform(30, 70)
        self.float_angle = random.uniform(0, math.pi * 2)
        self.alive = True

    def update(self, dt, player):
        self.y += self.vy * dt
        self.float_angle += 5 * dt
        self.x += math.sin(self.float_angle) * 20 * dt

        dx = player.x - self.x
        dy = player.y - self.y
        dist_sq = dx * dx + dy * dy
        if dist_sq < 140 * 140:
            dist = max(1, math.sqrt(dist_sq))
            self.x += dx / dist * 280 * dt
            self.y += dy / dist * 280 * dt

        if circle_collision(self.x, self.y, self.radius, player.x, player.y, player.radius):
            player.gold += self.value
            self.alive = False

        if self.y > HEIGHT + 50:
            self.alive = False

    def draw(self, surface):
        pygame.draw.circle(surface, YELLOW, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (255, 245, 170), (int(self.x), int(self.y)), max(2, self.radius - 4))


class Player:
    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT - 90
        self.radius = 18
        self.speed = 320
        self.max_hp = BASE_PLAYER_MAX_HP
        self.hp = self.max_hp
        self.damage = BASE_PLAYER_DAMAGE
        self.fire_delay = 0.24
        self.bullet_speed = 700
        self.bullet_count = 1
        self.pierce = 0
        self.gold = 0
        self.last_shot_time = 0.0
        self.invincible_timer = 0.0

    def reset_for_new_game(self):
        self.x = WIDTH / 2
        self.y = HEIGHT - 90
        self.max_hp = BASE_PLAYER_MAX_HP
        self.hp = self.max_hp
        self.speed = 320
        self.damage = BASE_PLAYER_DAMAGE
        self.fire_delay = 0.24
        self.bullet_speed = 700
        self.bullet_count = 1
        self.pierce = 0
        self.gold = 0
        self.last_shot_time = 0.0
        self.invincible_timer = 0.0

    def full_heal(self):
        self.hp = self.max_hp

    def update(self, dt, keys):
        move_x = 0
        move_y = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move_x -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move_x += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            move_y -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            move_y += 1

        length = math.hypot(move_x, move_y)
        if length > 0:
            move_x /= length
            move_y /= length

        self.x += move_x * self.speed * dt
        self.y += move_y * self.speed * dt

        self.x = clamp(self.x, 30, WIDTH - 30)
        self.y = clamp(self.y, 50, HEIGHT - 30)

        if self.invincible_timer > 0:
            self.invincible_timer -= dt

    def try_shoot(self, now, bullets):
        if now - self.last_shot_time < self.fire_delay:
            return
        self.last_shot_time = now

        pattern = []
        if self.bullet_count == 1:
            pattern = [0]
        elif self.bullet_count == 2:
            pattern = [-10, 10]
        elif self.bullet_count == 3:
            pattern = [-16, 0, 16]
        elif self.bullet_count == 4:
            pattern = [-24, -8, 8, 24]
        elif self.bullet_count == 5:
            pattern = [-28, -14, 0, 14, 28]
        else:
            half = self.bullet_count // 2
            spacing = 12
            pattern = [(i - half) * spacing for i in range(self.bullet_count)]

        for offset in pattern:
            angle = 0
            if self.bullet_count >= 4:
                angle = offset * 0.008
            vx = math.sin(angle)
            vy = -math.cos(angle)
            bullets.append(
                PlayerBullet(
                    self.x + offset,
                    self.y - 18,
                    vx,
                    vy,
                    self.damage,
                    self.bullet_speed,
                    self.pierce
                )
            )

    def take_damage(self, amount):
        if self.invincible_timer > 0:
            return False
        self.hp -= amount
        self.invincible_timer = 1.0
        return True

    def draw(self, surface):
        blink = self.invincible_timer > 0 and int(self.invincible_timer * 12) % 2 == 0
        if blink:
            return
        points = [
            (self.x, self.y - 22),
            (self.x - 18, self.y + 18),
            (self.x, self.y + 8),
            (self.x + 18, self.y + 18),
        ]
        pygame.draw.polygon(surface, BLUE, points)
        pygame.draw.polygon(surface, WHITE, points, 2)
        pygame.draw.circle(surface, CYAN, (int(self.x), int(self.y + 2)), 6)


class Enemy:
    def __init__(self, stage, big=False):
        self.stage = stage
        self.big = big
        self.x = random.randint(40, WIDTH - 40)
        self.y = random.randint(-140, -40)
        self.alive = True
        self.hit_flash_timer = 0.0

        hp_base = 20 if not big else 50
        stage_mul = 1.0 if stage == 1 else (1.5 if stage == 2 else 2.25)
        self.hp = int(hp_base * stage_mul)
        self.max_hp = self.hp

        base_speed = random.uniform(110, 160) if not big else random.uniform(70, 110)
        stage_speed_mul = 1.0 if stage == 1 else (1.2 if stage == 2 else 1.4)
        self.speed = base_speed * stage_speed_mul

        self.radius = 16 if not big else 28
        self.damage = 1
        self.wave = random.uniform(0, math.pi * 2)
        self.color = PURPLE if not big else MAGENTA
        self.gold_drop_chance = 0.45 if not big else 0.8

    def update(self, dt):
        self.wave += 2.2 * dt
        self.y += self.speed * dt
        self.x += math.sin(self.wave) * 45 * dt
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= dt
        if self.y > HEIGHT + 80:
            self.alive = False

    def draw(self, surface):
        draw_color = WHITE if self.hit_flash_timer > 0 else self.color
        if self.big:
            pygame.draw.circle(surface, draw_color, (int(self.x), int(self.y)), self.radius)
            pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.radius, 2)
            pygame.draw.circle(surface, BLACK, (int(self.x - 8), int(self.y - 6)), 3)
            pygame.draw.circle(surface, BLACK, (int(self.x + 8), int(self.y - 6)), 3)
        else:
            points = [
                (self.x, self.y - self.radius),
                (self.x - self.radius, self.y + self.radius * 0.6),
                (self.x + self.radius, self.y + self.radius * 0.6),
            ]
            pygame.draw.polygon(surface, draw_color, points)
            pygame.draw.polygon(surface, WHITE, points, 2)


class LaserAttack:
    def __init__(self, x, width, warning_time, active_time, damage, color_warning=RED, color_active=(255, 80, 80)):
        self.x = x
        self.width = width
        self.warning_time = warning_time
        self.active_time = active_time
        self.damage = damage
        self.color_warning = color_warning
        self.color_active = color_active
        self.timer = 0.0
        self.phase = "warning"
        self.alive = True

    def update(self, dt):
        self.timer += dt
        if self.phase == "warning" and self.timer >= self.warning_time:
            self.phase = "active"
            self.timer = 0.0
        elif self.phase == "active" and self.timer >= self.active_time:
            self.alive = False

    def is_damaging(self):
        return self.phase == "active"

    def get_rect(self):
        return pygame.Rect(self.x - self.width // 2, 0, self.width, HEIGHT)

    def draw(self, surface):
        rect = self.get_rect()
        if self.phase == "warning":
            alpha = 120 + int(100 * abs(math.sin(self.timer * 10)))
            laser_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            laser_surface.fill((self.color_warning[0], self.color_warning[1], self.color_warning[2], alpha))
            surface.blit(laser_surface, rect)
        else:
            pygame.draw.rect(surface, self.color_active, rect)
            pygame.draw.rect(surface, WHITE, rect, 2)


class PulseLineLaser:
    def __init__(self, x1, y1, x2, y2, warning_time, active_time, width, damage, color_warning=RED, color_active=(255, 80, 80)):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.warning_time = warning_time
        self.active_time = active_time
        self.width = width
        self.damage = damage
        self.color_warning = color_warning
        self.color_active = color_active
        self.phase = "warning"
        self.timer = 0.0
        self.alive = True

    def update(self, dt):
        self.timer += dt
        if self.phase == "warning" and self.timer >= self.warning_time:
            self.phase = "active"
            self.timer = 0.0
        elif self.phase == "active" and self.timer >= self.active_time:
            self.alive = False

    def is_damaging(self):
        return self.phase == "active"

    def collides_with_circle(self, x, y, radius):
        return line_circle_collision(self.x1, self.y1, self.x2, self.y2, x, y, radius, self.width)

    def draw(self, surface):
        if self.phase == "warning":
            pygame.draw.line(surface, self.color_warning, (self.x1, self.y1), (self.x2, self.y2), max(2, self.width // 3))
        else:
            pygame.draw.line(surface, self.color_active, (self.x1, self.y1), (self.x2, self.y2), self.width)
            pygame.draw.line(surface, WHITE, (self.x1, self.y1), (self.x2, self.y2), 2)


class PulseCircleLaserSpawner:
    def __init__(self, cx, cy, start_angle=0.0, angle_step=0.22, shots=18,
                 warning_time=0.08, active_time=0.07, length=980, width=14, damage=1):
        self.cx = cx
        self.cy = cy
        self.angle = start_angle
        self.angle_step = angle_step
        self.shots_total = shots
        self.shots_done = 0
        self.warning_time = warning_time
        self.active_time = active_time
        self.length = length
        self.width = width
        self.damage = damage
        self.spawn_delay = 0.04
        self.timer = 0.0
        self.alive = True

    def update(self, dt, boss):
        self.cx = boss.x
        self.cy = boss.y
        self.timer += dt
        produced = []
        while self.timer >= self.spawn_delay and self.shots_done < self.shots_total:
            self.timer -= self.spawn_delay
            ex = self.cx + math.cos(self.angle) * self.length
            ey = self.cy + math.sin(self.angle) * self.length
            produced.append(
                PulseLineLaser(
                    self.cx, self.cy, ex, ey,
                    self.warning_time, self.active_time,
                    self.width, self.damage
                )
            )
            self.angle += self.angle_step
            self.shots_done += 1

        if self.shots_done >= self.shots_total:
            self.alive = False

        return produced


class DashTelegraph:
    def __init__(self, x1, y1, x2, y2, width, warning_time, damage, color=ORANGE):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.width = width
        self.warning_time = warning_time
        self.damage = damage
        self.color = color
        self.timer = 0.0
        self.alive = True
        self.triggered = False

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.warning_time:
            self.triggered = True
            self.alive = False

    def draw(self, surface):
        pygame.draw.line(surface, self.color, (self.x1, self.y1), (self.x2, self.y2), self.width)
        pygame.draw.line(surface, WHITE, (self.x1, self.y1), (self.x2, self.y2), 2)


class Boss:
    def __init__(self, stage):
        self.stage = stage
        self.x = WIDTH / 2
        self.y = 140
        self.base_x = WIDTH / 2
        self.base_y = 140
        self.move_t = 0.0
        self.attack_timer = 0.0
        self.pattern_timer = 0.0
        self.alive = True
        self.color = WHITE
        self.name = ""
        self.body_radius = 46
        self.contact_damage = 1
        self.hit_flash_timer = 0.0

        self.lasers = []
        self.line_lasers = []
        self.pulse_circle_spawners = []
        self.dash_telegraphs = []
        self.enemy_bullets = []

        self.state = "normal"
        self.dash_queue = []
        self.dash_vx = 0
        self.dash_vy = 0
        self.dash_time_left = 0.0
        self.target_x = self.base_x
        self.target_y = self.base_y
        self.pending_dash = None

        self.arm_left = [self.x - 90, self.y + 20]
        self.arm_right = [self.x + 90, self.y + 20]
        self.arm_left_target = self.arm_left[:]
        self.arm_right_target = self.arm_right[:]
        self.arm_dash_timer = 0.0
        self.arm_phase = "idle"
        self.arm_left_warning = None
        self.arm_right_warning = None

        stage_mul = 1.0 if stage == 1 else (1.5 if stage == 2 else 2.25)
        boss_hp = 500
        self.hp = int(boss_hp * stage_mul)
        self.max_hp = self.hp

        if stage == 1:
            roll = random.random()
            if roll < 0.5:
                self.name = "오염된 위성"
                self.variant = "bullet_focus"
                self.color = PURPLE
            else:
                self.name = "개조된 행성"
                self.variant = "laser_focus"
                self.color = ORANGE
        elif stage == 2:
            self.name = "깨어난 혜성"
            self.variant = "dash_focus"
            self.color = CYAN
        else:
            self.name = "차원간전투지휘인공지능병기알파노바엑스터미네이터코어"
            self.variant = "robot"
            self.color = LIGHT_GRAY
            self.body_radius = 52

    def update(self, dt, player):
        self.move_t += dt
        self.attack_timer += dt
        self.pattern_timer += dt
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= dt

        for laser in self.lasers:
            laser.update(dt)
        self.lasers = [l for l in self.lasers if l.alive]

        for laser in self.line_lasers:
            laser.update(dt)
        self.line_lasers = [l for l in self.line_lasers if l.alive]

        for tele in self.dash_telegraphs:
            tele.update(dt)
        self.dash_telegraphs = [t for t in self.dash_telegraphs if t.alive]

        for bullet in self.enemy_bullets:
            bullet.update(dt)
        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]

        produced_lasers = []
        for spawner in self.pulse_circle_spawners:
            produced_lasers.extend(spawner.update(dt, self))
        self.line_lasers.extend(produced_lasers)
        self.pulse_circle_spawners = [s for s in self.pulse_circle_spawners if s.alive]

        if self.stage == 2:
            self.update_stage2_state(dt, player)
        elif self.stage == 3:
            self.update_stage3_state(dt, player)
        else:
            self.update_normal_move(dt)

        if self.stage == 1:
            self.update_stage1_patterns(dt, player)
        elif self.stage == 2:
            self.update_stage2_patterns(dt, player)
        else:
            self.update_stage3_patterns(dt, player)

    def update_normal_move(self, dt):
        self.x = self.base_x + math.sin(self.move_t * 2.0) * 120
        self.y = self.base_y + math.sin(self.move_t * 4.0) * 26

    def update_stage2_state(self, dt, player):
        if self.state == "normal":
            self.x = self.base_x + math.sin(self.move_t * 2.0) * 120
            self.y = self.base_y + math.sin(self.move_t * 4.0) * 26

        elif self.state == "dash_warning":
            if self.pending_dash and self.pending_dash.triggered:
                dx = self.pending_dash.x2 - self.x
                dy = self.pending_dash.y2 - self.y
                dist = max(1, math.hypot(dx, dy))
                speed = 860
                self.dash_vx = dx / dist * speed
                self.dash_vy = dy / dist * speed
                self.dash_time_left = dist / speed
                self.state = "dashing"
                self.pending_dash = None

        elif self.state == "dashing":
            self.x += self.dash_vx * dt
            self.y += self.dash_vy * dt
            self.dash_time_left -= dt
            if self.dash_time_left <= 0:
                if self.dash_queue:
                    self.start_next_dash(player)
                else:
                    self.state = "returning"

        elif self.state == "returning":
            dx = self.base_x - self.x
            dy = self.base_y - self.y
            dist = math.hypot(dx, dy)
            if dist < 8:
                self.x = self.base_x
                self.y = self.base_y
                self.state = "normal"
            else:
                self.x += dx / dist * 340 * dt
                self.y += dy / dist * 340 * dt

    def update_stage3_state(self, dt, player):
        self.x = self.base_x + math.sin(self.move_t * 2.0) * 120
        self.y = self.base_y + math.sin(self.move_t * 4.0) * 26

        if self.arm_phase == "idle":
            self.arm_left[0] = self.x - 90 + math.sin(self.move_t * 2.8) * 20
            self.arm_left[1] = self.y + 20 + math.cos(self.move_t * 3.5) * 10
            self.arm_right[0] = self.x + 90 + math.sin(self.move_t * 2.8 + 1.7) * 20
            self.arm_right[1] = self.y + 20 + math.cos(self.move_t * 3.5 + 1.7) * 10

        self.update_arm_logic(dt, player)

    def update_stage1_patterns(self, dt, player):
        if self.variant == "bullet_focus":
            if self.attack_timer >= 1.35:
                self.attack_timer = 0.0
                if random.random() < 0.75:
                    self.fire_radial_bullets(12, 170, 1)
                else:
                    self.fire_fan_to_player(player, 7, 230, 1)

            if self.pattern_timer >= 5.8:
                self.pattern_timer = 0.0
                if random.random() < 0.65:
                    self.spawn_pulse_circle_laser()
                else:
                    self.spawn_vertical_laser_random()
        else:
            if self.attack_timer >= 1.0:
                self.attack_timer = 0.0
                if random.random() < 0.65:
                    self.spawn_vertical_laser_random()
                else:
                    self.fire_fan_to_player(player, 5, 220, 1)

            if self.pattern_timer >= 5.0:
                self.pattern_timer = 0.0
                if random.random() < 0.7:
                    self.spawn_pulse_circle_laser()
                else:
                    self.spawn_vertical_laser_random(width=72, warning=0.85, active=0.6)

    def update_stage2_patterns(self, dt, player):
        if self.state == "normal":
            if self.attack_timer >= 1.15:
                self.attack_timer = 0.0
                self.fire_fan_to_player(player, 6, 250, 1)

            if self.pattern_timer >= 4.7:
                self.pattern_timer = 0.0
                dash_count = random.randint(2, 3)
                self.dash_queue = []
                for _ in range(dash_count):
                    tx = clamp(player.x + random.uniform(-70, 70), 60, WIDTH - 60)
                    ty = clamp(player.y + random.uniform(-40, 40), 80, HEIGHT - 90)
                    self.dash_queue.append((tx, ty))
                self.start_next_dash(player)

    def update_stage3_patterns(self, dt, player):
        if self.attack_timer >= 1.0:
            self.attack_timer = 0.0
            if random.random() < 0.5:
                self.fire_fan_to_player(player, 7, 260, 1)
            else:
                self.fire_radial_bullets(10, 180, 1)

        if self.pattern_timer >= 4.0:
            self.pattern_timer = 0.0
            if random.random() < 0.55:
                self.spawn_vertical_laser_random(width=72, warning=0.9, active=0.7)
            else:
                self.spawn_pulse_circle_laser(shots=20, angle_step=0.18)

        self.arm_dash_timer += dt
        if self.arm_dash_timer >= 3.4 and self.arm_phase == "idle":
            self.arm_dash_timer = 0.0
            self.arm_phase = "left_warning"
            tx = clamp(player.x + random.uniform(-60, 60), 70, WIDTH - 70)
            ty = clamp(player.y + random.uniform(-30, 30), 90, HEIGHT - 60)
            self.arm_left_target = [tx, ty]
            self.arm_left_warning = DashTelegraph(self.arm_left[0], self.arm_left[1], tx, ty, 14, 0.7, 1, color=PURPLE)
            self.dash_telegraphs.append(self.arm_left_warning)

    def start_next_dash(self, player):
        if not self.dash_queue:
            self.state = "returning"
            return
        tx, ty = self.dash_queue.pop(0)
        self.pending_dash = DashTelegraph(self.x, self.y, tx, ty, 18, 0.8, 1, color=ORANGE)
        self.dash_telegraphs.append(self.pending_dash)
        self.state = "dash_warning"

    def update_arm_logic(self, dt, player):
        if self.arm_phase == "left_warning":
            if self.arm_left_warning and self.arm_left_warning.triggered:
                self.arm_phase = "left_dash"

        elif self.arm_phase == "left_dash":
            dx = self.arm_left_target[0] - self.arm_left[0]
            dy = self.arm_left_target[1] - self.arm_left[1]
            dist = math.hypot(dx, dy)
            if dist < 12:
                self.arm_phase = "right_warning"
                tx = clamp(player.x + random.uniform(-60, 60), 70, WIDTH - 70)
                ty = clamp(player.y + random.uniform(-30, 30), 90, HEIGHT - 60)
                self.arm_right_target = [tx, ty]
                self.arm_right_warning = DashTelegraph(self.arm_right[0], self.arm_right[1], tx, ty, 14, 0.7, 1, color=PURPLE)
                self.dash_telegraphs.append(self.arm_right_warning)
            else:
                self.arm_left[0] += dx / dist * 760 * dt
                self.arm_left[1] += dy / dist * 760 * dt

        elif self.arm_phase == "right_warning":
            if self.arm_right_warning and self.arm_right_warning.triggered:
                self.arm_phase = "right_dash"

        elif self.arm_phase == "right_dash":
            dx = self.arm_right_target[0] - self.arm_right[0]
            dy = self.arm_right_target[1] - self.arm_right[1]
            dist = math.hypot(dx, dy)
            if dist < 12:
                self.arm_phase = "return_both"
            else:
                self.arm_right[0] += dx / dist * 760 * dt
                self.arm_right[1] += dy / dist * 760 * dt

        elif self.arm_phase == "return_both":
            lx_target = self.x - 90
            ly_target = self.y + 20
            rx_target = self.x + 90
            ry_target = self.y + 20

            dlx = lx_target - self.arm_left[0]
            dly = ly_target - self.arm_left[1]
            drx = rx_target - self.arm_right[0]
            dry = ry_target - self.arm_right[1]

            ldist = math.hypot(dlx, dly)
            rdist = math.hypot(drx, dry)

            if ldist > 3:
                self.arm_left[0] += dlx / max(1, ldist) * 360 * dt
                self.arm_left[1] += dly / max(1, ldist) * 360 * dt
            if rdist > 3:
                self.arm_right[0] += drx / max(1, rdist) * 360 * dt
                self.arm_right[1] += dry / max(1, rdist) * 360 * dt
            if ldist < 8 and rdist < 8:
                self.arm_phase = "idle"

    def fire_radial_bullets(self, count, speed, damage):
        angle_offset = random.uniform(0, math.pi * 2)
        for i in range(count):
            ang = angle_offset + (math.pi * 2 / count) * i
            vx = math.cos(ang)
            vy = math.sin(ang)
            self.enemy_bullets.append(
                EnemyBullet(self.x, self.y, vx, vy, speed, damage, radius=8, color=ORANGE)
            )

    def fire_fan_to_player(self, player, count, speed, damage):
        dx = player.x - self.x
        dy = player.y - self.y
        base = math.atan2(dy, dx)
        spread = 0.9
        if count == 1:
            angles = [base]
        else:
            angles = [base - spread / 2 + spread * i / (count - 1) for i in range(count)]
        for ang in angles:
            vx = math.cos(ang)
            vy = math.sin(ang)
            self.enemy_bullets.append(
                EnemyBullet(self.x, self.y, vx, vy, speed, damage, radius=8, color=PURPLE if self.stage == 1 else ORANGE)
            )

    def spawn_vertical_laser_random(self, width=64, warning=1.0, active=0.55):
        lx = random.randint(100, WIDTH - 100)
        self.lasers.append(LaserAttack(lx, width, warning, active, 1))

    def spawn_pulse_circle_laser(self, shots=18, angle_step=0.22):
        start_angle = random.uniform(0, math.pi * 2)
        self.pulse_circle_spawners.append(
            PulseCircleLaserSpawner(
                self.x, self.y,
                start_angle=start_angle,
                angle_step=angle_step,
                shots=shots,
                warning_time=0.07,
                active_time=0.06,
                length=980,
                width=14,
                damage=1
            )
        )

    def take_damage(self, amount):
        self.hp -= amount
        self.hit_flash_timer = 0.08
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def draw(self, surface):
        draw_color = WHITE if self.hit_flash_timer > 0 else self.color

        if self.stage == 1:
            pygame.draw.circle(surface, draw_color, (int(self.x), int(self.y)), self.body_radius)
            pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), self.body_radius, 3)
            pygame.draw.circle(surface, BLACK, (int(self.x - 14), int(self.y - 8)), 4)
            pygame.draw.circle(surface, BLACK, (int(self.x + 14), int(self.y - 8)), 4)
            pygame.draw.arc(surface, BLACK, (self.x - 18, self.y, 36, 18), math.pi * 0.1, math.pi * 0.9, 2)

        elif self.stage == 2:
            points = [
                (self.x, self.y - 54),
                (self.x - 34, self.y + 20),
                (self.x, self.y + 42),
                (self.x + 34, self.y + 20),
            ]
            pygame.draw.polygon(surface, draw_color, points)
            pygame.draw.polygon(surface, WHITE, points, 3)
            pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y - 10)), 8)

        else:
            body_rect = pygame.Rect(0, 0, 120, 110)
            body_rect.center = (int(self.x), int(self.y))
            pygame.draw.rect(surface, (220, 220, 220) if self.hit_flash_timer > 0 else (130, 140, 170), body_rect, border_radius=16)
            pygame.draw.rect(surface, WHITE, body_rect, 3, border_radius=16)

            left_arm_rect = pygame.Rect(0, 0, 38, 74)
            left_arm_rect.center = (int(self.arm_left[0]), int(self.arm_left[1]))
            right_arm_rect = pygame.Rect(0, 0, 38, 74)
            right_arm_rect.center = (int(self.arm_right[0]), int(self.arm_right[1]))

            pygame.draw.rect(surface, (100, 110, 135), left_arm_rect, border_radius=12)
            pygame.draw.rect(surface, WHITE, left_arm_rect, 2, border_radius=12)
            pygame.draw.rect(surface, (100, 110, 135), right_arm_rect, border_radius=12)
            pygame.draw.rect(surface, WHITE, right_arm_rect, 2, border_radius=12)

            pygame.draw.line(surface, LIGHT_GRAY, (self.x - 40, self.y + 10), (self.arm_left[0], self.arm_left[1]), 6)
            pygame.draw.line(surface, LIGHT_GRAY, (self.x + 40, self.y + 10), (self.arm_right[0], self.arm_right[1]), 6)

            pygame.draw.circle(surface, RED, (int(self.x), int(self.y - 10)), 12)
            pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y - 10)), 12, 2)

        for laser in self.lasers:
            laser.draw(surface)
        for laser in self.line_lasers:
            laser.draw(surface)
        for tele in self.dash_telegraphs:
            tele.draw(surface)
        for bullet in self.enemy_bullets:
            bullet.draw(surface)

    def body_hit_test(self, bullet):
        if self.stage == 3:
            body_rect = pygame.Rect(0, 0, 120, 110)
            body_rect.center = (self.x, self.y)
            return rect_circle_collision(body_rect, bullet.x, bullet.y, bullet.radius)
        return circle_collision(self.x, self.y, self.body_radius, bullet.x, bullet.y, bullet.radius)

    def check_player_collisions(self, player):
        if circle_collision(self.x, self.y, self.body_radius, player.x, player.y, player.radius):
            player.take_damage(self.contact_damage)

        if self.stage == 3:
            if circle_collision(self.arm_left[0], self.arm_left[1], 30, player.x, player.y, player.radius):
                player.take_damage(1)
            if circle_collision(self.arm_right[0], self.arm_right[1], 30, player.x, player.y, player.radius):
                player.take_damage(1)

        for bullet in self.enemy_bullets:
            if bullet.alive and circle_collision(bullet.x, bullet.y, bullet.radius, player.x, player.y, player.radius):
                if player.take_damage(bullet.damage):
                    bullet.alive = False

        for laser in self.lasers:
            if laser.is_damaging() and rect_circle_collision(laser.get_rect(), player.x, player.y, player.radius):
                player.take_damage(laser.damage)

        for laser in self.line_lasers:
            if laser.is_damaging() and laser.collides_with_circle(player.x, player.y, player.radius):
                player.take_damage(laser.damage)


class Upgrade:
    def __init__(self, name, desc, cost, key, value):
        self.name = name
        self.desc = desc
        self.cost = cost
        self.key = key
        self.value = value

    def apply(self, player):
        if self.key == "multishot":
            player.bullet_count += self.value
        elif self.key == "fire_rate":
            player.fire_delay = max(0.07, player.fire_delay * self.value)
        elif self.key == "damage":
            player.damage += self.value
        elif self.key == "max_hp":
            player.max_hp += self.value
            player.hp += self.value
        elif self.key == "move_speed":
            player.speed += self.value
        elif self.key == "bullet_speed":
            player.bullet_speed += self.value
        elif self.key == "pierce":
            player.pierce += self.value


def make_upgrade_pool():
    return [
        Upgrade("발사 탄수 증가", "한 번에 발사하는 탄수가 1 증가", 70, "multishot", 1),
        Upgrade("공격속도 증가", "발사 간격 15% 감소", 35, "fire_rate", 0.85),
        Upgrade("공격력 증가", "탄환 피해 +5", 35, "damage", 5),
        Upgrade("최대체력 증가", "최대 체력 +1", 40, "max_hp", 1),
        Upgrade("이동속도 증가", "이동속도 +40", 28, "move_speed", 40),
        Upgrade("탄속 증가", "탄속 +120", 28, "bullet_speed", 120),
        Upgrade("탄관통력 증가", "탄환 관통 +1", 75, "pierce", 1),
    ]


class Game:
    def __init__(self):
        self.stars = [Star() for _ in range(70)]
        self.player = Player()
        self.state = STATE_START
        self.stage = 1
        self.farming_timer = FARMING_DURATION

        self.player_bullets = []
        self.enemies = []
        self.gold_drops = []
        self.boss = None
        self.effects = []

        self.spawn_timer = 0.0
        self.big_spawn_timer = 0.0

        self.warning_total_time = 2.6
        self.warning_timer = 0.0
        self.warning_display_index = 0
        self.warning_char_interval = 0.08
        self.current_boss_name = ""
        self.boss_warning_elapsed = 0.0

        self.shop_items = []
        self.upgrade_pool = make_upgrade_pool()
        self.shop_rects = []
        self.shop_hover_index = -1

    def add_hit_effect(self, x, y, color, count=8, big=False):
        if big:
            self.effects.append(HitParticle(x, y, color, count=count, size_min=3, size_max=7, speed_min=100, speed_max=260, life=0.35))
        else:
            self.effects.append(HitParticle(x, y, color, count=count, size_min=2, size_max=5, speed_min=80, speed_max=220, life=0.22))

    def reset_game(self):
        self.player.reset_for_new_game()
        self.state = STATE_START
        self.stage = 1
        self.farming_timer = FARMING_DURATION
        self.player_bullets.clear()
        self.enemies.clear()
        self.gold_drops.clear()
        self.effects.clear()
        self.boss = None
        self.spawn_timer = 0.0
        self.big_spawn_timer = 0.0
        self.warning_timer = 0.0
        self.warning_display_index = 0
        self.current_boss_name = ""
        self.shop_items.clear()
        self.shop_rects.clear()
        self.boss_warning_elapsed = 0.0

    def start_stage_farming(self):
        self.state = STATE_FARMING
        self.farming_timer = FARMING_DURATION
        self.player_bullets.clear()
        self.enemies.clear()
        self.gold_drops.clear()
        self.effects.clear()
        self.boss = None
        self.spawn_timer = 0.0
        self.big_spawn_timer = 0.0

    def start_boss_warning(self):
        self.state = STATE_BOSS_WARNING
        self.player_bullets.clear()
        self.enemies.clear()
        self.gold_drops.clear()
        self.boss = Boss(self.stage)
        self.current_boss_name = self.boss.name
        self.warning_timer = 0.0
        self.warning_display_index = 0
        self.warning_char_interval = max(0.025, 0.13 - len(self.current_boss_name) * 0.0015)
        self.boss_warning_elapsed = 0.0

    def start_boss_battle(self):
        self.state = STATE_BOSS
        self.player_bullets.clear()

    def open_shop(self):
        self.state = STATE_SHOP
        self.player.full_heal()
        self.roll_shop_items()

    def roll_shop_items(self):
        self.shop_items = random.sample(self.upgrade_pool, 3)

    def finish_stage(self):
        if self.stage >= 3:
            self.state = STATE_CLEAR
        else:
            self.stage += 1
            self.start_stage_farming()

    def spawn_enemy(self, big=False):
        self.enemies.append(Enemy(self.stage, big=big))

    def buy_shop_item(self, idx):
        if idx < 0 or idx >= len(self.shop_items):
            return
        item = self.shop_items[idx]
        if self.player.gold >= item.cost:
            self.player.gold -= item.cost
            item.apply(self.player)
            self.roll_shop_items()

    def handle_event(self, event):
        if self.state == STATE_START:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.stage = 1
                self.player.reset_for_new_game()
                self.start_stage_farming()

        elif self.state == STATE_SHOP:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.finish_stage()
                elif event.key == pygame.K_r:
                    if self.player.gold >= REROLL_COST:
                        self.player.gold -= REROLL_COST
                        self.roll_shop_items()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for i, rect in enumerate(self.shop_rects):
                    if rect.collidepoint(mx, my):
                        self.buy_shop_item(i)
                        break

        elif self.state == STATE_GAME_OVER:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.reset_game()

        elif self.state == STATE_CLEAR:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.reset_game()

    def update(self, dt):
        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()

        for star in self.stars:
            star.update(dt)

        for effect in self.effects:
            effect.update(dt)
        self.effects = [e for e in self.effects if e.alive]

        if self.state == STATE_FARMING:
            self.player.update(dt, keys)
            now = pygame.time.get_ticks() / 1000.0
            if keys[pygame.K_SPACE]:
                self.player.try_shoot(now, self.player_bullets)

            self.farming_timer -= dt
            self.spawn_timer += dt
            self.big_spawn_timer += dt

            stage_enemy_interval = 0.75 if self.stage == 1 else (0.58 if self.stage == 2 else 0.46)
            stage_big_interval = 5.2 if self.stage == 1 else (4.4 if self.stage == 2 else 3.7)

            if self.spawn_timer >= stage_enemy_interval:
                self.spawn_timer = 0.0
                self.spawn_enemy(big=False)

            if self.big_spawn_timer >= stage_big_interval:
                self.big_spawn_timer = 0.0
                self.spawn_enemy(big=True)

            for bullet in self.player_bullets:
                bullet.update(dt)
            for enemy in self.enemies:
                enemy.update(dt)
            for gold in self.gold_drops:
                gold.update(dt, self.player)

            self.handle_bullet_enemy_collisions()
            self.handle_enemy_player_collisions()

            self.player_bullets = [b for b in self.player_bullets if b.alive]
            self.enemies = [e for e in self.enemies if e.alive]
            self.gold_drops = [g for g in self.gold_drops if g.alive]

            if self.player.hp <= 0:
                self.state = STATE_GAME_OVER

            if self.farming_timer <= 0:
                self.start_boss_warning()

        elif self.state == STATE_BOSS_WARNING:
            self.warning_timer += dt
            if self.warning_timer >= self.warning_char_interval:
                self.warning_timer = 0.0
                if self.warning_display_index < len(self.current_boss_name):
                    self.warning_display_index += 1

            self.boss_warning_elapsed += dt
            total_display_time = self.warning_total_time + len(self.current_boss_name) * self.warning_char_interval
            if self.boss_warning_elapsed >= total_display_time:
                self.start_boss_battle()

        elif self.state == STATE_BOSS:
            self.player.update(dt, keys)
            now = pygame.time.get_ticks() / 1000.0
            if keys[pygame.K_SPACE]:
                self.player.try_shoot(now, self.player_bullets)

            for bullet in self.player_bullets:
                bullet.update(dt)
            for gold in self.gold_drops:
                gold.update(dt, self.player)

            if self.boss:
                self.boss.update(dt, self.player)
                self.boss.check_player_collisions(self.player)

            self.handle_boss_bullet_collisions()

            self.player_bullets = [b for b in self.player_bullets if b.alive]
            self.gold_drops = [g for g in self.gold_drops if g.alive]

            if self.player.hp <= 0:
                self.state = STATE_GAME_OVER

            if self.boss and not self.boss.alive:
                self.spawn_boss_gold(self.boss)
                self.add_hit_effect(self.boss.x, self.boss.y, ORANGE, count=24, big=True)
                self.open_shop()

        elif self.state == STATE_SHOP:
            self.player.update(dt, keys)
            self.shop_hover_index = -1
            for i, rect in enumerate(self.shop_rects):
                if rect.collidepoint(mouse_pos):
                    self.shop_hover_index = i
                    break

    def spawn_enemy_gold(self, enemy):
        if random.random() < enemy.gold_drop_chance:
            value = 5 if enemy.big else random.choice([2, 3, 4])
            self.gold_drops.append(GoldDrop(enemy.x, enemy.y, value))

    def spawn_boss_gold(self, boss):
        count = 12 if boss.stage == 1 else (16 if boss.stage == 2 else 20)
        for _ in range(count):
            value = random.choice([8, 10, 12, 15])
            self.gold_drops.append(
                GoldDrop(
                    boss.x + random.uniform(-60, 60),
                    boss.y + random.uniform(-30, 30),
                    value
                )
            )

    def handle_bullet_enemy_collisions(self):
        for bullet in self.player_bullets:
            if not bullet.alive:
                continue
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                if circle_collision(bullet.x, bullet.y, bullet.radius, enemy.x, enemy.y, enemy.radius):
                    enemy.hp -= bullet.damage
                    enemy.hit_flash_timer = 0.08
                    self.add_hit_effect(bullet.x, bullet.y, CYAN, count=6, big=enemy.big)

                    bullet.pierce_left -= 1
                    if bullet.pierce_left < 0:
                        bullet.alive = False

                    if enemy.hp <= 0:
                        enemy.alive = False
                        self.spawn_enemy_gold(enemy)
                        self.add_hit_effect(enemy.x, enemy.y, MAGENTA if enemy.big else PURPLE, count=14, big=True)

                    if not bullet.alive:
                        break

    def handle_enemy_player_collisions(self):
        for enemy in self.enemies:
            if enemy.alive and circle_collision(enemy.x, enemy.y, enemy.radius, self.player.x, self.player.y, self.player.radius):
                if self.player.take_damage(enemy.damage):
                    self.add_hit_effect(self.player.x, self.player.y, RED, count=14, big=True)
                    enemy.alive = False
                    self.add_hit_effect(enemy.x, enemy.y, ORANGE, count=10, big=False)

    def handle_boss_bullet_collisions(self):
        if not self.boss:
            return
        for bullet in self.player_bullets:
            if not bullet.alive:
                continue
            if self.boss.body_hit_test(bullet):
                self.boss.take_damage(bullet.damage)
                self.add_hit_effect(bullet.x, bullet.y, CYAN, count=8, big=False)

                bullet.pierce_left -= 1
                if bullet.pierce_left < 0:
                    bullet.alive = False

    def draw(self, surface):
        surface.fill(BLACK)
        for star in self.stars:
            star.draw(surface)

        if self.state == STATE_START:
            self.draw_start(surface)
        elif self.state == STATE_FARMING:
            self.draw_farming(surface)
        elif self.state == STATE_BOSS_WARNING:
            self.draw_boss_warning(surface)
        elif self.state == STATE_BOSS:
            self.draw_boss(surface)
        elif self.state == STATE_SHOP:
            self.draw_shop(surface)
        elif self.state == STATE_GAME_OVER:
            self.draw_game_over(surface)
        elif self.state == STATE_CLEAR:
            self.draw_clear(surface)

        for effect in self.effects:
            effect.draw(surface)

        pygame.display.flip()

    def draw_common_hud(self, surface):
        draw_text(surface, f"스테이지: {self.stage}", FONT_28, WHITE, 18, 12)
        draw_text(surface, f"골드: {self.player.gold}", FONT_28, YELLOW, 18, 44)

        for i in range(self.player.max_hp):
            color = RED if i < self.player.hp else DARK_RED
            pygame.draw.circle(surface, color, (WIDTH - 28 - i * 28, 28), 10)
            pygame.draw.circle(surface, WHITE, (WIDTH - 28 - i * 28, 28), 10, 2)

        draw_text(surface, f"공격력 {self.player.damage}", FONT_22, LIGHT_GRAY, WIDTH - 220, 50)
        draw_text(surface, f"탄수 {self.player.bullet_count}", FONT_22, LIGHT_GRAY, WIDTH - 220, 76)
        draw_text(surface, f"관통 {self.player.pierce}", FONT_22, LIGHT_GRAY, WIDTH - 220, 102)

    def draw_start(self, surface):
        draw_text(surface, "Space_Defense", FONT_72, WHITE, WIDTH // 2, 110, center=True)
        guide = [
            "스테이지는 잡몹 파밍 -> 보스전 -> 상점 순서로 진행",
            "이동: 방향키 또는 WASD",
            "발사: 스페이스바",
            "상점: 마우스 클릭 구매 / Enter 다음 스테이지 / R 리롤",
            "1스테이지는 오염된 위성 또는 개조된 행성이 랜덤 등장",
            "3스테이지 보스는 몸체에만 데미지가 들어간다",
        ]
        y = 240
        for line in guide:
            draw_text(surface, line, FONT_28, LIGHT_GRAY, WIDTH // 2, y, center=True)
            y += 40

        draw_text(surface, "스페이스바를 눌러 시작", FONT_36, YELLOW, WIDTH // 2, HEIGHT - 100, center=True)

    def draw_farming(self, surface):
        for gold in self.gold_drops:
            gold.draw(surface)
        for bullet in self.player_bullets:
            bullet.draw(surface)
        for enemy in self.enemies:
            enemy.draw(surface)
        self.player.draw(surface)

        self.draw_common_hud(surface)
        draw_text(surface, f"파밍 남은 시간: {max(0, int(self.farming_timer))}초", FONT_28, GREEN, WIDTH // 2, 20, center=True)

    def draw_boss_warning(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        draw_text(surface, "보스 출현", FONT_72, RED, WIDTH // 2, HEIGHT // 2 - 90, center=True)
        name_to_show = self.current_boss_name[:self.warning_display_index]
        draw_text(surface, name_to_show, FONT_36, WHITE, WIDTH // 2, HEIGHT // 2 + 10, center=True)

    def draw_boss(self, surface):
        for gold in self.gold_drops:
            gold.draw(surface)
        for bullet in self.player_bullets:
            bullet.draw(surface)
        if self.boss:
            self.boss.draw(surface)
        self.player.draw(surface)

        self.draw_common_hud(surface)

        if self.boss:
            bar_w = 520
            bar_h = 24
            x = WIDTH // 2 - bar_w // 2
            y = 16
            pygame.draw.rect(surface, (50, 50, 60), (x, y, bar_w, bar_h), border_radius=8)
            ratio = self.boss.hp / max(1, self.boss.max_hp)
            pygame.draw.rect(surface, RED, (x, y, int(bar_w * ratio), bar_h), border_radius=8)
            pygame.draw.rect(surface, WHITE, (x, y, bar_w, bar_h), 2, border_radius=8)
            draw_text(surface, self.boss.name, FONT_28, WHITE, WIDTH // 2, y + 36, center=True)

            if self.stage == 3:
                draw_text(surface, "3스테이지 보스는 몸체만 피격됨", FONT_22, YELLOW, WIDTH // 2, y + 66, center=True)

    def draw_shop(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, (0, 0))

        draw_text(surface, "상점", FONT_72, WHITE, WIDTH // 2, 80, center=True)
        draw_text(surface, f"보유 골드: {self.player.gold}", FONT_36, YELLOW, WIDTH // 2, 140, center=True)

        box_w = 250
        box_h = 250
        start_x = WIDTH // 2 - (box_w * 3 + 40) // 2
        y = 220

        self.shop_rects = []

        for i, item in enumerate(self.shop_items):
            x = start_x + i * (box_w + 20)
            rect = pygame.Rect(x, y, box_w, box_h)
            self.shop_rects.append(rect)

            fill = (35, 40, 60)
            if i == self.shop_hover_index:
                fill = (55, 65, 95)

            pygame.draw.rect(surface, fill, rect, border_radius=14)
            pygame.draw.rect(surface, WHITE, rect, 2, border_radius=14)

            draw_text(surface, item.name, FONT_28, WHITE, x + 12, y + 14)
            draw_text(surface, item.desc, FONT_22, LIGHT_GRAY, x + 12, y + 78)
            draw_text(surface, f"가격: {item.cost}", FONT_28, YELLOW, x + 12, y + 188)

            afford = self.player.gold >= item.cost
            draw_text(surface, "클릭해서 구매", FONT_20, GREEN if afford else DARK_RED, x + 12, y + 220)

        draw_text(surface, f"R: 리롤 ({REROLL_COST} 골드)", FONT_28, CYAN, WIDTH // 2, HEIGHT - 120, center=True)
        draw_text(surface, "Enter: 다음 스테이지 진행", FONT_28, GREEN, WIDTH // 2, HEIGHT - 80, center=True)

    def draw_game_over(self, surface):
        draw_text(surface, "GAME OVER", FONT_72, RED, WIDTH // 2, HEIGHT // 2 - 40, center=True)
        draw_text(surface, "R 키를 눌러 재시작", FONT_36, WHITE, WIDTH // 2, HEIGHT // 2 + 40, center=True)

    def draw_clear(self, surface):
        draw_text(surface, "STAGE CLEAR", FONT_72, GREEN, WIDTH // 2, HEIGHT // 2 - 60, center=True)
        draw_text(surface, "최종 스테이지를 클리어했다", FONT_36, WHITE, WIDTH // 2, HEIGHT // 2 + 10, center=True)
        draw_text(surface, "R 키를 눌러 처음부터 다시 시작", FONT_28, YELLOW, WIDTH // 2, HEIGHT // 2 + 70, center=True)


def main():
    game = Game()

    while True:
        dt = CLOCK.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            game.handle_event(event)

        game.update(dt)
        game.draw(SCREEN)


if __name__ == "__main__":
    main()