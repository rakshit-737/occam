import pytest

pytest.importorskip("sklearn")
from occam.classifier import TechniqueClassifier, split_sentences  # noqa: E402

TRAIN = [
    ("The actor sent spearphishing emails with malicious Word attachments.", {"T1566.001"}),
    ("Victims received phishing messages carrying a weaponized document attachment.", {"T1566.001"}),
    ("A malicious attachment was emailed to employees in a spearphishing campaign.", {"T1566.001"}),
    ("The ransomware encrypted files on every drive and demanded payment.", {"T1486"}),
    ("Files were encrypted for impact and a ransom note was dropped.", {"T1486"}),
    ("The malware encrypts user documents with AES and appends an extension.", {"T1486"}),
    ("PowerShell was used to download and execute the second stage.", {"T1059.001"}),
    ("The loader ran an encoded PowerShell command to fetch the payload.", {"T1059.001"}),
    ("Attackers executed PowerShell scripts for discovery.", {"T1059.001"}),
]


@pytest.fixture(scope="module")
def clf():
    texts, labels = zip(*TRAIN)
    return TechniqueClassifier(threshold=0.3, names={"T1486": "Data Encrypted for Impact"}).fit(texts, labels)


def test_split_sentences_offsets():
    text = "First sentence is long enough.  Second one is also long enough!"
    for s, e, sent in split_sentences(text):
        assert text[s:e] == sent


def test_predictions_and_span_anchored_hits(clf):
    assert set(clf.classes) == {"T1059.001", "T1486", "T1566.001"}
    text = "Intro text that says nothing at all. Then the ransomware encrypted files and demanded a ransom."
    hits = clf.hits(text, "doc")
    assert "T1486" in {h.technique_id for h in hits}
    for h in hits:
        assert text[h.span.start:h.span.end] == h.span.text
        assert h.matched.startswith("classifier p=")


def test_save_load_roundtrip(clf, tmp_path):
    p = tmp_path / "m.pkl"
    clf.save(p)
    again = TechniqueClassifier.load(p)
    assert again.predict(["files were encrypted by ransomware"]) == clf.predict(["files were encrypted by ransomware"])


def test_hits_top_k_limits_techniques():
    pytest.importorskip("sklearn")
    from occam.classifier import TechniqueClassifier

    texts = ["the actor used powershell scripts to run commands"] * 4 + ["keylogger captured keystrokes from users"] * 4 \
        + ["remote desktop protocol was used to move laterally"] * 4
    labels = [{"T1059.001"}] * 4 + [{"T1056.001"}] * 4 + [{"T1021.001"}] * 4
    clf = TechniqueClassifier(threshold=0.0).fit(texts, labels)
    doc = "The actor used powershell scripts. A keylogger captured keystrokes. Remote desktop protocol moved laterally."
    assert len(clf.hits(doc)) == 3
    assert len(clf.hits(doc, top_k=1)) == 1
    clf.top_k = 2
    assert len(clf.hits(doc)) == 2
