from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_base_tokenizer(base: dict[str, Any], tokenizer: dict[str, Any]) -> None:
    if base.get("tokenizer_id") != tokenizer.get("tokenizer_id"):
        raise ValueError("base/tokenizer id mismatch")
    if base.get("tokenizer_version") != tokenizer.get("version"):
        raise ValueError("base/tokenizer version mismatch")
    if base.get("max_length") != tokenizer.get("max_length"):
        raise ValueError("base/tokenizer max_length mismatch")


def tokenize(text: Any, tokenizer: dict[str, Any]) -> list[int]:
    permissive = os.environ.get("MODERN_MODEL_BUG") == "invalid-input-coercion"
    if not isinstance(text, str):
        if permissive:
            text = str(text)
        else:
            raise ValueError("text must be a string")
    words = text.lower().split()
    if not words:
        raise ValueError("text must contain at least one token")
    if len(words) > int(tokenizer["max_length"]):
        raise ValueError("text exceeds max_length")
    vocab = tokenizer["vocab"]
    unknown = [word for word in words if word not in vocab]
    if unknown and not permissive:
        raise ValueError(f"unknown token(s): {', '.join(unknown)}")
    return [int(vocab.get(word, 0)) for word in words]


def attention(token_ids: list[int], base: dict[str, Any]) -> dict[str, list[list[float]]]:
    if not token_ids:
        raise ValueError("attention requires at least one token")
    if len(token_ids) > int(base["max_length"]):
        raise ValueError("token sequence exceeds base max_length")
    embeddings = base["embeddings"]
    try:
        vectors = [[float(value) for value in embeddings[str(token)]] for token in token_ids]
    except KeyError as exc:
        raise ValueError(f"token id missing from base model: {exc.args[0]}") from exc
    dimension = int(base["embedding_dim"])
    if any(len(vector) != dimension for vector in vectors):
        raise ValueError("embedding dimension mismatch")

    bug = os.environ.get("MODERN_MODEL_BUG")
    raw: list[list[float]] = []
    for row, query in enumerate(vectors):
        values: list[float] = []
        for column, key in enumerate(vectors):
            allowed = column <= row
            if bug == "causal-mask-reversal":
                allowed = column >= row
            score = sum(left * right for left, right in zip(query, key)) / math.sqrt(dimension)
            values.append(math.exp(score) if allowed else 0.0)
        raw.append(values)

    if bug == "wrong-softmax-axis":
        denominators = [sum(raw[row][column] for row in range(len(raw))) for column in range(len(raw))]
        weights = [
            [raw[row][column] / denominators[column] if denominators[column] else 0.0 for column in range(len(raw))]
            for row in range(len(raw))
        ]
    else:
        weights = []
        for row in raw:
            denominator = sum(row)
            if denominator <= 0.0:
                raise ValueError("attention row has no unmasked key")
            weights.append([value / denominator for value in row])

    context = [
        [sum(weights[row][column] * vectors[column][axis] for column in range(len(vectors))) for axis in range(dimension)]
        for row in range(len(vectors))
    ]
    return {"weights": weights, "context": context}


def sequence_feature(text: Any, tokenizer: dict[str, Any], base: dict[str, Any]) -> list[float]:
    token_ids = tokenize(text, tokenizer)
    contexts = attention(token_ids, base)["context"]
    return [sum(row[axis] for row in contexts) / len(contexts) for axis in range(len(contexts[0]))]


def sigmoid(logit: float) -> float:
    if logit >= 0:
        value = math.exp(-logit)
        return 1.0 / (1.0 + value)
    value = math.exp(logit)
    return value / (1.0 + value)


def probability(feature: list[float], adapter: dict[str, Any]) -> float:
    mode = adapter.get("mode")
    weights = [float(value) for value in adapter["head_weights"]]
    bias = float(adapter["head_bias"])
    if mode == "frozen":
        transformed = feature
    elif mode == "partial":
        scale = [float(value) for value in adapter["adapter_scale"]]
        shift = [float(value) for value in adapter["adapter_shift"]]
        transformed = [math.tanh(scale[index] * value + shift[index]) for index, value in enumerate(feature)]
    else:
        raise ValueError(f"unsupported adapter mode: {mode!r}")
    if len(weights) != len(transformed):
        raise ValueError("adapter/head dimension mismatch")
    return sigmoid(sum(weight * value for weight, value in zip(weights, transformed)) + bias)
