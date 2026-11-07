from fastapi import HTTPException

from src.library import list_sources


def check_scope(scope):
    if scope and scope not in list_sources():
        raise HTTPException(404, "That document is not in the library.")


