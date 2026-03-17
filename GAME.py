import pygame
import sys
import math
import random

pygame.init()

# 화면 설정
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Shape Eat Game")

# 색상
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARKGRAY = (150, 150, 150)
RED = (255, 80, 80)

# 폰트
font = pygame.font.SysFont(None, 36)

# 시계
clock = pygame.time.Clock()

# 플레이어 위치
x = 400
y = 300
speed = 5
player_size = 40

# 도형 종류: 0=별, 1=원, 2=네모
shape_type = 0

# 점수
score = 0

# 버튼 영역
button_rect = pygame.Rect(620, 20, 150, 50)

# 먹이 설정
food_radius = 10

def make_food():
    food_x = random.randint(30, 770)
    food_y = random.randint(80, 570)
    return food_x, food_y

food_x, food_y = make_food()

def draw_star(surface, color, center, outer_radius, inner_radius, points=5):
    cx, cy = center
    star_points = []

    for i in range(points * 2):
        angle = math.radians(i * 180 / points - 90)
        radius = outer_radius if i % 2 == 0 else inner_radius

        px = cx + math.cos(angle) * radius
        py = cy + math.sin(angle) * radius
        star_points.append((px, py))

    pygame.draw.polygon(surface, color, star_points)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if button_rect.collidepoint(event.pos):
                shape_type = (shape_type + 1) % 3

    # 방향키 입력
    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:
        x -= speed
    if keys[pygame.K_RIGHT]:
        x += speed
    if keys[pygame.K_UP]:
        y -= speed
    if keys[pygame.K_DOWN]:
        y += speed

    # 화면 밖 제한
    if x < player_size:
        x = player_size
    if x > 800 - player_size:
        x = 800 - player_size
    if y < player_size:
        y = player_size
    if y > 600 - player_size:
        y = 600 - player_size

    # 먹이 충돌 판정
    distance = math.sqrt((x - food_x) ** 2 + (y - food_y) ** 2)
    if distance < player_size + food_radius:
        score += 1
        food_x, food_y = make_food()

    # 화면 그리기
    screen.fill(WHITE)

    # 플레이어 도형 그리기
    if shape_type == 0:
        draw_star(screen, BLUE, (x, y), 40, 18)
        shape_name = "STAR"
    elif shape_type == 1:
        pygame.draw.circle(screen, BLUE, (x, y), 40)
        shape_name = "CIRCLE"
    else:
        pygame.draw.rect(screen, BLUE, (x - 40, y - 40, 80, 80))
        shape_name = "SQUARE"

    # 먹이 그리기
    pygame.draw.circle(screen, RED, (food_x, food_y), food_radius)

    # 버튼 그리기
    mouse_pos = pygame.mouse.get_pos()
    if button_rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, DARKGRAY, button_rect)
    else:
        pygame.draw.rect(screen, GRAY, button_rect)

    pygame.draw.rect(screen, BLACK, button_rect, 2)

    button_text = font.render("Change", True, BLACK)
    screen.blit(button_text, (button_rect.x + 25, button_rect.y + 10))

    # 정보 표시
    info_text = font.render(f"Shape: {shape_name}", True, BLACK)
    score_text = font.render(f"Score: {score}", True, BLACK)

    screen.blit(info_text, (20, 20))
    screen.blit(score_text, (20, 60))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()