import webbrowser
from datetime import datetime, timezone
from supabase import Client, create_client

SUPABASE_URL = "https://upqlntuxqqeqohkxwyix.supabase.co"
SUPABASE_KEY = "sb_publishable_6ot9xOXfYKPqrm3PvnEZ5A_RQOlO3kk"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
current_user = None  # Guardará la sesión del usuario actual


def _crear_perfil_inicial(user_id, username, email):
    """Crea la fila inicial en la tabla profiles si no existe."""
    try:
        supabase.table("profiles").upsert(
            {
                "id": user_id,
                "username": username,
                "email": email,
                "coins": 50,
                "level": 1,
            }
        ).execute()
    except Exception as e:
        print(f"Error creando perfil inicial: {e}")


def registrar_usuario(email, password, username):
    """Registra un nuevo usuario, crea su perfil en la BD y guarda la sesión."""
    try:
        response = supabase.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {"data": {"username": username}},
            }
        )
        global current_user
        current_user = response.user

        if current_user:
            _crear_perfil_inicial(current_user.id, username, email)

        return True, "Registro exitoso."
    except Exception as e:
        return False, str(e)


def iniciar_sesion(email, password):
    """Inicia sesión con email y contraseña."""
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        global current_user
        current_user = response.user
        return True, "Inicio de sesión correcto."
    except Exception as e:
        return False, str(e)


def iniciar_sesion_google():
    """Abre el navegador para la autenticación de Google en Supabase."""
    try:
        data = supabase.auth.sign_in_with_oauth(
            {
                "provider": "google",
                "options": {
                    "redirect_to": "https://upqlintuxqqeqohkxwyix.supabase.co/auth/v1/callback"
                },
            }
        )
        webbrowser.open(data.url)
        return True, "Navegador abierto para Google Auth."
    except Exception as e:
        return False, str(e)


def obtener_perfil():
    """Obtiene el perfil del usuario actual sin romper el juego si falla la red."""
    if not current_user:
        return None
    try:
        res = (
            supabase.table("profiles")
            .select("*")
            .eq("id", current_user.id)
            .single()
            .execute()
        )
        return res.data
    except Exception as e:
        print(f"Error al obtener perfil: {e}")
        return None


def reclamar_recompensa_diaria():
    """Verifica si pasaron 24 horas y entrega 10 monedas."""
    perfil = obtener_perfil()
    if not perfil:
        return False, "Usuario no autenticado o error de red."

    if not perfil.get("last_daily_reward"):
        last_reward = datetime(1970, 1, 1, tzinfo=timezone.utc)
    else:
        last_reward = datetime.fromisoformat(
            perfil["last_daily_reward"].replace("Z", "+00:00")
        )

    now = datetime.now(timezone.utc)
    horas_transcurridas = (now - last_reward).total_seconds() / 3600

    if horas_transcurridas >= 24:
        nuevas_monedas = perfil.get("coins", 0) + 10
        try:
            supabase.table("profiles").update(
                {
                    "coins": nuevas_monedas,
                    "last_daily_reward": now.isoformat(),
                }
            ).eq("id", current_user.id).execute()
            return True, "¡Has reclamado +10 monedas diarias!"
        except Exception as e:
            return False, f"Error al guardar: {e}"
    else:
        horas_restantes = int(24 - horas_transcurridas)
        return False, f"Vuelve en {horas_restantes} horas para tu recompensa."


def guardar_monedas_nave(monedas_ganadas):
    """Verifica los 30 min de cooldown y guarda las monedas recolectadas."""
    perfil = obtener_perfil()
    if not perfil:
        return False, "Error de sesión o red."

    if not perfil.get("last_ship_game"):
        last_ship = datetime(1970, 1, 1, tzinfo=timezone.utc)
    else:
        last_ship = datetime.fromisoformat(
            perfil["last_ship_game"].replace("Z", "+00:00")
        )

    now = datetime.now(timezone.utc)
    minutos_transcurridos = (now - last_ship).total_seconds() / 60

    if minutos_transcurridos < 30:
        min_restantes = int(30 - minutos_transcurridos)
        return (
            False,
            f"La nave está en recarga. Espera {min_restantes} min.",
        )

    nuevas_monedas = perfil.get("coins", 0) + monedas_ganadas
    try:
        supabase.table("profiles").update(
            {"coins": nuevas_monedas, "last_ship_game": now.isoformat()}
        ).eq("id", current_user.id).execute()

        return True, f"¡Sumaste +{monedas_ganadas} monedas a tu perfil!"
    except Exception as e:
        return False, f"Error al guardar: {e}"


def obtener_top_mundial():
    """Obtiene los 10 jugadores con más monedas."""
    try:
        res = (
            supabase.table("profiles")
            .select("username, coins, level")
            .order("coins", desc=True)
            .limit(10)
            .execute()
        )
        return res.data if res.data else []
    except Exception as e:
        print(f"Error al obtener top mundial: {e}")
        return []