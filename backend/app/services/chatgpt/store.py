"""Stockage chiffré de la connexion ChatGPT, dans DATA_DIR/secrets/.

Le SDK officiel s'appuie sur le trousseau du système, absent d'un conteneur Docker.
Ici, les jetons sont chiffrés (Fernet) avec une clé générée au premier usage et rangée
à côté, lisible par le seul propriétaire. Cela évite toute fuite accidentelle (copie de la
base, sauvegarde, logs) mais ne protège pas d'une personne qui a déjà accès à la machine.
"""

import json
import os
import uuid
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel

KEY_FILE = "credentials.key"
CONNECTION_FILE = "chatgpt-connection.enc"
HOST_FILE = "chatgpt-host.json"


class Credentials(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_at: float  # horodatage Unix


class PendingRefresh(BaseModel):
    """Jetons reçus d'un rafraîchissement dont l'identité n'est pas encore vérifiée."""

    credentials: Credentials
    scopes: list[str]
    id_token: str


class Connection(BaseModel):
    client_id: str
    subject: str = ""
    email: str = ""
    name: str = ""
    scopes: list[str] = []
    credentials: Credentials | None = None
    pending_refresh: PendingRefresh | None = None
    model: str = ""


class StoreError(Exception):
    pass


class CredentialStore:
    def __init__(self, data_dir: Path) -> None:
        self.dir = data_dir / "secrets"

    def _ensure_dir(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.dir, 0o700)

    def _write_private(self, name: str, data: bytes) -> None:
        """Écriture atomique d'un fichier lisible par le seul propriétaire."""
        self._ensure_dir()
        target = self.dir / name
        temporary = target.with_suffix(target.suffix + ".tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "wb") as file:
            file.write(data)
        os.replace(temporary, target)

    def _fernet(self) -> Fernet:
        key_path = self.dir / KEY_FILE
        if not key_path.exists():
            self._write_private(KEY_FILE, Fernet.generate_key())
        return Fernet(key_path.read_bytes().strip())

    def read_secret(self, name: str) -> bytes | None:
        """Contenu déchiffré d'un fichier chiffré du dossier secrets, ou None s'il n'existe pas."""
        path = self.dir / name
        if not path.exists():
            return None
        try:
            return self._fernet().decrypt(path.read_bytes())
        except InvalidToken as exc:
            raise StoreError(f"{name} ne peut pas être déchiffré.") from exc

    def write_secret(self, name: str, data: bytes) -> None:
        self._write_private(name, self._fernet().encrypt(data))

    def host_id(self) -> str:
        """Identifiant non secret de cette installation (ext_agent_host_id)."""
        path = self.dir / HOST_FILE
        if path.exists():
            return str(json.loads(path.read_text())["host_id"])
        host_id = f"urn:uuid:{uuid.uuid4()}"
        self._write_private(HOST_FILE, json.dumps({"host_id": host_id}).encode())
        return host_id

    def load(self) -> Connection | None:
        # Un fichier illisible n'est jamais écrasé : la clé a peut-être été déplacée.
        plaintext = self.read_secret(CONNECTION_FILE)
        return None if plaintext is None else Connection.model_validate_json(plaintext)

    def save(self, connection: Connection) -> None:
        self.write_secret(CONNECTION_FILE, connection.model_dump_json().encode())
