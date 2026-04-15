from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from src.review.pipeline import StructuredReviewExecutor

__all__ = ['StructuredReviewExecutor']


def __getattr__(name: str):
    if name == 'StructuredReviewExecutor':
        from src.review.pipeline import StructuredReviewExecutor
        return StructuredReviewExecutor
    raise AttributeError(name)
