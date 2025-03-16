import socket
import getpass
from tinydb import TinyDB, where
import os
from dataclasses import dataclass, asdict, field, fields
from datetime import datetime
from typing import Any, Optional


@dataclass
class Option:
    model: list[str] = field(default_factory=lambda: [
        "qwen2.5:32b", "qwen2.5-coder:32b", "llama3.3", 
        "deepseek-r1:32b", "gemma3:27b-it-q8_0"
    ])
    context_size: list[int] = field(default_factory=lambda: [
        1024, 2048, 4096, 8192, 16384])
    num_retrieve: list[int] = field(default_factory=lambda: [
        5, 10, 20, 30, 40, 50, 100])
    score_threshold: list[float] = field(default_factory=lambda: [
        round(i * 0.1, 1) for i in range(11)])

@dataclass
class Message:
    role: str
    content: str

@dataclass
class Setting:
    model: str = "qwen2.5:32b"
    context_size: int = 4096
    num_retrieve: int = 30
    score_threshold: float = 0.3

@dataclass
class Session:
    id: Optional[int] = None
    summary: str = ""
    messages: list[Message] = field(default_factory=lambda: [])

def from_dict(cls, d):
    """Convert a dictionary to a dataclass, recursively."""
    fieldtypes = {field.name: field.type for field in fields(cls)}
    args = {}
    
    for field, field_type in fieldtypes.items():
        if field in d:
            value = d[field]
            if (isinstance(value, list) and value and isinstance(value[0], dict)
                and hasattr(field_type.__args__[0], "__dataclass_fields__")):
                # If the field is a list of dataclasses, recursively convert
                # each item.
                args[field] = [
                    from_dict(field_type.__args__[0], item) for item in value]
            elif (isinstance(value, dict) 
                  and hasattr(field_type, "__dataclass_fields__")):
                args[field] = from_dict(field_type, value)
            else:
                args[field] = value
    return cls(**args)

class Client():
    def __init__(
            self,
            base_directory: str = "./resources",
            record_name: str = "client_records.json"):

        self.id = Client._get_client_id()

        folder_path = os.path.join(base_directory, self.id)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        record_directory = os.path.join(folder_path, record_name)
        # Create or load the tiny database to store the injest records.
        record_db = TinyDB(record_directory)
        self.session_table = record_db.table("session")
        self.setting_table = record_db.table("setting")

    def _get_client_id():
        """Generate a unique client ID using the user and node name."""
        user_name = getpass.getuser()
        node_name = socket.gethostname()
        return f"{user_name}@{node_name}"

    def append_message(self, role: str, content: str):
        """Add a new message to the session."""
        existing_items = self.session_table.all()
        if not existing_items:
            new_session = Session(messages=[Message(role, content)])
            self.session_table.insert(asdict(new_session))
        else:
            new_session = from_dict(Session, existing_items[-1])
            new_session.messages.append(Message(role, content))
            self.session_table.update(asdict(new_session))

    def reset_session(self):
        existing_items = self.session_table.all()
        if existing_items:
            doc_id = existing_items[-1].doc_id
            self.session_table.remove(doc_ids = [doc_id])
        self.session_table.insert(asdict(Session()))

    @property
    def session(self) -> Session:
        existing_items = self.session_table.all()
        if not existing_items:
            return Session()
        return from_dict(Session, existing_items[-1])
    
    @session.setter
    def session(self, new_session: Session):
        # Remove old sessions if there are more than X sessions.
        self.session_table.insert(asdict(new_session))

    @property
    def setting(self) -> Setting:
        existing_items = self.setting_table.all()
        if not existing_items:
            self.setting_table.insert(asdict(Setting()))
        return from_dict(Setting, self.setting_table.all()[-1])
    
    @setting.setter
    def setting(self, new_session: Setting):
        existing_items = self.setting_table.all()
        if existing_items:
            self.setting_table.update(asdict(new_session))
        else:
            self.setting_table.insert(asdict(new_session))


if __name__ == "__main__":
    client = Client()

    client.session = Session(
        id = 0, 
        summary="Hello", 
        messages= [Message(
            role="assistant",
            content="Hello! How can I assist you today?")],
        )

    client.setting = Setting(
        model="qwen2.5:32b",
        context_size=4096,
        num_retrieve=20,
        score_threshold=0.3
    )

    print(client.setting)