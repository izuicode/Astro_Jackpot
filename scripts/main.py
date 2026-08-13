import pygame
import random
import sys
import os
from datetime import datetime, timezone
import database  # Tu archivo database.py en la misma carpeta

# --- Inicialización de Pygame ---
pygame.init()
WIDTH, HEIGHT = 900, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Astro Jackpot")
clock = pygame.time.Clock()
FPS = 60

# --- Cargar Fuentes ---
font_small = pygame.font.SysFont("Arial", 18)
font_medium = pygame.font.SysFont("Arial", 24, bold=True)
font_large = pygame.font.SysFont("Arial", 36, bold=True)

# --- Definición de Rutas de Imágenes ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "..", "img")
BG_DIR = os.path.join(BASE_DIR, "..", "img_background")

def load_img(folder, filename, size=None):
    path = os.path.join(folder, filename)
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except Exception as e:
        print(f"Error cargando {path}: {e}")
        surf = pygame.Surface(size if size else (50, 50))
        surf.fill((255, 0, 255))
        return surf

# --- Cargar Assets ---
img_asteroide = load_img(IMG_DIR, "asteriod_dark.png", (120, 150))
img_button = load_img(IMG_DIR, "button.png", (160, 50))
img_campana = load_img(IMG_DIR, "campana.png", (120, 150))
img_coin = load_img(IMG_DIR, "coin.png", (40, 40))
img_nave = load_img(IMG_DIR, "nave.png", (120, 150))
img_seven = load_img(IMG_DIR, "seven.png", (120, 150))
img_x3 = load_img(IMG_DIR, "x3.png", (120, 150))
img_x5 = load_img(IMG_DIR, "x5.png", (120, 150))

# Nave recortada para el minijuego
img_nave_game = load_img(IMG_DIR, "nave.png", (60, 60))
img_asteroide_game = load_img(IMG_DIR, "asteriod_dark.png", (50, 50))

# Mapeo de Símbolos y Pagos Base
SLOT_ITEMS = [
    {"name": "nave", "img": img_nave, "mult": 50, "weight": 2},
    {"name": "seven", "img": img_seven, "mult": 20, "weight": 5},
    {"name": "x5", "img": img_x5, "mult": 10, "weight": 10},
    {"name": "x3", "img": img_x3, "mult": 5, "weight": 15},
    {"name": "campana", "img": img_campana, "mult": 3, "weight": 20},
    {"name": "asteroide", "img": img_asteroide, "mult": 0, "weight": 48}
]

# --- Variables de Estado del Juego ---
game_state = "LOGIN" # LOGIN, RULETA, NAVE
bet_multiplier = 1   # Multiplicador de Apuesta: 1, 3 o 5
slot_reels = [SLOT_ITEMS[0], SLOT_ITEMS[1], SLOT_ITEMS[2]]
is_spinning = False
spin_timer = 0

# Sesión local (Sincronizada con Supabase)
user_data = {"coins": 50, "username": "Invitado", "last_ship": None}
top_world = []

# Variables Minijuego Nave
ship_x = WIDTH // 2
ship_y = HEIGHT - 80
ship_speed = 8
ship_coins_collected = 0
ship_start_time = 0
falling_asteroids = []
falling_coins_game = []

# --- Funciones de Login y Sync ---
def sync_user():
    global user_data, top_world
    profile = database.obtener_perfil()
    if profile:
        user_data["coins"] = profile["coins"]
        user_data["username"] = profile["username"]
        user_data["last_ship"] = profile["last_ship_game"]
    top_world = database.obtener_top_mundial()

# --- Lógica de la Tragamonedas ---
def spin_slots():
    global is_spinning, spin_timer, user_data
    cost = bet_multiplier
    if user_data["coins"] >= cost:
        user_data["coins"] -= cost
        is_spinning = True
        spin_timer = pygame.time.get_ticks()

def check_spin_result():
    global is_spinning, user_data
    # Selección ponderada por pesos
    weights = [item["weight"] for item in SLOT_ITEMS]
    for i in range(3):
        slot_reels[i] = random.choices(SLOT_ITEMS, weights=weights, k=1)[0]
    
    # Evaluar premio si los 3 son iguales
    if slot_reels[0] == slot_reels[1] == slot_reels[2]:
        win = slot_reels[0]["mult"] * bet_multiplier
        user_data["coins"] += win
    
    # Guardar en base de datos al finalizar giro
    if database.current_user:
        database.supabase.table("profiles").update({"coins": user_data["coins"]}).eq("id", database.current_user.id).execute()
        sync_user()
        
    is_spinning = False

# --- Renderizado de Pantallas ---
def draw_login():
    screen.fill((20, 20, 35))
    txt = font_large.render("ASTRO JACKPOT", True, (255, 215, 0))
    screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 100))
    
    btn_login = pygame.Rect(WIDTH//2 - 120, 250, 240, 50)
    pygame.draw.rect(screen, (0, 180, 100), btn_login, border_radius=10)
    txt_btn = font_medium.render("ENTRAR / REGISTRO", True, (255, 255, 255))
    screen.blit(txt_btn, (btn_login.centerx - txt_btn.get_width()//2, btn_login.centery - txt_btn.get_height()//2))
    return btn_login

def draw_ruleta():
    screen.fill((15, 15, 25))
    
    # 1. Header (Usuario y Monedas)
    txt_user = font_medium.render(f"Piloto: {user_data['username']}", True, (255, 255, 255))
    screen.blit(txt_user, (30, 20))
    
    screen.blit(img_coin, (30, 60))
    txt_coins = font_large.render(str(user_data["coins"]), True, (255, 215, 0))
    screen.blit(txt_coins, (80, 62))

    # 2. slots (Contenedor de los 3 símbolos)
    start_x = 100
    for i in range(3):
        rect = pygame.Rect(start_x + i * 150, 200, 130, 160)
        pygame.draw.rect(screen, (40, 40, 60), rect, border_radius=10)
        pygame.draw.rect(screen, (255, 215, 0), rect, 3, border_radius=10)
        
        item = slot_reels[i] if not is_spinning else random.choice(SLOT_ITEMS)
        screen.blit(item["img"], (rect.x + 5, rect.y + 5))

    # 3. Botones de Apuesta (x1, x3, x5)
    btn_bets = []
    for idx, mult in enumerate([1, 3, 5]):
        btn = pygame.Rect(100 + idx * 90, 400, 70, 40)
        color = (0, 200, 255) if bet_multiplier == mult else (60, 60, 80)
        pygame.draw.rect(screen, color, btn, border_radius=8)
        txt = font_medium.render(f"x{mult}", True, (255, 255, 255))
        screen.blit(txt, (btn.centerx - txt.get_width()//2, btn.centery - txt.get_height()//2))
        btn_bets.append((btn, mult))

    # 4. Botón SPIN
    btn_spin = pygame.Rect(100, 470, 250, 60)
    can_spin = user_data["coins"] >= bet_multiplier and not is_spinning
    color_spin = (0, 220, 100) if can_spin else (100, 100, 100)
    pygame.draw.rect(screen, color_spin, btn_spin, border_radius=12)
    txt_spin = font_large.render("GIRAR", True, (0, 0, 0) if can_spin else (200, 200, 200))
    screen.blit(txt_spin, (btn_spin.centerx - txt_spin.get_width()//2, btn_spin.centery - txt_spin.get_height()//2))

    # 5. Botón Minijuego Nave (Arriba izquierda / Condicional)
    btn_ship = pygame.Rect(30, 120, 200, 45)
    pygame.draw.rect(screen, (220, 50, 50), btn_ship, border_radius=8)
    txt_ship = font_small.render("DESPEGAR NAVE", True, (255, 255, 255))
    screen.blit(txt_ship, (btn_ship.centerx - txt_ship.get_width()//2, btn_ship.centery - txt_ship.get_height()//2))

    # 6. Lateral Derecho: Top Mundial
    pygame.draw.rect(screen, (25, 25, 40), (580, 20, 290, 600), border_radius=12)
    pygame.draw.rect(screen, (255, 215, 0), (580, 20, 290, 600), 2, border_radius=12)
    
    txt_top = font_medium.render("TOP 10 MUNDIAL", True, (255, 215, 0))
    screen.blit(txt_top, (650, 40))
    
    for i, p in enumerate(top_world[:10]):
        row_txt = font_small.render(f"#{i+1} {p['username'][:10]}: {p['coins']} 🪙", True, (220, 220, 220))
        screen.blit(row_txt, (600, 90 + i * 45))

    return btn_spin, btn_bets, btn_ship

# --- Bucle Principal ---
running = True
while running:
    clock.tick(FPS)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            
            if game_state == "LOGIN":
                btn_login = draw_login()
                if btn_login.collidepoint(mx, my):
                    # Demo Login - En prod usarás un formulario de texto
                    success, msg = database.iniciar_sesion("test@astro.com", "123456")
                    if not success:
                        database.registrar_usuario("test@astro.com", "123456", "AstroPlayer")
                        database.iniciar_sesion("test@astro.com", "123456")
                    sync_user()
                    game_state = "RULETA"

            elif game_state == "RULETA":
                btn_spin, btn_bets, btn_ship = draw_ruleta()
                
                # Botón Spin
                if btn_spin.collidepoint(mx, my) and not is_spinning:
                    spin_slots()
                
                # Multiplicadores
                for btn, mult in btn_bets:
                    if btn.collidepoint(mx, my):
                        bet_multiplier = mult
                
                # Ir a Nave
                if btn_ship.collidepoint(mx, my):
                    # Iniciar Minijuego
                    game_state = "NAVE"
                    ship_coins_collected = 0
                    ship_start_time = pygame.time.get_ticks()
                    falling_asteroids.clear()
                    falling_coins_game.clear()

    # --- Actualizar Animación Spin ---
    if is_spinning:
        if pygame.time.get_ticks() - spin_timer > 1200: # 1.2 segundos girando
            check_spin_result()

    # --- Renderizado según Estado ---
    if game_state == "LOGIN":
        draw_login()
    elif game_state == "RULETA":
        draw_ruleta()
    elif game_state == "NAVE":
        # Lógica Nave con aceleración de asteroides
        screen.fill((5, 5, 15))
        elapsed_sec = (pygame.time.get_ticks() - ship_start_time) // 1000
        
        # Mover nave con teclado
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and ship_x > 0: ship_x -= ship_speed
        if keys[pygame.K_RIGHT] and ship_x < WIDTH - 60: ship_x += ship_speed
        
        # Spawner progresivo de Asteroides
        spawn_rate = max(0.02, 0.02 + (elapsed_sec * 0.005)) # Aumenta la densidad
        if random.random() < spawn_rate:
            falling_asteroids.append(pygame.Rect(random.randint(0, WIDTH-50), -50, 50, 50))
            
        if random.random() < 0.03:
            falling_coins_game.append(pygame.Rect(random.randint(0, WIDTH-30), -30, 30, 30))

        # Dibujar Nave
        screen.blit(img_nave_game, (ship_x, ship_y))
        ship_rect = pygame.Rect(ship_x, ship_y, 50, 50)

        # Mover y dibujar Asteroides
        for ast in falling_asteroids[:]:
            ast.y += 4 + (elapsed_sec // 10) # Caen más rápido
            screen.blit(img_asteroide_game, (ast.x, ast.y))
            if ast.colliderect(ship_rect): # Chocar = Fin de la partida
                database.guardar_monedas_nave(ship_coins_collected)
                sync_user()
                game_state = "RULETA"
            if ast.y > HEIGHT: falling_asteroids.remove(ast)

        # Mover y dibujar Monedas
        for c in falling_coins_game[:]:
            c.y += 3
            screen.blit(img_coin, (c.x, c.y))
            if c.colliderect(ship_rect):
                ship_coins_collected += 1
                falling_coins_game.remove(c)
            elif c.y > HEIGHT: falling_coins_game.remove(c)

        # HUD Nave
        txt_hud = font_medium.render(f"Tiempo: {elapsed_sec}s  |  Monedas: {ship_coins_collected}", True, (255, 255, 255))
        screen.blit(txt_hud, (20, 20))

    pygame.display.flip()

pygame.quit()
sys.exit()