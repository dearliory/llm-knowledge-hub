"""Load documents into database from a local directory."""
import os
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import pandas as pd
from pathlib import Path

import database


def _load_xlsx(file_path: str) -> list[Document]:
    xls = pd.ExcelFile(file_path)
    docs = []
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        if df.empty:
            continue
        doc = Document(
            page_content=df.to_json(orient="records"),
            metadata={"sheet_name": sheet_name},
        )
        docs.append(doc)
    return docs


def load_file(file_path: str) -> list[Document]:
    """Load a file into Document objects"""
    if not file_path:
        return []
    file_name = os.path.basename(file_path)
    extension = os.path.splitext(file_name)[-1].lower()
    if extension == ".pdf":
        return PyMuPDFLoader(file_path=file_path).load()
    elif extension == ".xlsx":
        return _load_xlsx(file_path)
    raise NotImplementedError(f"The file type {extension} is not supported.")


def split_docs(
        documents: list[Document],
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[Document]:
    """Split documents into chunks."""
    if chunk_size == 0:
        return documents
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    ).split_documents(documents=documents)


def process_file(
        file_path: str,
        collection: database.Collection,
        chunk_size: int = 2048,
        chunk_overlap: int = 64):
    if collection.contains(url=file_path):
        print(f"The file {file_path} is already injested.")
        return

    docs = load_file(file_path)
    if not docs:
        print("The document is empty, skip.")
        return
    chunks = split_docs(docs, chunk_size, chunk_overlap)
    filtered_chunks = filter_complex_metadata(chunks)
    texts = list(map(lambda c: c.page_content, filtered_chunks))
    # TODO: move to logging
    print("\t num chunks: " + str(len(texts)))

    if not texts:
        print(f"No content found in the file {file_path}.")
        return

    filename = os.path.basename(file_path)
    title = os.path.splitext(filename)[0]
    metadatas = [{"title": title, "url": file_path}] * len(texts)

    collection.add_record(
        content_params={
            "texts": texts,
            "metadatas": metadatas,
        },
        record_params={
            "url": file_path,
            "title": title,
        },
    )


def sanitize_table_name(table_name: str) -> str:
    """Sanitizes the given table name by replacing spaces (' ') with 
    underscores ('_') and sequences of dots ('..') with single 
    underscores ('_').

    Args:
        table_name (str): The original vector table name to be sanitized.

    Returns:
        str: The sanitized vector table name.
    """
    return table_name.replace('..', '_').replace(' ', '_')


def add_folder(client_id: str, folder_path: str):
    file_paths = Path(folder_path).rglob("*.[pP][dD][fF]")

    name = os.path.split(folder_path)[-1]
    sanitized_name = sanitize_table_name(name)
    print(f"Connect to vector store with the name \"{sanitized_name}\".")
    collection = database.Collection(client_id, sanitized_name)
    for file_path_posix in file_paths:
        file_path = str(file_path_posix)
        process_file(file_path, collection)


def add_file(client_id: str, file_path: str):
    name = os.path.split(file_path)[-1]
    sanitized_name = sanitize_table_name(name)
    collection = database.Collection(client_id, sanitized_name)
    process_file(file_path, collection)


def add_folder_or_file(client_id: str, folder_or_file: str):
    if os.path.isdir(folder_or_file):
        add_folder(client_id, folder_or_file)
        return
    if os.path.isfile(folder_or_file):
        add_file(client_id, folder_or_file)
        return
    raise FileExistsError(f"The path {folder_or_file} does not exist.") 