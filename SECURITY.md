# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.3.x | ✅ |
| < 0.3 | ❌ (pre-release, internal only) |

## Reporting a vulnerability

Please **do not** open a public issue for a security problem.

Use GitHub's private vulnerability reporting:

1. Go to the repository's **Security** tab.
2. Click **Report a vulnerability**.
3. Include: affected version, a minimal reproduction, and the impact you expect.

If private reporting is unavailable, contact the maintainers listed in
`pyproject.toml` and encrypt nothing sensitive in the first message — just ask
for a channel.

You can expect an acknowledgement within 7 days and a decision on a fix within
30 days. Reporters are credited in `CHANGELOG.md` unless they ask otherwise.

## Scope

Things this project treats as security issues:

* **Path traversal / arbitrary file write** — a config pointing `output`,
  `image`, `file` or `append_code_from_file.file` outside the intended tree, or a
  docx package entry name that escapes the zip root.
* **Arbitrary code execution** — a config path is executed as Python
  (`config_loader._load_python_mapping` uses `importlib`). Treat config files as
  code: never load a config from an untrusted source. If this becomes a problem,
  the `.py` config format is a candidate for removal.
* **Zip-slip / decompression bombs** in `read_document_xml` /
  `write_document_xml`.
* **XXE** — `xml.etree.ElementTree` is used; entity expansion is not enabled, but
  malformed XML from an untrusted `.docx` should be reported if it crashes the
  process.

## Out of scope

* A malicious `.docx` template causing Word/WPS to misbehave (that is a Word
  issue).
* PDF export via Word COM: results depend on the local Word installation.
* Anything requiring the attacker to already have write access to your config
  directory.
* Denial of service through deliberately huge images/documents.

## Hardening recommendations for users

* Run the tool on documents and configs you produced or trust.
* Prefer YAML/JSON configs over `.py` configs when the source is not trusted.
* Keep `Pillow`, `python-docx` and `PyYAML` up to date.
