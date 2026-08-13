import os
import random
import sys
import pygame
import pygame_gui
import database

# --- Inicialización de Pygame ---
pygame.init()

WIDTH, HEIGHT = 450, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Astro Jackpot")
clock = pygame.time.Clock()
FPS = 60

# --- Pygame GUI Manager ---
manager = pygame_gui.UIManager((WIDTH, HEIGHT))

# --- Fuentes ---
font_small = pygame.font.SysFont("Arial", 16)
font_medium = pygame.font.SysFont("Arial", 20, bold=True)
font_large = pygame.font.SysFont("Arial", 28, bold=True)

# --- Rutas e Imágenes ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "..", "img")


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


# Carga de Assets PNG
img_asteroide = load_img(IMG_DIR, "asteriod_dark.png", (90, 110))
img_button_spin = load_img(IMG_DIR, "button.png", (180, 65))
img_campana = load_img(IMG_DIR, "campana.png", (90, 110))
img_coin = load_img(IMG_DIR, "coin.png", (35, 35))
img_nave = load_img(IMG_DIR, "nave.png", (90, 110))
img_seven = load_img(IMG_DIR, "seven.png", (90, 110))
img_x3 = load_img(IMG_DIR, "x3.png", (90, 110))
img_x5 = load_img(IMG_DIR, "x5.png", (90, 110))

# Minijuego
img_nave_game = load_img(IMG_DIR, "nave.png", (50, 50))
img_asteroide_game = load_img(IMG_DIR, "asteriod_dark.png", (45, 45))

SLOT_ITEMS = [
    {"name": "nave", "img": img_nave, "mult": 50, "weight": 2},
    {"name": "seven", "img": img_seven, "mult": 20, "weight": 5},
    {"name": "x5", "img": img_x5, "mult": 10, "weight": 10},
    {"name": "x3", "img": img_x3, "mult": 5, "weight": 15},
    {"name": "campana", "img": img_campana, "mult": 3, "weight": 20},
    {"name": "asteroide", "img": img_asteroide, "mult": 0, "weight": 48},
]

# --- Estados del Juego ---
game_state = "AUTH"  # AUTH, RULETA, NAVE
auth_mode = "LOGIN"  # LOGIN o REGISTER
bet_multiplier = 1
slot_reels = [SLOT_ITEMS[0], SLOT_ITEMS[1], SLOT_ITEMS[2]]
is_spinning = False
spin_timer = 0
show_top_modal = False

user_data = {"coins": 0, "username": "Invitado"}
top_world = []

# Variables Minijuego Nave
ship_x = WIDTH // 2 - 25
ship_y = HEIGHT - 90
ship_coins_collected = 0
ship_start_time = 0
falling_asteroids = []
falling_coins_game = []


# --- Creación de Elementos GUI (Formulario Auth Corregido) ---
def build_auth_gui():
    manager.clear_and_reset()

    # Título
    pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect((25, 40), (400, 50)),
        text="ASTRO JACKPOT",
        manager=manager,
    )

    # Botón Toggle Modo
    btn_toggle = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((75, 100), (300, 40)),
        text=(
            "¿Sin cuenta? Regístrate aquí"
            if auth_mode == "LOGIN"
            else "¿Ya tienes cuenta? Inicia sesión"
        ),
        manager=manager,
    )

    # Entradas de Texto (Placeholder nativo)
    input_email = pygame_gui.elements.UITextEntryLine(
        relative_rect=pygame.Rect((50, 170), (350, 45)),
        manager=manager,
        placeholder_text="Correo electrónico",
    )

    input_password = pygame_gui.elements.UITextEntryLine(
        relative_rect=pygame.Rect((50, 230), (350, 45)),
        manager=manager,
        placeholder_text="Contraseña",
    )
    input_password.set_text_hidden(True)

    input_username = None
    if auth_mode == "REGISTER":
        input_username = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((50, 290), (350, 45)),
            manager=manager,
            placeholder_text="Nombre de usuario",
        )

    # Botón Principal
    btn_y = 350 if auth_mode == "REGISTER" else 290
    btn_submit = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((50, btn_y), (350, 50)),
        text="INGRESAR" if auth_mode == "LOGIN" else "CREAR CUENTA",
        manager=manager,
    )

    # Botón Google
    btn_google = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((50, btn_y + 60), (350, 45)),
        text="🌐 Continuar con Google",
        manager=manager,
    )

    lbl_status = pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect((25, btn_y + 115), (400, 30)),
        text="",
        manager=manager,
    )

    return {
        "toggle": btn_toggle,
        "email": input_email,
        "pass": input_password,
        "user": input_username,
        "submit": btn_submit,
        "google": btn_google,
        "status": lbl_status,
    }


auth_widgets = build_auth_gui()


# --- Funciones de Lógica ---
def sync_user():
    global user_data, top_world
    profile = database.obtener_perfil()
    if profile:
        user_data["coins"] = profile.get("coins", 0)
        user_data["username"] = profile.get("username", "Piloto")
    top_world = database.obtener_top_mundial()


def spin_slots():
    global is_spinning, spin_timer, user_data
    if user_data["coins"] >= bet_multiplier:
        user_data["coins"] -= bet_multiplier
        is_spinning = True
        spin_timer = pygame.time.get_ticks()


def check_spin_result():
    global is_spinning, user_data
    weights = [item["weight"] for item in SLOT_ITEMS]
    for i in range(3):
        slot_reels[i] = random.choices(SLOT_ITEMS, weights=weights, k=1)[0]

    if slot_reels[0] == slot_reels[1] == slot_reels[2]:
        win = slot_reels[0]["mult"] * bet_multiplier
        user_data["coins"] += win

    if database.current_user:
        try:
            database.supabase.table("profiles").update(
                {"coins": user_data["coins"]}
            ).eq("id", database.current_user.id).execute()
        except Exception as e:
            print(f"Error sincronizando saldo: {e}")
        sync_user()
    is_spinning = False


def draw_ruleta():
    screen.fill((15, 15, 25))

    # Header
    screen.blit(img_coin, (20, 25))
    txt_coins = font_large.render(str(user_data["coins"]), True, (255, 215, 0))
    screen.blit(txt_coins, (65, 27))

    txt_user = font_small.render(
        f"Piloto: {user_data['username']}", True, (200, 200, 200)
    )
    screen.blit(txt_user, (20, 70))

    # Botón TOP MUNDIAL
    btn_top = pygame.Rect(WIDTH - 140, 25, 120, 40)
    pygame.draw.rect(screen, (255, 215, 0), btn_top, border_radius=8)
    txt_top_btn = font_small.render("🏆 TOP 10", True, (0, 0, 0))
    screen.blit(
        txt_top_btn,
        (
            btn_top.centerx - txt_top_btn.get_width() // 2,
            btn_top.centery - txt_top_btn.get_height() // 2,
        ),
    )

    # Botón DESPEGAR NAVE
    btn_ship = pygame.Rect(20, 110, 410, 45)
    pygame.draw.rect(screen, (220, 50, 50), btn_ship, border_radius=8)
    txt_ship = font_medium.render("🚀 IR AL MINIJUEGO NAVE", True, (255, 255, 255))
    screen.blit(
        txt_ship,
        (
            btn_ship.centerx - txt_ship.get_width() // 2,
            btn_ship.centery - txt_ship.get_height() // 2,
        ),
    )

    # Tragamonedas (Slots Centrados)
    slot_y = 220
    gap = 15
    slot_w = 110
    start_x = (WIDTH - (3 * slot_w + 2 * gap)) // 2

    for i in range(3):
        rect = pygame.Rect(start_x + i * (slot_w + gap), slot_y, slot_w, 140)
        pygame.draw.rect(screen, (30, 30, 45), rect, border_radius=10)
        pygame.draw.rect(screen, (255, 215, 0), rect, 2, border_radius=10)

        item = slot_reels[i] if not is_spinning else random.choice(SLOT_ITEMS)
        screen.blit(item["img"], (rect.x + (slot_w - 90) // 2, rect.y + 15))

    # Multiplicadores
    btn_bets = []
    bet_y = 400
    for idx, mult in enumerate([1, 3, 5]):
        btn = pygame.Rect(80 + idx * 110, bet_y, 80, 45)
        color = (0, 200, 255) if bet_multiplier == mult else (50, 50, 70)
        pygame.draw.rect(screen, color, btn, border_radius=8)
        txt = font_medium.render(f"x{mult}", True, (255, 255, 255))
        screen.blit(
            txt,
            (
                btn.centerx - txt.get_width() // 2,
                btn.centery - txt.get_height() // 2,
            ),
        )
        btn_bets.append((btn, mult))

    # Botón GIRAR (PNG)
    btn_spin = pygame.Rect(WIDTH // 2 - 90, 480, 180, 65)
    screen.blit(img_button_spin, (btn_spin.x, btn_spin.y))

    if user_data["coins"] < bet_multiplier:
        overlay = pygame.Surface((180, 65), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (btn_spin.x, btn_spin.y))

    # Modal TOP MUNDIAL
    if show_top_modal:
        modal = pygame.Rect(30, 100, 390, 580)
        pygame.draw.rect(screen, (20, 20, 35), modal, border_radius=15)
        pygame.draw.rect(screen, (255, 215, 0), modal, 3, border_radius=15)

        txt_t = font_medium.render("RANKING MUNDIAL", True, (255, 215, 0))
        screen.blit(txt_t, (modal.centerx - txt_t.get_width() // 2, 120))

        for i, p in enumerate(top_world[:10]):
            r_txt = font_small.render(
                f"#{i+1} {p['username'][:12]}: {p['coins']} 🪙",
                True,
                (255, 255, 255),
            )
            screen.blit(r_txt, (60, 170 + i * 40))

        btn_close = pygame.Rect(modal.centerx - 50, 620, 100, 40)
        pygame.draw.rect(screen, (220, 50, 50), btn_close, border_radius=8)
        txt_c = font_small.render("CERRAR", True, (255, 255, 255))
        screen.blit(
            txt_c,
            (
                btn_close.centerx - txt_c.get_width() // 2,
                btn_close.centery - txt_c.get_height() // 2,
            ),
        )

    return btn_spin, btn_bets, btn_ship, btn_top


# --- Bucle Principal ---
running = True
while running:
    time_delta = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if game_state == "AUTH":
            manager.process_events(event)

            if event.type == pygame_gui.UI_BUTTON_START_PRESS:
                if event.ui_element == auth_widgets["toggle"]:
                    auth_mode = "REGISTER" if auth_mode == "LOGIN" else "LOGIN"
                    auth_widgets = build_auth_gui()

                elif event.ui_element == auth_widgets["submit"]:
                    email = auth_widgets["email"].get_text().strip()
                    pas = auth_widgets["pass"].get_text().strip()

                    if auth_mode == "LOGIN":
                        ok, msg = database.iniciar_sesion(email, pas)
                    else:
                        usr = auth_widgets["user"].get_text().strip() if auth_widgets["user"] else ""
                        ok, msg = database.registrar_usuario(email, pas, usr)

                    if ok:
                        sync_user()
                        manager.clear_and_reset()
                        game_state = "RULETA"
                    else:
                        auth_widgets["status"].set_text(msg)

                elif event.ui_element == auth_widgets["google"]:
                    ok, msg = database.iniciar_sesion_google()
                    auth_widgets["status"].set_text(msg)

        elif game_state == "RULETA":
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()

                if show_top_modal:
                    show_top_modal = False
                else:
                    btn_spin, btn_bets, btn_ship, btn_top = draw_ruleta()

                    if btn_top.collidepoint(mx, my):
                        top_world = database.obtener_top_mundial()
                        show_top_modal = True
                    elif btn_spin.collidepoint(mx, my) and not is_spinning:
                        spin_slots()
                    elif btn_ship.collidepoint(mx, my):
                        game_state = "NAVE"
                        ship_coins_collected = 0
                        ship_start_time = pygame.time.get_ticks()
                        falling_asteroids.clear()
                        falling_coins_game.clear()
                    else:
                        for btn, mult in btn_bets:
                            if btn.collidepoint(mx, my):
                                bet_multiplier = mult

    # Animación Spin
    if is_spinning:
        if pygame.time.get_ticks() - spin_timer > 1000:
            check_spin_result()

    # --- Renders ---
    if game_state == "AUTH":
        screen.fill((15, 15, 25))
        manager.update(time_delta)
        manager.draw_ui(screen)

    elif game_state == "RULETA":
        draw_ruleta()

    elif game_state == "NAVE":
        screen.fill((5, 5, 15))
        elapsed_sec = (pygame.time.get_ticks() - ship_start_time) // 1000

        # Arrastre para mover nave
        if pygame.mouse.get_pressed()[0]:
            mx, _ = pygame.mouse.get_pos()
            ship_x = max(0, min(WIDTH - 50, mx - 25))

        spawn_rate = max(0.02, 0.02 + (elapsed_sec * 0.006))
        if random.random() < spawn_rate:
            falling_asteroids.append(
                pygame.Rect(random.randint(0, WIDTH - 45), -45, 45, 45)
            )
        if random.random() < 0.03:
            falling_coins_game.append(
                pygame.Rect(random.randint(0, WIDTH - 35), -35, 35, 35)
            )

        screen.blit(img_nave_game, (ship_x, ship_y))
        ship_rect = pygame.Rect(ship_x, ship_y, 50, 50)

        for ast in falling_asteroids[:]:
            ast.y += 4 + (elapsed_sec // 8)
            screen.blit(img_asteroide_game, (ast.x, ast.y))
            if ast.colliderect(ship_rect):
                database.guardar_monedas_nave(ship_coins_collected)
                sync_user()
                game_state = "RULETA"
            if ast.y > HEIGHT:
                falling_asteroids.remove(ast)

        for c in falling_coins_game[:]:
            c.y += 3
            screen.blit(img_coin, (c.x, c.y))
            if c.colliderect(ship_rect):
                ship_coins_collected += 1
                falling_coins_game.remove(c)
            elif c.y > HEIGHT:
                falling_coins_game.remove(c)

        txt_hud = font_medium.render(
            f"Tiempo: {elapsed_sec}s | Monedas: {ship_coins_collected}",
            True,
            (255, 255, 255),
        )
        screen.blit(txt_hud, (20, 20))

    pygame.display.flip()

pygame.quit()
sys.exit()