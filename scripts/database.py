from supabase import create_client, Client
from datetime import datetime, timezone

# Reemplaza con tus llaves de Project Settings > API en Supabase
SUPABASE_URL = "https://upqlintuxqqeqohkxwyix.supabase.co"
SUPABASE_KEY = "sb_publishable_6ot9xOXfYKPqrm3PvnEZ5A_RQOlO3kk"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
current_user = None  # Guardará la sesión del usuario actual

def registrar_usuario(email, password, username):
    """Registra un nuevo usuario y guarda su nombre de usuario."""
    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"username": username}}
        })
        global current_user
        current_user = response.user
        return True, "Registro exitoso."
    except Exception as e:
        return False, str(e)

def iniciar_sesion(email, password):
    """Inicia sesión con email y contraseña."""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        global current_user
        current_user = response.user
        return True, "Inicio de sesión correcto."
    except Exception as e:
        return False, str(e)

def obtener_perfil():
    """Obtiene las monedas, nivel y tiempos del usuario actual."""
    if not current_user:
        return None
    res = supabase.table("profiles").select("*").eq("id", current_user.id).single().execute()
    return res.data

def reclamar_recompensa_diaria():
    """Verifica si pasaron 24 horas y entrega 10 monedas."""
    perfil = obtener_perfil()
    if not perfil:
        return False, "Usuario no autenticado."

    # Parsear tiempo
    last_reward = datetime.fromisoformat(perfil["last_daily_reward"].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    
    # Calcular diferencia en horas
    horas_transcurridas = (now - last_reward).total_seconds() / 3600
    
    if horas_transcurridas >= 24:
        nuevas_monedas = perfil["coins"] + 10
        supabase.table("profiles").update({
            "coins": nuevas_monedas,
            "last_daily_reward": now.isoformat()
        }).eq("id", current_user.id).execute()
        return True, "¡Has reclamado +10 monedas diarias!"
    else:
        horas_restantes = int(24 - horas_transcurridas)
        return False, f"Vuelve en {horas_restantes} horas para tu recompensa."

def guardar_monedas_nave(monedas_ganadas):
    """Verifica los 30 min de cooldown y guarda las monedas recolectadas en la nave."""
    perfil = obtener_perfil()
    if not perfil:
        return False, "Error de sesión."

    last_ship = datetime.fromisoformat(perfil["last_ship_game"].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    minutos_transcurridos = (now - last_ship).total_seconds() / 60

    if minutos_transcurridos < 30:
        min_restantes = int(30 - minutos_transcurridos)
        return False, f"La nave está en recarga. Espera {min_restantes} min."

    # Actualizar monedas y timestamp de la nave
    nuevas_monedas = perfil["coins"] + monedas_ganadas
    supabase.table("profiles").update({
        "coins": nuevas_monedas,
        "last_ship_game": now.isoformat()
    }).eq("id", current_user.id).execute()
    
    return True, f"¡Sumaste +{monedas_ganadas} monedas a tu perfil!"

def obtener_top_mundial():
    """Obtiene los 10 jugadores con más monedas."""
    res = supabase.table("profiles") \
        .select("username, coins, level") \
        .order("coins", desc=True) \
        .limit(10) \
        .execute()
    return res.data