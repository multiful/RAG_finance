"""
로그 마스킹: API 키·토큰·비밀번호 등 민감 정보가 로그에 출력되지 않도록 필터.
"""
import re
import logging
from typing import Optional

# 마스킹할 패턴 (정규식). 매칭 시 앞뒤 4자만 노출하고 나머지는 *** 로.
SECRET_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'sk-proj-[a-zA-Z0-9\-_]{20,}', re.I), 'sk-proj-****'),
    (re.compile(r'eyJ[a-zA-Z0-9\-_\.]+\.eyJ[a-zA-Z0-9\-_\.]+\.[a-zA-Z0-9\-_\.]+', re.I), '***JWT***'),
    (re.compile(r'lsv2_pt_[a-zA-Z0-9_]+', re.I), 'lsv2_pt_****'),
    (re.compile(r'llx-[a-zA-Z0-9]+', re.I), 'llx-****'),
    (re.compile(r'redis://[^@\s]+@[^\s]+', re.I), 'redis://****@****'),
]

# 키=값 형태 (값만 마스킹)
SECRET_KEY_VALUE_PATTERN = re.compile(
    r'(api[_-]?key|password|secret|token)\s*[:=]\s*["\']?([^"\'&\s]{8,})', re.I
)
MASK_CHAR = "*"


def mask_secrets(message: str) -> str:
    """문자열 내 민감 패턴을 마스킹한 복사본 반환."""
    if not message or not isinstance(message, str):
        return message
    out = message
    for pattern, replacement in SECRET_PATTERNS:
        out = pattern.sub(replacement, out)

    def _repl(m: re.Match) -> str:
        prefix = m.group(1)
        val = m.group(2)
        if len(val) <= 8:
            masked = MASK_CHAR * len(val)
        else:
            masked = val[:2] + MASK_CHAR * (len(val) - 4) + val[-2:]
        return f"{prefix}={masked}"

    out = SECRET_KEY_VALUE_PATTERN.sub(_repl, out)
    return out


class SecretMaskingFilter(logging.Filter):
    """logging.Filter: LogRecord.msg와 args 내 문자열을 마스킹."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = mask_secrets(str(record.msg))
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: mask_secrets(str(v)) if isinstance(v, str) else v for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(mask_secrets(str(a)) if isinstance(a, str) else a for a in record.args)
        except Exception:
            pass
        return True


def install_log_masking(logger: Optional[logging.Logger] = None) -> None:
    """루트 로거 또는 지정 로거에 SecretMaskingFilter 추가."""
    target = logger or logging.getLogger()
    if not any(isinstance(f, SecretMaskingFilter) for f in target.filters):
        target.addFilter(SecretMaskingFilter())
