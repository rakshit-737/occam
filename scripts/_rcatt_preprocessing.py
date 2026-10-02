"""Text clean-up from rcATT (vlegoy/rcATT @ f82f7fd, classification_tools/preprocessing.py).

Vendored (not downloaded and imported) so the reproduction runs reviewed code.
The regular expressions are kept as in the original, including its quirks
(several patterns run after lower-casing and so never match upper-case text),
because the point is to reproduce its behaviour.

MIT License -- Copyright (c) 2019 Valentine Legoy. Permission is hereby
granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions: The above copyright notice and this
permission notice shall be included in all copies or substantial portions of
the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
"""
from __future__ import annotations

import re

_SUBS = [
    ("\r\n", "\t"),
    (r"what's", "what is "),
    (r"\'s", " "),
    (r"\'ve", " have "),
    (r"can't", "can not "),
    (r"n't", " not "),
    (r"i'm", "i am "),
    (r"\'re", " are "),
    (r"\'d", " would "),
    (r"\'ll", " will "),
    (r"\'scuse", " excuse "),
    (r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.)\{3\}(?:25[0-5] |2[0-4][0-9]|[01]?[0-9][0-9]?)(/([0-2][0-9]|3[0-2]|[0-9]))?", "IPv4"),
    ("\b(CVE\\-[0-9]{4}\\-[0-9]{4,6})\b", "CVE"),
    ("\b([a-z][_a-z0-9-.]+@[a-z0-9-]+\\.[a-z]+)\b", "email"),
    ("\b(\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})\b", "IP"),
    ("\b([a-f0-9]{32}|[A-F0-9]{32})\b", "MD5"),
    ("\b((HKLM|HKCU)\\\\[\\\\A-Za-z0-9-_]+)\b", "registry"),
    ("\b([a-f0-9]{40}|[A-F0-9]{40})\b", "SHA1"),
    ("\b([a-f0-9]{64}|[A-F0-9]{64})\b", "SHA250"),
    ("http(s)?:\\\\[0-9a-zA-Z_\\.\\-\\\\]+.", "URL"),
    ("CVE-[0-9]{4}-[0-9]{4,6}", "vulnerability"),
    ("[a-zA-Z]{1}:\\\\[0-9a-zA-Z_\\.\\-\\\\]+", "file"),
    ("\b[a-fA-F\\d]{32}\b|\b[a-fA-F\\d]{40}\b|\b[a-fA-F\\d]{64}\b", "hash"),
    ("x[A-Fa-f0-9]{2}", " "),
    (r"\W", " "),
    (r"\s+", " "),
]


def clean_text(text) -> str:
    """rcATT's clean_text: lower-case, expand contractions, mask artefacts, drop non-word characters."""
    text = str(text).lower()
    for pat, rep in _SUBS:
        text = re.sub(pat, rep, text)
    return text.strip(" ")
