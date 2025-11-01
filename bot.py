# bot.py — Discord key bot with timestamps and admin tools.
# Python 3.10+. pip install -U discord.py

import os, json, tempfile, asyncio, io, csv
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

import discord
from discord import app_commands
from discord.ui import View, button, Button

DATA_DIR = os.getenv("DATA_DIR", ".")
KEYS_PATH = os.path.join(DATA_DIR, "keys.json")
CLAIMS_PATH = os.path.join(DATA_DIR, "claims.json")
REQUESTS_PATH = os.path.join(DATA_DIR, "requests.json")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_LOG_CHANNEL_ID = os.getenv("ADMIN_LOG_CHANNEL_ID")  # optional

DEFAULT_MIN_DAYS = 7
DEFAULT_MODE = "account"  # "account" | "guild"

if not DISCORD_TOKEN:
    raise RuntimeError("Set DISCORD_TOKEN")

def _atomic_write(path: str, payload) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=os.path.dirname(path) or ".") as tf:
        json.dump(payload, tf, indent=2, ensure_ascii=False)
        tmp = tf.name
    os.replace(tmp, path)

def _load(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def format_date(iso_str: str) -> str:
    """Convert ISO timestamp to readable format: '1 November 2025 at 22:22'"""
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        month_names = ["January", "February", "March", "April", "May", "June", 
                       "July", "August", "September", "October", "November", "December"]
        return f"{dt.day} {month_names[dt.month - 1]} {dt.year} at {dt.hour:02d}:{dt.minute:02d}"
    except Exception:
        return iso_str

class KeyStore:
    def __init__(self):
        self._lock = asyncio.Lock()
        data = _load(KEYS_PATH, {"pool": [], "config": {"min_days": DEFAULT_MIN_DAYS, "mode": DEFAULT_MODE}})
        self._pool: List[str] = list(dict.fromkeys([k.strip() for k in data.get("pool", []) if k.strip()]))
        self._config = {
            "min_days": int(data.get("config", {}).get("min_days", DEFAULT_MIN_DAYS)),
            "mode": data.get("config", {}).get("mode", DEFAULT_MODE),
        }
        # claims: { user_id: {"key": str, "claimed_at": iso } }
        self._claims: Dict[str, Dict[str, str]] = _load(CLAIMS_PATH, {})
        # requests: { user_id: {"last_requested_at": iso } }
        self._requests: Dict[str, Dict[str, str]] = _load(REQUESTS_PATH, {})
        
        # MIGRATION: old schema "user_id": "key" -> new schema "user_id": {"key": "...", "claimed_at": "..."}
        if self._claims:
            sample = next(iter(self._claims.values()))
            if isinstance(sample, str):
                migrated = {uid: {"key": k, "claimed_at": now_iso()} for uid, k in self._claims.items()}
                self._claims = migrated
                self._save_all()

    def _save_all(self):
        _atomic_write(KEYS_PATH, {"pool": self._pool, "config": self._config})
        _atomic_write(CLAIMS_PATH, self._claims)
        _atomic_write(REQUESTS_PATH, self._requests)

    # keys
    async def add_keys(self, keys: List[str]) -> int:
        keys = [k.strip() for k in keys if k.strip()]
        async with self._lock:
            used = {v["key"] for v in self._claims.values()}
            existing = set(self._pool) | used
            new = [k for k in keys if k not in existing]
            if new:
                self._pool.extend(new)
                self._save_all()
            return len(new)

    def available_count(self) -> int: return len(self._pool)
    def list_pool(self) -> List[str]: return list(self._pool)

    # requests
    async def record_request(self, user_id: int):
        async with self._lock:
            self._requests[str(user_id)] = {"last_requested_at": now_iso()}
            self._save_all()

    def last_request(self, user_id: int) -> Optional[str]:
        rec = self._requests.get(str(user_id))
        return rec.get("last_requested_at") if rec else None

    # claims
    async def has_claimed(self, user_id: int) -> bool:
        return str(user_id) in self._claims

    async def get_claim(self, user_id: int) -> Optional[Dict[str, str]]:
        return self._claims.get(str(user_id))

    async def claim(self, user_id: int) -> Optional[str]:
        async with self._lock:
            if str(user_id) in self._claims or not self._pool:
                return None
            key = self._pool.pop(0)
            self._claims[str(user_id)] = {"key": key, "claimed_at": now_iso()}
            self._save_all()
            return key

    async def revoke_claim(self, user_id: int, return_to_pool: bool = True) -> Optional[str]:
        async with self._lock:
            entry = self._claims.pop(str(user_id), None)
            if not entry:
                return None
            key = entry["key"]
            if return_to_pool and key not in self._pool:
                self._pool.insert(0, key)
            self._save_all()
            return key

    async def assign_key_to_user(self, user_id: int, key: str) -> bool:
        async with self._lock:
            uid = str(user_id)
            if uid in self._claims:
                return False
            if key in self._pool:
                self._pool.remove(key)
            # prevent assigning already-claimed key
            for v in self._claims.values():
                if v["key"] == key:
                    return False
            self._claims[uid] = {"key": key, "claimed_at": now_iso()}
            self._save_all()
            return True

    async def remove_key(self, key: str) -> bool:
        async with self._lock:
            changed = False
            if key in self._pool:
                self._pool = [k for k in self._pool if k != key]
                changed = True
            for uid, v in list(self._claims.items()):
                if v["key"] == key:
                    del self._claims[uid]
                    changed = True
            if changed:
                self._save_all()
            return changed

    def list_claims(self) -> Dict[str, Dict[str, str]]:
        return dict(self._claims)

    def get_config(self) -> Dict[str, str | int]:
        return dict(self._config)

    async def set_config(self, *, min_days: Optional[int] = None, mode: Optional[str] = None):
        async with self._lock:
            if min_days is not None:
                self._config["min_days"] = int(min_days)
            if mode is not None:
                if mode not in ("account", "guild"):
                    raise ValueError("mode must be 'account' or 'guild'")
                self._config["mode"] = mode
            self._save_all()

store = KeyStore()

intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

async def admin_log(guild: Optional[discord.Guild], text: str):
    if not ADMIN_LOG_CHANNEL_ID:
        return
    try:
        chan = bot.get_channel(int(ADMIN_LOG_CHANNEL_ID))
        if chan:  # pyright: ignore[reportOptionalMemberAccess]
            await chan.send(text)  # pyright: ignore[reportOptionalMemberAccess]
    except Exception:
        pass

# ---------- User-facing success message (French) ----------
DOWNLOAD_LINK = "https://mega.nz/folder/ZloHhDoT#22Sn1h2b2scwINgPyVpZsw"
def success_message(key: str) -> str:
    return (
        "Bonjour,\n\n"
        "Voici votre clé de licence 🎁 :\n\n"
        f"{key}\n\n"
        "Merci d’avoir essayé notre service ! 😄\n\n"
        "Nous espérons que vous apprécierez l’expérience.\n\n"
        "⚠️ Remarque : Voici votre programme de téléchargement\n\n"
        f"{DOWNLOAD_LINK}\n\n"
        "N’hésitez pas à nous contacter si vous avez besoin d’aide.\n\n"
        "À bientôt,\n"
        "Azec Unlock"
    )

class TryView(View):
    def __init__(self): super().__init__(timeout=None)

    @button(label="Try", style=discord.ButtonStyle.success, custom_id="trial:try")
    async def try_button(self, interaction: discord.Interaction, _: Button):
        await store.record_request(interaction.user.id)

        cfg = store.get_config()
        min_days = int(cfg.get("min_days", DEFAULT_MIN_DAYS))
        mode = str(cfg.get("mode", DEFAULT_MODE))
        delta = timedelta(days=min_days)
        now = datetime.now(timezone.utc)

        if mode == "guild":
            if not interaction.guild:
                await interaction.response.send_message("Action uniquement dans un serveur.", ephemeral=True)
                return
            member = interaction.guild.get_member(interaction.user.id) or await interaction.guild.fetch_member(interaction.user.id)
            joined_at = getattr(member, "joined_at", None)
            if not joined_at or (now - joined_at) < delta:
                await interaction.response.send_message(
                    f"Condition non remplie. Vous devez être sur ce serveur depuis au moins {min_days} jour(s).",
                    ephemeral=True,
                )
                return
        else:
            created_at = getattr(interaction.user, "created_at", None)
            if not created_at or (now - created_at) < delta:
                await interaction.response.send_message(
                    f"Condition non remplie. Votre compte doit avoir au moins {min_days} jour(s).",
                    ephemeral=True,
                )
                return

        if await store.has_claimed(interaction.user.id):
            prev = await store.get_claim(interaction.user.id)
            # Robust handling of both old (string) and new (dict) format
            if prev and isinstance(prev, dict):
                k = prev.get("key", "N/A")
                ca = prev.get("claimed_at", "N/A")
            else:
                k = str(prev) if prev else "N/A"
                ca = "N/A"
            await interaction.response.send_message(
                f"Vous avez déjà une clé.\nVotre clé : `{k}`\nDate d’attribution : `{ca}`",
                ephemeral=True,
            )
            return

        key = await store.claim(interaction.user.id)
        if not key:
            await interaction.response.send_message("Aucune clé disponible pour le moment.", ephemeral=True)
            return

        await interaction.response.send_message(success_message(key), ephemeral=True)
        await admin_log(interaction.guild, f"{interaction.user} ({interaction.user.id}) claimed key at {now_iso()}")

# --------- Commands ---------
def admin_only():
    return app_commands.checks.has_permissions(administrator=True)

@tree.command(name="posttrial", description="Post the Try button")
@admin_only()
async def posttrial(interaction: discord.Interaction):
    await interaction.response.send_message("Cliquez **Try** pour demander une clé si vous êtes éligible.", view=TryView())

@tree.command(name="addkeys", description="Add keys separated by commas or new lines")
@admin_only()
async def addkeys(interaction: discord.Interaction, keys: str):
    parts = [p.strip() for line in keys.splitlines() for p in line.split(",")]
    added = await store.add_keys(parts)
    await interaction.response.send_message(f"Ajouté: {added}. Stock: {store.available_count()}", ephemeral=True)

@tree.command(name="mykey", description="Show your key")
async def mykey(interaction: discord.Interaction):
    c = await store.get_claim(interaction.user.id)
    if not c:
        await interaction.response.send_message("Aucune clé attribuée.", ephemeral=True); return
    req = store.last_request(interaction.user.id)
    claimed_fmt = format_date(c['claimed_at'])
    req_fmt = format_date(req) if req else "Never"
    await interaction.response.send_message(
        f"**Your Key**\nKey: `{c['key']}`\nClaimed: {claimed_fmt}\nLast request: {req_fmt}",
        ephemeral=True,
    )

@tree.command(name="listclaims", description="List claims with dates (admin)")
@admin_only()
async def listclaims(interaction: discord.Interaction, attach: bool = False):
    claims = store.list_claims()
    if not claims:
        await interaction.response.send_message("Aucune attribution.", ephemeral=True); return

    rows = []
    for uid, entry in claims.items():
        key, claimed_at = entry["key"], entry["claimed_at"]
        req = store.last_request(int(uid))
        name = uid
        try:
            user = await bot.fetch_user(int(uid))
            name = f"{user} ({uid})"
        except Exception:
            name = f"{uid}"
        rows.append((name, key, claimed_at, req or ""))

    if not attach and len(rows) <= 20:
        formatted_rows = []
        for i, (n, k, ca, rq) in enumerate(rows):
            claimed_fmt = format_date(ca)
            requested_fmt = format_date(rq) if rq else "Never"
            formatted_rows.append(f"{i+1}. **{n}**\n   Key: `{k}`\n   Claimed: {claimed_fmt}\n   Last request: {requested_fmt}")
        text = "\n\n".join(formatted_rows)
        await interaction.response.send_message(text, ephemeral=True)
    else:
        bio = io.StringIO()
        w = csv.writer(bio)
        w.writerow(["user", "key", "claimed_at", "last_requested_at"])
        for r in rows: w.writerow(r)
        data = io.BytesIO(bio.getvalue().encode("utf-8"))
        await interaction.response.send_message("Claims export.", file=discord.File(fp=data, filename="claims.csv"), ephemeral=True)

@tree.command(name="listkeys", description="List available keys (admin)")
@admin_only()
async def listkeys(interaction: discord.Interaction, attach: bool = False):
    pool = store.list_pool()
    if not pool:
        await interaction.response.send_message("Aucune clé en stock.", ephemeral=True); return
    if not attach and len(pool) <= 20:
        await interaction.response.send_message("Clés disponibles:\n" + "\n".join(f"{i+1}. `{k}`" for i,k in enumerate(pool)), ephemeral=True)
    else:
        data = io.BytesIO("\n".join(pool).encode("utf-8"))
        await interaction.response.send_message("Export des clés.", file=discord.File(fp=data, filename="keys_pool.txt"), ephemeral=True)

@tree.command(name="revoke", description="Revoke a user's claim (admin)")
@admin_only()
async def revoke(interaction: discord.Interaction, user: discord.User, return_to_pool: bool = True):
    key = await store.revoke_claim(user.id, return_to_pool)
    if not key:
        await interaction.response.send_message("Cet utilisateur n’a pas de clé.", ephemeral=True); return
    await interaction.response.send_message(f"Révoquée: `{key}` de {user}. Retour au stock: {return_to_pool}", ephemeral=True)

@tree.command(name="assign", description="Assign a key to a user (admin)")
@admin_only()
async def assign(interaction: discord.Interaction, user: discord.User, key: str):
    # prevent assigning already-claimed key
    for v in store.list_claims().values():
        if v["key"] == key:
            await interaction.response.send_message("Clé déjà attribuée.", ephemeral=True); return
    ok = await store.assign_key_to_user(user.id, key)
    if not ok:
        await interaction.response.send_message("Échec de l’attribution.", ephemeral=True); return
    await interaction.response.send_message(f"Attribué `{key}` à {user}.", ephemeral=True)

@tree.command(name="removekey", description="Remove a key from pool or claims (admin)")
@admin_only()
async def removekey(interaction: discord.Interaction, key: str):
    ok = await store.remove_key(key)
    await interaction.response.send_message("Supprimée." if ok else "Clé introuvable.", ephemeral=True)

@tree.command(name="setdays", description="Set minimum required days (admin)")
@admin_only()
async def setdays(interaction: discord.Interaction, days: int):
    if days < 0 or days > 3650:
        await interaction.response.send_message("Valeur invalide.", ephemeral=True); return
    await store.set_config(min_days=days)
    await interaction.response.send_message(f"Seuil réglé sur {days} jour(s).", ephemeral=True)

@tree.command(name="setmode", description="Set check mode: account or guild (admin)")
@admin_only()
async def setmode(interaction: discord.Interaction, mode: str):
    mode = mode.lower()
    if mode not in ("account", "guild"):
        await interaction.response.send_message("Mode invalide.", ephemeral=True); return
    await store.set_config(mode=mode)
    await interaction.response.send_message(f"Mode: {mode}", ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(TryView())
    try: await tree.sync()
    except Exception: pass
    print(f"Logged in as {bot.user} ({bot.user.id})")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
