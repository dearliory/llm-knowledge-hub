"""This module manages documents using the Chroma and TinyDB database."""

import glob
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from tinydb import TinyDB, where
from typing import Any
import os
import shutil

# The default embedding function used to encode documents
_DEFAULT_EMBEDDING_FUNCTION = OllamaEmbeddings(
    model="nomic-embed-text", base_url="http://localhost:11434/")


def list_collections(
        path: str = "./resources",
        prefix: str = "chroma_db_",
    ) -> list[str]:
    """List the collection names from the given directory.
    
    For example, when encountering a folder name ./resources/chroma_db_file,
    this function will return a item only contains the collection name "file"
    """
    get_name_fn = lambda p: os.path.split(p)[-1].removeprefix(prefix)
    folder_paths = glob.glob(os.path.join(path, prefix + "*"))
    return list(map(get_name_fn, folder_paths))


class Collection():
    """The collection class that manages the content and injest records.

    Parameters:
        name: The collection name.
        content: The content in a Chorma DB collection.
        record: The injest record in a TinyDB table.
    """
    def __init__(
            self,
            client_id: str,
            name: str,
            base_directory: str = "./resources",
            content_persist_prefix: str = "chroma_db_",
            record_persist_name: str = "injest_records.json",
            embedding_function = _DEFAULT_EMBEDDING_FUNCTION):
        folder_path = os.path.join(base_directory, client_id)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        self._content_persist_directory = os.path.join(
            folder_path, content_persist_prefix + name)
        self._record_persist_directory = os.path.join(
            folder_path, record_persist_name)
        
        self.name = name

        # Create or load the tiny database to store the injest records.
        self._injest_record_db = TinyDB(self._record_persist_directory)
        self.record = self._injest_record_db.table(name)

        # Create or load the collections from the Chroma database.
        self.content = Chroma(
                collection_name=name,
                embedding_function=embedding_function,
                persist_directory=self._content_persist_directory,
        )

    def contains(self, **kwargs) -> bool:
        """Check if the input key-value pair is already contained in the table.
        
        Usually used to determine if a file is already processed or not. 
        This function supprts mutliple key-value matches, which returns True if
        any key-value pair is found in the injest record data table."""
        for key, value in kwargs.items():
            if bool(self.record.search(where(key) == value)):
                return True
        return False

    def add_record(
            self,
            content_params: dict[str:Any],
            record_params: dict[str:Any]):
        """Add record to the content and record.

        For example:
            content_params defines the arguments for the chroma_db insertion.
            chroma_db.add_texts(
                texts = texts,
                metadatas = metadatas
            )
            and record_params defines the arguments for the injested records.
            injested_record.insert({
                "url": file_path,
                "title": title
            })
        """
        self.content.add_texts(**content_params)
        self.record.insert(record_params)

    def clear(self):
        # Drop the table from TinyDB
        self._injest_record_db.drop_table(self.name)

        # Remove the content persist directory
        shutil.rmtree(self._content_persist_directory, ignore_errors=True)


if __name__ == "__main__":
    # Clear the default databases
    Collection("file").clear()